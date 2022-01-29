# Copyright 2021 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time

from tempest import config
from tempest.lib import exceptions

from manila_tempest_tests.services.share.v2.json import shares_client
from manila_tempest_tests import share_exceptions

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


def _get_access_rule(body, rule_id):
    for rule in body:
        if rule['id'] in rule_id:
            return rule


def _get_name_of_raise_method(resource_name):
    if resource_name == 'snapshot_access':
        return 'AccessRuleBuildErrorException'
    if resource_name == 'share_replica':
        return 'ShareInstanceBuildErrorException'
    resource_name = resource_name.title()
    name = resource_name.replace('_', '')
    return name + 'BuildErrorException'


def wait_for_resource_status(client, resource_id, status,
                             resource_name='share', rule_id=None,
                             status_attr='status',
                             raise_rule_in_error_state=True,
                             version=LATEST_MICROVERSION):
    """Waits for a resource to reach a given status."""

    get_resource_action = {
        'share': 'get_share',
        'snapshot': 'get_snapshot',
        'share_server': 'show_share_server',
        'share_instance': 'get_share_instance',
        'snapshot_instance': 'get_snapshot_instance',
        'access_rule': 'list_access_rules',
        'snapshot_access': 'list_snapshot_access_rules',
        'share_group': 'get_share_group',
        'share_group_snapshot': 'get_share_group_snapshot',
        'share_replica': 'get_share_replica',
    }

    action_name = get_resource_action[resource_name]
    # This code snippet is intended to set the dictionary key of the returned
    # response for share access rule and for snapshot access rule.
    if 'access' in resource_name:
        rn = '_'.join(action_name.split('_')[1:-1]) + '_list'
    else:
        rn = resource_name

    # Since API v2 requests require an additional parameter for micro-versions,
    # it's necessary to pass the required parameters according to the version.
    resource_action = getattr(client, action_name)
    method_args = [resource_id]
    method_kwargs = {}
    if isinstance(client, shares_client.SharesV2Client):
        method_kwargs.update({'version': version})
    body = resource_action(*method_args, **method_kwargs)[rn]

    if 'access' in resource_name:
        status_attr = 'state'
        body = _get_access_rule(body, rule_id)

    resource_status = body[status_attr]
    start = int(time.time())

    exp_status = status if isinstance(status, list) else [status]
    while resource_status not in exp_status:
        time.sleep(client.build_interval)
        body = resource_action(*method_args, **method_kwargs)[rn]

        if 'access' in resource_name:
            status_attr = 'state'
            body = _get_access_rule(body, rule_id)

        resource_status = body[status_attr]

        if resource_status in exp_status:
            return
        elif 'error' in resource_status.lower() and raise_rule_in_error_state:
            raise_method = _get_name_of_raise_method(resource_name)
            resource_exception = getattr(share_exceptions, raise_method)
            raise resource_exception(resource_id=resource_id)
        if int(time.time()) - start >= client.build_timeout:
            message = ('%s %s failed to reach %s status (current %s) '
                       'within the required time (%s s).' %
                       (resource_name.replace('_', ' '), resource_id, status,
                        resource_status, client.build_timeout))
            raise exceptions.TimeoutException(message)


def wait_for_migration_status(client, share_id, dest_host, status_to_wait,
                              version=LATEST_MICROVERSION):
    """Waits for a share to migrate to a certain host."""
    statuses = ((status_to_wait,)
                if not isinstance(status_to_wait, (tuple, list, set))
                else status_to_wait)
    share = client.get_share(share_id, version=version)['share']
    migration_timeout = CONF.share.migration_timeout
    start = int(time.time())
    while share['task_state'] not in statuses:
        time.sleep(client.build_interval)
        share = client.get_share(share_id, version=version)['share']
        if share['task_state'] in statuses:
            break
        elif share['task_state'] == 'migration_error':
            raise share_exceptions.ShareMigrationException(
                share_id=share['id'], src=share['host'], dest=dest_host)
        elif int(time.time()) - start >= migration_timeout:
            message = ('Share %(share_id)s failed to reach a status in'
                       '%(status)s when migrating from host %(src)s to '
                       'host %(dest)s within the required time '
                       '%(timeout)s.' % {
                           'src': share['host'],
                           'dest': dest_host,
                           'share_id': share['id'],
                           'timeout': client.build_timeout,
                           'status': str(statuses),
                       })
            raise exceptions.TimeoutException(message)
    return share


