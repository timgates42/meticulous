#!/bin/bash

set -euxo pipefail

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR="$( dirname "$( dirname "${THISDIR}" )" )"

# shellcheck source=/dev/null
source "${BASEDIR}/ci/in_docker/prepare.sh"

cd "${BASEDIR}/app"
rm -rf dist build
for PYVER in ${PYTHONVERS} ; do
  "python${PYVER}" setup.py sdist bdist_wheel
done
python3.8 -m twine check dist/*
python3.8 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
python3.8 -m twine upload dist/*
