.PHONY: help
.DEFAULT_GOAL := help

help: ## PTG API Server
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)



full: https api record ml dash  ## bring the full system up

https:  ## bring up the https reverse proxy
	docker-compose -f docker-compose.https.yaml up -d --build

api: base  ## bring just the api services up
	docker-compose up -d --build

services: api ## alias for api

record: base  ## bring up the recording containers
	cd ptg-server-ml && docker-compose -f docker-compose.record.yaml up -d --build && cd -
	
ml: base  ## bring up the recording containers
	cd ptgctl
	docker build -f Dockerfile.gpu -t ptgctl:gpu .
	cd ..
	cd ptg-server-ml
	docker-compose -f docker-compose.ml.yaml up -d --build
	cd -

dash:  ## bring up the dashboard containers
	cd tim-dashboard && ls && docker-compose --env-file ../.env -f docker-compose.prod.yml up -d --build && cd -

base:  ## build the ptgctl container
	cd ptgctl
	docker build -t ptgctl -t ptgctl:latest .
	cd ..
	
	cd ptg-server-ml
	cp ../.env .env
	docker build -t ptgprocess -t ptgprocess:latest .
	cd ..

pull:
	git pull --recurse-submodules

down:  ## docker-compose down everything
	docker-compose \
		-f docker-compose.yaml \
		-f docker-compose.https.yaml \
		-f ptg-server-ml/docker-compose.ml.yaml \
		-f ptg-server-ml/docker-compose.record.yaml \
		-f tim-dashboard/docker-compose.prod.yaml \
		down
