#!/bin/bash

set -euxo pipefail

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TOP="$(dirname "${BASEDIR}")"

cd "${TOP}"
readarray -t FILES < <(git status -s docs | grep -E ^.D | sed s/^...//)
if [ ${#FILES[@]} -ne 0 ] ; then
    git checkout "${FILES[@]}"
fi
git checkout -- \
 app/meticulous \
 app/tests \
 app/.gitignore

rm -rf app/pip/2.7 app/pip/3.5
