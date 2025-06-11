# Copyright 2025 Cloudifcation GmbH.  All rights reserved.
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

import ddt
from oslo_log import log
from tempest import config
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.common import barbican_client_mgr
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LOG = log.getLogger(__name__)


@ddt.ddt
class ShareEncryptionNFSTest(base.BaseSharesMixedTest):
    """Covers share functionality, that is related to NFS share type."""
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(ShareEncryptionNFSTest, cls).skip_checks()
        if not CONF.share.run_encryption_tests:
            raise cls.skipException('Encryption tests are disabled.')
        utils.check_skip_if_microversion_not_supported("2.90")

        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

        if ('share_server' not in CONF.share.capability_encryption_support and
                'share' not in CONF.share.capability_encryption_support):
            message = "Unsupported value of encryption support capability"
            raise cls.skipException(message)

    @classmethod
    def resource_setup(cls):
        super(ShareEncryptionNFSTest, cls).resource_setup()

        extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        if 'share_server' in CONF.share.capability_encryption_support:
            extra_specs.update({'encryption_support': 'share_server'})
        elif 'share' in CONF.share.capability_encryption_support:
            extra_specs.update({'encryption_support': 'share'})

        # create share_type
        cls.share_type_enc = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_enc_id = cls.share_type_enc['id']

        # setup barbican client
        cls.barbican_mgr = barbican_client_mgr.BarbicanClientManager()
        cls.barbican_mgr.setup_clients(cls.os_primary)

    @decorators.idempotent_id('21ad41fb-04cf-493c-bc2f-66c80220898c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_share_with_share_server_encryption_key_ref(self):

        secret_href = self.barbican_mgr.store_secret()
        secret_href_uuid = self.barbican_mgr.ref_to_uuid(secret_href)

        share = self.create_share(
            share_protocol=self.protocol,
            share_type_id=self.share_type_enc_id,
            share_network_id=self.shares_v2_client.share_network_id,
            size=1,
            name="encrypted_share",
            encryption_key_ref=secret_href_uuid,
            cleanup_in_class=False)

        self.assertEqual(share['encryption_key_ref'], secret_href_uuid)

        # Delete Barbican secret
        self.barbican_mgr.delete_secret(secret_href_uuid)


class ShareEncryptionCIFSTest(ShareEncryptionNFSTest):
    """Covers share functionality, that is related to CIFS share type."""
    protocol = "cifs"
