.PHONY: help
.DEFAULT_GOAL := help

help: ## PTG API Server
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)



full: https services ml dash  ## bring the full system up

https:  ## bring up the https reverse proxy
	docker-compose -f docker-compose.https.yaml up -d --build

services: base  ## bring just the services up
	docker-compose up -d --build

record: base  ## bring up the recording containers
	cd ptg-server-ml && docker-compose -f docker-compose.record.yaml up -d --build && cd -

dash:  ## bring up the dashboard containers
	cd tim-dashboard && ls && docker-compose --env-file ../.env -f docker-compose.prod.yml up -d --build && cd -

base:  ## build the ptgctl container
	cp .env ptg-server-ml/.env
	#docker build -t ptgctl -t ptgctl:latest ./ptgctl
	#docker build -t ptgprocess -t ptgprocess:latest ./ptg-server-ml

pull:
	git pull --recurse-submodules

update: pull services  ## pull then update docker


down:  ## docker-compose down everything
	docker-compose -f docker-compose.yaml -f docker-compose.https.yaml -f ptg-server-ml/docker-compose.yaml down
