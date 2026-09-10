.PHONY: test-unit test-contract test-integration test-security test-web test-e2e test-all lint typecheck build

test-unit:
	python -m nox -s unit

test-contract:
	python -m nox -s contract

test-integration:
	@echo "Integration tests begin in a later stage."

test-security:
	python -m nox -s security

test-web:
	pnpm --filter @flopbench/web test

test-e2e:
	pnpm --filter @flopbench/web e2e

test-all: test-unit test-contract test-security test-web test-e2e

lint:
	python -m nox -s lint
	pnpm --filter @flopbench/web lint

typecheck:
	python -m nox -s typecheck
	pnpm --filter @flopbench/web typecheck

build:
	python -m nox -s build
	pnpm --filter @flopbench/web build
