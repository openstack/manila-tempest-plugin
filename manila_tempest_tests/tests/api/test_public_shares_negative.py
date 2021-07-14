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

from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base


class PublicSharesNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(PublicSharesNegativeTest, cls).resource_setup()
        # create share_type
        share_type = cls.create_share_type()
        share_type_id = share_type['id']
        # create a public share - manila's default RBAC only allows
        # administrator users operating at system scope to create public shares
        cls.share = cls.create_share(
            name='public_share',
            description='public_share_desc',
            share_type_id=share_type_id,
            is_public=True,
            metadata={'key': 'value'},
            client=cls.admin_shares_v2_client
        )

    @decorators.idempotent_id('255011c0-4ed9-4174-bb13-8bbd06a62529')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_share_with_wrong_public_value(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.admin_shares_v2_client.update_share,
                          self.share["id"],
                          is_public="truebar")

    @decorators.idempotent_id('3443493b-f56a-4faa-9968-e7cbb0d2802f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_other_tenants_public_share(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_shares_v2_client.update_share,
                          self.share["id"],
                          name="new_name")

    @decorators.idempotent_id('68d1f1bc-16e4-4086-8982-7e44ca6bdc4d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_other_tenants_public_share(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_shares_v2_client.delete_share,
                          self.share['id'])

    @decorators.idempotent_id('1f9e5d84-0885-4a4b-9196-9031a1c01508')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_of_other_tenants_public_share(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_shares_v2_client.set_metadata,
                          self.share['id'],
                          {'key': 'value'})

    @decorators.idempotent_id('fed7a935-9699-43a1-854e-67b61ba6233e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_metadata_of_other_tenants_public_share(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_shares_v2_client.update_all_metadata,
                          self.share['id'],
                          {'key': 'value'})

    @decorators.idempotent_id('bd62adeb-73c2-4b04-8812-80b479cd5c3b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_metadata_of_other_tenants_public_share(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.alt_shares_v2_client.delete_metadata,
                          self.share['id'],
                          'key')
