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


class ShareRbacShareTypesTests(rbac_base.ShareRbacBaseTests,
                               metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacShareTypesTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()

    @classmethod
    def resource_setup(cls):
        super(ShareRbacShareTypesTests, cls).resource_setup()
        cls.share_type = cls.get_share_type()

    def share_type_properties(self):
        share_type = {}
        share_type['extra_specs'] = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        share_type['name'] = data_utils.rand_name("share-type")
        return share_type

    @abc.abstractmethod
    def test_create_share_type(self):
        pass

    @abc.abstractmethod
    def test_get_share_type(self):
        pass

    @abc.abstractmethod
    def test_list_share_type(self):
        pass

    @abc.abstractmethod
    def test_update_share_type(self):
        pass


class ProjectAdminTests(ShareRbacShareTypesTests, base.BaseSharesTest):

    credentials = ['project_admin']

    @classmethod
    def setup_clients(cls):
        super(ProjectAdminTests, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('b24bf137-352a-4ebd-b736-27518d32c1bd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_type(self):
        share_type = self.do_request(
            'create_share_type', expected_status=200,
            **self.share_type_properties())['share_type']
        self.addCleanup(self.delete_resource, self.client,
                        st_id=share_type['id'])

    @decorators.idempotent_id('741d69f3-b3fe-49cf-9e33-6b0696b353ec')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_type(self):
        self.do_request(
            'get_share_type', expected_status=200,
            share_type_id=self.share_type['id'])

    @decorators.idempotent_id('3f811ac6-a345-424f-863a-1a7a49ba0a32')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_type(self):
        share_type_list = self.do_request(
            'list_share_types', expected_status=200)['share_types']
        share_type_id_list = [
            st['id'] for st in share_type_list
        ]
        self.assertIn(self.share_type['id'], share_type_id_list)

    @decorators.idempotent_id('3bb9aaab-3c17-45be-a9b1-dd8b6942cb59')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_share_type(self):
        share_type = self.client.create_share_type(
            **self.share_type_properties())['share_type']
        self.addCleanup(self.client.delete_share_type, share_type['id'])

        name = data_utils.rand_name("updated_share_type")
        self.do_request(
            'update_share_type', expected_status=200,
            share_type_id=share_type['id'], name=name)


class ProjectMemberTests(ShareRbacShareTypesTests, base.BaseSharesTest):

    credentials = ['project_member']

    @decorators.idempotent_id('270761cf-07b4-4fc7-96b5-4deb205adce3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_type(self):
        self.do_request(
            'create_share_type', expected_status=lib_exc.Forbidden,
            **self.share_type_properties())

    @decorators.idempotent_id('d3f53218-d92f-489d-8e2e-985178e7fd02')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_type(self):
        self.do_request(
            'get_share_type', expected_status=200,
            share_type_id=self.share_type['id'])

    @decorators.idempotent_id('757c7ccd-e14e-4c1a-9172-998ae5eed1b8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_type(self):
        share_type_list = self.do_request(
            'list_share_types', expected_status=200)['share_types']
        share_type_id_list = [
            st['id'] for st in share_type_list
        ]
        self.assertIn(self.share_type['id'], share_type_id_list)

    @decorators.idempotent_id('5210170c-b749-4645-a86f-7347c3ba3e99')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_type(self):
        name = data_utils.rand_name("updated_share_type")
        self.do_request(
            'update_share_type', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'], name=name)


class ProjectReaderTests(ShareRbacShareTypesTests, base.BaseSharesTest):

    credentials = ['project_reader']

    @decorators.idempotent_id('f4c352c4-c12b-4722-9fe7-9a2ec639ee63')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_type(self):
        self.do_request(
            'create_share_type', expected_status=lib_exc.Forbidden,
            **self.share_type_properties())

    @decorators.idempotent_id('e9d9f244-7778-443b-aadc-bac9f2b687b7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_type(self):
        self.do_request(
            'get_share_type', expected_status=200,
            share_type_id=self.share_type['id'])

    @decorators.idempotent_id('cf0e97f1-4853-4cf2-9e9a-041c6e57bab5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_type(self):
        share_type_list = self.do_request(
            'list_share_types', expected_status=200)['share_types']
        share_type_id_list = [
            st['id'] for st in share_type_list
        ]
        self.assertIn(self.share_type['id'], share_type_id_list)

    @decorators.idempotent_id('338d579b-ff91-4a30-af53-d0b317919efb')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_type(self):
        name = data_utils.rand_name("updated_share_type")
        self.do_request(
            'update_share_type', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'], name=name)
