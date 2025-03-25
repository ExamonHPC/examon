FROM cassandra:3.0.19

COPY cassandra.yaml /etc/cassandra/cassandra.yaml
RUN chown -R cassandra:cassandra /etc/cassandra/cassandra.yaml && \
    chmod 644 /etc/cassandra/cassandra.yaml
