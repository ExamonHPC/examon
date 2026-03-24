FROM eclipse-temurin:17-jre

ENV KAIROSDB_VERSION=1.3.0

RUN apt-get update && apt-get install -y --no-install-recommends \
        wget curl \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q "https://github.com/kairosdb/kairosdb/releases/download/v${KAIROSDB_VERSION}/kairosdb_${KAIROSDB_VERSION}-1_all.deb" \
    && dpkg -i "kairosdb_${KAIROSDB_VERSION}-1_all.deb" \
    && rm "kairosdb_${KAIROSDB_VERSION}-1_all.deb"

COPY kairosdb.properties /opt/kairosdb/conf/kairosdb.properties
COPY kairosdb-env.sh /opt/kairosdb/bin/kairosdb-env.sh
COPY config-kairos.sh /usr/bin/config-kairos.sh
RUN chmod +x /usr/bin/config-kairos.sh

EXPOSE 4242 8083 2003

CMD ["/usr/bin/config-kairos.sh"]
