#!/bin/bash

set -euxo pipefail

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR="$( dirname "${THISDIR}" )"

if ! command -v docker ; then
    echo 'Docker is missing!' >&2
    exit 1
fi
if ! command -v docker-compose ; then
    echo 'Docker-Compose is missing!' >&2
    exit 1
fi
cd "${BASEDIR}"

CMD="${1:-test}"
if [[ "$CMD" =~ [^a-zA-Z0-9_] ]]; then
    echo "Invalid Command: ${CMD}" >&2
    exit 1
fi
TASK="ci/in_docker/${CMD}.sh"
OUT_DOCKER="${BASEDIR}/${TASK}"
IN_DOCKER="/workspace/${TASK}"
if [ ! -f "${OUT_DOCKER}" ] ; then
    echo "No command: ${OUT_DOCKER}" >&2
    exit 1
fi
if [ ! -x "${OUT_DOCKER}" ] ; then
    echo "Not executable: ${OUT_DOCKER}" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${BASEDIR}/ci/shared/_docker_helper.sh"

docker_compose_run "app" "${IN_DOCKER}" "${@:2}"


