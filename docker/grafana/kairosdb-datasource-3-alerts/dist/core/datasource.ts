import _ from "lodash";
import {TemplatingFunction} from "../beans/function";
import {LegacyTargetConverter} from "../beans/request/legacy_target_converter";
import {TemplatingFunctionsCtrl} from "../controllers/templating_functions_ctrl";
import {PromiseUtils} from "../utils/promise_utils";
import {TemplatingFunctionResolver} from "../utils/templating_function_resolver";
import {TemplatingUtils} from "../utils/templating_utils";
import {MetricNamesStore} from "./metric_names_store";
import {KairosDBQueryBuilder} from "./request/query_builder";
import {TargetValidator} from "./request/target_validator";
import {KairosDBResponseHandler} from "./response/response_handler";
import {SeriesNameBuilder} from "./response/series_name_builder";

export class KairosDBDatasource {
    public initialized: boolean = false;
    public initializationError: boolean = false;
    public metricNamesStore: MetricNamesStore;
    private type: string;
    private url: string;
    private withCredentials: boolean;
    private name: string;
    private basicAuth: string;
    private responseHandler: KairosDBResponseHandler;
    private templatingFunctionsCtrl: TemplatingFunctionsCtrl;
    private promiseUtils: PromiseUtils;
    private targetValidator: TargetValidator;
    private backendSrv: any;
    private templateSrv: any;
    private legacyTargetConverter: LegacyTargetConverter;
    private templatingUtils: TemplatingUtils;
    private queryOptions: any;

    constructor(instanceSettings, $q, backendSrv, templateSrv) {
        this.type = instanceSettings.type;
        this.url = instanceSettings.url;
        this.name = instanceSettings.name;
        this.withCredentials = instanceSettings.withCredentials;
        this.basicAuth = instanceSettings.basicAuth;
        this.backendSrv = backendSrv;
        this.templateSrv = templateSrv;
        this.responseHandler = new KairosDBResponseHandler(new SeriesNameBuilder());
        this.promiseUtils = new PromiseUtils($q);
        this.metricNamesStore = new MetricNamesStore(this, this.promiseUtils, this.url);
        this.templatingUtils = new TemplatingUtils(templateSrv, {});
        this.templatingFunctionsCtrl = new TemplatingFunctionsCtrl(new TemplatingFunctionResolver(this.templatingUtils));
        this.targetValidator = new TargetValidator();
        this.legacyTargetConverter = new LegacyTargetConverter();
        this.registerTemplatingFunctions();
    }

    public initialize(): Promise<boolean> {
        return this.metricNamesStore.getMetricNames().then(
            () => this.initialized = true,
            () => this.initializationError = true
        ).then(() => this.initialized);
    }

    public query(options) {
        this.queryOptions = options;
        const enabledTargets = _.cloneDeep(options.targets.filter((target) => !target.hide));
        const convertedTargets = _.map(enabledTargets, (target) => {
            return this.legacyTargetConverter.isApplicable(target) ?
                {query: this.legacyTargetConverter.convert(target)} : target;
        });

        if (!this.targetValidator.areValidTargets(convertedTargets)) {
            return; // todo: target validation, throw message to grafana with detailed info
        }
        const aliases = convertedTargets.map((target) => target.query.alias);
        const templatingUtils = this.templateSrv;
        const unpackedTargets = _.flatten(convertedTargets.map((target) => {
            const replacedQuery = templatingUtils.replace(JSON.stringify(target.query), options.scopedVars);
            return [JSON.parse(replacedQuery)].map((query) => {
                const clonedTarget = _.cloneDeep(target);
                clonedTarget.query  = query;
                return clonedTarget;
            });
        }));
        const requestBuilder = this.getRequestBuilder(options.scopedVars);
        return this.executeRequest(requestBuilder.buildDatapointsQuery(unpackedTargets, options))
            .then((response) => this.responseHandler.convertToDatapoints(response.data, aliases));
    }

    public getMetricTags(metricNameTemplate, filters = {}) {
        const metricName = this.templatingUtils.replace(metricNameTemplate)[0];
        return this.executeRequest(this.getRequestBuilder().buildMetricTagsQuery(metricName, filters))
            .then(this.handleMetricTagsResponse);
    }

    public metricFindQuery(query: string, options) {
        const func = this.templatingFunctionsCtrl.resolve(query, options.scopedVars);
        return func().then((values) => values.map((value) => this.mapToTemplatingValue(value)));
    }

    public getMetricNames() {
        return this.executeRequest(this.getRequestBuilder().buildMetricNameQuery());
    }

    public testDatasource() {
        return this.executeRequest(this.getRequestBuilder().buildHealthCheckQuery());
    }

    private getRequestBuilder(scopedVars: any = {}): KairosDBQueryBuilder {
        return new KairosDBQueryBuilder(this.withCredentials, this.url, "/api/v1", this.templateSrv, scopedVars);
    }

    private executeRequest(request) {
        return this.backendSrv.datasourceRequest(request);
    }

    private handleMetricTagsResponse(response): Map<string, Set<string>> {
        return response.data.queries[0].results[0].tags;
    }

    private registerTemplatingFunctions(): void {
        [
            new TemplatingFunction("metrics",
                (metricNamePart) => this.getMetricNamesContaining(metricNamePart)),
            new TemplatingFunction("tag_names", this.getMetricTagNames.bind(this)),
            new TemplatingFunction("tag_values", this.getMetricTagValues.bind(this))
        ].forEach((func) => this.templatingFunctionsCtrl.register(func));
    }

    private getMetricNamesContaining(metricNamePart) {
        return this.metricNamesStore.getMetricNames()
            .then((metricNames) => _.filter(metricNames, (metricName) => _.includes(metricName, metricNamePart)));
    }

    private getMetricTagNames(metricName) {
        return this.getMetricTags(metricName)
            .then((tags) => _.keys(tags));
    }

    private getMetricTagValues(metricName: string, tagName: string, filters: any) {
        return this.getMetricTags(metricName, filters)
            .then((tags) => {
                return _.values(tags[tagName]);
            });
    }

    private mapToTemplatingValue(entry) {
        return {
            text: entry,
            value: entry
        };
    }
}
