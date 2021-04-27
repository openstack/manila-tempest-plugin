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

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


class PublicSharesTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(PublicSharesTest, cls).resource_setup()
        # create share_type
        share_type = cls.create_share_type()
        cls.share_type_id = share_type['id']

    @decorators.idempotent_id('557a0474-9e30-47b4-a766-19e2afb13e66')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_public_with_detail(self):
        # The default RBAC policy in manila only allows admin users with
        # system scope to create public shares since the Stein release
        public_share = self.create_share(
            name='public_share - must be visible to all projects in the cloud',
            description='public_share_desc',
            share_type_id=self.share_type_id,
            is_public=True,
            cleanup_in_class=False,
            client=self.admin_shares_v2_client,
            version=LATEST_MICROVERSION
        )
        private_share = self.create_share(
            name='private_share',
            description='private share in the primary user project',
            share_type_id=self.share_type_id,
            is_public=False,
            cleanup_in_class=False,
            version=LATEST_MICROVERSION
        )

        params = {'is_public': True}
        shares = self.alt_shares_v2_client.list_shares_with_detail(
            params)['shares']

        keys = [
            'status', 'description', 'links', 'availability_zone',
            'created_at', 'share_proto', 'name', 'snapshot_id', 'id',
            'size', 'project_id', 'is_public',
        ]
        [self.assertIn(key, sh.keys()) for sh in shares for key in keys]

        retrieved_public_share = [
            share for share in shares if share['id'] == public_share['id']
        ]
        msg = 'expected id lists %s times in share list' % (
            len(retrieved_public_share))
        self.assertEqual(1, len(retrieved_public_share), msg)
        self.assertTrue(retrieved_public_share[0]['is_public'])

        self.assertFalse(any([s['id'] == private_share['id'] for s in shares]))

    @decorators.idempotent_id('e073182e-459d-4e08-9300-5bc964ca806b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_update_share_set_is_public(self):
        share_name = data_utils.rand_name('tempest-share-name')
        share = self.create_share(name=share_name,
                                  description='a share we will update',
                                  share_type_id=self.share_type_id,
                                  is_public=False,
                                  cleanup_in_class=False,
                                  version=LATEST_MICROVERSION)

        share = self.shares_v2_client.get_share(share['id'])['share']
        self.assertEqual(share_name, share['name'])
        self.assertEqual('a share we will update', share['description'])
        self.assertFalse(share['is_public'])

        # update share, manila's default RBAC only allows administrator
        # users with a system scope token to update a private share to public
        new_name = data_utils.rand_name('tempest-new-share-name')
        new_desc = 'share is now updated'
        updated = self.admin_shares_v2_client.update_share(
            share['id'], name=new_name, desc=new_desc, is_public=True)['share']
        self.assertEqual(new_name, updated['name'])
        self.assertEqual(new_desc, updated['description'])
        self.assertTrue(updated['is_public'])

        # this share must now be publicly accessible
        share = self.alt_shares_v2_client.get_share(share['id'])['share']
        self.assertEqual(new_name, share['name'])
        self.assertEqual(new_desc, share['description'])
        self.assertTrue(share['is_public'])
