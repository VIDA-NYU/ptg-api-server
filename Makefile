.PHONY: help
.DEFAULT_GOAL := help

help: ## PTG API Server
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)



full: https services  ## bring the full system up

https:  ## bring up the https reverse proxy
	docker-compose -f docker-compose.https.yaml up -d --build

services: build-ptgctl  ## bring just the services up
	docker-compose up -d --build

build-ptgctl:  ## build the ptgctl container
	docker build -t ptgctl -t ptgctl:latest ./ptgctl

pull:
	git pull --recurse-submodules

update: pull services  ## pull then update docker