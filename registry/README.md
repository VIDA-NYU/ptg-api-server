# Deploying without the source code

## Install

Download the docker-compose file.

Bring up the services:
```bash
docker-compose up -d
```

Install ptgctl
```bash
pip install git+https://github.com/VIDA-NYU/ptgctl.git
```

Relevant Pages:
 - http://localhost:3010 - Argus (Online)
 - http://localhost:3000 - Argus (Historical)

## Streaming data

Install the hololens app.



#### Backup plan

Or just pretend to stream some data:
```bash
ptgctl mock video main path/to/video.mp4
```

However this will only mock the video stream so you won't have 3D renderings. This is just to verify that the server is running.

## Make a recording
Go on the dashboard. Click record. When you're done, click stop recording. Then go to [ARGUS](http://localhost:3000) to view the data from the recording.
