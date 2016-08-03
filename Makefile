SHELL := /bin/bash

all: designate-carina ruin

designate-carina:
	git clone git@github.com:rackerlabs/designate-carina.git
	cd designate-carina && git checkout 50a37aed8d33edaff7062947f4d52eca322d46ce

lint:
	tox -e flake8

ruin: lint
	tox -e py27

clean:
	rm -rf designate-carina/
