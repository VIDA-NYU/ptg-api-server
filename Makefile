.PHONY: help
.DEFAULT_GOAL := help

help: ## PTG API Server
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## create env file
	[ ! -f .env ] && cp .env.sample .env

full: https api record ml dash  ## bring the full system up

https: env  ## bring up the https reverse proxy
	docker-compose -f docker-compose.https.yaml up -d --build

api: base  ## bring just the api services up
	docker network create web || : 0
	docker-compose up -d --build

services: api ## alias for api

record: base baseml  ## bring up the recording containers
	cd ptg-server-ml && docker-compose -f docker-compose.record.yaml up -d --build && cd -
	
ml: base baseml  ## bring up the recording containers
	cd ptgctl && docker build -f Dockerfile.gpu -t ptgctl:gpu .
	cd ptg-server-ml && docker-compose -f docker-compose.ml.yaml up -d --build

dash: env  ## bring up the dashboard containers
	cd tim-dashboard && ls && docker-compose --env-file ../.env -f docker-compose.prod.yml up -d --build && cd -

base: env  ## build the ptgctl container
	cp .env ptg-server-ml/.env
	docker build -t ptgctl -t ptgctl:latest ./ptgctl

baseml: base  ## build the ptgctl container
	cp .env ptg-server-ml/.env
	docker build -t ptgprocess -t ptgprocess:latest ./ptg-server-ml

pull:
	git pull --recurse-submodules

down:  ## docker-compose down everything
	[ -f ptg-server-ml/.env ] && cd ptg-server-ml && docker-compose \
		-f docker-compose.ml.yaml \
		-f docker-compose.record.yaml \
		down || : 0
	cd tim-dashboard && docker-compose \
	    -f docker-compose.prod.yml \
	    down || : 0
	docker-compose \
        -f docker-compose.yaml \
        -f docker-compose.https.yaml \
		down || : 0
