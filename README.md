# Examon HPC Monitoring

A highly scalable framework for the performance and energy monitoring of HPC servers

## Setup

This setup will install all server-side components of the ExaMon framework:

 - MQTT broker and Db connector
 - Grafana
 - KairosDB
 - Cassandra
 - Out of band plugins

 This Examon installation includes the following plugins:

- `examon_pub`

Please note: the `examon_pub` plugin is used to test the system and it will publish random metrics.
It can be disabled as described in the [Enable/disable the plugins](#enable-disable-the-plugins) section.

## Prerequisites
Since Cassandra is the component that requires the majority of resources, you can find more details about the suggested hardware configuration of the system that will host the services here:

[Hardware Configuration](https://cassandra.apache.org/doc/latest/operating/hardware.html#:~:text=While%20Cassandra%20can%20be%20made,at%20least%2032GB%20of%20RAM)

To install all the services needed by ExaMon we will use Docker and Docker Compose:

[Install Docker and Docker Compose](https://docs.docker.com/engine/installation/).

## Install instructions

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

## Configuration

### Configure Grafana

Log in to the Grafana server using your browser and the default credentials:

**NOTE:** This installation sets the default password to `GF_SECURITY_ADMIN_PASSWORD` in the `docker-compose.yml` file.

http://localhost:3000

Follow the normal procedure for adding a new data source:

[Add a Datasource](https://grafana.com/docs/grafana/latest/datasources/add-a-data-source/)

From the Grafana UI, add a new data source and select `KairosDB`.

Fill out the form with the following settings:

 - Name: `kairosdb` 
 - Url: http://kairosdb:8083 
 - Access: `Server`

To import the dashboards stored in the `dashboards/` folder:    

[Import dashboard](https://grafana.com/docs/grafana/latest/dashboards/export-import/#import-dashboard)

To test the installation, you can import the `Examon Test - Random Sensor.json` dashboard.


### Configure the plugins

Installing the ExaMon plugins requires the configuration of each individual component.

It is necessary to define all the properties of the `.conf` configuration file of the plugins 
with the appropriate values related to the server hosting the framework. In particular, it is necessary 
to define the IP addresses and ports of the server where the KairosDB and/or MQTT broker services run, 
as well as their credentials. 
The configuration files to be edited are located in the respective plugin folders contained in the 
following folders:

| Plugin          | Path                        |
|-----------------|-----------------------------|
| examon_pub      | `/publishers/examon_pub`    |

Please refer to the respective plugin readme file (*Configuration* section) for further details.


### Manage the plugins

The plugins are managed by supervisord, which is the microservices manager for the examon container.

The majority of the commands follow the supervisorctl syntax:

```bash
supervisorctl <command> <plugin-name>
```

The most used commands are:

- `start`
- `stop`
- `restart`
- `status`
- `tail`

to see the full list of commands, you can use the following command:

```bash
docker exec -it <examon-container-name> supervisorctl help
```

To start the plugins, you need to run the following command:

```bash
docker exec -it <examon-container-name> supervisorctl start <plugin-name>
```
Example:

```bash
docker exec -it examon supervisorctl start plugins:examon_pub
```

Or, if you want to start all the plugins, you can use the following command:

```bash
docker exec -it <examon-container-name> supervisorctl start plugins:*
```
As an alternative, you can open the supervisor shell to manage the plugins and start/stop them individually:

```bash
docker exec -it <examon-container-name> supervisorctl
```

### Check the logs

To check the logs of the plugins, you can use the following command:

```bash
docker exec -it <examon-container-name> supervisorctl tail [-f] <plugin-name>
```

### Enable/disable the plugins

The plugins are disabled by default and need to be started manually each time the examon container is started.

To enable and start the plugins automatically, you need to edit the supervisor configuration file for the examon service.

```bash
docker exec -it <examon-container-name> bash

vi /etc/supervisor/conf.d/supervisor.conf
```
Then, for each plugin, set the following parameters to true:

```bash
autostart=True
```
Restart the examon container to apply the changes:

```bash
docker restart <examon-container-name>
```
Please note that the supervisor configuration will be lost in case the container is recreated.
To make the settings persistent, you need to edit the supervisor configuration file in `docker/examon/supervisor.conf` and rebuild.

## Examon server configuration

The Examon server must be enabled in the supervisor configuration file and configured to use the Examon REST API.

Please refer to the `README.rst` file in the `web/examon-server` folder for more information.

**NOTE:** The Cassandra related settings must be the same as the ones used in the Slurm publisher in the Cassandra section.

## Data persistence

During the installation, two Docker volumes are created, which are required for data persistence.

 ```bash
$ docker volume ls
DRIVER    VOLUME NAME
local     <project_name>_cassandra_volume
local     <project_name>_grafana_volume
 ```

*   The `slurm-dash_cassandra_volume` is used to store the collected metrics
*   The `slurm-dash_grafana_volume` is used to store Grafana:
    *   users account data
    *   dashboards

To set a custom volume path, you can use the following settings in the `docker-compose.yml` file:

```yaml
volumes:
  cassandra_volume:
    driver: local
    driver_opts:
      type: none
      device: /path/to/cassandra/volume
      o: bind
  grafana_volume:
    driver: local
    driver_opts:
      type: none
      device: /path/to/grafana/volume
      o: bind  
```

