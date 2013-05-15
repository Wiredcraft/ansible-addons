#!/usr/bin/python

"""
devops external inventory script
=================================

Ansible has a feature where instead of reading from /etc/ansible/hosts
as a text file, it can query external programs to obtain the list
of hosts, groups the hosts are in, and even variables to assign to each host.

To use this, copy this file over /etc/ansible/hosts and chmod +x the file.
This, more or less, allows you to keep one central database containing
info about all of your managed instances.

NOTE: The cobbler system names will not be used.  Make sure a
cobbler --dns-name is set for each cobbler system.   If a system
appears with two DNS names we do not add it twice because we don't want
ansible talking to it twice.  The first one found will be used. If no
--dns-name is set the system will NOT be visible to ansible.  We do
not add cobbler system names because there is no requirement in cobbler
that those correspond to addresses.

See http://ansible.github.com/api.html for more info

Tested with Devops Ansible API 0.0.1.
"""



import sys
import urllib
import urllib2
import cookielib
import os

try:
    import json
except:
    import simplejson as json

cookieJar = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar))

url = "http://127.0.0.1:3000"
url_login = url +'/login'
url_ansible = url +'/ansible'

# Auth as admin
params = urllib.urlencode({
    'username': 'admin',
    'password': 'admin'
});

space_env = 'ANSIBLE_DEVOPS_SPACE'
space = os.environ.get(space_env)

###################################################
# executed with no parameters, return the list of
# all groups and hosts

if len(sys.argv) == 2 and (sys.argv[1] == '--list') and isinstance(space, str):

    # Connect and save cookie
    opener.open(url_login, params)

    # query api
    groups_io = opener.open(url_ansible +"?space="+ space)
    data = groups_io.read()
    code = groups_io.getcode()

    if code == 500:
        sys.stderr.write(data)
        sys.exit(1)

    try:
        # Only used to ensure we have a valid JSON file
        groups = json.loads(data);
        sys.stdout.write(json.dumps(groups))
        sys.exit(0)
    except ValueError:
        sys.stderr.write(data)
        sys.exit(1)

#####################################################
# executed with a hostname as a parameter, return the
# variables for that host

elif len(sys.argv) == 3 and (sys.argv[1] == '--host') and isinstance(space, str):

    # Connect and save cookie
    opener.open(url_login, params)

    # query api
    host_var_io = opener.open(url_ansible +"/"+ sys.argv[2] +"?space="+ space)
    host_var = json.load(host_var_io);

    print json.dumps(host_var)
    sys.exit(0)

else:
    print "Need to define Environment Variable "+ space_env
    print "usage: --list  ..OR.. --host <hostname>"
    sys.exit(1)