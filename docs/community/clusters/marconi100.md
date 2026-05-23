# Marconi 100 - CINECA


<figure markdown>
  ![](../images/Marconi100.jpg){ width="300" }
</figure>


- Model: IBM Power AC922 (Whiterspoon)
- Racks: 55 total (49 compute)
- Nodes: 980
- Processors: 2x16 cores IBM POWER9 AC922 at 2.6(3.1) GHz
- Accelerators: 4 x NVIDIA Volta V100 GPUs/node, Nvlink 2.0, 16GB
- Cores: 32 cores/node, Hyperthreading x4
- RAM: 256 GB/node (242 usable)
- Peak Performance: about 32 Pflop/s, 32 TFlops per node
- Internal Network: Mellanox IB EDR DragonFly++ 100Gb/s
- Disk Space: 8PB raw GPFS storage

## Metrics 

This Section is a brief description of some of the metrics collected by ExaMon from the Marconi100 cluster. It is intended only as an example and is therefore not exhaustive. The Marconi, Galileo and Galileo 100 clusters have similar metrics.

## IPMI 

The following table describes the metrics collected by the ipmi_pub plugin.

|                  |                                                                            |      |
|------------------|----------------------------------------------------------------------------|------|
| Metric Name      | Description                                                                | Unit |
| pX_coreY_temp    | Temperature of core n. Y in the CPU socket n. X. X=0..1, Y=0..23           | °C   |
| dimmX_temp       | Temperature of DIMM module n. X. X=0..15                                   | °C   |
| gpuX_core_temp   | Temperature of the core for the GPU id X. X=0,1,3,4                        | °C   |
| gpuX_mem_temp    | Temperature of the memory for the GPU id X. X=0,1,3,4                      | °C   |
| fanX_Y           | Speed of the Fan Y in module X. X=0..3, Y=0,1                              | RPM  |
| pX_vdd_temp      | Temperature of the voltage regulator for the CPU socket n. X. X=0..1       | °C   |
| fan_disk_power   | Power consumption of the disk fan                                          | W    |
| pX_io_power      | Power consumption for the I/O subsystem for the CPU socket n. X. X=0..1    | W    |
| pX_mem_power     | Power consumption for the memory subsystem for the CPU socket n. X. X=0..1 | W    |
| pX_power         | Power consumption for the CPU socket n. X. X=0..1                          | W    |
| psX_input_power  | Power consumption at the input of power supply n. X. X=0..1                | W    |
| total_power      | Total node power consumption                                               | W    |
| psX_input_voltag | Voltage at the input of power supply n. X. X=0..1                          | V    |
| psX_output_volta | Voltage at the output of power supply n. X. X=0..1                         | V    |
| psX_output_curre | Current at the output of power supply n. X. X=0..1                         | A    |
| pcie             | Temperature at the PCIExpress slots                                        | °C   |
| ambient          | Temperature at the node inlet                                              | °C   |

## Ganglia 

