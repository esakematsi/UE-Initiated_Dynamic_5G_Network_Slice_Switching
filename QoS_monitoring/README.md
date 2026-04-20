# Goodput Monitoring and Slice Switching

This directory contains the monitoring and decision-making component of the system.

---

## Requirements

Install Python dependencies from the root directory:

```
pip install -r ../requirements.txt
```



## Run

```
python3 goodput_monitoring.py --source-ip <IP_ADDRESS> --port <PORT> --threshold <THRESHOLD>
```


## Parameters

| Parameter     | Description                          | Required | Default |
|---------------|--------------------------------------|----------|---------|
| `--source-ip` | IP address of the monitored TCP flow | Yes      | -       |
| `--port`      | TCP port of the monitored TCP flow   | Yes      | -       |
| `--threshold` | Goodput threshold in Mbps            | No       | 2.0     |
| `--debug`     | Enables verbose debug output         | No       | False   |
