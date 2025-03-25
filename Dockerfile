FROM examonhpc/examon:0.2.0

ENV EXAMON_HOME /etc/examon_deploy/examon

# Create a backup of the existing sources.list
RUN mv /etc/apt/sources.list /etc/apt/sources.list.backup

# Create a new sources.list file
RUN touch /etc/apt/sources.list

# Debian strech moved to archived
RUN echo "deb https://debian.mirror.garr.it/debian-archive/ stretch main" > /etc/apt/sources.list

# Install dependencies
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    libffi-dev \
    build-essential \
    libssl-dev \
    python-dev \
	&& rm -rf /var/lib/apt/lists/*

# copy app
ADD ./publishers/random_pub ${EXAMON_HOME}/publishers/random_pub
ADD ./lib/examon-common $EXAMON_HOME/lib/examon-common
ADD ./docker/examon/supervisor.conf /etc/supervisor/conf.d/supervisor.conf
ADD ./scripts/examon.conf $EXAMON_HOME/scripts/examon.conf
ADD ./web $EXAMON_HOME/web

# install
RUN pip --trusted-host pypi.python.org install --upgrade pip==20.1.1
ENV PIP $EXAMON_HOME/scripts/ve/bin/pip

WORKDIR $EXAMON_HOME/lib/examon-common
RUN $PIP install .
RUN pip install .

WORKDIR $EXAMON_HOME/publishers/random_pub
RUN $PIP install -r requirements.txt

WORKDIR $EXAMON_HOME/web
RUN virtualenv flask
RUN flask/bin/pip --trusted-host pypi.python.org install --upgrade pip==20.1.1
RUN CASS_DRIVER_BUILD_CONCURRENCY=8 flask/bin/pip --trusted-host pypi.python.org install -r ./examon-server/requirements.txt

WORKDIR $EXAMON_HOME/scripts

EXPOSE 1883 9001

CMD ["./frontend_ctl.sh", "start"]
