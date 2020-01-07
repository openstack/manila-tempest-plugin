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
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


@ddt.ddt
class ShareTypeAvailabilityZonesNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareTypeAvailabilityZonesNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported('2.48')

    @classmethod
    def resource_setup(cls):
        super(ShareTypeAvailabilityZonesNegativeTest, cls).resource_setup()
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
    @ddt.data('az1,     az2, az 3,  ', 'az1,,az 3', ',az2,  az 3')
    def test_share_type_azs_create_with_invalid_az_spec(self, spec):
        az_spec = {'availability_zones': spec}
        extra_specs = self.add_extra_specs_to_dict(az_spec)

        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_type,
            data_utils.rand_name('share_type_invalid_az_spec'),
            cleanup_in_class=False,
            extra_specs=extra_specs,
            client=self.admin_shares_v2_client)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_type_azs_filter_by_invalid_azs_extra_spec(self):
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type_id, self.az_spec, self.valid_azs_spec)
        share_type_no_az_spec = self.create_share_type(
            data_utils.rand_name('support_any_az_share_type'),
            cleanup_in_class=False,
            extra_specs=self.add_extra_specs_to_dict(),
            client=self.admin_shares_v2_client)['share_type']

        share_types = self.admin_shares_v2_client.list_share_types(params={
            'extra_specs': {'availability_zones': self.invalid_azs_spec}}
        )['share_types']
        share_type_ids = [s['id'] for s in share_types]
        self.assertNotIn(self.share_type_id, share_type_ids)
        self.assertIn(share_type_no_az_spec['id'], share_type_ids)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_type_azs_shares_unsupported_az(self):
        """Test using an AZ not supported by the share type."""
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type_id, self.az_spec, self.invalid_azs_spec)
        self.assertRaises(
            lib_exc.BadRequest, self.create_share,
            share_type_id=self.share_type_id,
            availability_zone=self.valid_azs[0],
            cleanup_in_class=False)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_type_azs_share_groups_unsupported(self):
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type_id, self.az_spec, self.invalid_azs_spec)
        self.assertRaises(
            lib_exc.BadRequest, self.create_share_group,
            share_group_type_id=self.share_group_type_id,
            share_type_ids=[self.share_type_id],
            availability_zone=self.valid_azs[0],
            cleanup_in_class=False)
