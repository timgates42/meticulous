#!/bin/bash

set -euxo pipefail

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${BASEDIR}"

apk add --no-cache \
    build-base \
    aspell aspell-en \
    hunspell hunspell-en \
    shellcheck \
    git \
    libxslt-dev \
    libffi-dev \
    curl \
    openssl-dev gcc musl-dev postgresql-dev

RUSTUP_HOME=/rust
export RUSTUP_HOME
CARGO_HOME=/cargo 
export CARGO_HOME
PATH=/cargo/bin:/rust/bin:$PATH
export PATH
curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain nightly --no-modify-path
rustup default nightly

cd "${BASEDIR}/pip/${PYVER}"
for reqfile in */requirements.txt ; do
if [ "$(wc -l < "${reqfile}")" -gt 0 ] ; then
  "python${PYVER}" -m pip install -r "${reqfile}"
fi
done
# Display installation
"python${PYVER}" -m pip freeze
"python${PYVER}" -m safety check
