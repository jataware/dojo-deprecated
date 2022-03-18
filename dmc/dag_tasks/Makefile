VERSION=1.0.0


.DEFAULT_GOAL := build

check-%:
	@: $(if $(value $*),,$(error $* is undefined))


.PHONY: docker_build
docker_build:
	docker build -t jataware/dag-tasks:${VERSION} -t jataware/dag-tasks:dev -t dag-tasks:dev .

.PHONY: lint
lint:
	isort --force-single-line-imports scripts/*.py
	autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place scripts/*.py
	black --line-length 119 scripts/*.py
	isort scripts/*.py
	flake8 scripts/*.py


.PHONY: build
build:| lint docker_build


.PHONY: docker_login-dockerhub
docker_login-dockerhub:| check-DOCKERHUB_USER check-DOCKERHUB_TOKEN  ## Login to docker registery. Requires DOCKERHUB_USER and DOCKERHUB_TOKEN to be set in the environment
	@printf "${DOCKERHUB_TOKEN}\n" | docker login -u "${DOCKERHUB_USER}" --password-stdin



.PHONY: docker_push
docker_push:| docker_login-dockerhub  ## Pushes docker image to docker hub
	@echo "push ${VERSION}"
	docker push "jataware/dag-tasks:${VERSION}"
	docker push "jataware/dag-tasks:dev"
