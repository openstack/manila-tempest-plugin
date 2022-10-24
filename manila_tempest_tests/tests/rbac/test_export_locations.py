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

from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base

CONF = config.CONF


class ShareRbacExportLocationsTests(rbac_base.ShareRbacBaseTests,
                                    metaclass=abc.ABCMeta):

    @classmethod
    def skip_checks(cls):
        super(ShareRbacExportLocationsTests, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def setup_clients(cls):
        super(ShareRbacExportLocationsTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @abc.abstractmethod
    def test_list_export_locations(self):
        pass

    @abc.abstractmethod
    def test_show_export_location(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacExportLocationsTests,
                               base.BaseSharesTest):

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

    @decorators.idempotent_id('c8d75c9f-104b-48a8-9817-17280ce516a8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_export_locations(self):
        self.do_request(
            'list_share_export_locations', expected_status=200,
            share_id=self.share['id'])

        self.do_request(
            'list_share_export_locations', expected_status=200,
            share_id=self.alt_share['id'])

    @decorators.idempotent_id('01ac6355-fcad-4af8-b0ad-748fc111051d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_show_export_location(self):
        export_location = self.share_member_client.list_share_export_locations(
            self.share['id'])['export_locations']
        self.do_request(
            'get_share_export_location', expected_status=200,
            share_id=self.share['id'],
            export_location_uuid=export_location[0]['id'])

        export_location = (
            self.alt_project_share_v2_client.list_share_export_locations(
                self.alt_share['id'])['export_locations'])
        self.do_request(
            'get_share_export_location', expected_status=200,
            share_id=self.alt_share['id'],
            export_location_uuid=export_location[0]['id'])


class TestProjectMemberTestsNFS(ShareRbacExportLocationsTests,
                                base.BaseSharesTest):

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

    @decorators.idempotent_id('b25351bb-102f-437e-a0c1-01d926fa0a7d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_export_locations(self):
        self.do_request(
            'list_share_export_locations', expected_status=200,
            share_id=self.share['id'])

        self.do_request(
            'list_share_export_locations', expected_status=lib_exc.Forbidden,
            share_id=self.alt_share['id'])

    @decorators.idempotent_id('95297484-1081-4225-986d-e4b3017d992f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_show_export_location(self):
        share_client = getattr(self, 'share_member_client', self.client)
        export_location = share_client.list_share_export_locations(
            self.share['id'])['export_locations']
        self.do_request(
            'get_share_export_location', expected_status=200,
            share_id=self.share['id'],
            export_location_uuid=export_location[0]['id'])

        export_location = (
            self.alt_project_share_v2_client.list_share_export_locations(
                self.alt_share['id'])['export_locations'])
        self.do_request(
            'get_share_export_location', expected_status=lib_exc.Forbidden,
            share_id=self.alt_share['id'],
            export_location_uuid=export_location[0]['id'])


class TestProjectReaderTestsNFS(TestProjectMemberTestsNFS):
    """Test suite for basic share export location operations by reader user

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

    @classmethod
    def resource_setup(cls):
        super(TestProjectReaderTestsNFS, cls).resource_setup()
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('889ecfa7-89b3-4b16-a368-f55bbc6af228')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_export_locations(self):
        super(TestProjectReaderTestsNFS, self).test_list_export_locations()

    @decorators.idempotent_id('1ab5f0c2-d844-4284-9b66-1ba2aa14b835')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_show_export_location(self):
        super(TestProjectReaderTestsNFS, self).test_show_export_location()


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
