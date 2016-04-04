SHELL := /bin/bash

all: designate-carina deps ruin

designate-carina:
	git clone git@github.com:rackerlabs/designate-carina.git
	cd designate-carina && git checkout d8f6fefa300a87d515bfa9313b8921b2555d3ca4

.venv:
	virtualenv .venv

deps: .venv
	.venv/bin/pip install -r test-requirements.txt

ruin:
	. .venv/bin/activate && py.test -v ./ruiner/

clean:
	rm -rf designate-carina/
