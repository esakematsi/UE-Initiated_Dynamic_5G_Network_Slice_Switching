# Performance Monitoring and Slice Switching

This directory contains the monitoring and decision-making component of the system.

Two monitoring approaches are supported:
- socket-based monitoring using `ss`
- active throughput monitoring using `iperf3`


## 1. Socket-based Monitoring (`ss`)


The ss tool is used to retrieve socket-level statistics directly from the Linux kernel.

In this implementation, it is used to:

- monitor active TCP/UDP connections
- extract the total number of received bytes (bytes_received)
- provide real-time socket information 


### Requirements

Install Python dependencies from the root directory:

```
pip install -r ../requirements.txt
```

Ensure that:
- Slice API is running at http://localhost:5000
- There is an active connection to monitor



### Run

```
python3 goodput_monitoring.py --source-ip <IP_ADDRESS> --port <PORT> --threshold <THRESHOLD>
```


### Parameters

| Parameter     | Description                          | Required | Default |
|---------------|--------------------------------------|----------|---------|
| `--source-ip` | IP address of the monitored flow | Yes      | -       |
| `--port`      | Port of the monitored flow   | Yes      | -       |
| `--threshold` | Goodput threshold in Mbps            | No       | 2.0     |
| `--debug`     | Enables verbose debug output         | No       | False   |





## 2. Live Throughput Monitoring (`iperf3`)


This implementation:

- launches an `iperf3` client toward a specified server
- logs output to a file (`iperf_output.log`)
- parses throughput values in real time
- compares measured throughput against a configurable threshold



### Requirements

Install Python dependencies from the root directory:

```
pip install -r ../requirements.txt
```

Ensure that:
- Slice API is running at http://localhost:5000
- There is an active iperf3 server to connect to 



### Run

```
python3 iperf3_monitoring.py --server <SERVER_IP> --port <PORT> --threshold <THRESHOLD>
```


### Parameters


| Parameter   | Description                     | Required | Default |
|-------------|---------------------------------|----------|---------|
| `--server`  | IP address of the iperf3 server | Yes      | -       |
| `--port`    | iperf3 server port              | No       | 5201    |
| `--threshold` | Throughput threshold in Mbps  | No       | 20.0    |
| `--debug`   | Enables verbose debug output    | No       | False   |









