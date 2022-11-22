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


class ShareRbacExtraSpecsTests(rbac_base.ShareRbacBaseTests,
                               metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacExtraSpecsTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.admin_shares_v2_client = (
            cls.os_project_admin.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacExtraSpecsTests, cls).resource_setup()
        cls.extra_specs = {u'key': u'value'}
        cls.share_type = cls.create_share_type()

    @abc.abstractmethod
    def test_create_share_type_extra_specs(self):
        pass

    @abc.abstractmethod
    def test_get_share_type_extra_specs(self):
        pass

    @abc.abstractmethod
    def test_update_share_type_extra_spec(self):
        pass

    @abc.abstractmethod
    def test_delete_share_type_extra_spec(self):
        pass


class ProjectAdminTests(ShareRbacExtraSpecsTests, base.BaseSharesTest):

    credentials = ['project_admin']

    @classmethod
    def setup_clients(cls):
        super(ProjectAdminTests, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('d51817f4-b186-4eca-8779-f3c36dcd98e7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_type_extra_specs(self):
        self.do_request(
            'create_share_type_extra_specs', expected_status=200,
            share_type_id=self.share_type['id'], extra_specs=self.extra_specs)
        self.addCleanup(
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            self.share_type['id'], extra_spec_name='key')

    @decorators.idempotent_id('d4deeb0b-8765-4487-9f1f-9f10088934dd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_type_extra_specs(self):
        self.do_request(
            'get_share_type_extra_specs', expected_status=200,
            share_type_id=self.share_type['id'])

    @decorators.idempotent_id('bb27641b-5249-4343-bb08-5a123f31b9f1')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_share_type_extra_spec(self):
        self.do_request(
            'update_share_type_extra_spec', expected_status=200,
            share_type_id=self.share_type['id'], spec_name='key',
            spec_value='value_updated')

    @decorators.idempotent_id('81d59322-8ec1-4f32-a50d-2fedd1cca655')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_delete_share_type_extra_spec(self):
        self.admin_shares_v2_client.create_share_type_extra_specs(
            self.share_type['id'], self.extra_specs)
        self.do_request(
            'delete_share_type_extra_spec', expected_status=202,
            share_type_id=self.share_type['id'], extra_spec_name='key')


class ProjectMemberTests(ShareRbacExtraSpecsTests, base.BaseSharesTest):

    credentials = ['project_member', 'project_admin']

    @decorators.idempotent_id('446c1e7c-5ca2-46f5-b2f3-6417152e5bf8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_type_extra_specs(self):
        self.do_request(
            'create_share_type_extra_specs', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'], extra_specs=self.extra_specs)

    @decorators.idempotent_id('aabdf0c1-8b68-4c40-a542-cc1dbd039279')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_share_type_extra_specs(self):
        self.do_request(
            'get_share_type_extra_specs', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'])

    @decorators.idempotent_id('3629f91c-ad21-4321-acd9-7fca92a4721a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_type_extra_spec(self):
        self.do_request(
            'update_share_type_extra_spec', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'], spec_name='key',
            spec_value='value_updated')

    @decorators.idempotent_id('0bee97ab-b406-481c-9b8b-4813fb9f49dc')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_type_extra_spec(self):
        self.admin_shares_v2_client.create_share_type_extra_specs(
            self.share_type['id'], self.extra_specs)
        self.do_request(
            'delete_share_type_extra_spec', expected_status=lib_exc.Forbidden,
            share_type_id=self.share_type['id'], extra_spec_name='key')
        self.addCleanup(
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            self.share_type['id'], extra_spec_name='key')


class ProjectReaderTests(ProjectMemberTests):

    credentials = ['project_reader', 'project_admin']

    @decorators.idempotent_id('da80b823-9a96-45c3-8f86-e9f7fc5ad2c6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_type_extra_specs(self):
        super(ProjectReaderTests, self).test_create_share_type_extra_specs()

    @decorators.idempotent_id('78989220-22dc-46d2-b83b-63f070988eed')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_share_type_extra_specs(self):
        super(ProjectReaderTests, self).test_get_share_type_extra_specs()

    @decorators.idempotent_id('c77173d4-b90c-4edf-a9b6-a26c81aaec42')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_type_extra_spec(self):
        super(ProjectReaderTests, self).test_update_share_type_extra_spec()

    @decorators.idempotent_id('46fc8e62-b987-444f-ab9f-cd86a8960156')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_type_extra_spec(self):
        super(ProjectReaderTests, self).test_delete_share_type_extra_spec()
