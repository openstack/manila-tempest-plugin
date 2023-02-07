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


class ShareRbacQuotasTests(rbac_base.ShareRbacBaseTests,
                           metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacQuotasTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacQuotasTests, cls).resource_setup()
        cls.quotas = cls.client.show_quotas(cls.client.tenant_id)['quota_set']
        cls.alt_quotas = cls.alt_project_share_v2_client.show_quotas(
            cls.alt_project_share_v2_client.tenant_id)['quota_set']

    @abc.abstractmethod
    def test_default_quotas(self):
        pass

    @abc.abstractmethod
    def test_show_quotas(self):
        pass

    @abc.abstractmethod
    def test_show_quotas_detail(self):
        pass

    @abc.abstractmethod
    def test_update_tenant_quota_shares(self):
        pass

    @abc.abstractmethod
    def test_delete_quotas(self):
        pass


class TestProjectAdminTests(ShareRbacQuotasTests, base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']

    @decorators.idempotent_id('e102292f-93f9-4918-96b2-bb270e29e43e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_default_quotas(self):
        self.do_request(
            'default_quotas', expected_status=200,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'default_quotas', expected_status=200,
            tenant_id=self.alt_project_share_v2_client.tenant_id)

    @decorators.idempotent_id('77c14ee8-9dbc-47dc-a86e-3a26f33beda5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_show_quotas(self):
        self.do_request(
            'show_quotas', expected_status=200,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'show_quotas', expected_status=200,
            tenant_id=self.alt_project_share_v2_client.tenant_id)

    @decorators.idempotent_id('0bce045c-5575-4301-b526-032812a2e71f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_show_quotas_detail(self):
        self.do_request(
            'detail_quotas', expected_status=200,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'detail_quotas', expected_status=200,
            tenant_id=self.alt_project_share_v2_client.tenant_id)

    @decorators.idempotent_id('b055f9ea-6176-45f9-a918-d9120912fcf6')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_update_tenant_quota_shares(self):
        self.do_request(
            'update_quotas', expected_status=200,
            tenant_id=self.client.tenant_id,
            shares=int(self.quotas['shares']) + 2)

        self.do_request(
            'update_quotas', expected_status=200,
            tenant_id=self.alt_project_share_v2_client.tenant_id,
            shares=int(self.alt_quotas['shares']) + 2)

    @decorators.idempotent_id('fe9ce5ab-4e93-4bdf-bd2d-d1b35a8b19f8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_quotas(self):
        self.do_request(
            'reset_quotas', expected_status=202,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'reset_quotas', expected_status=202,
            tenant_id=self.alt_project_share_v2_client.tenant_id)


class TestProjectMemberTests(ShareRbacQuotasTests, base.BaseSharesTest):

    credentials = ['project_member', 'project_alt_member']

    @decorators.idempotent_id('a81d40fc-04b2-4535-ad44-c989a51e49b9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_default_quotas(self):
        self.do_request(
            'default_quotas', expected_status=200,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'default_quotas', expected_status=200,
            tenant_id=self.alt_project_share_v2_client.tenant_id)

    @decorators.idempotent_id('52194358-6268-446c-ada4-74fb7e23dbe9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_show_quotas(self):
        self.do_request(
            'show_quotas', expected_status=200,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'show_quotas', expected_status=lib_exc.Forbidden,
            tenant_id=self.alt_project_share_v2_client.tenant_id)

    @decorators.idempotent_id('68b3d3e7-8ebd-4b20-bf56-7b4e4c365eda')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_show_quotas_detail(self):
        self.do_request(
            'detail_quotas', expected_status=200,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'detail_quotas', expected_status=lib_exc.Forbidden,
            tenant_id=self.alt_project_share_v2_client.tenant_id)

    @decorators.idempotent_id('5a86d62d-5fdf-448e-bd6b-43e26e39201f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_tenant_quota_shares(self):
        self.do_request(
            'update_quotas', expected_status=lib_exc.Forbidden,
            tenant_id=self.client.tenant_id,
            shares=int(self.quotas['shares']) + 2)

        self.do_request(
            'update_quotas', expected_status=lib_exc.Forbidden,
            tenant_id=self.alt_project_share_v2_client.tenant_id,
            shares=int(self.alt_quotas['shares']) + 2)

    @decorators.idempotent_id('1928eea7-ca78-4004-8e5f-6d58a446503c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_quotas(self):
        self.do_request(
            'reset_quotas', expected_status=lib_exc.Forbidden,
            tenant_id=self.client.tenant_id)

        self.do_request(
            'reset_quotas', expected_status=lib_exc.Forbidden,
            tenant_id=self.alt_project_share_v2_client.tenant_id)


class TestProjectReaderTests(TestProjectMemberTests):

    credentials = ['project_reader', 'project_alt_member']

    @decorators.idempotent_id('51ec3c23-8c3b-45ff-9e41-38141ac82145')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_default_quotas(self):
        super(TestProjectReaderTests, self).test_default_quotas()

    @decorators.idempotent_id('48ca6e6b-6ad1-43b6-bdb7-848fe6a4d0fb')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_show_quotas(self):
        super(TestProjectReaderTests, self).test_show_quotas()

    @decorators.idempotent_id('0648bf5f-d8c8-4fd4-9713-27e9b5a1cda8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_default_quotas_detail(self):
        super(TestProjectReaderTests, self).test_show_quotas_detail()

    @decorators.idempotent_id('4051f57d-3d79-4007-8b90-b5abf744b4b3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_tenant_quota_shares(self):
        super(TestProjectReaderTests, self).test_update_tenant_quota_shares()

    @decorators.idempotent_id('8185210d-edf4-40e7-840a-484ab21bf7bd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_quotas(self):
        super(TestProjectReaderTests, self).test_delete_quotas()
