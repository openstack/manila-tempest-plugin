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
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareRbacRulesTests(rbac_base.ShareRbacBaseTests, metaclass=abc.ABCMeta):

    @classmethod
    def skip_checks(cls):
        super(ShareRbacRulesTests, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def setup_clients(cls):
        super(ShareRbacRulesTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacRulesTests, cls).resource_setup()
        cls.metadata = {u'key': u'value'}

    def access(self, share_id, access_type, access_to, access_level='rw'):
        access = {}
        access['share_id'] = share_id
        access['access_type'] = access_type
        access['access_to'] = access_to
        access['access_level'] = access_level
        return access

    def allow_access(self, client, share_id, access_type, access_to,
                     access_level='rw', metadata=None, status='active',
                     cleanup=True):

        kwargs = {
            'access_type': access_type,
            'access_to': access_to,
            'access_level': access_level,
            'metadata': metadata
        }

        rule = client.create_access_rule(share_id, **kwargs)['access']
        waiters.wait_for_resource_status(
            client, share_id, status, resource_name='access_rule',
            rule_id=rule['id'])
        if cleanup:
            self.addCleanup(
                client.wait_for_resource_deletion, rule_id=rule['id'],
                share_id=share_id)
            self.addCleanup(client.delete_access_rule, share_id, rule['id'])
        return rule

    @abc.abstractmethod
    def test_grant_access_rule(self):
        pass

    @abc.abstractmethod
    def test_get_access(self):
        pass

    @abc.abstractmethod
    def test_list_access(self):
        pass

    @abc.abstractmethod
    def test_delete_access(self):
        pass

    @abc.abstractmethod
    def test_update_access_rule_metadata(self):
        pass

    @abc.abstractmethod
    def test_delete_access_rule_metadata(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacRulesTests, base.BaseSharesTest):
    credentials = ['project_admin', 'project_alt_member']
    protocol = 'nfs'

    @classmethod
    def setup_clients(cls):
        super(TestProjectAdminTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @classmethod
    def resource_setup(cls):
        super(TestProjectAdminTestsNFS, cls).resource_setup()
        share_type = cls.get_share_type()
        cls.share = cls.create_share(cls.client, share_type['id'])
        cls.alt_share = cls.create_share(
            cls.alt_project_share_v2_client, share_type['id'])

    @decorators.idempotent_id('5b6897d1-4b2a-490c-990e-941ea4893f47')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_access(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'get_access_rule', expected_status=200, access_id=access['id'])

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'get_access_rule', expected_status=200, access_id=alt_access['id'])

    @decorators.idempotent_id('f8e9a2bb-ccff-4fc5-8d61-2930f87406cd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_access(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type, access_to=access_to)
        access_list = self.do_request(
            'list_access_rules', expected_status=200,
            share_id=self.share['id'])['access_list'][0]['id']

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        alt_access_list = self.do_request(
            'list_access_rules', expected_status=200,
            share_id=self.share['id'])['access_list'][0]['id']

        self.assertIn(access['id'], access_list)
        self.assertNotIn(alt_access['id'], alt_access_list)

    @decorators.idempotent_id('b4d7a91c-a75e-4ad9-93cb-8e5234fea97a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_grant_access_rule(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.do_request(
            'create_access_rule', expected_status=200,
            **self.access(self.share['id'], access_type, access_to))['access']
        waiters.wait_for_resource_status(
            self.client, self.share["id"], "active",
            resource_name='access_rule', rule_id=access["id"])
        self.addCleanup(
            self.client.wait_for_resource_deletion, rule_id=access['id'],
            share_id=self.share['id'])
        self.addCleanup(
            self.client.delete_access_rule, self.share['id'], access['id'])

        alt_access = self.do_request(
            'create_access_rule', expected_status=200,
            **self.access(
                self.alt_share['id'], access_type, access_to))['access']
        waiters.wait_for_resource_status(
            self.client, self.alt_share["id"], "active",
            resource_name='access_rule', rule_id=alt_access["id"])
        self.addCleanup(
            self.client.wait_for_resource_deletion, rule_id=alt_access['id'],
            share_id=self.alt_share['id'])
        self.addCleanup(
            self.client.delete_access_rule, self.alt_share['id'],
            alt_access['id'])

    @decorators.idempotent_id('e24d7018-cb49-4306-9947-716b4e4250c5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_access(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type,
            access_to=access_to, cleanup=False)
        self.do_request(
            'delete_access_rule', expected_status=202,
            share_id=self.share['id'], rule_id=access['id'])
        self.client.wait_for_resource_deletion(
            rule_id=access['id'], share_id=self.share['id'])

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to,
            cleanup=False)
        self.do_request(
            'delete_access_rule', expected_status=202,
            share_id=self.alt_share['id'], rule_id=alt_access['id'])
        self.client.wait_for_resource_deletion(
            rule_id=alt_access['id'], share_id=self.alt_share['id'])

    @decorators.idempotent_id('ffc07445-d0d1-4bf9-9fbc-4f409d48bccd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_update_access_rule_metadata(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'update_access_metadata', expected_status=200,
            access_id=access['id'], metadata=self.metadata)

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'update_access_metadata', expected_status=200,
            access_id=alt_access['id'], metadata=self.metadata)

    @decorators.idempotent_id('fd580d91-1d8d-4dd0-8484-01c412ddb768')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_access_rule_metadata(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type, access_to=access_to,
            metadata=self.metadata)
        self.do_request(
            'delete_access_metadata', expected_status=200,
            access_id=access['id'], key='key')

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to,
            metadata=self.metadata)
        self.do_request(
            'delete_access_metadata', expected_status=200,
            access_id=alt_access['id'], key='key')


