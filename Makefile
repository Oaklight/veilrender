.PHONY: dev build run lint typecheck vendor clean deploy-dev deploy-hf help

REGISTRY_MIRROR ?= docker.io
DOCKER_IMAGE := oaklight/veilrender
VERSION := $(shell grep -oE '__version__[[:space:]]*=[[:space:]]*"[^"]+"' src/veilrender/__init__.py | grep -oE '"[^"]+"' | tr -d '"' || echo "0.1.0")

dev:
	python -m veilrender

build:
	docker build -t $(DOCKER_IMAGE):latest .

run:
	docker run --rm -p 7860:7860 -e VEILRENDER_API_TOKEN=dev-token $(DOCKER_IMAGE):latest

lint:
	ruff check --fix src/veilrender/ --exclude src/veilrender/_vendor/
	ruff format src/veilrender/ --exclude src/veilrender/_vendor/

typecheck:
	ty check src/veilrender/

vendor:
	cd ~/projects/zerodep && python zerodep.py add httpserver readability soup markdown cache config useragent retry structlog -d $(CURDIR)/src/veilrender/_vendor/ -y -f

clean:
	rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ──────────────────────────────────────────────
# Dev Deployment
# ──────────────────────────────────────────────

SSH_TARGET ?=
DEVTEST_STACK ?= /dockervol/dockge/stacks/veilrender

# Build dev-test image, push to remote VPS, restart container.
# Usage: make deploy-dev SSH_TARGET=cloud.usa2
deploy-dev:
ifndef SSH_TARGET
	$(error SSH_TARGET is required. Usage: make deploy-dev SSH_TARGET=cloud.usa2)
endif
	@set -e; \
	COMMIT=$$(git rev-parse --short HEAD); \
	DEV_VER="$(VERSION).dev0+g$$COMMIT"; \
	echo "==> Building Docker image ($$DEV_VER)..."; \
	docker build -t $(DOCKER_IMAGE):dev-test -q .; \
	echo "==> Deploying to $(SSH_TARGET) via zstd..."; \
	docker save $(DOCKER_IMAGE):dev-test | zstd -3 | ssh $(SSH_TARGET) \
		'zstd -d | docker load && \
		 cd $(DEVTEST_STACK) && \
		 sed -i "s|image:.*|image: $(DOCKER_IMAGE):dev-test|" compose.yaml && \
		 docker compose up -d --force-recreate && \
		 sleep 5 && \
		 echo "=== Health check ===" && \
		 curl -sS -o /dev/null -w "%{http_code} /health\n" http://127.0.0.1:7860/ || true'; \
	echo "==> VPS dev-test deployed successfully ($$DEV_VER)."

# Deploy to Hugging Face Spaces by pushing current code.
# Usage: make deploy-hf HF_SPACE=oaklight/veilrender
HF_SPACE ?=
deploy-hf:
ifndef HF_SPACE
	$(error HF_SPACE is required. Usage: make deploy-hf HF_SPACE=oaklight/veilrender)
endif
	@set -e; \
	COMMIT=$$(git rev-parse --short HEAD); \
	echo "==> Deploying to HF Space $(HF_SPACE) ($$COMMIT)..."; \
	TMP=$$(mktemp -d); \
	git clone --depth 1 . "$$TMP/repo"; \
	cd "$$TMP/repo"; \
	printf '%s\n' \
		'---' \
		'title: VeilRender' \
		'emoji: 👻' \
		'colorFrom: gray' \
		'colorTo: purple' \
		'sdk: docker' \
		'app_port: 7860' \
		'pinned: false' \
		'---' \
		'' \
		'# VeilRender' \
		'' \
		"Headless browser rendering API. See [GitHub repo]($$(git remote get-url origin | sed 's/\.git$$//; s|git@github.com:|https://github.com/|')) for full documentation." \
		> README.md; \
	rm -rf .github .pre-commit-config.yaml CLAUDE.md README_en.md README_zh.md Makefile; \
	git add -A; \
	git commit -m "deploy $$COMMIT" --allow-empty; \
	git push --force "https://oauth2:$${HF_TOKEN}@huggingface.co/spaces/$(HF_SPACE)" HEAD:main; \
	rm -rf "$$TMP"; \
	echo "==> HF Space deployed successfully ($$COMMIT)."

help:
	@echo "Available targets:"
	@echo "  dev          - Run development server on :7860"
	@echo "  build        - Build Docker image"
	@echo "  run          - Run Docker container"
	@echo "  lint         - Run ruff check and format"
	@echo "  typecheck    - Run ty check"
	@echo "  vendor       - Re-vendor zerodep modules"
	@echo "  clean        - Remove build artifacts"
	@echo "  deploy-dev   - Build dev image and deploy to remote VPS"
	@echo "  deploy-hf    - Deploy to Hugging Face Spaces"
	@echo ""
	@echo "Variables:"
	@echo "  SSH_TARGET=<host>     - SSH target for deploy-dev (required)"
	@echo "  HF_SPACE=<user/repo> - HF Space for deploy-hf (required)"
	@echo "  HF_TOKEN             - HF token (env var, required for deploy-hf)"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy-dev SSH_TARGET=cloud.usa2"
	@echo "  make deploy-hf HF_SPACE=oaklight/veilrender"
