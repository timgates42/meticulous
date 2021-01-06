#!/bin/bash

set -euxo pipefail

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR="$( dirname "$( dirname "${THISDIR}" )" )"

# shellcheck source=/dev/null
source "${BASEDIR}/ci/in_docker/prepare.sh"

cd "${BASEDIR}"
find . -iname \*.sh -print0 | xargs -0 shellcheck
# Run spelling in root to check docs
"python${PYVER}" -m spelling
# Run black to check all python
"python${PYVER}" -m black --check --diff "${BASEDIR}"
cd "${BASEDIR}/app"
"python${PYVER}" -m flake8 "${MODULES[@]}"
"python${PYVER}" -m isort -rc -c -m 3 -tc -w 88 --diff "${MODULES[@]}"
"python${PYVER}" -m bandit -r "${MODULES[@]}"
find "${MODULES[@]}" -iname \*.py -print0 | xargs -0 -n 1 "${BASEDIR}/ci/in_docker/pylint.sh" "python${PYVER}"
PYTEST_FAIL="NO"
if ! "python${PYVER}" -m pytest -n auto --cov-config=.coveragerc --cov-fail-under=100 "--cov=${MAIN_MODULE}" --cov-report=xml:test-cov.xml --cov-report=html ; then
  PYTEST_FAIL="YES"
fi
if [ -n "${TRAVIS_JOB_ID:-}" ] ; then
  "python${PYVER}" -m coveralls
fi
if [ "${PYTEST_FAIL}" == "YES" ] ; then
  echo 'PyTest Failed!' >&2
  exit 1
fi
# validate doco
"${BASEDIR}/ci/in_docker/doco.sh"
echo 'Testing Complete'
