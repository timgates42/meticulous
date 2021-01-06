#!/bin/bash

set -euxo pipefail

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR="$( dirname "$( dirname "${THISDIR}" )" )"

# shellcheck source=/dev/null
source "${BASEDIR}/ci/in_docker/prepare.sh"

cd "${BASEDIR}/app"
rm -rf dist build
"python${PYVER}" setup.py sdist bdist_wheel
"python${PYVER}" -m twine check dist/*
"python${PYVER}" -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
"python${PYVER}" -m twine upload dist/*