The following table describes the metrics collected by the ganglia_pub plugin. The data are extracted from a Ganglia^([\[6\]](#ftnt6)) instance that CINECA runs on Marconi100.

|                                  |           |             |                                                                                                                                                                                                                                |
|----------------------------------|-----------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Metric name                      | Type      | Unit        | Description                                                                                                                                                                                                                    |
| gexec                            | core      |             | gexec available                                                                                                                                                                                                                |
| cpu_aidle                        | cpu       | %           | Percent of time since boot idle CPU                                                                                                                                                                                            |
| cpu_idle                         | cpu       | %           | Percentage of time that the CPU or CPUs were idle and the system did not have an outstanding disk I/O request                                                                                                                  |
| cpu_nice                         | cpu       | %           | Percentage of CPU utilization that occurred while executing at the user level with nice priority                                                                                                                               |
| cpu_speed                        | cpu       | MHz         | CPU Speed in terms of MHz                                                                                                                                                                                                      |
| cpu_steal                        | cpu       | %           | cpu_steal                                                                                                                                                                                                                      |
| cpu_system                       | cpu       | %           | Percentage of CPU utilization that occurred while executing at the system level                                                                                                                                                |
| cpu_user                         | cpu       | %           | Percentage of CPU utilization that occurred while executing at the user level                                                                                                                                                  |
| cpu_wio                          | cpu       | %           | Percentage of time that the CPU or CPUs were idle during which the system had an outstanding disk I/O request                                                                                                                  |
| cpu_num                          |           |             |                                                                                                                                                                                                                                |
| disk_free                        | disk      | GB          | Total free disk space                                                                                                                                                                                                          |
| disk_total                       | disk      | GB          | Total available disk space                                                                                                                                                                                                     |
| part_max_used                    | disk      | %           | Maximum percent used for all partitions                                                                                                                                                                                        |
| load_fifteen                     | load      |             | Fifteen minute load average                                                                                                                                                                                                    |
| load_five                        | load      |             | Five minute load average                                                                                                                                                                                                       |
| load_one                         | load      |             | One minute load average                                                                                                                                                                                                        |
| mem_buffers                      | memory    | KB          | Amount of buffered memory                                                                                                                                                                                                      |
| mem_cached                       | memory    | KB          | Amount of cached memory                                                                                                                                                                                                        |
| mem_free                         | memory    | KB          | Amount of available memory                                                                                                                                                                                                     |
| mem_shared                       | memory    | KB          | Amount of shared memory                                                                                                                                                                                                        |
| mem_total                        | memory    | KB          | Total amount of memory displayed in KBs                                                                                                                                                                                        |
| swap_free                        | memory    | KB          | Amount of available swap memory                                                                                                                                                                                                |
| swap_total                       | memory    | KB          | Total amount of swap space displayed in KBs                                                                                                                                                                                    |
| bytes_in                         | network   | bytes/sec   | Number of bytes in per second                                                                                                                                                                                                  |
| bytes_out                        | network   | bytes/sec   | Number of bytes out per second                                                                                                                                                                                                 |
| pkts_in                          | network   | packets/sec | Packets in per second                                                                                                                                                                                                          |
| pkts_out                         | network   | packets/sec | Packets out per second                                                                                                                                                                                                         |
| proc_run                         | process   |             | Total number of running processes                                                                                                                                                                                              |
| proc_total                       | process   |             | Total number of processes                                                                                                                                                                                                      |
| boottime                         | system    | s           | The last time that the system was started                                                                                                                                                                                      |
| machine_type                     | system    |             | System architecture                                                                                                                                                                                                            |
| os_name                          | system    |             | Operating system name                                                                                                                                                                                                          |
| os_release                       | system    |             | Operating system release date                                                                                                                                                                                                  |
| cpu_ctxt                         | cpu       | ctxs/sec    | Context Switches                                                                                                                                                                                                               |
| cpu_intr                         | cpu       | %           | cpu_intr                                                                                                                                                                                                                       |
| cpu_sintr                        | cpu       | %           | cpu_sintr                                                                                                                                                                                                                      |
| multicpu_idle0                   | cpu       | %           | Percentage of CPU utilization that occurred while executing at the idle level                                                                                                                                                  |
| procs_blocked                    | cpu       | processes   | Processes blocked                                                                                                                                                                                                              |
| procs_created                    | cpu       | proc/sec    | Number of processes and threads created                                                                                                                                                                                        |
| disk_free_absolute_developers    | disk      | GB          | Disk space available (GB) on /developers                                                                                                                                                                                       |
| disk_free_percent_developers     | disk      | %           | Disk space available (%) on /developers                                                                                                                                                                                        |
| diskstat_sda_io_time             | diskstat  | s           | The time in seconds spent in I/O operations                                                                                                                                                                                    |
| diskstat_sda_percent_io_time     | diskstat  | percent     | The percent of disk time spent on I/O operations                                                                                                                                                                               |
| diskstat_sda_read_bytes_per_sec  | diskstat  | bytes/sec   | The number of bytes read per second                                                                                                                                                                                            |
| diskstat_sda_reads_merged        | diskstat  | reads       | The number of reads merged. Reads which are adjacent to each other may be merged for efficiency. Multiple reads may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.           |
| diskstat_sda_reads               | diskstat  | reads       | The number of reads completed                                                                                                                                                                                                  |
| diskstat_sda_read_time           | diskstat  | s           | The time in seconds spent reading                                                                                                                                                                                              |
| diskstat_sda_weighted_io_time    | diskstat  | s           | The weighted time in seconds spend in I/O operations. This measures each I/O start, I/O completion, I/O merge, or read of these stats by the number of I/O operations in progress times the number of seconds spent doing I/O. |
| diskstat_sda_write_bytes_per_sec | diskstat  | bytes/sec   | The number of bytes written per second                                                                                                                                                                                         |
| diskstat_sda_writes_merged       | diskstat  | writes      | The number of writes merged. Writes which are adjacent to each other may be merged for efficiency. Multiple writes may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.        |
| diskstat_sda_writes              | diskstat  | writes      | The number of writes completed                                                                                                                                                                                                 |
| diskstat_sda_write_time          | diskstat  | s           | The time in seconds spent writing                                                                                                                                                                                              |
| ipmi_ambient_temp                | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_avg_power                   | ipmi      | Watts       | IPMI data                                                                                                                                                                                                                      |
| ipmi_cpu1_temp                   | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_cpu2_temp                   | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_gpu_outlet_temp             | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_hdd_inlet_temp              | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_pch_temp                    | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_pci_riser_1\_temp           | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_pci_riser_2\_temp           | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| ipmi_pib_ambient_temp            | ipmi      | C           | IPMI data                                                                                                                                                                                                                      |
| mem_anonpages                    | memory    | Bytes       | AnonPages                                                                                                                                                                                                                      |
| mem_dirty                        | memory    | Bytes       | The total amount of memory waiting to be written back to the disk.                                                                                                                                                             |
| mem_hardware_corrupted           | memory    | Bytes       | HardwareCorrupted                                                                                                                                                                                                              |
| mem_mapped                       | memory    | Bytes       | Mapped                                                                                                                                                                                                                         |
| mem_writeback                    | memory    | Bytes       | The total amount of memory actively being written back to the disk.                                                                                                                                                            |
| vm_pgmajfault                    | memory_vm | ops/s       | pgmajfault                                                                                                                                                                                                                     |
| vm_pgpgin                        | memory_vm | ops/s       | pgpgin                                                                                                                                                                                                                         |
| vm_pgpgout                       | memory_vm | ops/s       | pgpgout                                                                                                                                                                                                                        |
| vm_vmeff                         | memory_vm | pct         | VM efficiency                                                                                                                                                                                                                  |
| rx_bytes_eth0                    | network   | bytes/sec   | received bytes per sec                                                                                                                                                                                                         |
| rx_drops_eth0                    | network   | pkts/sec    | receive packets dropped per sec                                                                                                                                                                                                |
| rx_errs_eth0                     | network   | pkts/sec    | received error packets per sec                                                                                                                                                                                                 |
| rx_pkts_eth0                     | network   | pkts/sec    | received packets per sec                                                                                                                                                                                                       |
| tx_bytes_eth0                    | network   | bytes/sec   | transmitted bytes per sec                                                                                                                                                                                                      |
| tx_drops_eth0                    | network   | pkts/sec    | transmitted dropped packets per sec                                                                                                                                                                                            |
| tx_errs_eth0                     | network   | pkts/sec    | transmitted error packets per sec                                                                                                                                                                                              |
| tx_pkts_eth0                     | network   | pkts/sec    | transmitted packets per sec                                                                                                                                                                                                    |
| procstat_gmond_cpu               | procstat  | percent     | The total percent CPU utilization                                                                                                                                                                                              |
| procstat_gmond_mem               | procstat  | B           | The total memory utilization                                                                                                                                                                                                   |
| softirq_blockiopoll              | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_block                    | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_hi                       | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_hrtimer                  | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_netrx                    | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_nettx                    | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_rcu                      | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_sched                    | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_tasklet                  | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| softirq_timer                    | softirq   | ops/s       | Soft Interrupts                                                                                                                                                                                                                |
| entropy_avail                    | ssl       | bits        | Entropy Available                                                                                                                                                                                                              |
| tcpext_listendrops               | tcpext    | count/s     | listendrops                                                                                                                                                                                                                    |
| tcpext_tcploss_percentage        | tcpext    | pct         | TCP percentage loss, tcploss / insegs + outsegs                                                                                                                                                                                |
| tcp_attemptfails                 | tcp       | count/s     | attempt fails                                                                                                                                                                                                                  |
| tcp_insegs                       | tcp       | count/s     | insegs                                                                                                                                                                                                                         |
| tcp_outsegs                      | tcp       | count/s     | outsegs                                                                                                                                                                                                                        |
| tcp_retrans_percentage           | tcp       | pct         | TCP retrans percentage, retranssegs / insegs + outsegs                                                                                                                                                                         |
| udp_indatagrams                  | udp       | count/s     | indatagrams                                                                                                                                                                                                                    |
| udp_inerrors                     | udp       | count/s     | inerrors                                                                                                                                                                                                                       |
| udp_outdatagrams                 | udp       | count/s     | outdatagrams                                                                                                                                                                                                                   |
| multicpu_idle16                  | cpu       | %           | Percentage of CPU utilization that occurred while executing at the idle level                                                                                                                                                  |
| multicpu_steal16                 | cpu       | %           | Percentage of CPU preempted by the hypervisor                                                                                                                                                                                  |
| multicpu_system16                | cpu       | %           | Percentage of CPU utilization that occurred while executing at the system level                                                                                                                                                |
| multicpu_user16                  | cpu       | %           | Percentage of CPU utilization that occurred while executing at the user level                                                                                                                                                  |
| multicpu_wio16                   | cpu       | %           | Percentage of CPU utilization that occurred while executing at the wio level                                                                                                                                                   |
| diskstat_sdb_io_time             | diskstat  | s           | The time in seconds spent in I/O operations                                                                                                                                                                                    |
| diskstat_sdb_percent_io_time     | diskstat  | percent     | The percent of disk time spent on I/O operations                                                                                                                                                                               |
| diskstat_sdb_read_bytes_per_sec  | diskstat  | bytes/sec   | The number of bytes read per second                                                                                                                                                                                            |
| diskstat_sdb_reads_merged        | diskstat  | reads       | The number of reads merged. Reads which are adjacent to each other may be merged for efficiency. Multiple reads may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.           |
| diskstat_sdb_reads               | diskstat  | reads       | The number of reads completed                                                                                                                                                                                                  |
| diskstat_sdb_read_time           | diskstat  | s           | The time in seconds spent reading                                                                                                                                                                                              |
| diskstat_sdb_weighted_io_time    | diskstat  | s           | The weighted time in seconds spend in I/O operations. This measures each I/O start, I/O completion, I/O merge, or read of these stats by the number of I/O operations in progress times the number of seconds spent doing I/O. |
| diskstat_sdb_write_bytes_per_sec | diskstat  | bytes/sec   | The number of bytes written per second                                                                                                                                                                                         |
| diskstat_sdb_writes_merged       | diskstat  | writes      | The number of writes merged. Writes which are adjacent to each other may be merged for efficiency. Multiple writes may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.        |
| diskstat_sdb_writes              | diskstat  | writes      | The number of writes completed                                                                                                                                                                                                 |
| diskstat_sdb_write_time          | diskstat  | s           | The time in seconds spent writing                                                                                                                                                                                              |
| GpuX_dec_utilization             | gpu       | %           | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_enc_utilization             | gpu       | %           | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_enforced_power_limit        | gpu       | Watts       | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_gpu_temp                    | gpu       | Celsius     | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_low_util_violation          | gpu       |             | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_mem_copy_utilization        | gpu       | %           | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_mem_util_samples            | gpu       |             | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_memory_clock                | gpu       | Mhz         | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_memory_temp                 | gpu       | Celsius     | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_power_management_limit      | gpu       | Watts       | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_power_usage                 | gpu       | Watts       | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_pstate                      | gpu       |             | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_reliability_violation       | gpu       |             | X=0,..,3                                                                                                                                                                                                                       |
| GpuX_sm_clock                    | gpu       | Mhz         | X=0,..,3                                                                                                                                                                                                                       |

## Nagios 

This is a description of the metrics collected by the ExaMon "nagios_pub" plugin. The data reflect those monitored by the Nagios^([\[7\]](#ftnt7)) tool that currently runs in the CINECA clusters. Specifically, the plugin interfaces with a Nagios extension developed by CINECA called "Hnagios"^([\[8\]](#ftnt8)). Although the monitored services and metrics are similar between all clusters, here we will specifically discuss those of Marconi100.

### Metrics

Currently, this plugin collects three metrics

|     |                              |
|-----|------------------------------|
|     | name                         |
| 0   | hostscheduleddowtimecomments |
| 1   | plugin_output                |
| 2   | state                        |

#### Hostscheduleddowtimecomments

This metric is obtained from the "Hnagios" output and reports comments made by system administrators about the maintenance status of the specific monitored resource

|     |                              |               |                                                    |
|-----|------------------------------|---------------|----------------------------------------------------|
|     | name                         | tag key       | tag values                                         |
| 0   | hostscheduleddowtimecomments | node          | \[ems02, login03, login08, master01, master02, ... |
| 1   | hostscheduleddowtimecomments | slot          | \[01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 1... |
| 2   | hostscheduleddowtimecomments | description   | \[afs::blocked_conn::status, afs::bosserver::st... |
| 3   | hostscheduleddowtimecomments | plugin        | \[nagios_pub\]                                     |
| 4   | hostscheduleddowtimecomments | chnl          | \[data\]                                           |
| 5   | hostscheduleddowtimecomments | host_group    | \[compute, compute,cincompute, efgwcompute, efg... |
| 6   | hostscheduleddowtimecomments | cluster       | \[galileo, marconi, marconi100\]                   |
| 7   | hostscheduleddowtimecomments | state         | \[0, 1, 2, 3\]                                     |
| 8   | hostscheduleddowtimecomments | nagiosdrained | \[0, 1\]                                           |
| 9   | hostscheduleddowtimecomments | org           | \[cineca\]                                         |
| 10  | hostscheduleddowtimecomments | state_type    | \[0, 1\]                                           |
| 11  | hostscheduleddowtimecomments | rack          | \[205, 206, 207, 208, 209, 210, 211, 212, 213, ... |

#### Plugin_output

This metric collects the outbound messages from Nagios agents responsible for monitoring services.

|     |               |               |                                                    |
|-----|---------------|---------------|----------------------------------------------------|
|     | name          | tag key       | tag values                                         |
| 0   | plugin_output | node          | \[ems02, ethcore01-mgt, ethcore02-mgt, gss03, g... |
| 1   | plugin_output | slot          | \[01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 1... |
| 2   | plugin_output | description   | \[EFGW_cluster::status::availability, EFGW_clus... |
| 3   | plugin_output | plugin        | \[nagios_pub\]                                     |
| 4   | plugin_output | chnl          | \[data\]                                           |
| 5   | plugin_output | host_group    | \[compute, compute,cincompute, containers, cumu... |
| 6   | plugin_output | cluster       | \[galileo, marconi, marconi100\]                   |
| 7   | plugin_output | state         | \[0, 1, 2, 3\]                                     |
| 8   | plugin_output | nagiosdrained | \[0, 1\]                                           |
| 9   | plugin_output | org           | \[cineca\]                                         |
| 10  | plugin_output | state_type    | \[0, 1\]                                           |
| 11  | plugin_output | rack          | \[202, 205, 206, 207, 208, 209, 210, 211, 212, ... |

#### State

This metric collects the equivalent numerical value of the actual state of the service monitored by Nagios.

|     |       |               |                                                    |
|-----|-------|---------------|----------------------------------------------------|
|     | name  | tag key       | tag values                                         |
| 0   | state | node          | \[ems02, ethcore01-mgt, ethcore02-mgt, gss03, g... |
| 1   | state | slot          | \[01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 1... |
| 2   | state | description   | \[EFGW_cluster::status::availability, EFGW_clus... |
| 3   | state | plugin        | \[nagios_pub\]                                     |
| 4   | state | chnl          | \[data\]                                           |
| 5   | state | host_group    | \[compute, compute,cincompute, containers, cumu... |
| 6   | state | cluster       | \[galileo, marconi, marconi100\]                   |
| 7   | state | nagiosdrained | \[0, 1\]                                           |
| 8   | state | org           | \[cineca\]                                         |
| 9   | state | state_type    | \[0, 1\]                                           |
| 10  | state | rack          | \[202, 205, 206, 207, 208, 209, 210, 211, 212, ... |

### Resources monitored in Marconi100

The name and type of the services/resources monitored by Nagios and corresponding to the metrics just described above are collected in the "description" tag.

#### Nagios checks for Marconi100

In the following table is collected a brief description of the services  monitored by Nagios in the Marconi100 cluster.

|                       |                                   |
|-----------------------|-----------------------------------|
| Service/resource      | Description                       |
| alive::ping           | Ping command output               |
| backup::local::status | Backup service                    |
| batchs::...           | Batch scheduler services          |
| bmc::events           | Events from the node BMC          |
| cluster::...          | Cluster availability              |
| container::...        | Status of the container system    |
| dev::...              | Node devices                      |
| file::integrity       | Files integrity                   |
| filesys::...          | Filesystem elements               |
| galera::...           | Status of the database components |
| globus::...           | Status of the FTP system          |
| memory::phys::total   | Physical memory size              |
| monitoring::health    | Monitoring subsystem              |
| net::ib::status       | Infiniband                        |
| nfs::rpc::status      | NFS                               |
| nvidia::...           | GPUs                              |
| service::...          | Misc. services                    |
| ssh::...              | SSH server                        |
| sys::...              | Misc. systems (GPFS,...)          |

### Nagios state encoding

This table describes the numerical encoding of the state metric values and the state_type tag, as defined by Nagios.

[TABLE]

## 

## Nvidia 

The following table describes the metrics collected by the nvidia_pub plugin.

PLEASE NOTE This plugin has collected data only for a short period (January/February 2020) and is currently not enabled due to CINECA policy.

|                                |                                                                                                                                                               |      |
|--------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| Metric name                    | Description                                                                                                                                                   | Unit |
| clock.sm                       | Current frequency of SM (Streaming Multiprocessor) clock.                                                                                                     | MHz  |
| clocks.gr                      | Current frequency of graphics (shader) clock.                                                                                                                 | MHz  |
| clocks.mem                     | Current frequency of memory clock.                                                                                                                            | MHz  |
| clocks_throttle_reasons.active | Bitmask of active clock throttle reasons. See nvml.h for more details                                                                                         |      |
| power.draw                     | The last measured power draw for the entire board, in watts. Only available if power management is supported. This reading is accurate to within +/- 5 watts. | W    |
| temperature.gpu                | Core GPU temperature. in degrees C.                                                                                                                           | °C   |

## Slurm 

Currently the job scheduler data is collected as per-job data in plain Cassandra tables.

This is a description of the data currently stored (where available) for each executed job:

|                       |                                                                                      |
|-----------------------|--------------------------------------------------------------------------------------|
| Table fields          | Description                                                                          |
| account               | charge to specified account                                                          |
| accrue_time           | time job is eligible for running                                                     |
| admin_comment         | administrator's arbitrary comment                                                    |
| alloc_node            | local node and system id making the resource allocation                              |
| alloc_sid             | local sid making resource alloc                                                      |
| array_job_id          | job_id of a job array or 0 if N/A                                                    |
| array_max_tasks       | Maximum number of running tasks                                                      |
| array_task_id         | task_id of a job array                                                               |
| array_task_str        | string expression of task IDs in this record                                         |
| assoc_id              | association id for job                                                               |
| batch_features        | features required for batch script's node                                            |
| batch_flag            | 1 if batch: queued job with script                                                   |
| batch_host            | name of host running batch script                                                    |
| billable_tres         | billable TRES cache. updated upon resize                                             |
| bitflags              | Various job flags                                                                    |
| boards_per_node       | boards per node required by job                                                      |
| burst_buffer          | burst buffer specifications                                                          |
| burst_buffer_state    | burst buffer state info                                                              |
| command               | command to be executed, built from submitted  job's argv and NULL for salloc command |
| comment               | arbitrary comment                                                                    |
| contiguous            | 1 if job requires contiguous nodes                                                   |
| core_spec             | specialized core count                                                               |
| cores_per_socket      | cores per socket required by job                                                     |
| cpu_freq_gov          | cpu frequency governor                                                               |
| cpu_freq_max          | Maximum cpu frequency                                                                |
| cpu_freq_min          | Minimum cpu frequency                                                                |
| cpus_alloc_layout     | map: list of cpu allocated per node                                                  |
| cpus_allocated        | map: number of cpu allocated per node                                                |
| cpus_per_task         | number of processors required for each task                                          |
| cpus_per_tres         | semicolon delimited list of TRES=# values                                            |
| dependency            | synchronize job execution with other jobs                                            |
| derived_ec            | highest exit code of all job steps                                                   |
| eligible_time         | time job is eligible for running                                                     |
| end_time              | time of termination, actual or expected                                              |
| exc_nodes             | comma separated list of excluded nodes                                               |
| exit_code             | exit code for job (status from wait call)                                            |
| features              | comma separated list of required features                                            |
| group_id              | group job submitted as                                                               |
| job_id                | job ID                                                                               |
| job_state             | state of the job, see enum job_states                                                |
| last_sched_eval       | last time job was evaluated for scheduling                                           |
| licenses              | licenses required by the job                                                         |
| max_cpus              | maximum number of cpus usable by job                                                 |
| max_nodes             | maximum number of nodes usable by job                                                |
| mem_per_cpu           | boolean                                                                              |
| mem_per_node          | boolean                                                                              |
| mem_per_tres          | semicolon delimited list of TRES=# values                                            |
| min_memory_cpu        | minimum real memory required per allocated CPU                                       |
| min_memory_node       | minimum real memory required per node                                                |
| name                  | name of the job                                                                      |
| network               | network specification                                                                |
| nice                  | requested priority change                                                            |
| nodes                 | list of nodes allocated to job                                                       |
| ntasks_per_board      | number of tasks to invoke on each board                                              |
| ntasks_per_core       | number of tasks to invoke on each core                                               |
| ntasks_per_core_str   | number of tasks to invoke on each core  as string                                    |
| ntasks_per_node       | number of tasks to invoke on each node                                               |
| ntasks_per_socket     | number of tasks to invoke on each socket                                             |
| ntasks_per_socket_str | number of tasks to invoke on each socket as string                                   |
| num_cpus              | minimum number of cpus required by job                                               |
| num_nodes             | minimum number of nodes required by job                                              |
| partition             | name of assigned partition                                                           |
| pn_min_cpus           | minimum \# CPUs per node, default=0                                                  |
| pn_min_memory         | minimum real memory per node, default=0                                              |
| pn_min_tmp_disk       | minimum tmp disk per node, default=0                                                 |
| power_flags           | power management flags,  see SLURM_POWERFLAGS                                        |
| pre_sus_time          | time job ran prior to last suspend                                                   |
| preempt_time          | preemption signal time                                                               |
| priority              | relative priority of the job, 0=held, 1=required nodes DOWN/DRAINED                  |
| profile               | Level of acct_gather_profile {all / none}                                            |
| qos                   | Quality of Service                                                                   |
| reboot                | node reboot requested before start                                                   |
| req_nodes             | comma separated list of required nodes                                               |
| req_switch            | Minimum number of switches                                                           |
| requeue               | enable or disable job requeue option                                                 |
| resize_time           | time of latest size change                                                           |
| restart_cnt           | count of job restarts                                                                |
| resv_name             | reservation name                                                                     |
| run_time              | job run time (seconds)                                                               |
| run_time_str          | job run time (seconds) as string                                                     |
| sched_nodes           | list of nodes scheduled to be used for job                                           |
| shared                | 1 if job can share nodes with other jobs                                             |
| show_flags            | conveys level of details requested                                                   |
| sockets_per_board     | sockets per board required by job                                                    |
| sockets_per_node      | sockets per node required by job                                                     |
| start_time            | time execution begins, actual or expected                                            |
| state_reason          | reason job still pending or failed, see slurm.h:enum job_state_reason                |
| std_err               | pathname of job's stderr file                                                        |
| std_in                | pathname of job's stdin file                                                         |
| std_out               | pathname of job's stdout file                                                        |
| submit_time           | time of job submission                                                               |
| suspend_time          | time job last suspended or resumed                                                   |
| system_comment        | slurmctld's arbitrary comment                                                        |
| threads_per_core      | threads per core required by job                                                     |
| time_limit            | maximum run time in minutes or INFINITE                                              |
| time_limit_str        | maximum run time in minutes or INFINITE as string                                    |
| time_min              | minimum run time in minutes or INFINITE                                              |
| tres_alloc_str        | tres used in the job as string                                                       |
| tres_bind             | Task to TRES binding directives                                                      |
| tres_freq             | TRES frequency directives                                                            |
| tres_per_job          | semicolon delimited list of TRES=# values                                            |
| tres_per_node         | semicolon delimited list of TRES=# values                                            |
| tres_per_socket       | semicolon delimited list of TRES=# values                                            |
| tres_per_task         | semicolon delimited list of TRES=# values                                            |
| tres_req_str          | tres requested in the job as string                                                  |
| user_id               | user the job runs as                                                                 |
| wait4switch           | Maximum time to wait for minimum switches                                            |
| wckey                 | wckey for job                                                                        |
| work_dir              | pathname of working directory                                                        |
