# UE-Driven 5G Slice Selection and Switching Mechanism

This repository presents an implementation of a **User Equipment (UE)-driven network slice selection and switching mechanism** in a 5G Standalone (SA) Network.

The system enables a UE to dynamically select and switch between network slices by controlling **PDU session establishment** at the modem level. Switching decisions are based on runtime performance measurements (throughput), enabling adaptive and performance-aware connectivity.

The implementation has been developed and evaluated using a Raspberry Pi 4 equipped with a Quectel RM520N-GL 5G modem in an Amarisoft 5G SA network.

---

## Repository Contents

The repository consists of the following components:

### Slice Selection and Modem Configuration

The file `slice_selection.md` contains the complete setup and configuration procedure.

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

### Goodput Monitoring and Switching Logic

The file `goodput_monitoring.py` implements the monitoring and decision-making mechanism.

It is responsible for:

- Measuring the performance of the active connection and triggering slice switching when the QoS is not sufficient. The performance metric used is **goodput**, defined as the rate of successfully received data.

The script uses the Linux `ss` tool to retrieve socket statistics from the kernel. Every second, it reads the total number of received bytes for a specific flow (filtered by IP address and port) and calculates the goodput based on the difference between consecutive measurements. The result is expressed in Mbps.

If the measured goodput falls below a predefined threshold for three consecutive measurements, the script triggers a slice switch by sending a request to the Slice API. After switching, it retrieves the updated network status and continues monitoring.

The monitoring process stops automatically when no active connection is detected.


Configurable parameters include:

- IP address and port of the monitored socket  
- Goodput threshold  
- Debug mode 

---

## System Operation

The system operates as follows:

1. Multiple PDU session profiles are configured on the modem  
2. Each profile corresponds to a specific slice  
3. A slice is selected by activating the corresponding profile  
4. The monitoring module continuously evaluates performance  
5. When performance degradation is detected, a new slice is selected and the modem performs a PDU Session Establishment Request using the new selected S-NSSAI.


<img width="1665" height="653" alt="image" src="https://github.com/user-attachments/assets/1f67c306-ce92-4971-9b3a-18595cc57ae5" />




---

## Experimental Setup

The system has been validated using:

- Amarisoft 5G Standalone Core and gNB  
- Raspberry Pi 4  
- Quectel RM520N-GL modem (Firmware: RM520NGLAAR03A03M4G)  

---
