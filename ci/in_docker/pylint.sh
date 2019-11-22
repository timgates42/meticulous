#!/bin/bash

set -euxo pipefail

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR="$( dirname "$( dirname "${THISDIR}" )" )"

PYTHON="${1}"
TARGET="${2}"
if ! "${PYTHON}" -m pylint --rcfile "${BASEDIR}/app/.pylintrc" "${TARGET}" ; then
   echo "Pylint failed on ${TARGET}" >&2
   exit 255
fi
