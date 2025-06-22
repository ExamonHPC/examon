# VERSION   1.2.2

FROM adoptopenjdk:8-jre-hotspot-focal

# Create a backup of the existing sources.list
#RUN mv /etc/apt/sources.list /etc/apt/sources.list.backup

# Create a new sources.list file
#RUN touch /etc/apt/sources.list

# Add the new server repository for focal packages
#RUN echo "deb https://ubuntu.mirror.garr.it/ubuntu/ focal main" > /etc/apt/sources.list

RUN set -eux; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		wget \
                ca-certificates \
	; \
	rm -rf /var/lib/apt/lists/*

# KairosDB

ENV KAIROSDB_VERSION 1.2.2

RUN wget https://github.com/kairosdb/kairosdb/releases/download/v${KAIROSDB_VERSION}/kairosdb_${KAIROSDB_VERSION}-1_all.deb
RUN dpkg -i kairosdb_${KAIROSDB_VERSION}-1_all.deb
RUN rm kairosdb_${KAIROSDB_VERSION}-1_all.deb

ADD kairosdb.properties /opt/kairosdb/conf/kairosdb.properties
ADD kairosdb-env.sh /opt/kairosdb/bin/kairosdb-env.sh

EXPOSE 4242 8083 2003

ADD config-kairos.sh /usr/bin/config-kairos.sh
RUN chmod +x /usr/bin/config-kairos.sh

# Run kairosdb in foreground on boot
CMD ["/usr/bin/config-kairos.sh"]
