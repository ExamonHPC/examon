#!flask/bin/python
from flask import Flask, jsonify, request, abort, Response

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
from cassandra.util import OrderedMapSerializedKey

import os
import sys
import json
import pandas as pd
from waitress import serve
from flask_httpauth import HTTPBasicAuth

import requests as req
from requests.auth import HTTPBasicAuth as RHTTPBasicAuth

from flask_gzip import Gzip

import logging
from logging.handlers import RotatingFileHandler

import configparser
from flask_caching import Cache


LOGFILE_SIZE_B = 5 * 1024 * 1024
LOG_LEVEL = logging.INFO
LOGFILE = 'server.log'


app = Flask(__name__,
           static_url_path='',
           static_folder='static/docs/html')
# enable gzipped responses
gzip = Gzip(app)
# enable basic auth
auth = HTTPBasicAuth()

# Configure Flask-Caching
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',  # Use in-memory cache
    'CACHE_DEFAULT_TIMEOUT': 18000  # 300 minutes
})


@auth.verify_password
@cache.memoize()
def verify_password(username, password):
    ret = req.get(AUTH_URL, auth=RHTTPBasicAuth(username, password))
    logger.info('USER: %s ret: %s', username, str(ret.status_code))
    if ret.status_code == 200:
        return True
    return False


def get_prep_query(session, stmt):
    global queries
    query = queries.get(stmt)
    if query is None:
        query = session.prepare(stmt)
        queries[stmt] = query
    return query


def pandas_factory(colnames, rows):
    # Convert tuple items of 'rows' into list (elements of tuples cannot be replaced)
    rows = [list(i) for i in rows]
    # Convert only 'OrderedMapSerializedKey' type list elements into dict
    for idx_row, i_row in enumerate(rows):
        for idx_value, i_value in enumerate(i_row):
            if isinstance(i_value, OrderedMapSerializedKey):
                rows[idx_row][idx_value] = dict(rows[idx_row][idx_value])
    df = pd.DataFrame(rows, columns=colnames)
    df = localize_timestamps(df, 'UTC')
    return [df]


def get_jobs(stmt, fetch_size=20000):  # Set a default fetch size
    df = pd.DataFrame()
    # Set the fetch size for the query
    statement = session.execute(stmt, timeout=120.0)
    statement.fetch_size = fetch_size
    for page in statement:
        df = pd.concat([df, pd.DataFrame(page)], ignore_index=True)
    logger.info('QUERYBUILDER: Number of records: %s', str(len(df)))
    return df


def qb_get_tables(query):
    tables = ''
    if query['metrics']:
        tables = ','.join(query['metrics'])
    return tables


def qb_get_columns(query):
    columns = '*'
    if query['groupby']:
        if isinstance(query['groupby'], list):
            if len(query['groupby'][0]['tags']) > 0:
                columns = ','.join(query['groupby'][0]['tags'])
            else:
                columns = '*'
        else:
            if len(query['groupby']['tags']) > 0:
                columns = ','.join(query['groupby']['tags'])
            else:
                columns = '*'
    return columns


def qb_get_aggrby(query):
    aggrby = ''
    if query.get('aggrby') and len(query['aggrby']) > 0:
        aggrby = str(query['aggrby'][0]['name'])
    return aggrby


def qb_get_where(query):
    _where = ''
    if query['tags'] and (len(query['tags']) > 0):
        for k, v in query['tags'].items():
            for i in v:
                _where += ' AND '
                # Different handling based on scheduler
                if SCHEDULER_TYPE == 'SLURM':
                    if k in ['user_id', 'job_id']:
                        _where += "{} = {}".format(str(k), str(i))
                    elif k == 'node':
                        _where += "cpus_alloc_layout CONTAINS KEY '{}'".format(str(i))
                    else:
                        _where += "{} = '{}'".format(str(k), str(i))
                else:  # PBS
                    if k.lower() in ['user_id', 'exit_status']:
                        _where += "{} = {}".format(str(k), str(i))
                    elif k == 'node':
                        _where += "cpus_alloc_layout CONTAINS KEY '{}'".format(str(i))
                    else:
                        _where += "{} = '{}'".format(str(k), str(i))
    return _where


def qb_get_tstart(query):
    tstart = ''
    if query['tstart']:
        tstart = query['tstart']
    return tstart


def qb_get_tstop(query):
    tstop = ''
    if query['tstop']:
        tstop = query['tstop']
    return tstop


def qb_get_limit(query):
    limit = ''
    if query['limit']:
        limit = str(query['limit'])
    return limit


def query_builder(query):
    """Build a cassandra query.

    Receive a serialized Query object and return a CQL query statement
    """
    cass_query = 'SELECT '
    if qb_get_columns(query):
        cass_query += qb_get_columns(query)
    if qb_get_tables(query):
        cass_query += ' FROM '
        cass_query += qb_get_tables(query)
    if qb_get_tstart(query):
        tstart = qb_get_tstart(query)
        cass_query += ' WHERE '

        aggrby = qb_get_aggrby(query)
        if SCHEDULER_TYPE == 'SLURM':
            if aggrby == 'started':
                cass_query += 'start_time >= ' + "{}".format(tstart)  # return started job between dates
            else:
                cass_query += '(start_time, end_time) >= ' + "({},{})".format(tstart, tstart)
        else:  # PBS
            if aggrby == 'started':
                cass_query += 'stime >= ' + "{}".format(tstart)  # return started job between dates
            else:
                cass_query += '(stime, mtime) >= ' + "({},{})".format(tstart, tstart)  # executed job between dates

    if qb_get_tstop(query):
        tstop = qb_get_tstop(query)
        cass_query += ' AND '

        aggrby = qb_get_aggrby(query)
        if SCHEDULER_TYPE == 'SLURM':
            if aggrby == 'started':
                cass_query += 'start_time <= ' + "{}".format(tstop)  # return started job between dates
            else:
                cass_query += '(start_time, end_time) <= ' + "({},{})".format(tstop, tstop)
        else:  # PBS
            if aggrby == 'started':
                cass_query += 'stime <= ' + "{}".format(tstop)  # return started job between dates
            else:
                cass_query += '(stime, mtime) <= ' + "({},{})".format(tstop, tstop)  # executed job between dates

    if qb_get_where(query):
        cass_query += qb_get_where(query)
    if qb_get_limit(query):
        cass_query += ' LIMIT '
        cass_query += qb_get_limit(query)
    cass_query += ' ALLOW FILTERING'
    return cass_query

