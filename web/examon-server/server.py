#!flask/bin/python
from flask import Flask, jsonify, request, abort, Response

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
from cassandra.util import OrderedMapSerializedKey

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

import ConfigParser


LOGFILE_SIZE_B = 5*1024*1024
LOG_LEVEL = logging.INFO
LOGFILE = 'server.log'


app = Flask(__name__,
            static_url_path='', 
            static_folder='static/docs/html')
# enable gzipped responses
gzip = Gzip(app)
# enable basic auth
auth = HTTPBasicAuth()

""" #conf = json.load(open('conf.json'))
c_auth = PlainTextAuthProvider(username=CASSANDRA_USER, password=CASSANDRA_PASSW)
cluster = Cluster(contact_points=(CASSANDRA_IP,), auth_provider = c_auth)
session = cluster.connect(CASSANDRA_KEY_SPACE)
queries = {} """


@auth.verify_password
def verify_password(username, password):
    ret = req.get(AUTH_URL, auth=RHTTPBasicAuth(username, password))
    logger.info('USER: %s ret: %s' % (username,str(ret.status_code),))
    if ret.status_code == 200:
        return True
    else:
        return False

def get_prep_query(session, stmt):
    global queries
    query = queries.get(stmt)
    if query is None:
       query = session.prepare(stmt)
       queries[stmt]=query
    return query


def pandas_factory(colnames, rows):

    # Convert tuple items of 'rows' into list (elements of tuples cannot be replaced)
    rows = [list(i) for i in rows]
    # Convert only 'OrderedMapSerializedKey' type list elements into dict
    for idx_row, i_row in enumerate(rows):
        for idx_value, i_value in enumerate(i_row):
            if type(i_value) is OrderedMapSerializedKey:
                rows[idx_row][idx_value] = dict(rows[idx_row][idx_value])
    return [pd.DataFrame(rows, columns=colnames)]



def get_jobs(stmt):
    df = pd.DataFrame()
    for page in session.execute(stmt, timeout=120.0):
        df = df.append(page, ignore_index=True)
    return df


def qb_get_tables(query):
    tables = ''
    if query['metrics']:
        tables = ','.join(query['metrics'])
    return tables

def qb_get_columns(query):
    columns = '*'
    if query['groupby']:
        if type(query['groupby']) == list:
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

def qb_get_where(query):
    _where = ''
    if query['tags'] and (len(query['tags']) > 0):
        for k,v in query['tags'].iteritems():
            for i in v:
                _where += ' AND '
                if k.lower() in ['user_id','job_id']:
                    _where += "{} = {}".format(str(k),str(i))
                elif k == 'node':
                    _where += "cpus_alloc_layout CONTAINS KEY '{}'".format(str(i))
                else:
                    _where += "{} = '{}'".format(str(k),str(i))
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
    """build a cassandra query.

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
        cass_query += '(start_time, end_time) >= ' + "({},{})".format(tstart, tstart)
    if qb_get_tstop(query):
        tstop = qb_get_tstop(query)
        cass_query += ' AND '
        cass_query += '(start_time, end_time) <= ' + "({},{})".format(tstop, tstop)
    if qb_get_where(query):
        cass_query += qb_get_where(query)
    if qb_get_limit(query):
        cass_query += ' LIMIT '
        cass_query += qb_get_limit(query)
    cass_query += ' ALLOW FILTERING'
    return cass_query

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
    logger.info('QUERY: Received query: %s' % (query,))
    try:
        stmt = query_builder(query)
        logger.info('QUERYBUILDER: %s' % (stmt,))
        df_json = get_jobs(stmt).to_json(date_format='iso', orient='records')
    except Exception as e:
        logger.error('QUERY: %s' % (stmt,))
        import traceback
        print traceback.format_exc()
        if hasattr(e, 'message'):
            logger.error('CASSANDRA: %s' % (e.message,))
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
    logger.info('QUERY: Received query: %s' % (query,))
    try:
        stmt = query_builder(query)
        logger.info('QUERYBUILDER: %s' % (stmt,))
        df_ = get_jobs(stmt)
        logger.info('QUERYBUILDER: Number of records: %s' % (str(len(df_)),))
        #logger.info('energy type: %s' % (df_['energy'].dtype,))
        if 'energy' in df_:
            df_['energy'] = df_['energy'].apply(lambda x: json.loads(x) if not pd.isnull(x) else {})
        df_json = df_.to_json(date_format='iso', orient='records')
    except Exception as e:
        logger.error('QUERY: %s' % (stmt,))
        import traceback
        print traceback.format_exc()
        if hasattr(e, 'message'):
            logger.error('CASSANDRA: %s' % (e.message,))
            return jsonify(e.message), 400
        abort(400)
    logger.info('QUERY: response: 200')
    #return jsonify(json.loads(df_json)), 200
    return Response(df_json, mimetype='application/json')

if __name__ == '__main__':

    # Load Config.
    config = ConfigParser.RawConfigParser()
    config.read('server.conf')
    AUTH_URL = config.get('Server', 'AUTH_URL')
    CASSANDRA_IP = config.get('Server', 'CASSANDRA_IP')
    CASSANDRA_KEY_SPACE = config.get('Server', 'CASSANDRA_KEY_SPACE')
    CASSANDRA_USER = config.get('Server', 'CASSANDRA_USER')
    CASSANDRA_PASSW = config.get('Server', 'CASSANDRA_PASSW')
    EXAMON_SERVER_HOST = config.get('Server', 'EXAMON_SERVER_HOST')
    EXAMON_SERVER_PORT = int(config.get('Server', 'EXAMON_SERVER_PORT'))

    # logging
    logger = logging.getLogger("waitress")
    handler = RotatingFileHandler(LOGFILE, mode='a', maxBytes=LOGFILE_SIZE_B, backupCount=2)
    log_formatter = logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)
    logger.setLevel(LOG_LEVEL)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(log_formatter)
    logger.addHandler(handler) 

    #conf = json.load(open('conf.json'))
    c_auth = PlainTextAuthProvider(username=CASSANDRA_USER, password=CASSANDRA_PASSW)
    cluster = Cluster(contact_points=(CASSANDRA_IP,), auth_provider = c_auth)
    session = cluster.connect(CASSANDRA_KEY_SPACE)
    queries = {}

    # setup cassandra row factory
    session.row_factory = pandas_factory
    # run
    serve(app, host=EXAMON_SERVER_HOST, port=EXAMON_SERVER_PORT, threads=8)
