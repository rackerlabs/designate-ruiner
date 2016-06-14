SHELL := /bin/bash

all: designate-carina ruin

designate-carina:
	git clone git@github.com:rackerlabs/designate-carina.git
	cd designate-carina && git checkout 4da2d7d137c41e61fb801e39fa2fc8ccc1e98392

lint:
	tox -e flake8

ruin: lint
	tox -e py27

clean:
	rm -rf designate-carina/
