# Copyright 2014 mirantis Inc.
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

from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class SharesNFSTest(base.BaseSharesMixedTest):
    """Covers share functionality, that is related to NFS share type."""
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(SharesNFSTest, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def resource_setup(cls):
        super(SharesNFSTest, cls).resource_setup()
        # create share_type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

    @decorators.idempotent_id('21ad41fb-04cf-493c-bc2f-66c80220898b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_get_delete_share(self):

        share = self.create_share(self.protocol,
                                  share_type_id=self.share_type_id)
        detailed_elements = {'name', 'id', 'availability_zone',
                             'description', 'project_id',
                             'created_at', 'share_proto', 'metadata',
                             'size', 'snapshot_id', 'share_network_id',
                             'status', 'share_type', 'volume_type', 'links',
                             'is_public'}
        msg = (
            "At least one expected element missing from share "
            "response. Expected %(expected)s, got %(actual)s." % {
                "expected": detailed_elements,
                "actual": share.keys(),
            }
        )
        self.assertTrue(detailed_elements.issubset(share.keys()), msg)
        self.assertFalse(share['is_public'])

        # The 'status' of the share returned by the create API must be
        # set and have value either 'creating' or
        # 'available' (if share creation is really fast as in
        # case of Dummy driver).
        self.assertIn(share['status'], ('creating', 'available'))

        # Get share using v 2.1 - we expect key 'snapshot_support' to be absent
        share_get = self.shares_v2_client.get_share(
            share['id'], version='2.1')['share']
        detailed_elements.add('export_location')
        self.assertTrue(detailed_elements.issubset(share_get.keys()), msg)

        # Get share using v 2.2 - we expect key 'snapshot_support' to exist
        share_get = self.shares_v2_client.get_share(
            share['id'], version='2.2')['share']
        detailed_elements.add('snapshot_support')
        self.assertTrue(detailed_elements.issubset(share_get.keys()), msg)

        if utils.is_microversion_supported('2.9'):
            # Get share using v 2.9 - key 'export_location' is expected
            # to be absent
            share_get = self.shares_v2_client.get_share(
                share['id'], version='2.9')['share']
            detailed_elements.remove('export_location')
            self.assertTrue(detailed_elements.issubset(share_get.keys()), msg)

        # In v 2.11 and beyond, we expect key 'replication_type' in the
        # share data returned by the share create API.
        if utils.is_microversion_supported('2.11'):
            detailed_elements.add('replication_type')
            self.assertTrue(detailed_elements.issubset(share.keys()), msg)

        # In v 2.16 and beyond, we add user_id in show/create/manage
        # share echo.
        if utils.is_microversion_supported('2.16'):
            detailed_elements.add('user_id')
            self.assertTrue(detailed_elements.issubset(share.keys()), msg)

        # In v 2.24 and beyond, we add create_share_from_snapshot_support in
        # show/create/manage share echo.
        if utils.is_microversion_supported('2.24'):
            detailed_elements.add('create_share_from_snapshot_support')
            self.assertTrue(detailed_elements.issubset(share.keys()), msg)

        # In v 2.54 and beyond, we expect key 'progress' in the share data
        # returned by the share create API.
        if utils.is_microversion_supported('2.54'):
            detailed_elements.add('progress')
            self.assertTrue(detailed_elements.issubset(share.keys()), msg)

        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_share,
                          share['id'])

    @decorators.idempotent_id('775f8f87-5727-4bb7-b69f-9ce6b9bdb140')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_create_delete_snapshot(self):
        extra_specs = {'snapshot_support': True}
        share_type = self.create_share_type(extra_specs=extra_specs,
                                            cleanup_in_class=False)
        share = self.create_share(self.protocol,
                                  share_type_id=share_type['id'],
                                  cleanup_in_class=False)

        # create snapshot
        snap = self.create_snapshot_wait_for_active(share["id"])

        detailed_elements = {'name', 'id', 'description',
                             'created_at', 'share_proto', 'size', 'share_size',
                             'share_id', 'status', 'links'}
        msg = (
            "At least one expected element missing from share "
            "response. Expected %(expected)s, got %(actual)s." % {
                "expected": detailed_elements,
                "actual": snap.keys(),
            }
        )
        self.assertTrue(detailed_elements.issubset(snap.keys()), msg)

        # In v2.17 and beyond, we expect user_id and project_id keys
        if utils.is_microversion_supported('2.17'):
            detailed_elements.update({'user_id', 'project_id'})
            self.assertTrue(detailed_elements.issubset(snap.keys()), msg)
        else:
            self.assertNotIn('user_id', detailed_elements)
            self.assertNotIn('project_id', detailed_elements)

        # In v2.73 and beyond, we expect metadata key
        if utils.is_microversion_supported('2.73'):
            detailed_elements.update({'metadata'})
            self.assertTrue(detailed_elements.issubset(snap.keys()), msg)
        else:
            self.assertNotIn('metadata', detailed_elements)

        # delete snapshot
        self.shares_client.delete_snapshot(snap["id"])
        self.shares_client.wait_for_resource_deletion(snapshot_id=snap["id"])
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_snapshot, snap['id'])

    @decorators.idempotent_id('8a14831d-ad1f-447f-b5de-2b8a233b24c0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @testtools.skipUnless(
        CONF.share.capability_create_share_from_snapshot_support,
        "Create share from snapshot tests are disabled.")
    def test_create_share_from_snapshot(self):
        # If multitenant driver used, share_network will be provided by default
        extra_specs = {
            'snapshot_support': True,
            'create_share_from_snapshot_support': True,
        }
        share_type = self.create_share_type(extra_specs=extra_specs,
                                            cleanup_in_class=False)
        share = self.create_share(self.protocol,
                                  share_type_id=share_type['id'],
                                  cleanup_in_class=False)

        # create snapshot
        snap = self.create_snapshot_wait_for_active(share["id"],
                                                    cleanup_in_class=False)

        # create share from snapshot
        s2 = self.create_share(self.protocol,
                               share_type_id=share_type['id'],
                               snapshot_id=snap["id"],
                               cleanup_in_class=False)

        # The 'status' of the share returned by the create API must be
        # set and have value either 'creating' or
        # 'available' (if share creation is really fast as in
        # case of Dummy driver).
        self.assertIn(s2['status'], ('creating', 'available'))

        # verify share, created from snapshot
        get = self.shares_client.get_share(s2["id"])['share']
        msg = ("Expected snapshot_id %s as "
               "source of share %s" % (snap["id"], get["snapshot_id"]))
        self.assertEqual(get["snapshot_id"], snap["id"], msg)

    @decorators.idempotent_id('c609c0b2-d649-4ca3-8334-629b213f5c72')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(not CONF.share.multitenancy_enabled,
                      "Only for multitenancy.")
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @testtools.skipUnless(
        CONF.share.capability_create_share_from_snapshot_support,
        "Create share from snapshot tests are disabled.")
    def test_create_share_from_snapshot_share_network_not_provided(self):
        # We expect usage of share network from parent's share
        # when creating share from snapshot using a driver that supports
        # multi-tenancy.

        extra_specs = {
            'snapshot_support': True,
            'create_share_from_snapshot_support': True,
        }
        share_type = self.create_share_type(extra_specs=extra_specs,
                                            cleanup_in_class=False)
        share = self.create_share(self.protocol,
                                  share_type_id=share_type['id'],
                                  cleanup_in_class=False)

        # get parent share
        parent = self.shares_client.get_share(share["id"])['share']

        # create snapshot
        snap = self.create_snapshot_wait_for_active(share["id"],
                                                    cleanup_in_class=False)

        # create share from snapshot
        child = self.create_share(self.protocol,
                                  snapshot_id=snap["id"],
                                  cleanup_in_class=False)

        # The 'status' of the share returned by the create API must be
        # set and have value either 'creating' or
        # 'available' (if share creation is really fast as in
        # case of Dummy driver).
        self.assertIn(child['status'], ('creating', 'available'))

        # verify share, created from snapshot
        get = self.shares_client.get_share(child["id"])['share']
        keys = {
            "share": share["id"],
            "actual_sn": get["share_network_id"],
            "expected_sn": parent["share_network_id"],
        }
        msg = ("Expected share_network_id %(expected_sn)s for "
               "share %(share)s, but %(actual_sn)s found." % keys)
        self.assertEqual(
            get["share_network_id"], parent["share_network_id"], msg)


class SharesCIFSTest(SharesNFSTest):
    """Covers share functionality, that is related to CIFS share type."""
    protocol = "cifs"


class SharesGLUSTERFSTest(SharesNFSTest):
    """Covers share functionality that is related to GLUSTERFS share type."""
    protocol = "glusterfs"


class SharesHDFSTest(SharesNFSTest):
    """Covers share functionality that is related to HDFS share type."""
    protocol = "hdfs"


class SharesCephFSTest(SharesNFSTest):
    """Covers share functionality that is related to CEPHFS share type."""
    protocol = "cephfs"


class SharesMapRFSTest(SharesNFSTest):
    """Covers share functionality that is related to MapRFS share type."""
    protocol = "maprfs"
