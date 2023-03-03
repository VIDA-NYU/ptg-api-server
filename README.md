# PTG API Server (Redesign 2023)

The main desirables:
 - easy to alter data model without touching server (directus)
 - accessible access to deploy custom functions/components that run e.g. when a file is uploaded, without touching server (PaaS)
 - accessible access to deploy ml models (PaaS)
 - ability to label data immediately after it's recorded (automatically available) (label studio)
 - decoupled API components



## Overview

### Data Streaming

Manage data streaming from the hololens and between components.

Components:
 - [up] [redis streamer](https://github.com/VIDA-NYU/redis-streamer): an API wrapper for streaming data to and from redis
    - can manage multiple devices and is (partially) backwards compatible with the old redis API
 - [up] redis
 - [up] redis-insight: admin dashboard for redis debugging

### Data Management

Components:
 - [up] [directus](https://directus.io/): database frontend / schema manager - this can be the interface to manage all of our relational data
 - [up] postgres: sql database
 - [up] pgadmin: admin dashboard for postgres debugging
 - [up] minio: s3 file store - files can be uploaded through directus

Directus manages data for:
 - recipes
    - ingredients / tools - could manage image examples
 - recordings
    - file uploads
 - sessions (?)
    - we need to think about how to scope

### Machine Learning

 - [up] mlflow: Can be used to track machine learning experiments and upload/serve machine learning models
 - ? [teachable machine](https://github.com/googlecreativelab/teachablemachine-community): few shot classification tool

### Data Labeling

 - label studio: data labeling tool (stores in postgres which is good)
 - fiftyone: dataset management tool

### Platform-as-a-Service / Functions-as-a-Service

The idea is to make it easy for anyone on the team to deploy individual components to the system.

Components:
 - [caprover](https://caprover.com/): PaaS - lets you deploy apps remotely
 
<!-- Our Options:
 - PaaS: this is a super-set of FaaS (FaaS can be a certain container image on PaaS) - basically each function would need to use FastAPI
    - [caprover](https://caprover.com/) - has both GUI and CLI
        - two issues - no SSO support
    - [coolify](https://coolify.io/) - looks to be only GUI - I don't see CLI. Otherwise it looks nice
 - FaaS: this is if we want to restrict to only event-driven serverless functions
    - nuclio

I'm thinking caprover so we have the flexibility to pivot approaches down the road. -->

### Authentication / Routing

 - [up] Keycloak: single sign on
 - [up] Traefik: reverse proxy
 - [up] traefik-forward-auth: keycloak-traefik proxy for unauth apps


## TODO

 - basically we need to implement all of the glue, however - we need a way of scaling these pipelines per device that connects
    - recorders need to upload to s3
        - do we still want to use zip files? mcap?
    - machine learning needs to be implemented using Ray Serve
        - how do we manage state?
    - replay from s3

 - what if we used Plasma Store to store video frames and only store IDs in redis?
    - we should run a benchmark comparing redis / plasma store
        - size of message vs transmission framerate: plasma alone, redis alone, plasma+mp queue, plasma+redis
