.PHONY: help
.DEFAULT_GOAL := help

help: ## setup
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)


full: infra  ## bring up everything

var_files = -var-file=main.tfvars -var-file=secrets.tfvars

plan:
	terraform plan ${var_files}

infra:  ## bring up the infrastructure
	terraform apply ${var_files}

tspass:  ## get the actual timescaledb password
	echo $$(kubectl get secret timescale-credentials  -o json | jq -r '.data.PATRONI_SUPERUSER_PASSWORD' | base64 -d)

tsport:  ## open a port to timescale
	kubectl port-forward  svc/timescale 8432:5432

destroy: ## tear everything down
	terraform destroy ${var_files}
