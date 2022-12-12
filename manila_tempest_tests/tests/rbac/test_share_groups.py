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


class ShareRbacShareGroupsTests(rbac_base.ShareRbacBaseTests,
                                metaclass=abc.ABCMeta):

    @classmethod
    def skip_checks(cls):
        super(ShareRbacShareGroupsTests, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def setup_clients(cls):
        super(ShareRbacShareGroupsTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.admin_shares_v2_client = (
            cls.os_project_admin.share_v2.SharesV2Client())
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacShareGroupsTests, cls).resource_setup()
        cls.share_type = cls.create_share_type()
        cls.share_group_type = cls.create_share_group_type(
            cls.share_type['id'])

    def share_group(self, share_group_type_id, share_type_ids):
        share_group = {}
        share_group['name'] = data_utils.rand_name('share_group')
        share_group['share_group_type_id'] = share_group_type_id
        share_group['share_type_ids'] = [share_type_ids]
        return share_group

    @abc.abstractmethod
    def test_get_share_group(self):
        pass

    @abc.abstractmethod
    def test_list_share_groups(self):
        pass

    @abc.abstractmethod
    def test_create_share_group(self):
        pass

    @abc.abstractmethod
    def test_delete_share_group(self):
        pass

    @abc.abstractmethod
    def test_force_delete_share_group(self):
        pass

    @abc.abstractmethod
    def test_update_share_group(self):
        pass

    @abc.abstractmethod
    def test_reset_share_group(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacShareGroupsTests, base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']
    protocol = 'nfs'

    @classmethod
    def setup_clients(cls):
        super(TestProjectAdminTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('0de993c5-8389-4997-8f7f-345e27f563f1')
    def test_get_share_group(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'get_share_group', expected_status=200,
            share_group_id=share_group['id'])

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'get_share_group', expected_status=200,
            share_group_id=alt_share_group['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('3b277a44-dcae-46da-a58c-f5281d8abc84')
    def test_list_share_groups(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])

        params = {"all_tenants": 1}
        share_group_list = self.do_request(
            'list_share_groups', expected_status=200,
            params=params)['share_groups']
        share_group_id_list = [
            s['id'] for s in share_group_list
        ]

        self.assertIn(share_group['id'], share_group_id_list)
        self.assertIn(alt_share_group['id'], share_group_id_list)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('d060996e-c5f2-4dff-820b-6892a096a425')
    def test_create_share_group(self):
        share_group = self.do_request(
            'create_share_group', expected_status=202,
            **self.share_group(self.share_group_type['id'],
                               self.share_type['id']))['share_group']
        waiters.wait_for_resource_status(
            self.client, share_group['id'], 'available',
            resource_name='share_group')
        self.addCleanup(self.client.wait_for_resource_deletion,
                        share_group_id=share_group['id'])
        self.addCleanup(self.client.delete_share_group, share_group['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('ea6cbb78-057e-4fbc-86bf-125b033cb76f')
    def test_delete_share_group(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'delete_share_group', expected_status=202,
            share_group_id=share_group['id'])
        self.client.wait_for_resource_deletion(
            share_group_id=share_group['id'])

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'delete_share_group', expected_status=202,
            share_group_id=alt_share_group['id'])
        self.client.wait_for_resource_deletion(
            share_group_id=alt_share_group['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('2cb00ffb-47e3-495e-853c-007752c9e679')
    def test_force_delete_share_group(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_force_delete', expected_status=202,
            share_group_id=share_group['id'])
        self.client.wait_for_resource_deletion(
            share_group_id=share_group['id'])

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_force_delete', expected_status=202,
            share_group_id=alt_share_group['id'])
        self.client.wait_for_resource_deletion(
            share_group_id=alt_share_group['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('1bab40d5-bdba-4a23-9300-807fe513bf15')
    def test_update_share_group(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        name = data_utils.rand_name('rename_share')
        self.do_request(
            'update_share_group', expected_status=200,
            share_group_id=share_group['id'], name=name)

        alt_share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        name = data_utils.rand_name('rename_share')
        self.do_request(
            'update_share_group', expected_status=200,
            share_group_id=alt_share_group['id'], name=name)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('069bc68e-6411-44b8-abe9-399885f0eee5')
    def test_reset_share_group(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_reset_state', expected_status=202,
            share_group_id=share_group['id'], status='error')

        alt_share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_reset_state', expected_status=202,
            share_group_id=alt_share_group['id'], status='error')


class TestProjectMemberTestsNFS(ShareRbacShareGroupsTests,
                                base.BaseSharesTest):

    credentials = ['project_member', 'project_admin', 'project_alt_member']
    protocol = 'nfs'

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('a29e1a68-220e-40fc-98ea-9092fd256d07')
    def test_get_share_group(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share_group = self.create_share_group(
            share_client, self.share_group_type['id'], [self.share_type['id']])
        self.do_request(
            'get_share_group', expected_status=200,
            share_group_id=share_group['id'])

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'get_share_group', expected_status=lib_exc.NotFound,
            share_group_id=alt_share_group['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('d9c04932-c47e-46e0-bfcf-79c2af32c4c7')
    def test_list_share_groups(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share_group = self.create_share_group(
            share_client, self.share_group_type['id'], [self.share_type['id']])
        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])

        params = {"all_tenants": 1}
        share_group_list = self.do_request(
            'list_share_groups', expected_status=200,
            params=params)['share_groups']
        share_group_id_list = [
            s['id'] for s in share_group_list
        ]

        self.assertIn(share_group['id'], share_group_id_list)
        self.assertNotIn(alt_share_group['id'], share_group_id_list)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('ebad2242-1fb5-4d99-9a5a-281c1944e03d')
    def test_create_share_group(self):
        share_group = self.do_request(
            'create_share_group', expected_status=202,
            **self.share_group(self.share_group_type['id'],
                               self.share_type['id']))['share_group']
        waiters.wait_for_resource_status(
            self.client, share_group['id'], 'available',
            resource_name='share_group')
        self.addCleanup(self.client.wait_for_resource_deletion,
                        share_group_id=share_group['id'])
        self.addCleanup(self.client.delete_share_group, share_group['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('f5c243e4-5128-4a1c-9a15-8c9f0a44437e')
    def test_delete_share_group(self):
        share_group = self.create_share_group(
            self.client, self.share_group_type['id'], [self.share_type['id']])
        self.do_request(
            'delete_share_group', expected_status=202,
            share_group_id=share_group['id'])
        self.client.wait_for_resource_deletion(
            share_group_id=share_group['id'])

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'delete_share_group', expected_status=lib_exc.NotFound,
            share_group_id=alt_share_group['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('36a58d50-1257-479f-80a2-f9b7a00814e2')
    def test_force_delete_share_group(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share_group = self.create_share_group(
            share_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_force_delete', expected_status=lib_exc.Forbidden,
            share_group_id=share_group['id'])

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_force_delete', expected_status=lib_exc.Forbidden,
            share_group_id=alt_share_group['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('cf9e34b6-6c04-4920-a811-2dbcf07ba14e')
    def test_update_share_group(self):
        share_group = self.create_share_group(
            self.client, self.share_group_type['id'], [self.share_type['id']])
        name = data_utils.rand_name('rename_share')
        self.do_request(
            'update_share_group', expected_status=200,
            share_group_id=share_group['id'], name=name)

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        name = data_utils.rand_name('rename_share')
        self.do_request(
            'update_share_group', expected_status=lib_exc.NotFound,
            share_group_id=alt_share_group['id'], name=name)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('2108c4cd-74e0-467f-823a-e44cf8686afa')
    def test_reset_share_group(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share_group = self.create_share_group(
            share_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_reset_state', expected_status=lib_exc.Forbidden,
            share_group_id=share_group['id'], status='error')

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'share_group_reset_state', expected_status=lib_exc.Forbidden,
            share_group_id=alt_share_group['id'], status='error')


class TestProjectReaderTestsNFS(TestProjectMemberTestsNFS):
    """Test suite for basic share group operations by reader user

    In order to test certain share operations we must create a share group
    resource for this. Since reader user is limited in resources creation, we
    are forced to use admin credentials, so we can test other share operations.
    In this class we use admin user to create a member user within reader
    project. That way we can perform a reader actions on this resource.
    """

    credentials = ['project_reader', 'project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(TestProjectReaderTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('ec0ecbb0-5d45-4624-bb26-8b2e140e2ea9')
    def test_get_share_group(self):
        super(TestProjectReaderTestsNFS, self).test_get_share_group()

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('4ac87837-5bdf-4253-ab50-dd6efdcea285')
    def test_list_share_groups(self):
        super(TestProjectReaderTestsNFS, self).test_list_share_groups()

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('526dcd91-e789-48f8-b209-c384d77e5803')
    def test_create_share_group(self):
        self.do_request(
            'create_share_group', expected_status=lib_exc.Forbidden,
            **self.share_group(self.share_group_type['id'],
                               self.share_type['id']))

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('fdf4d49e-a576-441f-9a3c-e2d58c0d8679')
    def test_delete_share_group(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'delete_share_group', expected_status=lib_exc.Forbidden,
            share_group_id=share_group['id'])

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        self.do_request(
            'delete_share_group', expected_status=lib_exc.Forbidden,
            share_group_id=alt_share_group['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('eddca093-e3a1-4a79-a8c7-8fd04c77b02f')
    def test_force_delete_share_group(self):
        super(TestProjectReaderTestsNFS, self).test_force_delete_share_group()

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('4530c19d-0aa5-402e-ac83-a3f2333f6c71')
    def test_update_share_group(self):
        share_group = self.create_share_group(
            self.share_member_client, self.share_group_type['id'],
            [self.share_type['id']])
        name = data_utils.rand_name('rename_share')
        self.do_request(
            'update_share_group', expected_status=lib_exc.Forbidden,
            share_group_id=share_group['id'], name=name)

        alt_share_group = self.create_share_group(
            self.alt_project_share_v2_client, self.share_group_type['id'],
            [self.share_type['id']])
        name = data_utils.rand_name('rename_share')
        self.do_request(
            'update_share_group', expected_status=lib_exc.Forbidden,
            share_group_id=alt_share_group['id'], name=name)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('37f23531-69b5-418d-bd91-7913341586ec')
    def test_reset_share_group(self):
        super(TestProjectReaderTestsNFS, self).test_reset_share_group()


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
