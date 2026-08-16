FROM examonhpc/examon:0.3.3

ENV EXAMON_HOME /etc/examon_deploy/examon

# Copy app
ADD ./publishers/random_pub ${EXAMON_HOME}/publishers/random_pub
ADD ./docker/examon/supervisor.conf /etc/supervisor/conf.d/supervisor.conf
ADD ./scripts/examon.conf $EXAMON_HOME/scripts/examon.conf
ADD ./web $EXAMON_HOME/web
# Platform release version served by /api/health; kept at EXAMON_HOME so the
# compose bind-mount of web/examon-server does not hide it
ADD ./VERSION $EXAMON_HOME/VERSION

# Venvs
WORKDIR $EXAMON_HOME/scripts
RUN virtualenv -p $(which python) py3_env

ENV PIP $EXAMON_HOME/scripts/ve/bin/pip
ENV S_PIP $EXAMON_HOME/scripts/py3_env/bin/pip

# Install
WORKDIR $EXAMON_HOME/lib/examon-common
RUN $S_PIP install .

# Random publisher
WORKDIR $EXAMON_HOME/publishers/random_pub
RUN $PIP install -r requirements.txt

# Web
WORKDIR $EXAMON_HOME/web
RUN virtualenv -p $(which python) flask
RUN CASS_DRIVER_BUILD_CONCURRENCY=8 flask/bin/pip install -r ./examon-server/requirements.txt

WORKDIR $EXAMON_HOME/scripts

EXPOSE 1883 5000 9001

CMD ["./frontend_ctl.sh", "start"]
