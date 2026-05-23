# ExaMon Docker Setup
This setup will install all server-side components of the ExaMon framework:

 - MQTT broker and Db connector
 - Grafana
 - KairosDB
 - Cassandra

## Prerequisites
Since Cassandra is the component that requires the majority of resources, you can find more details about the suggested hardware configuration of the system that will host the services here:

[Hardware Configuration](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/hardware.html)

To install all the services needed by ExaMon we will use Docker and Docker Compose:

[Install Docker and Docker Compose](https://docs.docker.com/engine/installation/).


## Setup

### Clone the Git repository

First you will need to clone the Git repository:

```bash
git clone https://github.com/ExamonHPC/examon.git
```

### Create Docker Services

Once you have the above setup, you need to create the Docker services:

```bash
docker compose up -d
```

This will build the Docker images and fetch some prebuilt images and then start the services. You can refer to the `docker-compose.yml` file to see the full configuration. 

### Configure Grafana

Log in to the Grafana server using your browser and the default credentials:

http://localhost:3000

Follow the normal procedure for adding a new data source (KairosDB):

[Add a Datasource](https://grafana.com/docs/grafana/latest/datasources/add-a-data-source/)

Fill out the form with the following settings:

 - Type: `KairosDB`  
 - Name: `kairosdb` 
 - Url: http://kairosdb:8083 
 - Access: `Server`

## Usage Examples

### Collecting data using the dummy "examon_pub" plugin
Once all Docker services are running (can be started either by `docker compose up -d` or `docker compose start`), the MQTT broker is available at `TEST_SERVER` port `1883` where `TEST_SERVER` is the address of the server where the services run.

To test the installation we can use the `examon_pub.py` plugin available in the `publishers/examon_pub` folder of  this project.

It is highly recommended to follow the tutorial described in the Jupyter notebook `README-notebook.ipynb` to understand how an Examon plugin works.

After having installed and configured it on one or more test nodes we can start the data collection running for example:

```bash
[root@testnode00]$ python ./examon_pub.py -b TEST_SERVER -p 1883 -s 1 run
```
If everything went well, the data are available both through the Grafana interface and using the [examon-client](../Users/Demo_ExamonQL.ipynb). 


## Where to go next

- Write your first plugin: [Example plugin](../Plugins/examon_pub.ipynb)
- Write your first query: [Example query](../Users/Demo_ExamonQL.ipynb)


