SHELL := /bin/bash

all: designate-carina ruin

designate-carina:
	git clone git@github.com:rackerlabs/designate-carina.git
	cd designate-carina && git checkout 763dfa4a123def68b68fcfc740555309e21956ca

lint:
	tox -e flake8

ruin: lint
	tox -e py27

clean:
	rm -rf designate-carina/
