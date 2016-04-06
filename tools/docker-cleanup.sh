#!/bin/bash
#
# This script can be used to manually cleanup docker environments left around
# by designate-ruiner. Normally, the ruiner tests will cleanup themselves, but
# things often don't work.

COMPOSE_FILES="-f base.yml -f envs/slappy-bind/designate.yml -f envs/slappy-bind/bind.yml"

# for use with the `docker-compose -p`
COMPOSE_PROJECT_TAG='ruin_designate'

# docker-compose uses the project name to assign unique container names
# for some reason, underscores and hyphens get stripped when this happens
MUNGED_CONTAINER_TAG=`echo $COMPOSE_PROJECT_TAG | sed 's/_\|-//g'`

DESIGNATE_CARINA_DIR='./designate-carina'
pushd $DESIGNATE_CARINA_DIR

# figure out the random tag for a project
RANDOM_TAGS=`docker ps --format "{{.Names}}" | grep $MUNGED_CONTAINER_TAG \
    | cut -d'_' -f1 | sed 's/ruindesignate//g' | uniq`

for random_tag in $RANDOM_TAGS; do
    COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_TAG}_$random_tag"
    set -x
    docker-compose $COMPOSE_FILES -p $COMPOSE_PROJECT_NAME down
    set +x
done

popd
