'''

I want to start a recording:
POST /recordings/start?filter=

 - get available streams

'''
import requests
from fastapi import FastAPI
from ray import serve

# 1: Define a FastAPI app and wrap it in a deployment with a route handler.
app = FastAPI()

@serve.deployment(route_prefix="/")
@serve.ingress(app)
class RecordingDeployment:
    @app.get("/hello")
    def say_hello(self, name: str) -> str:
        return f"Hello {name}!"

# 2: Deploy the deployment.
serve.start()
FastAPIDeployment.deploy()