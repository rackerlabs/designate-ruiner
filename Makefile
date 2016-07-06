SHELL := /bin/bash

all: designate-carina ruin

designate-carina:
	git clone git@github.com:rackerlabs/designate-carina.git
	cd designate-carina && git checkout 0af064d6b68afedaad2ee2b9de7e4e37df98835f

lint:
	tox -e flake8

ruin: lint
	tox -e py27

clean:
	rm -rf designate-carina/
