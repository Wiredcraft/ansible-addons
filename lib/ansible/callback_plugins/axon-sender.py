#!/usr/bin/env python
# coding:utf-8

import os
import sys
try:
    import json
except ImportError: 
    import simplejson as json

try:
    import axon
except ImportError:
    print "try 'pip install axon' to install the axon package"

AXON_HOST = '127.0.0.1'
AXON_PORT = 7777

def record(result):
    if 'axon' in sys.modules:
        sock = axon.Axon()
        result['space'] = os.environ.get('ANSIBLE_DEVOPS_SPACE', '')
        try: 
            sock.connect((AXON_HOST, AXON_PORT))
            sock.push('log', result)
        except Exception, e: 
            # send to logs
            print "Error; playbook callback can not send Axon message - %s" % e
            pass

class CallbackModule(object):

    def on_any(self, *args, **kwargs):
        pass

    def playbook_on_start(self):
        record({'type': 'Notifications', 'message': 'Start playbook'})

    def runner_on_failed(self, host, res, ignore_errors=False):
        if ignore_errors:
            return
        record({'type': 'Errors', 'source': host, 'message': res})

    def runner_on_ok(self, host, res):
        record({'type': 'Notifications', 'source': host, 'message': res})

    def runner_on_error(self, host, msg):
        record({'type': 'Errors', 'source': host, 'message': msg})

    def runner_on_skipped(self, host, item=None):
        record({'type': 'Notifications', 'source': host, 'item': item})

    def runner_on_unreachable(self, host, res):
        record({'type': 'Errors', 'source': host, 'message': res})

    def playbook_on_stats(self, stats):
        result = {}
        for host in stats.processed:
            record({'type':'Notifications', 'source': host, 'message': json.dumps(stats.summarize(host))})
            # result[host] = stats.summarize(host)

    # def runner_on_no_hosts(self):
    #     pass

    # def runner_on_async_poll(self, host, res, jid, clock):
    #     pass
    #     # record({'type': 'runner_on_async_poll', 'source':host, 'message':res, 'jid': jid, 'clock': clock})

    # def runner_on_async_ok(self, host, res, jid):
    #     pass
    #     # record({'type': 'Notifications', 'source':host, 'message':res, 'jid': jid})

    # def runner_on_async_failed(self, host, res, jid):
    #     pass
    #     # record({'type': 'Errors', 'source':host, 'message':res, 'jid': jid})

    # def playbook_on_notify(self, host, handler):
    #     pass
    #     # record({'type': 'Notifications', 'source':host, 'handler': handler})

    # def on_no_hosts_matched(self):
    #     pass

    # def on_no_hosts_remaining(self):
    #     pass

    # def playbook_on_task_start(self, name, is_conditional):
    #     pass

    # def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
    #     pass
    #     # record({'type': 'playbook_on_vars_prompt', 'varname': varname, 'private': private, 'prompt':prompt, 'encrypt':encrypt, 'confirm':confirm, 'salt_size':salt_size, 'salt':salt, 'default': default})

    # def playbook_on_setup(self):
    #     pass

    # def playbook_on_import_for_host(self, host, imported_file):
    #     pass
    #     # record({'type': 'Notifications', 'source':host, 'imported_file': imported_file})

    # def playbook_on_not_import_for_host(self, host, missing_file):
    #     pass

    # def playbook_on_play_start(self, pattern):
    #     pass

