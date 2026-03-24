# Release v0.5.0 Plan

we are going to release a new version of the current project. The new version will be v0.5.0.

## Features

### Main Features

- The main feature will be the addition of a Helm chart for the deployment to k8s of the current project
  - Currently the deployment is done solely using Docker Compose.
- Detailed deployment documentation in the following scenarios:
  - Kubernetes (Helm chart) the most important.
  - Containers (Docker, Podman, etc.) - current docker compose setup.
  - Baremetal, virtual machines (linux/ubuntu/rocky linux) - optional, for reference.

### Other Features

After the addition of the Helm chart and succesfully tested the deployment of the current release, we will also add the following secondary features:

- we will gradually upgrade an test the version of the following components:
  - Grafana to the latest version
    - install and check latest kairosdb datasource plugin (implemented internally or use third paarty)
  - KairosDB to v1.3.0 (potentially to 1.4.0-beta1)
  - Cassandra to v4.0+ (potentially to 5.0+)

## Planning for the K8s migration

The following are the maiin notes to be considered for the K8s migration:

- currently the whole infrastructur is deployed using the docker compose file, however this deployment is only a reference deployment for reference. the main objectives of the K8s migration are:
  - to have a more production-ready deployment
  - to have a more scalable deployment
  - to have a more reliable deployment
  - to have a more easy to maintain deployment
  - to have a more easy to deploy deployment
  - to have a more easy to scale deployment
  - to have a more easy to maintain deployment
  - to have a more easy to deploy deployment
  - to have a more easy to scale deployment

### Cassandra in k8s

- the core componet of the infrastructure is, at the moment, the Cassandra database. It is a component used mainly by the KairosDB database as storage backend. however other components, such as the examon web server, use directly the cassandra database as a storage backend to store relational like NoSQL data. 
- We need to evaluate the best strategy to deploy Cassandra in k8s to be easily scalable and reliable. We need to create a basic HA setup with 3 nodes. and we need to set it for the k8s node affinity. for example to have a data copy per k8s physichal node, so in case we lost temprarly a node, cassandra already manage this failure by design. we need to understand carefully how this works in the k8s cassandra operator. the target deployment strategy is to use the K8ssandra operator. But we need to check if this is the best strategy or there a new better way to deploy Cassandra in k8s.
- we have the k8ssandra operator Helm chart to check.
- we need to check the compatible cassandra version with the k8ssandra operator.

### KairosDB in k8s

- the KairosDB is a time series database that implement the timeseries database model and uses the Cassandra database as storage backend.
- it is stateless and can be easily scaled horizontally, the basic strategy can be an HA load balancer in front of the KairosDB instances, implemented in the k8s way.
- It is a component used by the Grafana dashboard to display the metrics data. 
- The kairosdb project already provides its own Helm chart, so we can use it to deploy KairosDB in k8s.

### Grafana in k8s

- Grafana is mainly used to visualize the data, especially but not only time series data.
- it also manage the alerting system, so we need to evaluate the best strategy to deploy Grafana in k8s to be easily scalable and reliable.
- Grafana is mature for the k8s deployment so we need to follow the best practices for the k8s deployment.

### ExaMon in k8s

- Examon currently is the part that we never deployed in k8s so we need to design from scratch.

#### ExaMon current deployment

- the examon infrastructure currently is defined inthe examon container asdefined in he dockerfile/docker compose file.
- the basic architecture of the container is a supervisord manager that start and manage multiple microservices in the examon container
  - the mosquitto broker. it is the transport layer for examon where the data collectors (publishers) and the data consumers (subscribers) communicate.
  - the random_pub plugin. it is a data collector that publishes random data to the examon system.
  - the mqtt2kairosdb plugin. it is a data consumer that subscribes to the random_pub plugin and publishes the data to the KairosDB database.
  - the examon-server. it is the web server that provides the API for the Grafana dashboard to fetch the data.
  - the log collector. it is a service that collects the logs from the other services and stores them in a log storage system.

#### ExaMon new deployment (k8s)

- the examon container will be replaced by k8s pods, each pod will contain the following services:
  - the mosquitto broker. it is the transport layer for examon where the data collectors (publishers) and the data consumers (subscribers) communicate.
  - the random_pub plugin. it is a data collector that publishes random data to the examon system.
  - the mqtt2kairosdb plugin. it is a data consumer that subscribes to the random_pub plugin and publishes the data to the KairosDB database.
  - the examon-server. it is the web server that manage the examon-client connection
  - and is an adapter for the cassandra relational data storage (insertion of relational data, now just from the batch hpc scheduler).
  - it is the web server that provides the API for the clients (examon-client, Grafana) to fetch the data about the HPC scheduler.
  - the log collector. it is a simple service that collects the logs from the other services and send them to the container log stdout.
- other specialized collectors can be added to the examon system, such as the slurm_pub plugin that publishes the data from the slurm scheduler to the examon system the ipmi_pub plugin that publishes the data from the ipmi sensors to the examon system the etc.
- the mqtt2kairosdb plugin currently is a special examon component that subscribes to all the topics that arrives to the brokers and publishes the data to the KairosDB database. it support parallelization of the data insertion to the KairosDB database.

#### Design considerations

- for the examon container we need to evaluate the best strategy. To ensure scalability and reliability can we keep using the mqtt broker or it is better to replace it with kafka (or better options) in k8s?
- the scalability of such compoents is managed currently manually adding more examon containers to the docker compose file. the we manually partition the data sent to the brokers. For example in the HPC application we can partition the data by the "rack" segment in the mqtt topics. So have as many examon containers as the number of racks in the HPC application. In k8s we need to evaluate the best strategy to scale the examon system. However this is a next step, for the first release we will keep the current deployment strategy.

## Goals for the first k8s release (in v0.5.0)

- have a minimal K8s deployment of the current release.
- Use Helm charts at the minimum for the deployment. Then possibly evaluate newer/better options for the deployment.
- Document the deployment for the k8s case.

# Current code

- examon-container: [https://github.com/ExamonHPC/examon-container](https://github.com/ExamonHPC/examon-container)
- examon-common: [https://github.com/ExamonHPC/examon-common](https://github.com/ExamonHPC/examon-common)

