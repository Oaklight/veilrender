.PHONY: dev build build-gateway run lint typecheck vendor clean build-package push-package deploy-dev update-blocklist help

REGISTRY_MIRROR ?= docker.io
BLOCKLIST_URL := https://cdn.jsdelivr.net/gh/StevenBlack/hosts@master/hosts
DOCKER_IMAGE := oaklight/veilrender
VERSION := $(shell grep -oE '__version__[[:space:]]*=[[:space:]]*"[^"]+"' src/veilrender/__init__.py | grep -oE '"[^"]+"' | tr -d '"' || echo "0.1.0")

dev:
	python -m veilrender

build:
	docker build --target full -t $(DOCKER_IMAGE):latest .

build-gateway:
	docker build --target gateway -t $(DOCKER_IMAGE):gateway .

run:
	docker run --rm -p 7860:7860 -e VEILRENDER_API_TOKEN=dev-token $(DOCKER_IMAGE):latest

lint:
	ruff check --fix src/veilrender/ --exclude src/veilrender/_vendor/
	ruff format src/veilrender/ --exclude src/veilrender/_vendor/

typecheck:
	ty check src/veilrender/

vendor:
	cd ~/projects/zerodep && python zerodep.py add httpserver readability soup cache s3 -d $(CURDIR)/src/veilrender/_vendor/ -y -f

update-blocklist:
	curl -sL "$(BLOCKLIST_URL)" \
	  | grep "^0.0.0.0 " | awk '{print $$2}' | grep -v "^0.0.0.0$$" \
	  > src/veilrender/data/blocklist.txt
	@echo "Updated blocklist: $$(wc -l < src/veilrender/data/blocklist.txt) domains"

clean:
	rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ──────────────────────────────────────────────
# Package targets
# ──────────────────────────────────────────────

build-package: clean
	python -m build

push-package:
	twine upload dist/*

# ──────────────────────────────────────────────
# Dev Deployment
# ──────────────────────────────────────────────

SSH_TARGET ?=
DEVTEST_STACK ?= /dockervol/dockge/stacks/veilrender-dev

# Build dev-test image, push to remote VPS, restart container.
# Usage: make deploy-dev SSH_TARGET=cloud.usa2
#        make deploy-dev SSH_TARGET=cloud.usa2 POOL=1   (gateway + worker)
POOL ?=
deploy-dev:
ifndef SSH_TARGET
	$(error SSH_TARGET is required. Usage: make deploy-dev SSH_TARGET=cloud.usa2)
endif
	@set -e; \
	COMMIT=$$(git rev-parse --short HEAD); \
	DEV_VER="$(VERSION).dev0+g$$COMMIT"; \
	echo "==> Building Docker image ($$DEV_VER)..."; \
	if [ -n "$(POOL)" ]; then \
		docker build --target gateway -t $(DOCKER_IMAGE):dev-test -q .; \
	else \
		docker build --target full -t $(DOCKER_IMAGE):dev-test -q .; \
	fi; \
	echo "==> Deploying to $(SSH_TARGET) via zstd..."; \
	if [ -n "$(POOL)" ]; then \
		COMPOSE_SRC="deploy/compose-pool.yaml"; \
	else \
		COMPOSE_SRC="deploy/compose-dev.yaml"; \
	fi; \
	docker save $(DOCKER_IMAGE):dev-test | zstd -3 | ssh $(SSH_TARGET) \
		'zstd -d | docker load'; \
	scp $$COMPOSE_SRC $(SSH_TARGET):$(DEVTEST_STACK)/compose.yaml; \
	ssh $(SSH_TARGET) \
		'cd $(DEVTEST_STACK) && \
		 sed -i "s|image: oaklight/veilrender:[^ ]*|image: $(DOCKER_IMAGE):dev-test|" compose.yaml && \
		 sed -i "s|VEILRENDER_API_TOKEN=changeme|VEILRENDER_API_TOKEN=$${VEILRENDER_API_TOKEN:-changeme}|" compose.yaml && \
		 docker compose up -d --force-recreate && \
		 sleep 5 && \
		 echo "=== Health check ===" && \
		 curl -sS -o /dev/null -w "%{http_code} /health\n" http://127.0.0.1:7861/ || true'; \
	echo "==> VPS dev-test deployed successfully ($$DEV_VER, $${COMPOSE_SRC})."

help:
	@echo "Available targets:"
	@echo "  dev            - Run development server on :7860"
	@echo "  build          - Build full Docker image (with CloakBrowser)"
	@echo "  build-gateway  - Build gateway-only Docker image (no browser)"
	@echo "  run            - Run Docker container"
	@echo "  lint         - Run ruff check and format"
	@echo "  typecheck    - Run ty check"
	@echo "  vendor       - Re-vendor zerodep modules"
	@echo "  update-blocklist - Update ad/tracker blocklist from StevenBlack/hosts"
	@echo "  clean         - Remove build artifacts"
	@echo "  build-package - Build Python package"
	@echo "  push-package  - Push package to PyPI"
	@echo "  deploy-dev    - Build dev image and deploy to remote VPS"
	@echo ""
	@echo "Variables:"
	@echo "  SSH_TARGET=<host>     - SSH target for deploy-dev (required)"
	@echo "  POOL=1                - Use pool mode (gateway + CloakBrowser workers)"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy-dev SSH_TARGET=cloud.usa2"
	@echo "  make deploy-dev SSH_TARGET=cloud.usa2 POOL=1"
