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
from oslo_utils import uuidutils
import six
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF

MICROVERSION = '2.37'
QUERY_BY_TIMESTAMP_MICROVERSION = '2.52'


class UserMessageNegativeTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(UserMessageNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_lt(MICROVERSION)

    def setUp(self):
        super(UserMessageNegativeTest, self).setUp()
        self.message = self.create_user_message()

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    def test_show_message_of_other_tenants(self):
        isolated_client = self.get_client_with_isolated_creds(
            type_of_creds='alt', client_version='2')
        self.assertRaises(lib_exc.NotFound,
                          isolated_client.get_message,
                          self.message['id'])

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    def test_show_nonexistent_message(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_message,
                          six.text_type(uuidutils.generate_uuid()))

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    def test_delete_message_of_other_tenants(self):
        isolated_client = self.get_client_with_isolated_creds(
            type_of_creds='alt', client_version='2')
        self.assertRaises(lib_exc.NotFound,
                          isolated_client.delete_message,
                          self.message['id'])

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    def test_delete_nonexistent_message(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_message,
                          six.text_type(uuidutils.generate_uuid()))

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @base.skip_if_microversion_not_supported(QUERY_BY_TIMESTAMP_MICROVERSION)
    def test_list_messages_with_invalid_time_format(self):
        params_key = ['created_since', 'created_before']
        for key in params_key:
            params = {key: 'invalid_time'}
            self.assertRaises(lib_exc.BadRequest,
                              self.shares_v2_client.list_messages,
                              params=params)
