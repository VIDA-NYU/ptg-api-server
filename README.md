# PTG Data Store API

## Getting started

To bring up the server on your local machine, do:

```bash
make services
```

You can access services using localhost.


To bring up a full server with https reverse proxy, do:

```bash
make full
```

To access:
 - API `localhost:7890` [docs](http://localhost:7890/docs)
 - HLS Video Streaming Server (WIP) `http://localhost:8089`, `rtmp://localhost:1935`
 - [Grafana Dashboards](http://localhost:3000)
 - [Mongo Express Dashboard](http://localhost:8081)


To update and run the latest API changes, do:
```bash
make pull  # optional: pull latest changes
make services
```

## Overview

REST + Web Socket API to interact with the data store. The endpoints are secured by bearer tokens, so one need to authenticate and obtain a token (through the `/token` endpoint) before accessing them. Currently, for development purposes, any **username** and **password** of the same value (e.g. *test:test*, or *user:user*) will be accepted by `/token`. If you're in a hurry, use the following token:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwdGciLCJleHAiOjE2NTI1NDU3MTl9.8S6dal-Q97TfJZG7rYLQWe5n3IovU9qCmtPYo7voNN4
```

Be sure to include the following field in all request header:
```
Authorization: Bearer TOKEN
```
replacing **TOKEN** with the actual token string.

In additional the endpoints presented on the OpenAPI portal, there are also two Web Socket endpoints for streaming data in and out of the store. These cannot be listed because there is no Web Socket specifications on the Open API standard. They are as follows:

### **WebSocket** **`/data/{stream_id}/push`**
Send data to a stream with the following query parameters:
* **stream_id**: string (required) - the unique ID of the stream, or **`*`** to push data to multiple streams (implying **batch** is `true`).
* **batch**: bool (default: `false`) - set to `true` if entries will be sent in batches (in an alternate text and bytes format, more below)
* **ack**: bool (default: `false`) - set to `true` if would like to server to respond to each entry/batch with inserted entry IDs

If **batch** and **ack** are set to `false` (by default), the client only needs to send data (binary expected) one time step at a time, for example:
```python
for entry in source:
  WebSocket.sendBinary(entry)
```

When **batch** is set to `true` or **stream_id** is `*`, the client must send to the server the correspond stream ID and offset of each data entry in the batch as a JSON list of list (e.g. `[["stream0", 0],["stream2",100],["stream0",256],...[`, then send the entire batch a single binary blob. For example:
```python
# for sending multiple streams and/or in batches
for batch in source:
  bytes = bytearray()
  entries = []
  for entry in batch:
    entries.append((streamname,len(bytes)))
    bytes += entry
  WebSocket.sendText(json.dumps(entries))
  WebSocket.sendBinary(bytes)
```

If **batch** is set to `true` but **stream_id** is not `*`, stream information of the batch entry header will be ignored (always push to the specify stream).

When **ack** is set to `true`, the server will send a confirmation message back to the client (IDs associated with each entry in the data store). The client must receive the message before going to the next push. For example, a request to `/data/mystream/push?ack=true` can be handled as:
```python
for entry in source:
  WebSocket.sendBinary(entry)
  entryIds = WebSocket.receiveText().split(',')
  # len(entryIds) should be 1 since batching is off
```

### **WebSocket** **`/data/{stream_id}/pull`**
Retrieve data from a stream with the following query parameters:
* **stream_id**: string (required) - the unique ID of the streams, separated by `+`
* **count**: int (default: `1`) - the maximum number of entries for each receive
* **last_entry_id**: bool (default: `$`) - only retrieve entries laters than the provided (last entry) ID

This endpoint assumes that data are always being sent in batches (even when **count** is set to `1`). The server socket will send back two messages: one JSON message describing the offsets of the batch `[[stream_id,entry_id,offset],...]`; and one binary message for the actual entry data. A sample handler could be:
```python
while True
  entries = json.loads(WebSocket.receiveText())
  bytes = WebSocket.receiveBinary()
  numEntries = len(entries)
```

This is a blocking call, if there's no entry matched the condition (no later than **last_entry_id**), the server will wait until it's available.

## Setup Instructions

These instructions are for setting up the server environment. You don't need to go through these if you just want to use the API. For development, we have a server running [here](https://eng-nrf233-01.engineering.nyu.edu/ptg/api/docs).

The code requires Python 3.10+ and rely on [Redis](https://redis.io/), [FastAPI](https://fastapi.tiangolo.com/), [Uvcorn](https://www.uvicorn.org/), [Gunicorn](https://gunicorn.org/) to run the server. It is easiest to create a Python's virtual environment for the server using [Miniconda](https://docs.conda.io/en/latest/miniconda.html) since some of the packages requires binary executables installed (`pip` should work with some additional environment settings but be sure that you have Python 3.10+ first).

### Setup Miniconda/Conda environment
```bash
cd ptg-api-server
conda create --name ptg --file conda_requirements.txt
```

After that, we may `conda activate ptg` to run the services inside our new environment.

### Start the Redis server
We need to run the Redis server before starting our API service. Redis can be run as daemonize (in the background) or interactive. For the development environment, since the log files are not required to be stored, the preferred method is to use `screen` session to run Redis interactively so that we can track what's going with the server. For example:
```bash
screen -S redis
conda activate ptg
cd ptg-api-server/redis
./start.sh
```

Alternatively, we can start Redis in daemonized mode (without screen):
```bash
conda activate ptg
cd ptg-api-server/redis
./start.sh --daemonize yes
```

Redis can be stopped by simply running the `stop.sh` script. This script only stops the Redis instance that runs on port 6789.

### Start the REST API server
The following script starts the API service in interactive mode. 
```bash
conda activate ptg
cd ptg-api-server
./run.sh
```
After that, the server will be run on port `:7890`, i.e. we can access the APIs through `http://127.0.0.1:7890`.
