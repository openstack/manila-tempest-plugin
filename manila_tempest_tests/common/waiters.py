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

import six
from tempest import config
from tempest.lib import exceptions

from manila_tempest_tests.common import constants
from manila_tempest_tests.services.share.v2.json import shares_client
from manila_tempest_tests import share_exceptions

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


def wait_for_share_instance_status(client, instance_id, status,
                                   version=LATEST_MICROVERSION):
    """Waits for a share to reach a given status."""
    body = client.get_share_instance(instance_id, version=version)
    instance_status = body['status']
    start = int(time.time())

    while instance_status != status:
        time.sleep(client.build_interval)
        body = client.get_share_instance(instance_id)
        instance_status = body['status']
        if instance_status == status:
            return
        elif 'error' in instance_status.lower():
            raise share_exceptions.ShareInstanceBuildErrorException(
                id=instance_id)

        if int(time.time()) - start >= client.build_timeout:
            message = ('Share instance %s failed to reach %s status within'
                       ' the required time (%s s).' %
                       (instance_id, status, client.build_timeout))
            raise exceptions.TimeoutException(message)


def wait_for_share_status(client, share_id, status, status_attr='status',
                          version=LATEST_MICROVERSION):
    """Waits for a share to reach a given status."""
    if isinstance(client, shares_client.SharesV2Client):
        body = client.get_share(share_id, version=version)
    else:
        body = client.get_share(share_id)
    share_status = body[status_attr]
    start = int(time.time())

    exp_status = status if isinstance(status, list) else [status]
    while share_status not in exp_status:
        time.sleep(client.build_interval)
        if isinstance(client, shares_client.SharesV2Client):
            body = client.get_share(share_id, version=version)
        else:
            body = client.get_share(share_id)
        share_status = body[status_attr]
        if share_status in exp_status:
            return
        elif 'error' in share_status.lower():
            raise share_exceptions.ShareBuildErrorException(
                share_id=share_id)
        if int(time.time()) - start >= client.build_timeout:
            message = ("Share's %(status_attr)s failed to transition to "
                       "%(status)s within the required "
                       "time %(seconds)s." %
                       {"status_attr": status_attr, "status": exp_status,
                        "seconds": client.build_timeout})
            raise exceptions.TimeoutException(message)


def wait_for_snapshot_status(client, snapshot_id, status,
                             version=LATEST_MICROVERSION):
    """Waits for a snapshot to reach a given status."""
    if isinstance(client, shares_client.SharesV2Client):
        body = client.get_snapshot(snapshot_id, version=version)
    else:
        body = client.get_snapshot(snapshot_id)
    snapshot_name = body['name']
    snapshot_status = body['status']
    start = int(time.time())

    while snapshot_status != status:
        time.sleep(client.build_interval)
        if isinstance(client, shares_client.SharesV2Client):
            body = client.get_snapshot(snapshot_id, version=version)
        else:
            body = client.get_snapshot(snapshot_id)
        snapshot_status = body['status']
        if snapshot_status in status:
            return
        if 'error' in snapshot_status:
            raise (share_exceptions.
                   SnapshotBuildErrorException(snapshot_id=snapshot_id))

        if int(time.time()) - start >= client.build_timeout:
            message = ('Share Snapshot %s failed to reach %s status '
                       'within the required time (%s s).' %
                       (snapshot_name, status, client.build_timeout))
            raise exceptions.TimeoutException(message)


def wait_for_access_rule_status(client, share_id, rule_id, status,
                                raise_rule_in_error_state=True):
    """Waits for an access rule to reach a given status."""
    rule_status = "new"
    start = int(time.time())
    while rule_status != status:
        time.sleep(client.build_interval)
        rules = client.list_access_rules(share_id)
        for rule in rules:
            if rule["id"] in rule_id:
                rule_status = rule['state']
                break
        if 'error' in rule_status and raise_rule_in_error_state:
            raise share_exceptions.AccessRuleBuildErrorException(
                rule_id=rule_id)

        if int(time.time()) - start >= client.build_timeout:
            message = ('Share Access Rule %s failed to reach %s status '
                       'within the required time (%s s).' %
                       (rule_id, status, client.build_timeout))
            raise exceptions.TimeoutException(message)


def wait_for_snapshot_instance_status(client, instance_id, expected_status):
    """Waits for a snapshot instance status to reach a given status."""
    body = client.get_snapshot_instance(instance_id)
    instance_status = body['status']
    start = int(time.time())

    while instance_status != expected_status:
        time.sleep(client.build_interval)
        body = client.get_snapshot_instance(instance_id)
        instance_status = body['status']
        if instance_status == expected_status:
            return
        if 'error' in instance_status:
            raise share_exceptions.SnapshotInstanceBuildErrorException(
                id=instance_id)

        if int(time.time()) - start >= client.build_timeout:
            message = ('The status of snapshot instance %(id)s failed to '
                       'reach %(expected_status)s status within the '
                       'required time (%(time)ss). Current '
                       'status: %(current_status)s.' %
                       {
                           'expected_status': expected_status,
                           'time': client.build_timeout,
                           'id': instance_id,
                           'current_status': instance_status,
                       })
            raise exceptions.TimeoutException(message)


