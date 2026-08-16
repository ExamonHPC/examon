#!flask/bin/python
from flask import Flask, jsonify, request, abort, Response

from cassandra.cluster import Cluster, OperationTimedOut, NoHostAvailable
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import ExponentialReconnectionPolicy
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

import time


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


def get_jobs(stmt, fetch_size=20000, max_retries=3):  # Set a default fetch size
    """Execute query with automatic retry on connection failures."""
    
    df = pd.DataFrame()
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Set the fetch size for the query
            statement = session.execute(stmt, timeout=120.0)
            statement.fetch_size = fetch_size
            for page in statement:
                df = pd.concat([df, pd.DataFrame(page)], ignore_index=True)
            logger.info('QUERYBUILDER: Number of records: %s', str(len(df)))
            return df
            
        except (OperationTimedOut, NoHostAvailable) as e:
            last_exception = e
            logger.warning(f'Connection issue during query execution (attempt {attempt + 1}/{max_retries}): {e}')
            
            if attempt < max_retries - 1:
                # Short delay before retry to allow driver reconnection
                time.sleep(1)
                continue
            else:
                logger.error(f'Query failed after {max_retries} attempts due to connection issues')
                raise
        except Exception as e:
            # For non-connection related errors, don't retry
            logger.error(f'Query failed with non-connection error: {e}')
            raise


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

def _read_platform_version():
    """Read the platform release version from the root VERSION file.

    Looks next to this file first (standalone image bakes it in /app),
    then two levels up (repo root / legacy image EXAMON_HOME).
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.path.join(base_dir, 'VERSION'),
                      os.path.abspath(os.path.join(base_dir, '..', '..', 'VERSION'))):
        try:
            with open(candidate) as f:
                version = f.read().strip()
                return version[1:] if version.startswith('v') else version
        except (IOError, OSError):
            continue
    return 'unknown'


PLATFORM_VERSION = _read_platform_version()


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'platform_version': PLATFORM_VERSION}), 200


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
        df_json = get_jobs(stmt, max_retries=5).to_json(date_format='iso', orient='records')
    except Exception as e:
        logger.error('QUERY: %s', stmt)
        import traceback
        print(traceback.format_exc())
        
        # Check if it's a connection-related error
        if isinstance(e, (OperationTimedOut, NoHostAvailable)):
            logger.error('CASSANDRA CONNECTION: %s', str(e))
            return jsonify({'error': 'Database temporarily unavailable, please try again later'}), 503
        
        # Handle other errors
        if hasattr(e, 'message'):
            logger.error('CASSANDRA: %s', e.message)
            return jsonify({'error': e.message}), 400
        else:
            logger.error('QUERY: Unexpected error: %s', str(e))
            return jsonify({'error': 'Query execution failed'}), 400
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
        
        # Check if it's a connection-related error
        if isinstance(e, (OperationTimedOut, NoHostAvailable)):
            logger.error('CASSANDRA CONNECTION: %s', str(e))
            return jsonify({'error': 'Database temporarily unavailable, please try again later'}), 503
        
        # Handle other errors
        if hasattr(e, 'message'):
            logger.error('CASSANDRA: %s', e.message)
            return jsonify({'error': e.message}), 400
        else:
            logger.error('QUERY: Unexpected error: %s', str(e))
            return jsonify({'error': 'Query execution failed'}), 400
    logger.info('QUERY: response: 200')
    logger.debug('QUERY: response: %s', json.dumps(df_json, indent=4))
    #return jsonify(json.loads(df_json)), 200
    return Response(df_json, mimetype='application/json')


def connect_to_cassandra_with_retry(cassandra_ip, cassandra_user, cassandra_passw, cassandra_keyspace, max_retries=30, initial_delay=1, max_delay=60):
    """Connect to Cassandra with retry logic and exponential backoff.

    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to Cassandra (attempt {attempt + 1}/{max_retries})...")
            
            c_auth = PlainTextAuthProvider(username=cassandra_user, password=cassandra_passw)
            cluster = Cluster(contact_points=(cassandra_ip,), auth_provider=c_auth, reconnection_policy=ExponentialReconnectionPolicy(base_delay=1, max_delay=60))
            session = cluster.connect(cassandra_keyspace)
            
            logger.info("Successfully connected to Cassandra")
            return cluster, session
            
        except Exception as e:
            last_exception = e
            logger.warning(f"Failed to connect to Cassandra (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                
                # Exponential backoff with max limit
                delay = min(delay * 2, max_delay)
    
    # If we get here, all retries failed
    logger.error(f"Failed to connect to Cassandra after {max_retries} attempts")
    raise last_exception


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
    CASSANDRA_USER = os.environ.get('CASSANDRA_USER') or config.get('Server', 'CASSANDRA_USER')
    CASSANDRA_PASSW = os.environ.get('CASSANDRA_PASSWORD') or config.get('Server', 'CASSANDRA_PASSW')
    EXAMON_SERVER_HOST = config.get('Server', 'EXAMON_SERVER_HOST')
    EXAMON_SERVER_PORT = int(config.get('Server', 'EXAMON_SERVER_PORT'))
    THREADS_NUM = int(config.get('Server', 'THREADS_NUM'))  
    


    # Load scheduler type (SLURM or PBS)
    SCHEDULER_TYPE = str(config.get('Server', 'SCHEDULER_TYPE', fallback='SLURM'))
    logger.info("Starting examon server with scheduler type: %s", SCHEDULER_TYPE)

    # Connect to Cassandra with retry logic
    cluster, session = connect_to_cassandra_with_retry(
        cassandra_ip=CASSANDRA_IP,
        cassandra_user=CASSANDRA_USER,
        cassandra_passw=CASSANDRA_PASSW,
        cassandra_keyspace=CASSANDRA_KEY_SPACE
    )
    queries = {}

    # setup cassandra row factory
    session.row_factory = pandas_factory
    # run
    serve(app, host=EXAMON_SERVER_HOST, port=EXAMON_SERVER_PORT, threads=THREADS_NUM)
