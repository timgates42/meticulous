#!/bin/bash

set -euxo pipefail

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR="$( dirname "$( dirname "${THISDIR}" )" )"

# shellcheck source=/dev/null
source "${BASEDIR}/ci/in_docker/prepare.sh"

cd "${BASEDIR}"
find . -iname \*.sh -print0 | xargs -0 shellcheck

# Version independant checks
LATESTPYVER=3.8
PYVER="${LATESTPYVER}"
# Run spelling in root to check docs
"python${PYVER}" -m spelling

# Run in app for python checks
cd "${BASEDIR}/app"
# Run black to check all python on 3.8 only
"python${PYVER}" -m black --check --diff "${BASEDIR}"
# Run pylint to lint all python on 3.8 only
find "${MODULES[@]}" -iname \*.py -print0 | xargs -0 -n 1 "${BASEDIR}/ci/in_docker/pylint.sh" "python${PYVER}"

# Version dependant checks
for PYVER in ${PYTHONVERS} ; do
  "python${PYVER}" -m flake8 "${MODULES[@]}"
  "python${PYVER}" -m isort -rc -c -m 3 -tc -w 88 --diff "${MODULES[@]}"
  "python${PYVER}" -m bandit -r "${MODULES[@]}"
  PYTEST_FAIL="NO"
  if ! "python${PYVER}" -m pytest --cov-config=.coveragerc --cov-fail-under=0 "--cov=${MAIN_MODULE}" --cov-report=xml:test-cov.xml --cov-report=html --cov-report=term-missing ; then
    PYTEST_FAIL="YES"
  fi
  if [ -n "${TRAVIS_JOB_ID:-}" ] && [ "${PYVER}" == "${LATESTPYVER}" ] ; then
    "python${PYVER}" -m coveralls
  fi
  if [ "${PYTEST_FAIL}" == "YES" ] ; then
    echo 'PyTest Failed!' >&2
    exit 1
  fi
done
# validate doco
"${BASEDIR}/ci/in_docker/doco.sh"
echo 'Testing Complete'
