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

import abc

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base

CONF = config.CONF


class ShareRbacUserMessageTests(rbac_base.ShareRbacBaseTests,
                                metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacUserMessageTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.share_admin_client = cls.os_project_admin.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        # One of the options for generating a user message is to create a share
        # type with invalid extra_specs. Creating a manila share with this
        # share type will fail because no valid host is found.
        extra_specs = {
            'key': 'value',
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        share_type_name = data_utils.rand_name('share-type')
        cls.share_type = cls.share_admin_client.create_share_type(
            name=share_type_name, extra_specs=extra_specs)['share_type']
        cls.addClassResourceCleanup(
            cls.share_admin_client.delete_share_type, cls.share_type['id'])

    def create_user_message(self, client, cleanup=True):
        # Trigger a 'no valid host' situation to generate a message.
        share = client.create_share(
            share_type_id=self.share_type['id'])['share']
        self.addCleanup(client.delete_share, share['id'])
        waiters.wait_for_resource_status(client, share['id'], 'error')

        message = waiters.wait_for_message(client, share['id'])
        if cleanup:
            self.addCleanup(client.delete_message, message['id'])
        return message

    @abc.abstractmethod
    def test_list_messages(self):
        pass

    @abc.abstractmethod
    def test_show_message(self):
        pass

    @abc.abstractmethod
    def test_delete_message(self):
        pass


class ProjectAdminTests(ShareRbacUserMessageTests, base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(ProjectAdminTests, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('2067d8ba-953d-4035-b65d-6001b3d4ea8f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_messages(self):
        message = self.create_user_message(
            self.share_member_client, self.share_type)
        message_alt = self.create_user_message(
            self.alt_project_share_v2_client, self.share_type)

        message_list = self.do_request(
            'list_messages', expected_status=200)['messages']
        message_id_list = [
            s['id'] for s in message_list
        ]

        self.assertIn(message['id'], message_id_list)
        self.assertIn(message_alt['id'], message_id_list)

    @decorators.idempotent_id('ec46f10e-c768-4df5-b75a-0ce3e22d8038')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_show_message(self):
        message = self.create_user_message(
            self.share_member_client, self.share_type)
        self.do_request(
            'get_message', message_id=message['id'], expected_status=200)

        message_alt = self.create_user_message(
            self.alt_project_share_v2_client, self.share_type)
        self.do_request(
            'get_message', message_id=message_alt['id'], expected_status=200)

    @decorators.idempotent_id('b91c355b-a5f8-47aa-8ab4-00a350f8ac7f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_delete_message(self):
        message = self.create_user_message(
            self.share_member_client, cleanup=False)
        self.do_request(
            'delete_message', message_id=message['id'], expected_status=204)

        message_alt = self.create_user_message(
            self.alt_project_share_v2_client, cleanup=False)
        self.do_request(
            'delete_message', message_id=message_alt['id'],
            expected_status=204)


class ProjectMemberTests(ShareRbacUserMessageTests, base.BaseSharesTest):
    """Test suite for basic share use message operations by member user

    In order to test share user message operations we need to preform an action
    that generates a user message. One of the reasons for generating a user
    message is share creation that fails because no valid host is found.
    To achieve this goal we need to create a share type.
    Since only user with admin credentials can create a share type, we have to
    initialize these credentials within project member class.
    """

    credentials = ['project_member', 'project_admin', 'project_alt_member']

    @decorators.idempotent_id('1fd0f86d-cb1e-4694-a54e-4b7774c7c652')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_messages(self):
        share_client = getattr(self, 'share_member_client', self.client)
        message = self.create_user_message(share_client, self.share_type)

        message_alt = self.create_user_message(
            self.alt_project_share_v2_client, self.share_type)

        message_list = self.do_request(
            'list_messages', expected_status=200)['messages']
        message_id_list = [
            s['id'] for s in message_list
        ]

        self.assertIn(message['id'], message_id_list)
        self.assertNotIn(message_alt['id'], message_id_list)

    @decorators.idempotent_id('283d33be-727b-4180-a503-95d31cc99a79')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_show_message(self):
        share_client = getattr(self, 'share_member_client', self.client)
        message = self.create_user_message(share_client, self.share_type)
        self.do_request(
            'get_message', message_id=message['id'], expected_status=200)

        message_alt = self.create_user_message(
            self.alt_project_share_v2_client, self.share_type)
        self.do_request(
            'get_message', message_id=message_alt['id'],
            expected_status=lib_exc.NotFound)

    @decorators.idempotent_id('5821a3a9-6194-414a-9668-0d933a0d4fb0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_delete_message(self):
        share_client = getattr(self, 'share_member_client', self.client)
        message = self.create_user_message(
            share_client, cleanup=False)
        self.do_request(
            'delete_message', message_id=message['id'],
            expected_status=204)

        message_alt = self.create_user_message(
            self.alt_project_share_v2_client, cleanup=False)
        self.do_request(
            'delete_message', message_id=message_alt['id'],
            expected_status=lib_exc.NotFound)
        self.addCleanup(self.share_admin_client.delete_message,
                        message_alt['id'])


class ProjectReaderTests(ProjectMemberTests):
    """Test suite for basic share use message operations by reader user

    In order to test certain share operations we must create a share resource
    for this. Since reader user is limited in resources creation, we are forced
    to use admin credentials, so we can test other share operations.
    In this class we use admin user to create a member user within reader
    project. That way we can perform a reader actions on this resource.
    """

    credentials = ['project_reader', 'project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(ProjectReaderTests, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('ab3b8812-47df-4472-a410-7f84d52999f3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_messages(self):
        super(ProjectReaderTests, self).test_list_messages()

    @decorators.idempotent_id('f0603a61-b620-4f89-afc5-006d1195fa7f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_show_message(self):
        super(ProjectReaderTests, self).test_show_message()

    @decorators.idempotent_id('a03695c7-e05a-4c89-9a04-7d94a8dd2419')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_message(self):
        message = self.create_user_message(
            self.share_member_client, cleanup=False)
        self.do_request(
            'delete_message', message_id=message['id'],
            expected_status=lib_exc.Forbidden)
        self.addCleanup(self.share_admin_client.delete_message, message['id'])

        message_alt = self.create_user_message(
            self.alt_project_share_v2_client, cleanup=False)
        self.do_request(
            'delete_message', message_id=message_alt['id'],
            expected_status=lib_exc.Forbidden)
        self.addCleanup(self.share_admin_client.delete_message,
                        message_alt['id'])
