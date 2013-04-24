#!/bin/bash
#######################
# Apply devo.p addons to Ansible
#######################

if [ -d "/opt/ansible" ]; then
    ANSIBLE_ROOT=/opt/ansible
else
    echo "No Ansible root folder found - enter path: "
    read ANSIBLE_ROOT
    if [ ! -d "$ANSIBLE_ROOT" ]; then
        echo "Folder $ANSIBLE_ROOT does not exist - aborting." >&2
        exit 1
    fi
fi

for folder in $(ls -d */. | grep -v patches)
do
    echo "Copying files in $folder to Ansible source"
    find "$folder" -type f -exec sudo cp --parents '{}' "$ANSIBLE_ROOT"/. \;
done

cd $ANSIBLE_ROOT && sudo make && sudo make install
