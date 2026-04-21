# UE-Driven 5G Slice Selection and Switching Mechanism

This repository presents an implementation of a **User Equipment (UE)-driven network slice selection and switching mechanism** in a 5G Standalone (SA) Network.

The system enables a UE to dynamically select and switch between network slices by controlling **PDU session establishment** at the modem level. Switching decisions are based on runtime performance measurements (throughput), enabling adaptive and performance-aware connectivity.

The implementation has been developed and evaluated using a Raspberry Pi 4 equipped with a Quectel RM520N-GL 5G modem in an Amarisoft 5G SA network.

---

## Repository Contents

The repository consists of the following components:

### Slice Selection and Modem Configuration

The file `slice_selection.md` contains the complete setup and configuration procedure, **including all required system dependencies**.

It includes:

- Modem configuration in QMI mode  
- AT command usage  
- PDU session profile creation  
- Association of profiles with slices (S-NSSAI)  
- Establishment of connections using `quectel-CM`  

This file defines how slice selection is implemented at the UE level.

---

### Slice API

The file `Slice_API.py` implements a RESTful Application Programming Interface (API) that enables interaction with the slice selection and switching mechanism.

The API abstracts low-level modem operations, including AT command handling and QMI-based communication, and exposes a high-level interface for managing network slice selection via HTTP endpoints with JSON payloads.

The API provides the following endpoints:

- Retrieval of the current network status, including the active S-NSSAI, DNN, and assigned IP address (AT command-based)  
- Querying of available PDU session profiles and their associated slice information (AT command-based)  
- Dynamic slice selection through PDU Session Establishment Requests using a specified CID (`quectel-CM`)  
- Disconnection from the network by releasing the active PDU session (`quectel-CM`)  

The API can be accessed by external applications or users, or by the monitoring component, which evaluates Quality of Service (QoS) metrics such as throughput and latency and triggers slice switching when predefined thresholds are exceeded.


<img width="1719" height="791" alt="image" src="https://github.com/user-attachments/assets/83378a9b-9bd8-4c52-9cd5-b4fb46965941" />



---

### Performance Monitoring and Switching Logic

The repository includes monitoring components that evaluate runtime connection performance and trigger a slice switch when the currently active slice no longer satisfies the required QoS.

Two monitoring approaches are supported:

#### 1. Socket-based goodput monitoring 

The file `goodput_monitoring.py` measures goodput from Linux socket statistics using the `ss` utility.

It: 

- reads the number of received bytes for a selected flow (source ip and port)
- calculates goodput from consecutive measurements
- compares the measured goodput against a configurable threshold
- triggers a slice switch through the Slice API when the throughput is below the threshold for three consecutive measurements

The monitoring process stops automatically when no active connection is detected.

This method is suitable for monitoring an already active application flow.



#### 2. Live iperf3-based throughput monitoring 

The monitoring script `goodput_monitoring.py` can be used to evaluate uplink/ downlink performance with a live `iperf3` session.

It:
- launches an `iperf3` client toward a specified server and port
- stores the `iperf3` output in a log file
- parses throughput values from the live log output
- compares measured throughput against a configurable threshold
- triggers a slice switch through the Slice API if throughput remains below the threshold for three consecutive measurements
- retrieves the updated active CID and alternative CID after a successful switch and continues monitoring

This approach is useful when the slice switching decision should be based on an active throughput test. 


---

## System Operation

The system operates as follows:

1. Multiple PDU session profiles are configured on the modem  
2. Each profile corresponds to a specific slice  
3. A slice is selected by activating the corresponding profile  
4. The monitoring module continuously evaluates performance  
5. When performance degradation is detected, a new slice is selected and the modem performs a PDU Session Establishment Request using the new selected S-NSSAI.



---

## Experimental Setup

The system has been validated using:

- Amarisoft 5G Standalone Core and gNB  
- Raspberry Pi 4  
- Quectel RM520N-GL modem (Firmware: RM520NGLAAR03A03M4G)  

<img width="1192" height="461" alt="image" src="https://github.com/user-attachments/assets/afb0466b-0c34-458c-966b-d3c50d88d84a" />


This implementation relies on `quectel-CM`, a data call tool provided by Quectel. Access to `quectel-CM` can be requested through the Quectel support forums:

https://forums.quectel.com/



---
