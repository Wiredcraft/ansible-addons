#!/usr/bin/env bash

# echo ""

# #
# if [ -d "_patched" ]; then
#   rm -rf _patched
# fi

# echo "Clonging/Updaging ansible..."
# if [ -d "ansible" ]; then
#   cd ansible || return 1
#   git pull
# else
#   git clone git://github.com/ansible/ansible.git
#   #git submodule update --init
#   cd ansible || return 1
# fi

# echo ""

# echo "Patching..."
# git checkout-index -a -f --prefix=../_patched/
# cd ../_patched || return 1

# for p in $(find ../*.patch)
# do
#   patch -p1 < $p
# done

# chmod +x ./plugins/inventory/*.py

# echo ""
# echo "All patched have been applied successfully!"

