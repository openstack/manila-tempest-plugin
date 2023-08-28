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
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF

LOCKS_MIN_API_VERSION = '2.81'


class ResourceLockNegativeTestAPIOnly(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ResourceLockNegativeTestAPIOnly, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported(LOCKS_MIN_API_VERSION)

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @decorators.idempotent_id('dd978cf7-1622-49e8-a6c8-3da4ac6c6f86')
    def test_create_resource_lock_invalid_resource(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_resource_lock,
            'invalid-share-id',
            'share'
        )

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @decorators.idempotent_id('d5600bdc-72c8-43fd-9900-c112aa6c87fa')
    def test_delete_resource_lock_invalid(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.delete_resource_lock,
            'invalid-lock-id'
        )


class ResourceLockNegativeTestWithShares(base.BaseSharesMixedTest):
    @classmethod
    def skip_checks(cls):
        super(ResourceLockNegativeTestWithShares, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported(LOCKS_MIN_API_VERSION)

    @classmethod
    def resource_setup(cls):
        super(ResourceLockNegativeTestWithShares, cls).resource_setup()
        share_type = cls.create_share_type()
        cls.share = cls.create_share(share_type_id=share_type['id'])
        cls.user_project = cls.os_admin.projects_client.show_project(
            cls.shares_v2_client.project_id)['project']

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('658297a8-d675-471d-8a19-3d9e9af3a352')
    def test_create_resource_lock_invalid_resource_action(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_resource_lock,
            self.share['id'],
            'share',
            resource_action='invalid-action'
        )

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('0057b3e7-c250-492d-805b-e355dff954ed')
    def test_create_resource_lock_invalid_lock_reason_too_long(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_resource_lock,
            self.share['id'],
            'share',
            resource_action='delete',
            lock_reason='invalid' * 150,
        )

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('a2db3d29-b42f-4c0b-b484-afd32f91f747')
    def test_update_resource_lock_invalid_param(self):
        lock = self.create_resource_lock(self.share['id'])
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.update_resource_lock,
            lock['id'],
            resource_action='invalid-action'
        )
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.update_resource_lock,
            lock['id'],
            lock_reason='invalid' * 150,
        )

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('45b12120-0fc3-461f-8776-fdb92e599394')
    def test_update_resource_lock_created_by_different_user(self):
        lock = self.create_resource_lock(self.share['id'])
        new_user = self.create_user_and_get_client(project=self.user_project)
        self.assertRaises(
            lib_exc.Forbidden,
            new_user.shares_v2_client.update_resource_lock,
            lock['id'],
            lock_reason="I shouldn't be able to do this",
        )

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('00a8ef2b-8769-4aad-aefc-43fc579492f7')
    def test_delete_resource_lock_created_by_different_user(self):
        lock = self.create_resource_lock(self.share['id'])
        new_user = self.create_user_and_get_client(project=self.user_project)
        self.assertRaises(
            lib_exc.Forbidden,
            new_user.shares_v2_client.delete_resource_lock,
            lock['id'],
        )
