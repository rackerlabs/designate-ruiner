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


Using the `ruiner` script
-------------------------

Optionally, you may use the `ruiner` script to run tests as well. This is a
pure wrapper around `py.test`.

To install the `ruiner` script:

    $ pip install test-requirements.txt
    $ pip install .

To run tests:

    $ ruiner py.test ./ruiner/test/

Show all log dirs from previous test runs (most recent first):

    $ ruiner logs
    ./ruiner-logs/2016-08-10_18_18_03.688111
    ./ruiner-logs/2016-08-10_18_02_36.744491
    ./ruiner-logs/2016-08-10_18_01_38.265400
    ...

Show the log dir from the last run:

    $ ruiner logs --last
    ./ruiner-logs/2016-08-10_18_18_03.688111

List all log files from the last run:

     $ ruiner logs --last -r
    ./ruiner-logs/2016-08-10_18_18_03.688111/master.log
    ./ruiner-logs/2016-08-10_18_18_03.688111/ruiner.test.test_docker_composer.TestDockerComposer.test_args/master.log
    ./ruiner-logs/2016-08-10_18_18_03.688111/ruiner.test.test_docker_composer.TestDockerComposer.test_get_host/master.log
    ./ruiner-logs/2016-08-10_18_18_03.688111/ruiner.test.test_docker_composer.TestDockerComposer.test_get_host_respects_docker_host/master.log
    ...


### Why to use the `ruiner` script to run `designate-ruiner` tests

- It is not a custom test runner. `ruiner py.test <args>` uses `py.test`. All
args (including flags) are passed along to `py.test` unmodified, so all
`py.test` functionality is available.
- It ensures timestamped log directories, in a way that works with multiple
processes. By default, your logs are placed in `<log-dir>/latest/`. With
`ruiner`, a new directory is created for each run, like
`<log-dir>/2016-08-10_18_18_03.688111/`.
- It supports listing logs from previous runs.
