#!/usr/bin/env bash

#
if [ -d "_patched" ]; then
  rm -rf _patched
fi

git submodule update --init

cd ansible || return 1

git checkout-index -a -f --prefix=../_patched/

cd ../_patched || return 1

for p in $(find ../*.patch)
do
  patch -p1 < $p
done

chmod +x ./plugins/inventory/*.py

echo ""
echo "All patched have been applied successfully!"
