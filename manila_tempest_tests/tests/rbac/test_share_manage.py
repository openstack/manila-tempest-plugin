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

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base

CONF = config.CONF


class ShareRbacManageShareTests(rbac_base.ShareRbacBaseTests,
                                metaclass=abc.ABCMeta):

    @classmethod
    def skip_checks(cls):
        super(ShareRbacManageShareTests, cls).skip_checks()
        if not CONF.share.run_manage_unmanage_tests:
            raise cls.skipException('Manage/unmanage tests are disabled.')
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def setup_clients(cls):
        super(ShareRbacManageShareTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.admin_shares_v2_client = (
            cls.os_project_admin.share_v2.SharesV2Client())
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacManageShareTests, cls).resource_setup()
        cls.share_type = cls.get_share_type()

    def share_manage_preparations(self, share_id, unmanage=True):
        share_info = self.admin_shares_v2_client.get_share(share_id)['share']
        export_path = self.admin_shares_v2_client.list_share_export_locations(
            share_id)['export_locations'][0]
        protocol = share_info['share_proto']
        service_host = share_info['host']

        if unmanage:
            self.admin_shares_v2_client.unmanage_share(share_id)
            self.admin_shares_v2_client.wait_for_resource_deletion(
                share_id=share_id)
        return {
            'export_path': export_path,
            'protocol': protocol,
            'service_host': service_host
        }

    @abc.abstractmethod
    def test_manage_share(self):
        pass

    @abc.abstractmethod
    def test_unmanage_share(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacManageShareTests, base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']
    protocol = 'nfs'

    @classmethod
    def setup_clients(cls):
        super(TestProjectAdminTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('8a21f805-2d45-4b0c-8ec5-3f45337bbf66')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        share_data = self.share_manage_preparations(share['id'])
        self.do_request(
            'manage_share', expected_status=200,
            share_type_id=self.share_type['id'], **share_data)

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        alt_share_data = self.share_manage_preparations(alt_share['id'])
        self.do_request(
            'manage_share', expected_status=200,
            share_type_id=self.share_type['id'], **alt_share_data)

    @decorators.idempotent_id('be5b836d-d6cc-40a5-acf4-e5f249035383')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        share_data = self.share_manage_preparations(
            share['id'], unmanage=False)
        self.do_request(
            'unmanage_share', expected_status=202, share_id=share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])

        # Unmanaged share operation removes the share from the management of
        # the shared file systems service without deleting the share.
        # In order to be able to delete the share we need to manage it again,
        # otherwise, it would leave some allocated space.
        managed_share = self.client.manage_share(
            share_type_id=self.share_type['id'], **share_data)['share']
        waiters.wait_for_resource_status(
            self.client, managed_share['id'], constants.STATUS_AVAILABLE)

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        share_data = self.share_manage_preparations(
            alt_share['id'], unmanage=False)
        self.do_request(
            'unmanage_share', expected_status=202, share_id=alt_share['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            share_id=alt_share['id'])

        alt_managed_share = self.client.manage_share(
            share_type_id=self.share_type['id'], **share_data)['share']
        waiters.wait_for_resource_status(
            self.client, alt_managed_share['id'], constants.STATUS_AVAILABLE)


class TestProjectMemberTestsNFS(ShareRbacManageShareTests,
                                base.BaseSharesTest):

    credentials = ['project_member', 'project_admin', 'project_alt_member']
    protocol = 'nfs'

    @decorators.idempotent_id('46f884b2-531d-41c0-8455-8874629b3ea3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share = self.create_share(share_client, self.share_type['id'])
        share_data = self.share_manage_preparations(
            share['id'], unmanage=False)
        self.do_request(
            'manage_share', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'], **share_data)

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        alt_share_data = self.share_manage_preparations(
            alt_share['id'], unmanage=False)
        self.do_request(
            'manage_share', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'], **alt_share_data)

    @decorators.idempotent_id('9dc2b1a5-8195-46b8-a28a-9710be352f18')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share = self.create_share(share_client, self.share_type['id'])
        self.do_request(
            'unmanage_share', expected_status=lib_exc.Forbidden,
            share_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'unmanage_share', expected_status=lib_exc.Forbidden,
            share_id=alt_share['id'])


class TestProjectReaderTestsNFS(TestProjectMemberTestsNFS):
    """Test suite for basic share operations by reader user

    In order to test certain share operations we must create a share resource
    for this. Since reader user is limited in resources creation, we are forced
    to use admin credentials, so we can test other share operations.
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

    @decorators.idempotent_id('cec85349-b7e3-440e-bbbc-3bb5999b119a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share(self):
        super(TestProjectReaderTestsNFS, self).test_manage_share()

    @decorators.idempotent_id('a524620c-90b6-496c-8418-c469e711a607')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share(self):
        super(TestProjectReaderTestsNFS, self).test_unmanage_share()


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
