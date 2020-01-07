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

import ddt
from tempest import config
from tempest.lib.common.utils import data_utils
import testtools

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

tc = testtools.testcase
CONF = config.CONF


@ddt.ddt
class ShareTypeAvailabilityZonesTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareTypeAvailabilityZonesTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.48")

    @classmethod
    def resource_setup(cls):
        super(ShareTypeAvailabilityZonesTest, cls).resource_setup()
        cls.share_type = cls._create_share_type()
        cls.share_type_id = cls.share_type['id']
        cls.share_group_type = cls._create_share_group_type()
        cls.share_group_type_id = cls.share_group_type['id']
        all_azs = cls.get_availability_zones()
        cls.valid_azs = cls.get_availability_zones_matching_share_type(
            cls.share_type)
        cls.invalid_azs = ((set(all_azs) - set(cls.valid_azs))
                           or ['az_that_doesnt_exist'])
        cls.az_spec = 'availability_zones'
        cls.valid_azs_spec = ', '.join(cls.valid_azs)
        cls.invalid_azs_spec = ', '.join(cls.invalid_azs)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('az1,     az2, az 3  ', 'az1,az2,az 3', 'az1   ,az2,   az 3')
    def test_share_type_azs_create_and_get_share_type(self, spec):
        az_spec = {'availability_zones': spec}
        extra_specs = self.add_extra_specs_to_dict(az_spec)
        share_type = self.create_share_type(
            data_utils.rand_name('az_share_type'),
            cleanup_in_class=False,
            extra_specs=extra_specs,
            client=self.admin_shares_v2_client)['share_type']
        self.assertEqual(
            'az1,az2,az 3', share_type['extra_specs']['availability_zones'])

        share_type = self.admin_shares_v2_client.get_share_type(
            share_type['id'])['share_type']
        self.assertEqual(
            'az1,az2,az 3', share_type['extra_specs']['availability_zones'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('az1', 'az2', 'az 3', 'az1,  az 3', 'az 3, az1',
              'az2, az 3, az1')
    def test_share_type_azs_filter_by_availability_zones(self, filter):
        az_spec = {'availability_zones': 'az1, az2, az 3'}
        extra_specs = self.add_extra_specs_to_dict(az_spec)
        share_type_in_specific_azs = self.create_share_type(
            data_utils.rand_name('support_some_azs_share_type'),
            cleanup_in_class=False,
            extra_specs=extra_specs,
            client=self.admin_shares_v2_client)['share_type']

        extra_specs = self.add_extra_specs_to_dict()
        share_type_no_az_spec = self.create_share_type(
            data_utils.rand_name('support_any_az_share_type'),
            cleanup_in_class=False,
            extra_specs=extra_specs,
            client=self.admin_shares_v2_client)['share_type']

        share_types = self.admin_shares_v2_client.list_share_types(
            params={'extra_specs': {'availability_zones': filter}}
        )['share_types']
        share_type_ids = [s['id'] for s in share_types]
        self.assertIn(share_type_in_specific_azs['id'], share_type_ids)
        self.assertIn(share_type_no_az_spec['id'], share_type_ids)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_share_type_azs_old_version_api_ignores_spec(self):
        """< v2.48, configuring share type AZs shouldn't fail share creation"""
        # Use valid AZs as share_type's availability_zones
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type_id, self.az_spec, self.valid_azs_spec)
        self.create_share(share_type_id=self.share_type_id,
                          cleanup_in_class=False, version='2.47')

        # Use invalid AZs as share_type's availability_zones
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type_id, self.az_spec, self.invalid_azs_spec)
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False, version='2.47')
        share = self.shares_v2_client.get_share(share['id'])
        # Test default scheduler behavior: the share type capabilities should
        # have ensured the share landed in an AZ that is supported
        # regardless of the 'availability_zones' extra-spec
        self.assertIn(share['availability_zone'], self.valid_azs)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(True, False)
    def test_share_type_azs_shares_az_in_create_req(self, specify_az):
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type_id, self.az_spec, self.valid_azs_spec)
        kwargs = {
            'share_type_id': self.share_type_id,
            'cleanup_in_class': False,
            'availability_zone': self.valid_azs[0] if specify_az else None,
        }
        share = self.create_share(**kwargs)
        share = self.shares_v2_client.get_share(share['id'])
        if specify_az:
            self.assertEqual(self.valid_azs[0], share['availability_zone'])
        else:
            self.assertIn(share['availability_zone'], self.valid_azs)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(True, False)
    def test_share_type_azs_share_groups_az_in_create_req(self, specify_az):
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type_id, self.az_spec, self.valid_azs_spec)
        kwargs = {
            'share_group_type_id': self.share_group_type_id,
            'share_type_ids': [self.share_type_id],
            'cleanup_in_class': False,
            'availability_zone': self.valid_azs[0] if specify_az else None,
        }
        # Create share group
        share_group = self.create_share_group(**kwargs)
        share_group = self.shares_v2_client.get_share_group(share_group['id'])
        if specify_az:
            self.assertEqual(self.valid_azs[0],
                             share_group['availability_zone'])
        else:
            self.assertIn(share_group['availability_zone'], self.valid_azs)
