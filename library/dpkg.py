#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2013, Devo.ps
# Written by Vincent Viallet <vincent@devo.ps>
# Based on apt module
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#

DOCUMENTATION = '''
---
module: dpkg
short_description: Manages dpkg packages
description:
  - Manages I(dpkg) packages (such as for Debian/Ubuntu).
options:
  url:
    description:
      - A package url or package specifier with version, like C(http://example.com/foo.deb)
    required: true
    default: null
  pkg:
    description:
      - A deb file full path, like C(/bar/foo.deb)
    required: true
    default: null
  state:
    description:
      - Indicates the desired package state
    required: false
    default: present
    choices: [ "absent", "present" ]
  purge:
    description:
     - Will force purging of configuration files if the module state is set to I(absent).
    required: false
    default: "no"
    choices: [ "yes", "no" ]
  force:
    description:
      - If C(yes), force installs/removes.
    required: false
    default: "no"
    choices: [ "yes", "no" ]
author: Vincent Viallet
notes: []
examples:
    - code: "dpkg: pkg=/bar/foo.deb state=present"
      description: Install package (foo.deb) from folder /bar
    - code: "dpkg: url=http://example.com/foo.deb state=installed"
      description: Install the package C(http://example.com/foo.deb)
requirements: [ python-apt, aptitude ]
'''

import traceback
# added to stave off future warnings about apt api
import warnings
warnings.filterwarnings('ignore', "apt API not stable yet", FutureWarning)

# APT related constants
APT_PATH = "/usr/bin/apt-get"
DPKG_PATH = "/usr/bin/dpkg"
APT = "DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical %s" % APT_PATH
DPKG = "DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical %s" % DPKG_PATH

# Empirical size in bytes to fetch .deb header and extract package info
# without downloading the entire file
# 5Kb is more that enough, could be reduced down to ~2-3Kb - remain safe
HEADER_SIZE = 5000

# Get package from URL, fetching 
def package_from_url(m, url):
    '''
    Fetch the first HEADER_SIZE bytes of the file located at URL.
    Attempt to extract the .deb package info.
    Returns 
        - package record (apt.package.Record) to query package_status
        - debfile; (urllib) to resume reading if file need to be installed
        - header; to append to if remaining file is to be read
    '''
    import urllib
    import tarfile
    import io
    import re
    import apt

    try:
        debfile = urllib.urlopen(url)
    except: 
        m.fail_json(msg="Can not fetch url '%s'" % url)

    # Little trick to extract the package info from the beginning of the deb file:
    # - extract the control.tar.gz file that holds the package info (done via regex)
    # - untar and extract the './control' file
    # - populate a apt.package.Record with the content of the 'control' file
    try: 
        header = debfile.read(HEADER_SIZE)
    except:
        m.fail_json(msg="Failed to fetch package from url '%s'" % m.params['url'])

    match = re.search(b'control\.tar\.gz[^\n]*\n(.*)data\.tar\.gz', header, re.DOTALL)
    if match:
        match_data = match.groups()[0]
    else:
        # Can not find a match; either not deb file or HEADER_SIZE is too small
        m.fail_json(msg="Can not find control file from url '%s'" % url)

    try:
        control_fo = io.BytesIO(match_data)
        control_tar = tarfile.open(fileobj=control_fo)
        control = control_tar.extractfile('./control')
    except: 
        # Failed either to open the tar file or extract the ./control
        m.fail_json(msg="Invalid control file in Debian package from url '%s'" % url)

    try:
        record = apt.package.Record(control.read())
    except:
        # Failed to populate Record; bad format of the control
        m.fail_json(msg="Invalid control file's content format from url '%s'" % url)

    return (record, debfile, header)

def package_from_file(m, path):
    '''
    Open the file at path with debfile.DebPackage and attempt to read its info
    Returns 
        - package record (apt.package.Record) to query package_status
        - empty debfile and header (just to remain compliant with package_from_url return)
    '''
    import apt
    from apt import debfile

    try:
        pkg = debfile.DebPackage(path)
    except: 
        m.fail_json(msg="Can not open package '%s', ensure the file exists and is a valid deb package." % path)

    control = pkg.control_content('control')
    record = apt.package.Record(control)

    return (record, None, None)

def package_status(m, pkgname, version, cache):
    try:
        pkg = cache[pkgname]
    except KeyError:
        return False, False
    if version:
        try :
            return pkg.is_installed and pkg.installed.version == version, False
        except AttributeError:
            #assume older version of python-apt is installed
            return pkg.isInstalled and pkg.installedVersion == version, False
    else:
        try :
            return pkg.is_installed, pkg.is_upgradable
        except AttributeError:
            #assume older version of python-apt is installed
            return pkg.isInstalled, pkg.isUpgradable