def localize_timestamps(df, tz):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # If the column is naive, localize it to UTC
            if df[col].dt.tz is None:
                df[col] = df[col].dt.tz_localize(tz)
            # If the column has a timezone, convert it to UTC
            else:
                df[col] = df[col].dt.tz_convert(tz)
    return df

@app.route('/')
@auth.login_required
def index():
    return "Examon Server"


@app.route('/docs')
@app.route('/<path:path>')
@auth.login_required
def serve_sphinx_docs(path='index.html'):
    return app.send_static_file(path)


@app.route('/api/v1/examon/jobs/query', methods=['POST'])
@auth.login_required
def get_jobs_test():
    if not request.json:
        logger.error('QUERY: No payload. Response: 400')
        abort(400)
    query = json.loads(request.json)
    logger.info('QUERY: Received query: %s', query)
    try:
        stmt = query_builder(query)
        logger.info('QUERYBUILDER: %s', stmt)
        df_json = get_jobs(stmt).to_json(date_format='iso', orient='records')
    except Exception as e:
        logger.error('QUERY: %s', stmt)
        import traceback
        print(traceback.format_exc())
        if hasattr(e, 'message'):
            logger.error('CASSANDRA: %s', e.message)
            return jsonify(e.message), 400
            logger.error('QUERY: response: 400')
        abort(400)
    logger.info('QUERY: response: 200')
    return jsonify(df_json), 200


@app.route('/api/v2/examon/jobs/query', methods=['POST'])
@auth.login_required
def get_jobs_test_v2():
    if not request.json:
        logger.error('QUERY: No payload. Response: 400')
        abort(400)
    query = request.json
    logger.info('QUERY: Received query: %s', query)
    try:
        stmt = query_builder(query)
        logger.info('QUERYBUILDER: %s', stmt)
        df_ = get_jobs(stmt)
        if 'energy' in df_:
            df_['energy'] = df_['energy'].apply(lambda x: json.loads(x) if not pd.isnull(x) else {})
        df_json = df_.to_json(date_format='iso', orient='records')
    except Exception as e:
        logger.error('QUERY: %s', stmt)
        import traceback
        print(traceback.format_exc())
        if hasattr(e, 'message'):
            logger.error('CASSANDRA: %s', e.message)
            return jsonify(e.message), 400
        abort(400)
    logger.info('QUERY: response: 200')
    logger.debug('QUERY: response: %s', json.dumps(df_json, indent=4))
    #return jsonify(json.loads(df_json)), 200
    return Response(df_json, mimetype='application/json')


if __name__ == '__main__':
    # logging
    logger = logging.getLogger("waitress")
    handler = RotatingFileHandler(LOGFILE, mode='a', maxBytes=LOGFILE_SIZE_B, backupCount=2)
    log_formatter = logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                    datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)
    logger.setLevel(LOG_LEVEL)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)

    # Check if configuration file exists
    if not os.path.isfile('server.conf'):
        logger.error("Configuration file 'server.conf' not found. Please install the workload scheduler plugin and configure the server.conf file.")
        sys.exit(1)

    # Load Config.
    config = configparser.RawConfigParser()
    config.read('server.conf')

    # Check if keyspace is defined
    if not config.has_option('Server', 'CASSANDRA_KEY_SPACE') or not config.get('Server', 'CASSANDRA_KEY_SPACE'):
        logger.error("CASSANDRA_KEY_SPACE is not defined in the configuration file.")
        sys.exit(1)

    AUTH_URL = config.get('Server', 'AUTH_URL')
    CASSANDRA_IP = config.get('Server', 'CASSANDRA_IP')
    CASSANDRA_KEY_SPACE = config.get('Server', 'CASSANDRA_KEY_SPACE')
    CASSANDRA_USER = config.get('Server', 'CASSANDRA_USER')
    CASSANDRA_PASSW = config.get('Server', 'CASSANDRA_PASSW')
    EXAMON_SERVER_HOST = config.get('Server', 'EXAMON_SERVER_HOST')
    EXAMON_SERVER_PORT = int(config.get('Server', 'EXAMON_SERVER_PORT'))
    THREADS_NUM = int(config.get('Server', 'THREADS_NUM'))  
    


    # Load scheduler type (SLURM or PBS)
    SCHEDULER_TYPE = str(config.get('Server', 'SCHEDULER_TYPE', fallback='SLURM'))
    logger.info("Starting examon server with scheduler type: %s", SCHEDULER_TYPE)

    c_auth = PlainTextAuthProvider(username=CASSANDRA_USER, password=CASSANDRA_PASSW)
    cluster = Cluster(contact_points=(CASSANDRA_IP,), auth_provider=c_auth)
    session = cluster.connect(CASSANDRA_KEY_SPACE)
    queries = {}

    # setup cassandra row factory
    session.row_factory = pandas_factory
    # run
    serve(app, host=EXAMON_SERVER_HOST, port=EXAMON_SERVER_PORT, threads=THREADS_NUM)
