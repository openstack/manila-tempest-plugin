# Copyright 2023 NetApp, Inc.
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


class ShareRbacInstanceExportLocationsTests(rbac_base.ShareRbacBaseTests,
                                            metaclass=abc.ABCMeta):

    @classmethod
    def skip_checks(cls):
        super(ShareRbacInstanceExportLocationsTests, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def setup_clients(cls):
        super(ShareRbacInstanceExportLocationsTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.admin_client = cls.os_project_admin.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacInstanceExportLocationsTests, cls).resource_setup()
        share_type = cls.get_share_type()

        # 'share_member_client' attribute is initialized in the 'setup_clients'
        # of the reader class in order to use member credentials.
        share_client = getattr(cls, 'share_member_client', cls.client)
        share = cls.create_share(share_client, share_type['id'])

        alt_share = cls.create_share(
            cls.alt_project_share_v2_client, share_type['id'])

        cls.share_instances = cls.admin_client.get_instances_of_share(
            share['id'])['share_instances']
        cls.alt_share_instances = cls.admin_client.get_instances_of_share(
            alt_share['id'])['share_instances']

    @abc.abstractmethod
    def test_share_instance_list_export_locations(self):
        pass

    @abc.abstractmethod
    def test_share_instance_show_export_location(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacInstanceExportLocationsTests,
                               base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']
    protocol = 'nfs'

    @decorators.idempotent_id('f3218212-d70b-4a3d-bc05-8905a4f14279')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_share_instance_list_export_locations(self):
        locations = self.do_request(
            'list_share_instance_export_locations', expected_status=200,
            instance_id=self.share_instances[0]['id'])
        self.assertNotEmpty(locations)

        alt_locations = self.do_request(
            'list_share_instance_export_locations', expected_status=200,
            instance_id=self.alt_share_instances[0]['id'])
        self.assertNotEmpty(alt_locations)

    @decorators.idempotent_id('c58c74cf-4fcd-4404-a2f9-1a9e6b4443c4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_share_instance_show_export_location(self):
        export_location = (
            self.client.list_share_instance_export_locations(
                self.share_instances[0]['id'])['export_locations'])
        self.do_request(
            'get_share_instance_export_location', expected_status=200,
            instance_id=self.share_instances[0]['id'],
            export_location_uuid=export_location[0]['id'])

        alt_export_location = (
            self.client.list_share_instance_export_locations(
                self.alt_share_instances[0]['id'])['export_locations'])
        self.do_request(
            'get_share_instance_export_location', expected_status=200,
            instance_id=self.alt_share_instances[0]['id'],
            export_location_uuid=alt_export_location[0]['id'])


class TestProjectMemberTestsNFS(ShareRbacInstanceExportLocationsTests,
                                base.BaseSharesTest):
    """Test suite for share instance export location operations by member

    In order to test certain share operations we must create a share
    resource for this. Since project member user is limited in intances
    operations, we are forced to use admin credentials to get to instances,
    so we can test other operations.
    """

    credentials = ['project_member', 'project_admin', 'project_alt_member']
    protocol = 'nfs'

    @decorators.idempotent_id('27d495dd-b52d-417d-bfbf-9bb700e85f4d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_instance_list_export_locations(self):
        self.do_request(
            'list_share_instance_export_locations',
            expected_status=lib_exc.Forbidden,
            instance_id=self.share_instances[0]['id'])

        self.do_request(
            'list_share_instance_export_locations',
            expected_status=lib_exc.Forbidden,
            instance_id=self.alt_share_instances[0]['id'])

    @decorators.idempotent_id('8de74960-b9cf-4ee6-81dc-fbb5dbb291dd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_instance_show_export_location(self):
        export_location = (
            self.admin_client.list_share_instance_export_locations(
                self.share_instances[0]['id'])['export_locations'])
        self.do_request(
            'get_share_instance_export_location',
            expected_status=lib_exc.Forbidden,
            instance_id=self.share_instances[0]['id'],
            export_location_uuid=export_location[0]['id'])

        alt_export_location = (
            self.admin_client.list_share_instance_export_locations(
                self.alt_share_instances[0]['id'])['export_locations'])
        self.do_request(
            'get_share_instance_export_location',
            expected_status=lib_exc.Forbidden,
            instance_id=self.alt_share_instances[0]['id'],
            export_location_uuid=alt_export_location[0]['id'])


class TestProjectReaderTestsNFS(TestProjectMemberTestsNFS):
    """Test suite for share instance export location operations by reader user

    In order to test certain share operations we must create a share
    resource for this. Since reader user is limited in resources creation, we
    are forced to use member credentials, so we can test other share
    operations. In this class we use member user to create a share and admin
    to list its instances. That way we can perform a reader actions on
    this resource.
    """

    credentials = ['project_reader', 'project_member', 'project_admin',
                   'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(TestProjectReaderTestsNFS, cls).setup_clients()
        # Initialize a member user in the same project of reader user
        # for creating a share resource.
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('9db505c1-45d3-4d82-8879-38c4861e4fb3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_instance_list_export_locations(self):
        (super(TestProjectReaderTestsNFS, self)
            .test_share_instance_list_export_locations())

    @decorators.idempotent_id('09009203-ff20-4914-8764-7865839e29b2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_instance_show_export_location(self):
        (super(TestProjectReaderTestsNFS, self)
            .test_share_instance_show_export_location())


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
