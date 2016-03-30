SHELL := /bin/bash

all: designate-carina deps ruin

designate-carina:
	git clone git@github.com:rackerlabs/designate-carina.git
	cd designate-carina && git checkout 196b9b01d358bba089dda5bd1060953fde4b9411

.venv:
	virtualenv .venv

deps: .venv
	.venv/bin/pip install -r test-requirements.txt

ruin:
	. .venv/bin/activate && py.test -v ./ruiner/

clean:
	rm -rf designate-carina/
