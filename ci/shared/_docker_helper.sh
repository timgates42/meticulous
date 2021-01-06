#!/bin/bash

function docker_compose_run() {
    USEROPT="$(id -u):$(id -g)"
    docker-compose -p "py${PYVER}" build --build-arg PYVER="${PYVER}"
    docker-compose -p "py${PYVER}" up -d
    docker-compose -p "py${PYVER}" run --rm -u "${USEROPT}" "$@"
    docker-compose -p "py${PYVER}" down
}
