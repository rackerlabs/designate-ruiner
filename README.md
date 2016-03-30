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


Setup
-----

*For now, you will need to go to [designate-carina](https://github.com/rackerlabs/designate-carina)
and `docker-compose up` your designate first*

Provided your designate is running in docker via designate-carina, then you can
just do:

    make all

This does all the parts below and only requires that `git` and `virtualenv` are
installed.

##### fetch designate-carina

The tests leverage [designate-carina](https://github.com/rackerlabs/designate-carina)
for the docker bits. To fetch this, simply run:

    make clean && make designate-carina

The version of designate-carina to use is pinned in the makefile.

##### Install python libs

Create and activate a virtualenv.

    virtualenv .venv
    . .venv/bin/activate

Then install the `test-requirements.txt`

    pip install -r test-requirements.txt


Run
---

`py.test` is installed as the test runner.

    py.test -v ./ruiner/tests
