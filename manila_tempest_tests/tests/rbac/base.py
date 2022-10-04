# Copyright 2022 Red Hat, Inc.
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


from tempest import clients
from tempest import config
from tempest.lib import auth
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils

from manila_tempest_tests.common import waiters

CONF = config.CONF


class ShareRbacBaseTests(object):

    identity_version = 'v3'
    protocols = ['nfs', 'cifs', 'glusterfs', 'hdfs', 'cephfs', 'maprfs']

    @classmethod
    def skip_checks(cls):
        super(ShareRbacBaseTests, cls).skip_checks()
        if not CONF.enforce_scope.manila:
            raise cls.skipException(
                "Tempest is not configured to enforce_scope for manila, "
                "skipping RBAC tests. To enable these tests set "
                "`tempest.conf [enforce_scope] manila=True`."
            )
        if not CONF.share.default_share_type_name:
            raise cls.skipException("Secure rbac tests require a default "
                                    "share type")
        if not any(p in CONF.share.enable_protocols for p in cls.protocols):
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def delete_resource(cls, client, **kwargs):
        key_names = {
            'st': 'share_type',
            'sn': 'share_network',
        }
        key, resource_id = list(kwargs.items())[0]
        key = key.split('_')[0]
        resource_name = key_names[key] if key in key_names else key

        del_action = getattr(client, 'delete_{}'.format(resource_name))
        test_utils.call_and_ignore_notfound_exc(
            del_action, resource_id)
        test_utils.call_and_ignore_notfound_exc(
            client.wait_for_resource_deletion, **kwargs)

    @classmethod
    def create_share(cls, client, share_type_id, size=None, name=None,
                     metadata=None):
        kwargs = {}
        name = name or data_utils.rand_name('share')
        metadata = metadata or {}
        kwargs.update({
            'share_protocol': cls.protocol,
            'size': size or CONF.share.share_size,
            'name': name or data_utils.rand_name('share'),
            'share_type_id': share_type_id,
            'metadata': metadata,
        })
        share = client.create_share(**kwargs)['share']
        waiters.wait_for_resource_status(client, share['id'], 'available')
        cls.addClassResourceCleanup(
            cls.delete_resource, client,
            share_id=share['id'])
        return share

    @classmethod
    def create_snapshot(cls, client, share_id, name=None):
        name = name or data_utils.rand_name('snapshot')
        snapshot = client.create_snapshot(share_id, name=name)['snapshot']
        waiters.wait_for_resource_status(
            client, snapshot['id'], 'available', resource_name='snapshot')
        cls.addClassResourceCleanup(
            cls.delete_resource, client, snapshot_id=snapshot['id'])
        return snapshot

    @classmethod
    def create_share_network(cls, client, name=None):
        name = name or data_utils.rand_name('share_network')
        share_network = client.create_share_network(name=name)['share_network']

        cls.addClassResourceCleanup(
            cls.delete_resource, client, sn_id=share_network['id'])
        return share_network

    @classmethod
    def get_share_type(cls):
        return cls.shares_v2_client.get_default_share_type()['share_type']

    def do_request(self, method, expected_status=200, client=None, **payload):
        if not client:
            client = self.client
        if isinstance(expected_status, type(Exception)):
            self.assertRaises(expected_status,
                              getattr(client, method),
                              **payload)
        else:
            response = getattr(client, method)(**payload)
            self.assertEqual(response.response.status, expected_status)
            return response

    @classmethod
    def setup_user_client(cls, client, project_id=None):
        """Set up project user with its own client.

        This is useful for testing protection of resources in separate
        projects.
        NOTE(lkuchlan): Tempest creates 'project_member' and 'project_reader'
        dynamic credentials in different projects. So this method is also
        necessary for testing protection of resources in a specific project.

        Returns a client object and the user's ID.
        """

        projects_client = client.identity_v3.ProjectsClient()
        users_client = client.identity_v3.UsersClient()
        roles_client = client.identity_v3.RolesClient()

        user_dict = {
            'name': data_utils.rand_name('user'),
            'password': data_utils.rand_password(),
        }
        user_id = users_client.create_user(
            **user_dict)['user']['id']
        cls.addClassResourceCleanup(users_client.delete_user, user_id)

        if not project_id:
            project_id = projects_client.create_project(
                data_utils.rand_name())['project']['id']
            cls.addClassResourceCleanup(
                projects_client.delete_project,
                project_id)

        member_role_id = roles_client.list_roles(
            name='member')['roles'][0]['id']
        roles_client.create_user_role_on_project(
            project_id, user_id, member_role_id)
        creds = auth.KeystoneV3Credentials(
            user_id=user_id,
            password=user_dict['password'],
            project_id=project_id)
        auth_provider = clients.get_auth_provider(creds)
        creds = auth_provider.fill_credentials()
        client = clients.Manager(credentials=creds)
        return client
