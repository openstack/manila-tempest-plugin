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

from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base

CONF = config.CONF


class ShareRbacShareNetworkTests(rbac_base.ShareRbacBaseTests,
                                 metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacShareNetworkTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacShareNetworkTests, cls).resource_setup()
        cls.share_type = cls.get_share_type()

    @abc.abstractmethod
    def test_create_share_network(self):
        pass

    @abc.abstractmethod
    def test_list_share_network(self):
        pass

    @abc.abstractmethod
    def test_show_share_network(self):
        pass

    @abc.abstractmethod
    def test_delete_share_network(self):
        pass

    @abc.abstractmethod
    def test_update_share_network(self):
        pass


class ProjectAdminTests(ShareRbacShareNetworkTests, base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(ProjectAdminTests, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('358dd850-cd81-4b81-aefa-3dfcb7aa4551')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_network(self):
        share_network = self.do_request(
            'create_share_network', expected_status=200)['share_network']
        self.addCleanup(
            self.delete_resource, self.client, sn_id=share_network['id'])

    @decorators.idempotent_id('deb20301-9d7c-4c08-b1f0-fc2c403ea708')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_network(self):
        share_network = self.create_share_network(self.share_member_client)
        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        params = {"all_tenants": 1}
        share_network_list = self.do_request(
            'list_share_networks', expected_status=200,
            params=params)['share_networks']
        share_network_id_list = [
            s['id'] for s in share_network_list
        ]

        self.assertIn(share_network['id'], share_network_id_list)
        self.assertIn(alt_share_network['id'], share_network_id_list)

    @decorators.idempotent_id('43a3be84-d08b-4f17-89cf-02abda6df580')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_show_share_network(self):
        share_network = self.create_share_network(self.share_member_client)
        self.do_request(
            'get_share_network', expected_status=200,
            share_network_id=share_network['id'])

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'get_share_network', expected_status=200,
            share_network_id=alt_share_network['id'])

    @decorators.idempotent_id('6c403ed6-b810-4794-8e9b-d57f173443a2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_delete_share_network(self):
        share_network = self.create_share_network(self.share_member_client)
        self.do_request(
            'delete_share_network', expected_status=202,
            sn_id=share_network['id'])

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'delete_share_network', expected_status=202,
            sn_id=alt_share_network['id'])

    @decorators.idempotent_id('abd2443d-3490-462a-8e51-73b6a8f48795')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_share_network(self):
        share_network = self.create_share_network(self.share_member_client)
        name = data_utils.rand_name("updated_share_network")
        self.do_request(
            'update_share_network', expected_status=200,
            sn_id=share_network['id'], name=name)

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'update_share_network', expected_status=200,
            sn_id=alt_share_network['id'], name=name)


class ProjectMemberTests(ShareRbacShareNetworkTests, base.BaseSharesTest):

    credentials = ['project_member', 'project_alt_member']

    @decorators.idempotent_id('d051c749-3d1c-4485-86c5-6eb860b49cad')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_network(self):
        share_network = self.do_request(
            'create_share_network', expected_status=200)['share_network']
        self.addCleanup(
            self.delete_resource, self.client, sn_id=share_network['id'])

    @decorators.idempotent_id('ac33cd51-1efe-4aaf-99ab-b510b7551571')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_network(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share_network = self.create_share_network(share_client)
        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        share_network_list = self.do_request(
            'list_share_networks', expected_status=200)['share_networks']
        share_network_id_list = [
            s['id'] for s in share_network_list
        ]

        self.assertIn(share_network['id'], share_network_id_list)
        self.assertNotIn(alt_share_network['id'], share_network_id_list)

    @decorators.idempotent_id('dc3f8f95-f8c5-4030-93dd-e4c56e40b477')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_share_network(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share_network = self.create_share_network(share_client)
        self.do_request(
            'get_share_network', expected_status=200,
            share_network_id=share_network['id'])

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'get_share_network', expected_status=lib_exc.NotFound,
            share_network_id=alt_share_network['id'])

    @decorators.idempotent_id('717977ab-f077-411a-9bdc-06c8ec9d4f8c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_network(self):
        share_network = self.create_share_network(self.client)
        self.do_request(
            'delete_share_network', expected_status=202,
            sn_id=share_network['id'])

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'delete_share_network', expected_status=lib_exc.NotFound,
            sn_id=alt_share_network['id'])

    @decorators.idempotent_id('d1fce94c-b163-452d-bf79-13b6edf47e30')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_network(self):
        share_network = self.create_share_network(self.client)
        name = data_utils.rand_name("updated_share_network")
        self.do_request(
            'update_share_network', expected_status=200,
            sn_id=share_network['id'], name=name)

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'update_share_network', expected_status=lib_exc.NotFound,
            sn_id=alt_share_network['id'], name=name)


class ProjectReaderTests(ProjectMemberTests):
    """Test suite for basic share network operations by reader user

    In order to test certain share operations we must create a share network
    resource for this. Since reader user is limited in resources creation, we
    are forced to use admin credentials, so we can test other share
    operations. In this class we use admin user to create a member user within
    reader project. That way we can perform a reader actions on this resource.
    """

    credentials = ['project_reader', 'project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(ProjectReaderTests, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @decorators.idempotent_id('73dd9f09-7106-4fd5-a484-0eb986002e3b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_network(self):
        self.do_request(
            'create_share_network', expected_status=lib_exc.Forbidden)

    @decorators.idempotent_id('841e9e69-2a22-4572-9147-b233c8a842bc')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_network(self):
        super(ProjectReaderTests, self).test_list_share_network()

    @decorators.idempotent_id('c98893c8-cdc6-42af-a842-1ee9466904ae')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_share_network(self):
        super(ProjectReaderTests, self).test_show_share_network()

    @decorators.idempotent_id('f8f26bce-ff82-4472-a8dd-0f46c1757386')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_network(self):
        share_network = self.create_share_network(self.share_member_client)
        self.do_request(
            'delete_share_network', expected_status=lib_exc.Forbidden,
            sn_id=share_network['id'])

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'delete_share_network', expected_status=lib_exc.Forbidden,
            sn_id=alt_share_network['id'])

    @decorators.idempotent_id('67b745cd-e669-4872-bbb7-9307960fbd77')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_network(self):
        share_network = self.create_share_network(self.share_member_client)
        name = data_utils.rand_name("updated_share_network")
        self.do_request(
            'update_share_network', expected_status=lib_exc.Forbidden,
            sn_id=share_network['id'], name=name)

        alt_share_network = self.create_share_network(
            self.alt_project_share_v2_client)
        self.do_request(
            'update_share_network', expected_status=lib_exc.Forbidden,
            sn_id=alt_share_network['id'], name=name)
