Overview
--------

`designate-ruiner` is a set of intrusive functional tests for Designate. It has
the ability to:

- configure and deploy designate as part of test setup
- programmatically stop and start services from within test methods

This allows you to write automated tests for any kind of configuration of
Designate. With the ability to start/stop services, `designate-ruiner` allows
you to easily write automated resilience tests for designate's nameserver sync
process.


Quickstart
----------

### Install docker

You will first need to [install `docker` and `docker-compose`](
https://docs.docker.com/engine/installation/).

A config file location is specified by `$RUINER_CONF`. An example config is:

    $ cat $RUINER_CONF
    [ruiner]
    # build_timeout = 120
    # build_interval = 3
    # service_startup_wait_time = 15

### Setup [designate-carina](https://github.com/rackerlabs/designate-carina)

To do this:

    make clean && make designate-carina

The tests leverage designate-carina for the docker bits. For now, we need to
clone the designate-carina repository to a local dir. The version of
designate-carina to checkout is pinned in the makefile.

### Run the tests

The easiest away is using `tox`,

    ### consider creating a virtualenv first
    $ pip install tox
    $ tox

This will run the pep8 checks and the reliability tests for designate.