def missing_dependencies(m, depends, cache):
    """
    Check the dependencies against apt cache
    Returns:
    - True + [] if dependencies are matched (or none)
    - False + missing [] dependencies if dependencies are not matched
    """
    if not depends or len(depends) == 0:
        return (False, [])

    missing = False
    missing_deps = []

    from distutils.version import StrictVersion
    import operator
    operator_dict = {
        '>': operator.gt,
        '>=': operator.ge,
        '=': operator.eq,
        '<': operator.lt,
        '<=': operator.le
    }

    dependencies = [ dep.strip() for dep in depends.split(',') ]
    for dep in dependencies:
        try:
            pkg = cache[dep.split()[0]]
        except KeyError:
            missing = True
            missing_deps.append(dep)
            continue

        # Package is missing if .. not installed
        try:
            if not pkg.is_installed:
                missing = True
                missing_deps.append(dep)
                continue
        except AttributeError:
            if not pkg.isInstalled:
                missing = True
                missing_deps.append(dep)
                continue

        # Check version
        version = None
        try:
            versionSpec = dep.split('(')[1].split(')')[0]
            version = versionSpec.split(None, 1)
        except:
            pass

        if version:
            op = '='
            if len(version) == 2:
                op = version[0]
                version = version[1]

            # Version needs to be a string of integers - debian / ubuntu doesn't always comply...
            m_pkg_version = re.search('([a-zA-Z0-9\.]*)', pkg.installed.version)
            if m:
                pkg_version = m_pkg_version.groups()[0]
            else:
                m.exit_json(msg="Error while parsing package (dependency) version: '%s" % pkg.installed.version)

            match_version = operator_dict[op](StrictVersion(pkg_version), StrictVersion(version))
            if not match_version:
                missing = True
                missing_deps.append(dep)
                continue

    return (missing, missing_deps)

def install(m, record, debfile, content, cache, force=False):
    package = ""
    name = record['Package']
    version = record['Version']
    depends = record['Depends']

    installed, upgradable = package_status(m, name, version, cache)    
    if not installed or upgradable:
        if m.params['url']:
            # Fetch the remaining file from url
            try: 
                content += debfile.read()
            except:
                m.fail_json(msg="Failed to fetch package from url '%s'" % m.params['url'])

            # Save file locally to be processed by dpkg
            pkg_file_name = "%s_%s_%s.deb" % (name, version, record['Architecture'])
            pkg_file = open(pkg_file_name, 'wb')
            pkg_file.write(content)
            pkg_file.close()
            package = pkg_file_name
        else:
            package = m.params['package']

    if len(package) != 0:
        if force:
            force_all = '--force-all'
        else:
            # Look for missing dependencies
            missing, missing_deps = missing_dependencies(m, depends, cache)
            if missing:
                m.exit_json(msg="Not installing, missing dependencies: '%s', use --force to install" 
                              % ', '.join(missing_deps))
            else: 
                force_all = ''
    
        cmd = "%s --install --force-confold %s %s" % (DPKG, force_all, package)

        if m.check_mode:
            m.exit_json(changed=True)

        rc, out, err = m.run_command(cmd)
        if rc:
            m.fail_json(msg="'dpkg --install %s' failed: %s" % (package, err))
        else:
            m.exit_json(changed=True)
    else:
        m.exit_json(changed=False)

def remove(m, record, cache, purge=False):
    package = ""
    name = record['Package']
    version = record['Version']

    installed, upgradable = package_status(m, name, version, cache)
    if installed:
        package = name

    if len(package) == 0:
        m.exit_json(changed=False)
    else:
        purge = ''
        if purge:
            purge = '--purge'
        cmd = "%s -q -y %s remove %s" % (APT, purge, package)

        if m.check_mode:
            m.exit_json(changed=True)

        rc, out, err = m.run_command(cmd)
        if rc:
            m.fail_json(msg="'apt-get remove %s' failed: %s" % (package, err))
        m.exit_json(changed=True)

def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='installed', choices=['installed', 'removed', 'absent', 'present']),
            purge = dict(default='no', type='bool'),
            url = dict(default=None),
            package = dict(default=None, aliases=['pkg', 'name', 'path']),
            force = dict(default='no', type='bool'),
        ),
        mutually_exclusive = [['package', 'url']],
        required_one_of = [['package', 'url']],
        supports_check_mode = True
    )

    try:
        import apt
    except:
        module.fail_json(msg="Could not import python modules: apt. Please install python-apt package.")

    if not os.path.exists(APT_PATH):
        module.fail_json(msg="Cannot find apt-get")
    if not os.path.exists(DPKG_PATH):
        module.fail_json(msg="Cannot find dpkg")

    p = module.params

    try:
        cache = apt.Cache()

        force_all = p['force']

        if p['url']:
            record, debfile, header = package_from_url(module, p['url'])
        else:
            record, debfile, header = package_from_file(module, p['package'])

        if p['state'] in [ 'installed', 'present' ]:
            install(module, record, debfile, header, cache, force=force_all)
        elif p['state'] in [ 'removed', 'absent' ]:
            remove(module, record, cache, p['purge'])

    except apt.cache.LockFailedException:
        module.fail_json(msg="Failed to lock apt for exclusive operation")

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>

main()