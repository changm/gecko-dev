import copy
import json
import logging

import requests
from slugid import nice as slugid

from .registry import register_callback_action
from taskgraph.create import create_task
from taskgraph.util.time import (
    current_json_time,
    json_time_from_now
)

TASKCLUSTER_QUEUE_URL = "https://queue.taskcluster.net/v1/task"

logger = logging.getLogger(__name__)


@register_callback_action(
    title='Schedule mochitest retrigger',
    symbol='mdr',
    description="Retriggers the specified mochitest job with additional options",
    context=[{'test-type': 'mochitest'}],  # mochitest-only
    order=0,
    schema={
        'type': 'object',
        'properties': {
            'path': {
                'type': 'string',
                'maxLength': 255,
                'default': '',
                'title': 'Path name',
                'description': 'Path of mochitest to retrigger'
            },
            'logLevel': {
                'type': 'string',
                'enum': ['debug', 'info', 'warning', 'error', 'critical'],
                'default': 'debug',
                'title': 'Log level',
                'description': 'Log level for output (default is DEBUG, which is highest)'
            },
            'runUntilFail': {
                'type': 'boolean',
                'default': True,
                'title': 'Run until failure',
                'description': ('Runs the specified set of tests repeatedly '
                                'until failure (or 30 times)')
            },
            'repeat': {
                'type': 'integer',
                'default': 30,
                'minimum': 1,
                'title': 'Run tests N times',
                'description': ('Run tests repeatedly (usually used in '
                                'conjunction with runUntilFail)')
            },
            'environment': {
                'type': 'object',
                'default': {'MY_ENV_1': 'myvalue1'},
                'title': 'Extra environment variables',
                'description': 'Extra environment variables to use for this run'
            },
            'preferences': {
                'type': 'object',
                'default': {'mygeckopreferences.pref': 'myvalue2'},
                'title': 'Extra gecko (about:config) preferences',
                'description': 'Extra gecko (about:config) preferences to use for this run'
            }
        },
        'additionalProperties': False,
        'required': ['path']
    }
)
def mochitest_retrigger_action(parameters, input, task_group_id, task_id, task):
    new_task_definition = copy.copy(task)

    # set new created, deadline, and expiry fields
    new_task_definition['created'] = current_json_time()
    new_task_definition['deadline'] = json_time_from_now('1d')
    new_task_definition['expires'] = json_time_from_now('30d')

    # don't want to run mozharness tests, want a custom mach command instead
    new_task_definition['payload']['command'] += ['--no-run-tests']

    custom_mach_command = [
        'mochitest',
        '--keep-open=false',
        '-f', new_task_definition['payload']['env']['MOCHITEST_FLAVOR']
    ]

    enable_e10s = json.loads(new_task_definition['payload']['env'].get(
        'ENABLE_E10S', 'true'))
    if not enable_e10s:
        custom_mach_command += ['--disable-e10s']

    custom_mach_command += ['--log-tbpl=-',
                            '--log-tbpl-level={}'.format(input['logLevel'])]
    if input.get('runUntilFail'):
        custom_mach_command += ['--run-until-fail']
    if input.get('repeat'):
        custom_mach_command += ['--repeat', str(input['repeat'])]

    # add any custom gecko preferences
    for (key, val) in input.get('preferences', {}).iteritems():
        custom_mach_command += ['--setpref', '{}={}'.format(key, val)]

    custom_mach_command += [input['path']]
    new_task_definition['payload']['env']['CUSTOM_MACH_COMMAND'] = ' '.join(
        custom_mach_command)

    # update environment
    new_task_definition['payload']['env'].update(input.get('environment', {}))

    # tweak the treeherder symbol
    new_task_definition['extra']['treeherder']['symbol'] += '-custom'

    logging.info("New task definition: %s", new_task_definition)

    # actually create the new task
    new_task_id = slugid()
    logger.info("Creating new mochitest task with id %s", new_task_id)
    session = requests.Session()
    create_task(session, new_task_id, 'mochitest-debug', new_task_definition)
