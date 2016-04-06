SHELL := /bin/bash

all: designate-carina ruin

designate-carina:
	git clone git@github.com:rackerlabs/designate-carina.git
	cd designate-carina && git checkout 538b0bf5f70d0279401be6a2072a32b8f2f2fba9

lint:
	tox -e flake8

ruin: lint
	tox -e py27

clean:
	rm -rf designate-carina/
