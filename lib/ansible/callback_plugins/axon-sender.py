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
AXON_PORT = 3001

LVL_NOTI = 'notification'
LVL_WARN = 'warning'
LVL_ERR = 'error'
LVL_INFO = 'information'

def record(result):
    if 'axon' in sys.modules:
        sock = axon.Axon()
        result['space'] = os.environ.get('ANSIBLE_DEVOPS_SPACE', '')
        try: 
            sock.connect((AXON_HOST, AXON_PORT))
            sock.push('ansible', result)
        except Exception, e: 
            # send to logs
            print "Error; playbook callback can not send Axon message - %s" % e
            pass

class CallbackModule(object):

    def on_any(self, *args, **kwargs):
        pass

    def playbook_on_start(self):
        record({
            'type': LVL_NOTI, 
            'event': 'playbook_on_start', 
            'msg': 'Start playbook'
        })

    def runner_on_failed(self, host, res, ignore_errors=False):
        if ignore_errors:
            return
        result = {
            'type': LVL_ERR, 
            'event': 'runner_on_failed', 
            'source': host, 
        }
        result.update(res)
        record(result)

    def runner_on_ok(self, host, res):
        result = {
            'type': LVL_NOTI, 
            'event': 'runner_on_ok', 
            'source': host, 
        }
        result.update(res)
        record(result)

    def runner_on_error(self, host, msg):
        record({
            'type': LVL_ERR, 
            'event': 'runner_on_error', 
            'source': host, 
            'msg': msg
        })

    def runner_on_skipped(self, host, item=None):
        record({
            'type': LVL_NOTI, 
            'event': 'runner_on_skipped', 
            'source': host, 
            'item': item
        })

    def runner_on_unreachable(self, host, res):
        result = {
            'type': LVL_ERR, 
            'event': 'runner_on_unreachable', 
            'source': host, 
        }
        result.update(res)
        record(result)

    def playbook_on_stats(self, stats):
        for host in stats.processed:
            record({
                'type': LVL_NOTI, 
                'event': 'playbook_on_stats', 
                'source': host, 
                'stats': stats.summarize(host)
            })

    def playbook_on_notify(self, host, handler):
        record({
            'type': LVL_NOTI, 
            'event': 'playbook_on_notify', 
            'source': host, 
            'handler': handler
        })
