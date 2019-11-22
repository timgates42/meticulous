#!/bin/bash

set -euxo pipefail

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR="$( dirname "$( dirname "${THISDIR}" )" )"

# shellcheck source=/dev/null
source "${BASEDIR}/ci/in_docker/prepare.sh"

cd "${BASEDIR}/docs"
make html
