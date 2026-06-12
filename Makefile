.PHONY: dev build run lint typecheck vendor clean help

REGISTRY_MIRROR ?= docker.io

dev:
	python -m veilrender

build:
	docker build -t veilrender .

run:
	docker run --rm -p 7860:7860 -e VEILRENDER_API_TOKEN=dev-token veilrender

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

help:
	@echo "Available targets:"
	@echo "  dev        - Run development server on :7860"
	@echo "  build      - Build Docker image"
	@echo "  run        - Run Docker container"
	@echo "  lint       - Run ruff check and format"
	@echo "  typecheck  - Run ty check"
	@echo "  vendor     - Re-vendor zerodep modules"
	@echo "  clean      - Remove build artifacts"