def wait_for_share_group_status(client, share_group_id, status):
    """Waits for a share group to reach a given status."""
    body = client.get_share_group(share_group_id)
    sg_name = body['name']
    sg_status = body['status']
    start = int(time.time())

    while sg_status != status:
        time.sleep(client.build_interval)
        body = client.get_share_group(share_group_id)
        sg_status = body['status']
        if 'error' in sg_status and status != 'error':
            raise share_exceptions.ShareGroupBuildErrorException(
                share_group_id=share_group_id)

        if int(time.time()) - start >= client.build_timeout:
            sg_name = sg_name or share_group_id
            message = ('Share Group %s failed to reach %s status '
                       'within the required time (%s s). '
                       'Current status: %s' %
                       (sg_name, status, client.build_timeout, sg_status))
            raise exceptions.TimeoutException(message)


def wait_for_share_group_snapshot_status(client, share_group_snapshot_id,
                                         status):
    """Waits for a share group snapshot to reach a given status."""
    body = client.get_share_group_snapshot(share_group_snapshot_id)
    sg_snapshot_name = body['name']
    sg_snapshot_status = body['status']
    start = int(time.time())

    while sg_snapshot_status != status:
        time.sleep(client.build_interval)
        body = client.get_share_group_snapshot(share_group_snapshot_id)
        sg_snapshot_status = body['status']
        if 'error' in sg_snapshot_status and status != 'error':
            raise share_exceptions.ShareGroupSnapshotBuildErrorException(
                share_group_snapshot_id=share_group_snapshot_id)

        if int(time.time()) - start >= client.build_timeout:
            message = ('Share Group Snapshot %s failed to reach %s status '
                       'within the required time (%s s).' %
                       (sg_snapshot_name, status, client.build_timeout))
            raise exceptions.TimeoutException(message)


def wait_for_share_server_status(client, server_id, status,
                                 status_attr='status'):
    """Waits for a share to reach a given status."""
    body = client.show_share_server(server_id)
    server_status = body[status_attr]
    start = int(time.time())

    while server_status != status:
        time.sleep(client.build_interval)
        body = client.show_share_server(server_id)
        server_status = body[status_attr]
        if server_status in status:
            return
        elif constants.STATUS_ERROR in server_status.lower():
            raise share_exceptions.ShareServerBuildErrorException(
                server_id=server_id)

        if int(time.time()) - start >= client.build_timeout:
            message = ("Share server's %(status_attr)s failed to "
                       "transition to %(status)s within the required "
                       "time %(seconds)s." %
                       {"status_attr": status_attr, "status": status,
                        "seconds": client.build_timeout})
            raise exceptions.TimeoutException(message)


def wait_for_share_replica_status(client, replica_id, expected_status,
                                  status_attr='status'):
    """Waits for a replica's status_attr to reach a given status."""
    body = client.get_share_replica(replica_id)
    replica_status = body[status_attr]
    start = int(time.time())

    while replica_status != expected_status:
        time.sleep(client.build_interval)
        body = client.get_share_replica(replica_id)
        replica_status = body[status_attr]
        if replica_status == expected_status:
            return
        if ('error' in replica_status
                and expected_status != constants.STATUS_ERROR):
            raise share_exceptions.ShareInstanceBuildErrorException(
                id=replica_id)

        if int(time.time()) - start >= client.build_timeout:
            message = ('The %(status_attr)s of Replica %(id)s failed to '
                       'reach %(expected_status)s status within the '
                       'required time (%(time)ss). Current '
                       '%(status_attr)s: %(current_status)s.' %
                       {
                           'status_attr': status_attr,
                           'expected_status': expected_status,
                           'time': client.build_timeout,
                           'id': replica_id,
                           'current_status': replica_status,
                       })
            raise exceptions.TimeoutException(message)


def wait_for_snapshot_access_rule_status(client, snapshot_id, rule_id,
                                         expected_state='active'):
    rule = client.get_snapshot_access_rule(snapshot_id, rule_id)
    state = rule['state']
    start = int(time.time())

    while state != expected_state:
        time.sleep(client.build_interval)
        rule = client.get_snapshot_access_rule(snapshot_id, rule_id)
        state = rule['state']
        if state == expected_state:
            return
        if 'error' in state:
            raise share_exceptions.AccessRuleBuildErrorException(
                snapshot_id)

        if int(time.time()) - start >= client.build_timeout:
            message = ('The status of snapshot access rule %(id)s failed '
                       'to reach %(expected_state)s state within the '
                       'required time (%(time)ss). Current '
                       'state: %(current_state)s.' %
                       {
                           'expected_state': expected_state,
                           'time': client.build_timeout,
                           'id': rule_id,
                           'current_state': state,
                       })
            raise exceptions.TimeoutException(message)


def wait_for_migration_status(client, share_id, dest_host, status_to_wait,
                              version=LATEST_MICROVERSION):
    """Waits for a share to migrate to a certain host."""
    statuses = ((status_to_wait,)
                if not isinstance(status_to_wait, (tuple, list, set))
                else status_to_wait)
    share = client.get_share(share_id, version=version)
    migration_timeout = CONF.share.migration_timeout
    start = int(time.time())
    while share['task_state'] not in statuses:
        time.sleep(client.build_interval)
        share = client.get_share(share_id, version=version)
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
                           'status': six.text_type(statuses),
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
        for msg in client.list_messages():
            if msg['resource_id'] == resource_id:
                return msg

        if int(time.time()) - start >= client.build_timeout:
            message = ('No message for resource with id %s was created in'
                       ' the required time (%s s).' %
                       (resource_id, client.build_timeout))
            raise exceptions.TimeoutException(message)
