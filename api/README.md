# Slice API

This directory contains the REST API for slice selection and switching.

## Description

The API abstracts low-level modem interaction (AT commands and QMI) and provides HTTP endpoints for managing PDU sessions and network slice selection.

## Requirements

Install Python dependencies:

```
pip install -r ../requirements.txt
```


## Run


```
sudo uvicorn Slice_API:app --host 0.0.0.0 --port 5000
```

The API will be available at:

http://localhost:5000


## Interactive API Documentation

The API provides Swagger documentation at:

http://localhost:5000/docs



## Endpoints

| Method | Endpoint              | Description                                                       |
|--------|----------------------|-------------------------------------------------------------------|
| GET    | `/status`            | Returns current network status (DNN and active slice)            |
| GET    | `/available_slices`  | Returns configured PDU profiles and slice information            |
| GET    | `/alternative_slice` | Returns an alternative slice with the same DNN                   |
| POST   | `/activate_pdu`      | Activates a PDU session for a given CID                          |
| POST   | `/disconnect`        | Releases the active PDU session      
