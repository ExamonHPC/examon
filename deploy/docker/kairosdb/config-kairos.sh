#!/bin/bash

if [[ -z "$CASSANDRA_HOST_LIST" ]]; then
    export CASSANDRA_HOST_LIST=127.0.0.1:9042
fi
if [[ -z "$KAIROS_JETTY_PORT" ]]; then
    export KAIROS_JETTY_PORT=8083
fi

# Legacy .properties file
sed -i "s/^kairosdb.jetty.port.*$/kairosdb.jetty.port=$KAIROS_JETTY_PORT/" /opt/kairosdb/conf/kairosdb.properties
sed -i "s/^kairosdb.datastore.cassandra.cql_host_list.*$/kairosdb.datastore.cassandra.cql_host_list=$CASSANDRA_HOST_LIST/" /opt/kairosdb/conf/kairosdb.properties

# HOCON .conf file (KairosDB 1.3.0+) — extract host without port for the JSON list
CASS_HOST=$(echo "$CASSANDRA_HOST_LIST" | sed 's/:.*$//')
sed -i "s|cql_host_list: \[\"localhost\"\]|cql_host_list: [\"${CASS_HOST}\"]|g" /opt/kairosdb/conf/kairosdb.conf

# Cassandra authentication (K8ssandra enables auth by default)
if [[ -n "$CASSANDRA_USER" && -n "$CASSANDRA_PASSWORD" ]]; then
    sed -i "s|^kairosdb.datastore.cassandra.auth.user_name=.*|kairosdb.datastore.cassandra.auth.user_name=$CASSANDRA_USER|" /opt/kairosdb/conf/kairosdb.properties
    sed -i "s|^kairosdb.datastore.cassandra.auth.password=.*|kairosdb.datastore.cassandra.auth.password=$CASSANDRA_PASSWORD|" /opt/kairosdb/conf/kairosdb.properties
    # Uncomment and set auth in HOCON config
    sed -i "s|#auth.user_name=.*|auth.user_name=$CASSANDRA_USER|" /opt/kairosdb/conf/kairosdb.conf
    sed -i "s|#auth.password=.*|auth.password=$CASSANDRA_PASSWORD|" /opt/kairosdb/conf/kairosdb.conf
fi

/opt/kairosdb/bin/kairosdb.sh run

