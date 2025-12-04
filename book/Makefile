.DEFAULT_GOAL := test

PYTHON ?= python3
SWIFT ?= swift
REPO_ROOT := $(abspath $(CURDIR)/..)

.PHONY: test python-tests swift-check

test: python-tests swift-check

python-tests:
	@echo "Running Python tests (pytest-free harness)..."
	PYTHONPATH=$(REPO_ROOT) $(PYTHON) -m book.tests.run_all

swift-check:
	@echo "Building Swift sources..."
	cd graph && SWIFT_BIN="$(SWIFT)" $(PYTHON) swift_build.py
