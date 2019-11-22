#!/bin/bash

set -euxo pipefail

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "${BASEDIR}"

apt-get update
apt-get install -qq -y aspell aspell-en
apt-get install -qq -y hunspell hunspell-en-au
apt-get install -qq -y shellcheck
apt-get install -qq -y git

for PYVER in ${PYTHONVERS} ; do
  cd "${BASEDIR}/pip/${PYVER}"
  for reqfile in */requirements.txt ; do
    if [ "$(wc -l < "${reqfile}")" -gt 0 ] ; then
      "python${PYVER}" -m pip install -r "${reqfile}"
    fi
  done
  # Display installation
  "python${PYVER}" -m pip freeze
  "python${PYVER}" -m safety check
done
