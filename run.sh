#!/bin/bash
gunicorn app.main:app \
         --bind 127.0.0.1:7890 \
         --workers 4 \
         --worker-class uvicorn.workers.UvicornWorker

