SHELL := /bin/bash
.DEFAULT_GOAL := help
FORGE := .tools/bin/forge
PYTHON ?= python3
RPC_URL ?= http://127.0.0.1:8545
STATE ?= .tools/demo-state.json
SEPOLIA_STATE ?= .tools/sepolia/state.json

.PHONY: help install build fmt fmt-check test test-python coverage gas gas-matrix validate anvil deploy configure fund approve-a approve-b approve-funds approvals enable buy list trade claim demo
help:
	@echo 'install build fmt fmt-check test test-python coverage gas gas-matrix validate anvil'
	@echo 'deploy configure fund approvals enable buy list trade claim (RPC_URL y STATE opcionales)'
	@echo 'sepolia-doctor / sepolia-demo / sepolia-reconcile / sepolia-check (ver docs/sepolia.md)'
	@echo 'demo: dos recorridos completos en redes nuevas con evidencia en .tools/demo/'
install:
	bash tools/setup.sh
build:
	$(FORGE) build
fmt:
	$(FORGE) fmt
fmt-check:
	$(FORGE) fmt --check
test:
	$(FORGE) test -vv
test-python:
	$(PYTHON) -m unittest discover -s tools -p 'test_*.py' -v
coverage:
	$(FORGE) coverage --report summary --report debug
gas:
	$(FORGE) build --force
	$(FORGE) test --gas-report
gas-matrix:
	$(FORGE) build --force
	$(PYTHON) tools/measure-gas.py
validate:
	$(PYTHON) tools/validate-system.py
anvil:
	.tools/bin/anvil --host 127.0.0.1 --chain-id 31337 --hardfork paris --silent
deploy configure fund approve-a approve-b approve-funds enable buy list trade claim:
	$(PYTHON) tools/demo.py --stage $@ --rpc-url '$(RPC_URL)' --state '$(STATE)'
approvals:
	$(MAKE) approve-a
	$(MAKE) approve-b
	$(MAKE) approve-funds
demo:
	$(PYTHON) tools/demo.py

SEPOLIA_STAGES := doctor deploy verify configure fund approve-a approve-b approve-funds enable buy list trade claim reconcile check demo
.PHONY: $(addprefix sepolia-,$(SEPOLIA_STAGES)) sepolia-approvals
$(addprefix sepolia-,$(SEPOLIA_STAGES)):
	$(PYTHON) tools/sepolia.py --stage $(patsubst sepolia-%,%,$@) --state '$(SEPOLIA_STATE)'
sepolia-approvals:
	$(MAKE) sepolia-approve-a
	$(MAKE) sepolia-approve-b
	$(MAKE) sepolia-approve-funds
.PHONY: sepolia-recover-deploy
sepolia-recover-deploy:
	$(PYTHON) tools/sepolia.py --stage recover-deploy --failed-tx '$(FAILED_TX)' --state '$(SEPOLIA_STATE)'
