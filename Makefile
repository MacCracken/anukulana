# Makefile for anukulana — Cyrius reference binary (Type-3 pretrained import).
#
#   make build   — build the binary (src/main.cyr -> build/anukulana)
#   make test    — CPU test suites (tests/tcyr/*.tcyr)
#   make lint / fmt-check / vet  — quality gates
#   make clean   — scrub build/

CYRIUS ?= cyrius

.PHONY: check-lib-wiring
check-lib-wiring:
	@if [ -L lib ]; then \
		echo "ERROR: lib/ is a symlink ($$(readlink lib)). Fix: rm lib && cyrius deps"; \
		exit 1; \
	fi

.PHONY: build
build: check-lib-wiring
	@mkdir -p build
	CYRIUS_DCE=1 $(CYRIUS) build src/main.cyr build/anukulana
	@echo "binary: $$(wc -c < build/anukulana) bytes"

.PHONY: test
test: check-lib-wiring
	@for f in tests/tcyr/*.tcyr; do $(CYRIUS) test "$$f" || exit 1; done

.PHONY: lint
lint:
	@fail=0; \
	for f in src/*.cyr tests/tcyr/*.tcyr; do \
		out=$$($(CYRIUS) lint $$f 2>&1); echo "$$out"; \
		echo "$$out" | grep -qE '^\s*warn ' && fail=1; \
	done; \
	[ $$fail -eq 0 ] || { echo "lint: warnings present"; exit 1; }

.PHONY: fmt-check
fmt-check:
	@fail=0; \
	for f in src/*.cyr tests/tcyr/*.tcyr; do \
		if ! $(CYRIUS) fmt $$f --check > /dev/null 2>&1; then \
			echo "needs fmt: $$f"; fail=1; \
		fi; \
	done; \
	[ $$fail -eq 0 ] || { echo "fmt: drift detected"; exit 1; }

.PHONY: vet
vet:
	$(CYRIUS) vet src/main.cyr

.PHONY: clean
clean:
	rm -rf build/