class TestProjectMemberTestsNFS(ShareRbacRulesTests, base.BaseSharesTest):
    credentials = ['project_member', 'project_alt_member']
    protocol = 'nfs'

    @classmethod
    def resource_setup(cls):
        super(TestProjectMemberTestsNFS, cls).resource_setup()
        share_type = cls.get_share_type()
        share_client = getattr(cls, 'share_member_client', cls.client)
        cls.share = cls.create_share(share_client, share_type['id'])
        cls.alt_share = cls.create_share(
            cls.alt_project_share_v2_client, share_type['id'])

    @decorators.idempotent_id('de643909-88a2-470b-8a14-0417696ec451')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_access(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        share_client = getattr(self, 'share_member_client', self.client)
        access = self.allow_access(
            share_client, self.share['id'], access_type=access_type,
            access_to=access_to)
        self.do_request(
            'get_access_rule', expected_status=200, access_id=access['id'])

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'get_access_rule', expected_status=lib_exc.NotFound,
            access_id=alt_access['id'])

    @decorators.idempotent_id('7c6c4262-5095-4cd7-9d9c-8064009a9055')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_access(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        share_client = getattr(self, 'share_member_client', self.client)
        access = self.allow_access(
            share_client, self.share['id'], access_type=access_type,
            access_to=access_to)
        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)

        access_list = self.do_request(
            'list_access_rules', expected_status=200,
            share_id=self.share['id'])['access_list']
        access_id_list = [
            s['id'] for s in access_list
        ]

        self.assertIn(access['id'], access_id_list)
        self.assertNotIn(alt_access['id'], access_id_list)

    @decorators.idempotent_id('61cf6f6c-5d7c-48d7-9d5a-e6ea288afdbc')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_grant_access_rule(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        share_client = getattr(self, 'share_member_client', self.client)
        access = self.do_request(
            'create_access_rule', client=share_client, expected_status=200,
            **self.access(self.share['id'], access_type, access_to))['access']
        waiters.wait_for_resource_status(
            share_client, self.share["id"], "active",
            resource_name='access_rule', rule_id=access["id"])
        self.addCleanup(
            self.client.wait_for_resource_deletion, rule_id=access['id'],
            share_id=self.share['id'])
        self.addCleanup(
            self.client.delete_access_rule, self.share['id'], access['id'])

        self.do_request(
            'create_access_rule', client=share_client,
            expected_status=lib_exc.NotFound,
            **self.access(self.alt_share['id'], access_type, access_to))

    @decorators.idempotent_id('8665d1b1-de4c-42d4-93ff-8dc6d2b73a2d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_access(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        share_client = getattr(self, 'share_member_client', self.client)
        access = self.allow_access(
            share_client, self.share['id'], access_type=access_type,
            access_to=access_to, cleanup=False)
        self.do_request(
            'delete_access_rule', expected_status=202,
            share_id=self.share['id'], rule_id=access['id'])
        self.client.wait_for_resource_deletion(
            rule_id=access['id'], share_id=self.share['id'])

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'delete_access_rule', expected_status=lib_exc.NotFound,
            share_id=self.alt_share['id'], rule_id=alt_access['id'])

    @decorators.idempotent_id('c5e84362-6075-425b-bfa3-898abfd9d5a0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_access_rule_metadata(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        share_client = getattr(self, 'share_member_client', self.client)
        access = self.allow_access(
            share_client, self.share['id'], access_type=access_type,
            access_to=access_to)
        self.do_request(
            'update_access_metadata', expected_status=200,
            access_id=access['id'], metadata=self.metadata)

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'update_access_metadata', expected_status=lib_exc.NotFound,
            access_id=alt_access['id'], metadata=self.metadata)

    @decorators.idempotent_id('abb17315-6510-4b6e-ae6c-dd99a6088954')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_access_rule_metadata(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        share_client = getattr(self, 'share_member_client', self.client)
        access = self.allow_access(
            share_client, self.share['id'], access_type=access_type,
            access_to=access_to, metadata=self.metadata)
        self.do_request(
            'delete_access_metadata', expected_status=200,
            access_id=access['id'], key='key')

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to,
            metadata=self.metadata)
        self.do_request(
            'delete_access_metadata', expected_status=lib_exc.NotFound,
            access_id=alt_access['id'], key='key')


class TestProjectReaderTestsNFS(TestProjectMemberTestsNFS):
    """Test suite for basic share access rule operations by reader user

    In order to test certain share operations we must create a share
    resource for this. Since reader user is limited in resources creation, we
    are forced to use admin credentials, so we can test other share
    operations. In this class we use admin user to create a member user within
    reader project. That way we can perform a reader actions on this resource.
    """

    credentials = ['project_reader', 'project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(TestProjectReaderTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('0eec0f05-f2f3-4500-9d9e-1b77ebc476c2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_access(self):
        super(TestProjectReaderTestsNFS, self).test_get_access()

    @decorators.idempotent_id('9ddc26b6-f8bf-45d9-a2c6-a9eec9bfb8d2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_access(self):
        super(TestProjectReaderTestsNFS, self).test_list_access()

    @decorators.idempotent_id('ace870f9-af91-4259-8760-dc7d7107b7ff')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_grant_access_rule(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        self.do_request(
            'create_access_rule', expected_status=lib_exc.Forbidden,
            **self.access(self.share['id'], access_type, access_to))

        self.do_request(
            'create_access_rule', expected_status=lib_exc.Forbidden,
            **self.access(self.alt_share['id'], access_type, access_to))

    @decorators.idempotent_id('7a702c74-8d31-49e3-859a-cc8a78d7915e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_access(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'delete_access_rule', expected_status=lib_exc.Forbidden,
            share_id=self.share['id'], rule_id=access['id'])

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'delete_access_rule', expected_status=lib_exc.Forbidden,
            share_id=self.alt_share['id'], rule_id=alt_access['id'])

    @decorators.idempotent_id('a61d7f06-6f0e-4da3-b11d-1c3a0b5bd416')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_access_rule_metadata(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'update_access_metadata', expected_status=lib_exc.Forbidden,
            access_id=access['id'], metadata=self.metadata)

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to)
        self.do_request(
            'update_access_metadata', expected_status=lib_exc.Forbidden,
            access_id=alt_access['id'], metadata=self.metadata)

    @decorators.idempotent_id('5faf0e0b-b246-4392-901d-9e7d628f0d6e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_access_rule_metadata(self):
        access_type, access_to = (
            utils.get_access_rule_data_from_config(self.protocol))
        access = self.allow_access(
            self.share_member_client, self.share['id'],
            access_type=access_type, access_to=access_to,
            metadata=self.metadata)
        self.do_request(
            'delete_access_metadata', expected_status=lib_exc.Forbidden,
            access_id=access['id'], key='key')

        alt_access = self.allow_access(
            self.alt_project_share_v2_client, self.alt_share['id'],
            access_type=access_type, access_to=access_to,
            metadata=self.metadata)
        self.do_request(
            'delete_access_metadata', expected_status=lib_exc.Forbidden,
            access_id=alt_access['id'], key='key')


class TestProjectAdminTestsCEPHFS(TestProjectAdminTestsNFS):
    protocol = 'cephfs'


class TestProjectMemberTestsCEPHFS(TestProjectMemberTestsNFS):
    protocol = 'cephfs'


class TestProjectReaderTestsCEPHFS(TestProjectReaderTestsNFS):
    protocol = 'cephfs'


class TestProjectAdminTestsCIFS(TestProjectAdminTestsNFS):
    protocol = 'cifs'


class TestProjectMemberTestsCIFS(TestProjectMemberTestsNFS):
    protocol = 'cifs'


class TestProjectReaderTestsCIFS(TestProjectReaderTestsNFS):
    protocol = 'cifs'
