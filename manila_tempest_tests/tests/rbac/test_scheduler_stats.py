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


class ShareRbacSchedulerStatsTests(rbac_base.ShareRbacBaseTests,
                                   metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacSchedulerStatsTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()

    @abc.abstractmethod
    def test_list_storage_pools(self):
        pass


class ProjectAdminTests(ShareRbacSchedulerStatsTests, base.BaseSharesTest):

    credentials = ['project_admin']

    @decorators.idempotent_id('1ec4d0f5-0d60-4bbc-88a4-57fa92f6f62f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_storage_pools(self):
        self.do_request(
            'list_pools', expected_status=200)


class ProjectMemberTests(ShareRbacSchedulerStatsTests, base.BaseSharesTest):

    credentials = ['project_member']

    @decorators.idempotent_id('905aa5ea-eff9-4022-be41-df7a8593809d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_storage_pools(self):
        self.do_request(
            'list_pools', expected_status=lib_exc.Forbidden)


class ProjectReaderTests(ShareRbacSchedulerStatsTests, base.BaseSharesTest):

    credentials = ['project_reader']

    @decorators.idempotent_id('faab12f9-ff51-458d-af47-362d872761e9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_storage_pools(self):
        self.do_request(
            'list_pools', expected_status=lib_exc.Forbidden)
