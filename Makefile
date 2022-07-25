.PHONY: help
.DEFAULT_GOAL := help

help: ## PTG API Server
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)



full: https services ml  ## bring the full system up

https:  ## bring up the https reverse proxy
	docker-compose -f docker-compose.https.yaml up -d --build

services: build-ptgctl  ## bring just the services up
	docker-compose up -d --build

ml: build-ptgctl  ## bring up the machine learning containers
	cd ptg-server-ml && docker-compose up -d --build && cd -

dash:  ## bring up the dashboard containers
	cd tim-dashboard && ls && docker-compose --env-file ../.env -f docker-compose.prod.yml up -d --build && cd -

build-ptgctl:  ## build the ptgctl container
	docker build -t ptgctl -t ptgctl:latest ./ptgctl

pull:
	git pull --recurse-submodules

update: pull services  ## pull then update docker


down:  ## docker-compose down everything
	docker-compose -f docker-compose.yaml -f docker-compose.https.yaml -f ptg-server-ml/docker-compose.yaml down