def wait_for_snapshot_access_rule_deletion(client, snapshot_id, rule_id):
    rule = client.get_snapshot_access_rule(snapshot_id, rule_id)
    start = int(time.time())

    while rule is not None:
        time.sleep(client.build_interval)

        rule = client.get_snapshot_access_rule(snapshot_id, rule_id)

        if rule is None:
            return
        if int(time.time()) - start >= client.build_timeout:
            message = ('The snapshot access rule %(id)s failed to delete '
                       'within the required time (%(time)ss).' %
                       {
                           'time': client.build_timeout,
                           'id': rule_id,
                       })
            raise exceptions.TimeoutException(message)


def wait_for_message(client, resource_id):
    """Waits until a message for a resource with given id exists"""
    start = int(time.time())
    message = None

    while not message:
        time.sleep(client.build_interval)
        for msg in client.list_messages()['messages']:
            if msg['resource_id'] == resource_id:
                return msg

        if int(time.time()) - start >= client.build_timeout:
            message = ('No message for resource with id %s was created in'
                       ' the required time (%s s).' %
                       (resource_id, client.build_timeout))
            raise exceptions.TimeoutException(message)


def wait_for_soft_delete(client, share_id, version=LATEST_MICROVERSION):
    """Wait for a share soft delete to recycle bin."""
    share = client.get_share(share_id, version=version)['share']
    start = int(time.time())
    while not share['is_soft_deleted']:
        time.sleep(client.build_interval)
        share = client.get_share(share_id, version=version)['share']
        if share['is_soft_deleted']:
            break
        elif int(time.time()) - start >= client.build_timeout:
            message = ('Share %(share_id)s failed to be soft deleted to '
                       'recycle bin within the required time '
                       '%(timeout)s.' % {
                           'share_id': share['id'],
                           'timeout': client.build_timeout,
                       })
            raise exceptions.TimeoutException(message)


def wait_for_restore(client, share_id, version=LATEST_MICROVERSION):
    """Wait for a share restore from recycle bin."""
    share = client.get_share(share_id, version=version)['share']
    start = int(time.time())
    while share['is_soft_deleted']:
        time.sleep(client.build_interval)
        share = client.get_share(share_id, version=version)['share']
        if not share['is_soft_deleted']:
            break
        elif int(time.time()) - start >= client.build_timeout:
            message = ('Share %(share_id)s failed to restore from '
                       'recycle bin within the required time '
                       '%(timeout)s.' % {
                           'share_id': share['id'],
                           'timeout': client.build_timeout,
                       })
            raise exceptions.TimeoutException(message)


def wait_for_subnet_create_check(client, share_network_id,
                                 neutron_net_id=None,
                                 neutron_subnet_id=None,
                                 availability_zone=None):
    result = client.subnet_create_check(
        share_network_id, neutron_net_id=neutron_net_id,
        neutron_subnet_id=neutron_subnet_id,
        availability_zone=availability_zone)
    start = int(time.time())
    while not result['compatible']:
        time.sleep(client.build_interval)
        result = client.subnet_create_check(
            share_network_id, neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id,
            availability_zone=availability_zone)
        if result['compatible']:
            break
        elif int(time.time()) - start >= client.build_timeout or (
                result['compatible'] is False):
            message = ('Subnet create check failed within the '
                       'required time %(timeout)s seconds for share network '
                       '%(share_network)s.' % {
                           'timeout': client.build_timeout,
                           'share_network': share_network_id,
                       })
            raise exceptions.TimeoutException(message)
