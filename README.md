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

The file Slice_API.py implements a RESTful Application Programming Interface (API) that enables interaction with the slice selection and switching mechanism.

The API abstracts low-level modem operations, including AT command handling and QMI-based communication, and exposes a high-level interface for managing network slice selection via HTTP endpoints with JSON payloads.

The API provides the following endpoints:

-Retrieval of the current network status, including the active S-NSSAI, DNN, and assigned IP address (AT command-based)
-Querying of available PDU session profiles and their associated slice information (AT command-based)
-Dynamic slice selection through PDU Session Establishment Requests using a specified CID (quectel-CM)
-Disconnection from the network by releasing the active PDU session (quectel-CM)

The API can be accessed directly by external applications or users, or indirectly by the monitoring component, which evaluates Quality of Service (QoS) metrics such as throughput and latency and triggers slice switching when predefined thresholds are exceeded.

---

### Goodput Monitoring and Switching Logic

The file `goodput_monitoring.py` implements the monitoring and decision-making mechanism.

It is responsible for:

- Measuring throughput using system tools (Linux tool ss)  
- Evaluating connection performance  
- Triggering slice switching when performance degradation is detected  

The switching logic follows a performance-driven policy:

- If the measured goodput falls below a predefined threshold, a different slice is selected  

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

---
