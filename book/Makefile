.DEFAULT_GOAL := test

PYTHON ?= python3
SWIFT ?= swift
REPO_ROOT := $(abspath $(CURDIR)/..)

.PHONY: test ci validate swift

test: ci

ci:
	@echo "Running unified CI harness..."
	PYTHONPATH=$(REPO_ROOT) SWIFT=$(SWIFT) $(PYTHON) ci.py

# Optional subtargets to run pieces directly.
validate:
	PYTHONPATH=$(REPO_ROOT) $(PYTHON) -c "import ci; ci.run_python_harness()"

swift:
	PYTHONPATH=$(REPO_ROOT) SWIFT=$(SWIFT) $(PYTHON) -c "import ci; ci.run_swift_build()"
