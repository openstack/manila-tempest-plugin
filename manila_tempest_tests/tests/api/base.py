# Copyright 2014 Mirantis Inc.
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

import copy
import re
import traceback

from oslo_log import log
import six

from tempest import config
from tempest.lib.common import cred_client
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions
from tempest import test

from manila_tempest_tests import clients
from manila_tempest_tests.common import constants
from manila_tempest_tests import share_exceptions
from manila_tempest_tests import utils

CONF = config.CONF
LOG = log.getLogger(__name__)

# Test tags related to test direction
TAG_POSITIVE = "positive"
TAG_NEGATIVE = "negative"

# Test tags related to service involvement
# Only requires that manila-api service running.
TAG_API = "api"
# Requires all manila services running, intended to test back-end
# (manila-share) behavior.
TAG_BACKEND = "backend"
# Requires all manila services running, intended to test API behavior.
TAG_API_WITH_BACKEND = "api_with_backend"

TAGS_MAPPER = {
    "p": TAG_POSITIVE,
    "n": TAG_NEGATIVE,
    "a": TAG_API,
    "b": TAG_BACKEND,
    "ab": TAG_API_WITH_BACKEND,
}
TAGS_PATTERN = re.compile(
    r"(?=.*\[.*\b(%(p)s|%(n)s)\b.*\])(?=.*\[.*\b(%(a)s|%(b)s|%(ab)s)\b.*\])" %
    TAGS_MAPPER)


def verify_test_has_appropriate_tags(self):
    if not TAGS_PATTERN.match(self.id()):
        msg = (
            "Required attributes either not set or set improperly. "
            "Two test attributes are expected:\n"
            " - one of '%(p)s' or '%(n)s' and \n"
            " - one of '%(a)s', '%(b)s' or '%(ab)s'."
        ) % TAGS_MAPPER
        raise self.failureException(msg)


class handle_cleanup_exceptions(object):
    """Handle exceptions raised with cleanup operations.

    Always suppress errors when exceptions.NotFound or exceptions.Forbidden
    are raised.
    Suppress all other exceptions only in case config opt
    'suppress_errors_in_cleanup' in config group 'share' is True.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if not (isinstance(exc_value,
                           (exceptions.NotFound, exceptions.Forbidden)) or
                CONF.share.suppress_errors_in_cleanup):
            return False  # Do not suppress error if any
        if exc_traceback:
            LOG.error("Suppressed cleanup error in Manila: "
                      "\n%s", traceback.format_exc())
        return True  # Suppress error if any


skip_if_microversion_not_supported = utils.skip_if_microversion_not_supported
skip_if_microversion_lt = utils.skip_if_microversion_lt


class BaseSharesTest(test.BaseTestCase):
    """Base test case class for all Manila API tests."""

    credentials = ('primary', )
    force_tenant_isolation = False
    protocols = ["nfs", "cifs", "glusterfs", "hdfs", "cephfs", "maprfs"]

    # Will be cleaned up in resource_cleanup
    class_resources = []

    # Will be cleaned up in tearDown method
    method_resources = []

    # NOTE(andreaf) Override the client manager class to be used, so that
    # a stable class is used, which includes plugin registered services as well
    client_manager = clients.Clients

    def skip_if_microversion_not_supported(self, microversion):
        if not utils.is_microversion_supported(microversion):
            raise self.skipException(
                "Microversion '%s' is not supported." % microversion)

    def skip_if_microversion_lt(self, microversion):
        if utils.is_microversion_lt(CONF.share.max_api_microversion,
                                    microversion):
            raise self.skipException(
                "Microversion must be greater than or equal to '%s'." %
                microversion)

    @classmethod
    def skip_checks(cls):
        super(BaseSharesTest, cls).skip_checks()
        if not CONF.service_available.manila:
            raise cls.skipException("Manila support is required")
        if not any(p in CONF.share.enable_protocols for p in cls.protocols):
            skip_msg = "%s tests are disabled" % CONF.share.enable_protocols
            raise cls.skipException(skip_msg)

    @classmethod
    def verify_nonempty(cls, *args):
        if not all(args):
            msg = "Missing API credentials in configuration."
            raise cls.skipException(msg)

    @classmethod
    def setup_credentials(cls):
        # This call is used to tell the credential allocator to create
        # network resources for this test case. NOTE: it must go before the
        # super call, to override decisions in the base classes.
        network_resources = {}
        if (CONF.share.multitenancy_enabled and
                CONF.share.create_networks_when_multitenancy_enabled):
            # We're testing a DHSS=True driver, and manila is configured with
            # NeutronNetworkPlugin (or a derivative) that supports creating
            # share networks with project neutron networks, so lets ask for
            # neutron network resources to be created with test credentials
            network_resources.update({'network': True,
                                      'subnet': True,
                                      'router': True})
        cls.set_network_resources(**network_resources)
        super(BaseSharesTest, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(BaseSharesTest, cls).setup_clients()
        os = getattr(cls, 'os_%s' % cls.credentials[0])
        # Initialise share clients for test credentials
        cls.shares_client = os.share_v1.SharesClient()
        cls.shares_v2_client = os.share_v2.SharesV2Client()
        # Initialise network clients for test credentials
        cls.networks_client = None
        cls.subnets_client = None
        if CONF.service_available.neutron:
            cls.networks_client = os.network.NetworksClient()
            cls.subnets_client = os.network.SubnetsClient()

        # If DHSS=True, create a share network and set it in the client
        # for easy access.
        if CONF.share.multitenancy_enabled:
            if (not CONF.service_available.neutron and
                    CONF.share.create_networks_when_multitenancy_enabled):
                raise cls.skipException(
                    "Neutron support is required when "
                    "CONF.share.create_networks_when_multitenancy_enabled "
                    "is set to True")
            share_network_id = cls.provide_share_network(
                cls.shares_client, cls.networks_client)
            cls.shares_client.share_network_id = share_network_id
            cls.shares_v2_client.share_network_id = share_network_id

    def setUp(self):
        super(BaseSharesTest, self).setUp()
        self.addCleanup(self.clear_resources)
        verify_test_has_appropriate_tags(self)

    @classmethod
    def resource_cleanup(cls):
        cls.clear_resources(cls.class_resources)
        super(BaseSharesTest, cls).resource_cleanup()

    @classmethod
    def provide_and_associate_security_services(
            cls, shares_client, share_network_id, cleanup_in_class=True):
        """Creates a security service and associates to a share network.

        This method creates security services based on the Multiopt
        defined in tempest configuration named security_service. When this
        configuration is not provided, the method will return None.
        After the security service creation, this method also associates
        the security service to a share network.

        :param shares_client: shares client, which requires the provisioning
        :param share_network_id: id of the share network to associate the
            security service
        :param cleanup_in_class: if the security service and the association
            will be removed in the method teardown or class teardown
        :returns: None -- if the security service configuration is not
            defined
        """

        ss_configs = CONF.share.security_service
        if not ss_configs:
            return

        for ss_config in ss_configs:
            ss_name = "ss_autogenerated_by_tempest_%s" % (
                ss_config.get("ss_type"))

            ss_params = {
                "name": ss_name,
                "dns_ip": ss_config.get("ss_dns_ip"),
                "server": ss_config.get("ss_server"),
                "domain": ss_config.get("ss_domain"),
                "user": ss_config.get("ss_user"),
                "password": ss_config.get("ss_password")
            }
            ss_type = ss_config.get("ss_type")
            security_service = cls.create_security_service(
                ss_type,
                client=shares_client,
                cleanup_in_class=cleanup_in_class,
                **ss_params)

            cls.add_sec_service_to_share_network(
                shares_client, share_network_id,
                security_service["id"],
                cleanup_in_class=cleanup_in_class)

    @classmethod
    def add_sec_service_to_share_network(
            cls, client, share_network_id,
            security_service_id, cleanup_in_class=True):
        """Associates a security service to a share network.

        This method associates a security service provided by
        the security service configuration with a specific
        share network.

        :param share_network_id: the share network id to be
            associate with a given security service
        :param security_service_id: the security service id
            to be associate with a given share network
        :param cleanup_in_class: if the resources will be
            dissociate in the method teardown or class teardown
        """

        client.add_sec_service_to_share_network(
            share_network_id,
            security_service_id)
        resource = {
            "type": "dissociate_security_service",
            "id": security_service_id,
            "extra_params": {
                "share_network_id": share_network_id
            },
            "client": client,
        }

        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)

    @classmethod
    def provide_share_network(cls, shares_client, networks_client,
                              ignore_multitenancy_config=False):
        """Get or create share network for DHSS=True drivers

        When testing DHSS=True (multitenancy_enabled) drivers, shares must
        be requested on share networks.
        :returns: str -- share network id for shares_client tenant
        :returns: None -- if single-tenant driver (DHSS=False) is used
        """

        if (not ignore_multitenancy_config and
                not CONF.share.multitenancy_enabled):
            # Assumed usage of a single-tenant driver (DHSS=False)
            return None

        if shares_client.share_network_id:
            # Share-network already exists, use it
            return shares_client.share_network_id

        sn_name = "autogenerated_by_tempest"
        sn_desc = "This share-network was created by tempest"

        if not CONF.share.create_networks_when_multitenancy_enabled:
            # We need a new share network, but don't need to associate
            # any neutron networks to it - this configuration is used
            # when manila is configured with "StandaloneNetworkPlugin"
            # or "NeutronSingleNetworkPlugin" where all tenants share
            # a single backend network where shares are exported.
            sn = cls.create_share_network(cleanup_in_class=True,
                                          client=shares_client,
                                          add_security_services=True,
                                          name=sn_name,
                                          description=sn_desc)
            return sn['id']

        # Retrieve non-public network list owned by the tenant
        filters = {'project_id': shares_client.tenant_id,
                   'shared': False}
        tenant_networks = (
            networks_client.list_networks(**filters).get('networks', [])
        )
        tenant_networks_with_subnet = (
            [n for n in tenant_networks if n['subnets']]
        )

        if not tenant_networks_with_subnet:
            # This can only occur if using tempest's pre-provisioned
            # credentials and not allocating networks to them
            raise cls.skipException(
                "Test credentials must provide at least one "
                "non-shared project network with a valid subnet when "
                "CONF.share.create_networks_when_multitenancy_enabled is "
                "set to True.")

        net_id = tenant_networks_with_subnet[0]['id']
        subnet_id = tenant_networks_with_subnet[0]['subnets'][0]

        # Create suitable share-network
        sn = cls.create_share_network(cleanup_in_class=True,
                                      client=shares_client,
                                      add_security_services=True,
                                      name=sn_name,
                                      description=sn_desc,
                                      neutron_net_id=net_id,
                                      neutron_subnet_id=subnet_id)

        return sn['id']

    @classmethod
    def _create_share(cls, share_protocol=None, size=None, name=None,
                      snapshot_id=None, description=None, metadata=None,
                      share_network_id=None, share_type_id=None,
                      share_group_id=None, client=None,
                      cleanup_in_class=True, is_public=False, **kwargs):
        client = client or cls.shares_v2_client
        description = description or "Tempest's share"
        share_network_id = (share_network_id or
                            CONF.share.share_network_id or
                            client.share_network_id or None)
        metadata = metadata or {}
        size = size or CONF.share.share_size
        kwargs.update({
            'share_protocol': share_protocol,
            'size': size,
            'name': name,
            'snapshot_id': snapshot_id,
            'description': description,
            'metadata': metadata,
            'share_network_id': share_network_id,
            'share_type_id': share_type_id,
            'is_public': is_public,
        })
        if share_group_id:
            kwargs['share_group_id'] = share_group_id

        share = client.create_share(**kwargs)
        resource = {"type": "share", "id": share["id"], "client": client,
                    "share_group_id": share_group_id}
        cleanup_list = (cls.class_resources if cleanup_in_class else
                        cls.method_resources)
        cleanup_list.insert(0, resource)
        return share

    @classmethod
    def migrate_share(
            cls, share_id, dest_host, wait_for_status, client=None,
            force_host_assisted_migration=False, writable=False,
            nondisruptive=False, preserve_metadata=False,
            preserve_snapshots=False, new_share_network_id=None,
            new_share_type_id=None, **kwargs):
        client = client or cls.shares_v2_client
        client.migrate_share(
            share_id, dest_host,
            force_host_assisted_migration=force_host_assisted_migration,
            writable=writable, preserve_metadata=preserve_metadata,
            nondisruptive=nondisruptive, preserve_snapshots=preserve_snapshots,
            new_share_network_id=new_share_network_id,
            new_share_type_id=new_share_type_id, **kwargs)
        share = client.wait_for_migration_status(
            share_id, dest_host, wait_for_status, **kwargs)
        return share

    @classmethod
    def migration_complete(cls, share_id, dest_host, client=None, **kwargs):
        client = client or cls.shares_v2_client
        client.migration_complete(share_id, **kwargs)
        share = client.wait_for_migration_status(
            share_id, dest_host, 'migration_success', **kwargs)
        return share

    @classmethod
    def migration_cancel(cls, share_id, dest_host, client=None, **kwargs):
        client = client or cls.shares_v2_client
        client.migration_cancel(share_id, **kwargs)
        share = client.wait_for_migration_status(
            share_id, dest_host, 'migration_cancelled', **kwargs)
        return share

    @classmethod
    def create_share(cls, *args, **kwargs):
        """Create one share and wait for available state. Retry if allowed."""
        result = cls.create_shares([{"args": args, "kwargs": kwargs}])
        return result[0]

    @classmethod
    def create_shares(cls, share_data_list):
        """Creates several shares in parallel with retries.

        Use this method when you want to create more than one share at same
        time. Especially if config option 'share.share_creation_retry_number'
        has value more than zero (0).
        All shares will be expected to have 'available' status with or without
        recreation else error will be raised.

        :param share_data_list: list -- list of dictionaries with 'args' and
            'kwargs' for '_create_share' method of this base class.
            example of data:
                share_data_list=[{'args': ['quuz'], 'kwargs': {'foo': 'bar'}}}]
        :returns: list -- list of shares created using provided data.
        """

        for d in share_data_list:
            if not isinstance(d, dict):
                raise exceptions.TempestException(
                    "Expected 'dict', got '%s'" % type(d))
            if "args" not in d:
                d["args"] = []
            if "kwargs" not in d:
                d["kwargs"] = {}
            if len(d) > 2:
                raise exceptions.TempestException(
                    "Expected only 'args' and 'kwargs' keys. "
                    "Provided %s" % list(d))

        data = []
        for d in share_data_list:
            client = d["kwargs"].pop("client", cls.shares_v2_client)
            wait_for_status = d["kwargs"].pop("wait_for_status", True)
            local_d = {
                "args": d["args"],
                "kwargs": copy.deepcopy(d["kwargs"]),
            }
            local_d["kwargs"]["client"] = client
            local_d["share"] = cls._create_share(
                *local_d["args"], **local_d["kwargs"])
            local_d["cnt"] = 0
            local_d["available"] = False
            local_d["wait_for_status"] = wait_for_status
            data.append(local_d)

        while not all(d["available"] for d in data):
            for d in data:
                if not d["wait_for_status"]:
                    d["available"] = True
                if d["available"]:
                    continue
                client = d["kwargs"]["client"]
                share_id = d["share"]["id"]
                try:
                    client.wait_for_share_status(share_id, "available")
                    d["available"] = True
                except (share_exceptions.ShareBuildErrorException,
                        exceptions.TimeoutException) as e:
                    if CONF.share.share_creation_retry_number > d["cnt"]:
                        d["cnt"] += 1
                        msg = ("Share '%s' failed to be built. "
                               "Trying create another." % share_id)
                        LOG.error(msg)
                        LOG.error(e)
                        cg_id = d["kwargs"].get("consistency_group_id")
                        if cg_id:
                            # NOTE(vponomaryov): delete errored share
                            # immediately in case share is part of CG.
                            client.delete_share(
                                share_id,
                                params={"consistency_group_id": cg_id})
                            client.wait_for_resource_deletion(
                                share_id=share_id)
                        d["share"] = cls._create_share(
                            *d["args"], **d["kwargs"])
                    else:
                        raise

        return [d["share"] for d in data]

    @classmethod
    def create_share_group(cls, client=None, cleanup_in_class=True,
                           share_network_id=None, **kwargs):
        client = client or cls.shares_v2_client
        if kwargs.get('source_share_group_snapshot_id') is None:
            kwargs['share_network_id'] = (share_network_id or
                                          client.share_network_id or None)
        share_group = client.create_share_group(**kwargs)
        resource = {
            "type": "share_group",
            "id": share_group["id"],
            "client": client,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)

        if kwargs.get('source_share_group_snapshot_id'):
            new_share_group_shares = client.list_shares(
                detailed=True,
                params={'share_group_id': share_group['id']})

            for share in new_share_group_shares:
                resource = {"type": "share",
                            "id": share["id"],
                            "client": client,
                            "share_group_id": share.get("share_group_id")}
                if cleanup_in_class:
                    cls.class_resources.insert(0, resource)
                else:
                    cls.method_resources.insert(0, resource)

        client.wait_for_share_group_status(share_group['id'], 'available')
        return share_group

    @classmethod
    def create_share_group_type(cls, name=None, share_types=(), is_public=None,
                                group_specs=None, client=None,
                                cleanup_in_class=True, **kwargs):
        client = client or cls.shares_v2_client
        if (group_specs is None and
                CONF.share.capability_sg_consistent_snapshot_support):
            group_specs = {
                'consistent_snapshot_support': (
                    CONF.share.capability_sg_consistent_snapshot_support),
            }
        share_group_type = client.create_share_group_type(
            name=name,
            share_types=share_types,
            is_public=is_public,
            group_specs=group_specs,
            **kwargs)
        resource = {
            "type": "share_group_type",
            "id": share_group_type["id"],
            "client": client,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return share_group_type

    @classmethod
    def create_snapshot_wait_for_active(cls, share_id, name=None,
                                        description=None, force=False,
                                        client=None, cleanup_in_class=True):
        if client is None:
            client = cls.shares_v2_client
        if description is None:
            description = "Tempest's snapshot"
        snapshot = client.create_snapshot(share_id, name, description, force)
        resource = {
            "type": "snapshot",
            "id": snapshot["id"],
            "client": client,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        client.wait_for_snapshot_status(snapshot["id"], "available")
        return snapshot

    @classmethod
    def create_share_group_snapshot_wait_for_active(
            cls, share_group_id, name=None, description=None, client=None,
            cleanup_in_class=True, **kwargs):
        client = client or cls.shares_v2_client
        if description is None:
            description = "Tempest's share group snapshot"
        sg_snapshot = client.create_share_group_snapshot(
            share_group_id, name=name, description=description, **kwargs)
        resource = {
            "type": "share_group_snapshot",
            "id": sg_snapshot["id"],
            "client": client,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        client.wait_for_share_group_snapshot_status(
            sg_snapshot["id"], "available")
        return sg_snapshot

    @classmethod
    def get_availability_zones(cls, client=None, backends=None):
        """List the availability zones for "manila-share" services

         that are currently in "up" state.
         """
        client = client or cls.admin_shares_v2_client
        backends = (
            '|'.join(['^%s$' % backend for backend in backends])
            if backends else '.*'
        )
        cls.services = client.list_services()
        zones = [service['zone'] for service in cls.services if
                 service['binary'] == 'manila-share' and
                 service['state'] == 'up' and
                 re.search(backends, service['host'])]
        return list(set(zones))

    @classmethod
    def get_pools_matching_share_type(cls, share_type, client=None):
        client = client or cls.admin_shares_v2_client
        if utils.is_microversion_supported('2.23'):
            return client.list_pools(
                detail=True,
                search_opts={'share_type': share_type['id']})['pools']

        pools = client.list_pools(detail=True)['pools']
        share_type = client.get_share_type(share_type['id'])['share_type']
        extra_specs = {}
        for k, v in share_type['extra_specs'].items():
            extra_specs[k] = (
                True if six.text_type(v).lower() == 'true'
                else False if six.text_type(v).lower() == 'false' else v
            )
        return [
            pool for pool in pools if all(y in pool['capabilities'].items()
                                          for y in extra_specs.items())
        ]

    @classmethod
    def get_availability_zones_matching_share_type(cls, share_type,
                                                   client=None):

        client = client or cls.admin_shares_v2_client
        pools_matching_share_type = cls.get_pools_matching_share_type(
            share_type, client=client)
        backends_matching_share_type = set(
            [pool['name'].split("#")[0] for pool in pools_matching_share_type]
        )
        azs = cls.get_availability_zones(backends=backends_matching_share_type)
        return azs

    def get_pools_for_replication_domain(self):
        # Get the list of pools for the replication domain
        pools = self.admin_client.list_pools(detail=True)['pools']
        instance_host = self.admin_client.get_share(
            self.shares[0]['id'])['host']
        host_pool = [p for p in pools if p['name'] == instance_host][0]
        rep_domain = host_pool['capabilities']['replication_domain']
        pools_in_rep_domain = [p for p in pools if p['capabilities'][
            'replication_domain'] == rep_domain]
        return rep_domain, pools_in_rep_domain

    @classmethod
    def create_share_replica(cls, share_id, availability_zone, client=None,
                             cleanup_in_class=False, cleanup=True):
        client = client or cls.shares_v2_client
        replica = client.create_share_replica(
            share_id, availability_zone=availability_zone)
        resource = {
            "type": "share_replica",
            "id": replica["id"],
            "client": client,
            "share_id": share_id,
        }
        # NOTE(Yogi1): Cleanup needs to be disabled during promotion tests.
        if cleanup:
            if cleanup_in_class:
                cls.class_resources.insert(0, resource)
            else:
                cls.method_resources.insert(0, resource)
        client.wait_for_share_replica_status(
            replica["id"], constants.STATUS_AVAILABLE)
        return replica

    @classmethod
    def delete_share_replica(cls, replica_id, client=None):
        client = client or cls.shares_v2_client
        try:
            client.delete_share_replica(replica_id)
            client.wait_for_resource_deletion(replica_id=replica_id)
        except exceptions.NotFound:
            pass

    @classmethod
    def promote_share_replica(cls, replica_id, client=None):
        client = client or cls.shares_v2_client
        replica = client.promote_share_replica(replica_id)
        client.wait_for_share_replica_status(
            replica["id"],
            constants.REPLICATION_STATE_ACTIVE,
            status_attr="replica_state")
        return replica

    @classmethod
    def _get_access_rule_data_from_config(cls):
        """Get the first available access type/to combination from config.

        This method opportunistically picks the first configured protocol
        to create the share. Do not use this method in tests where you need
        to test depth and breadth in the access types and access recipients.
        """
        protocol = cls.shares_v2_client.share_protocol

        if protocol in CONF.share.enable_ip_rules_for_protocols:
            access_type = "ip"
            access_to = utils.rand_ip()
        elif protocol in CONF.share.enable_user_rules_for_protocols:
            access_type = "user"
            access_to = CONF.share.username_for_user_rules
        elif protocol in CONF.share.enable_cert_rules_for_protocols:
            access_type = "cert"
            access_to = "client3.com"
        elif protocol in CONF.share.enable_cephx_rules_for_protocols:
            access_type = "cephx"
            access_to = data_utils.rand_name(
                cls.__class__.__name__ + '-cephx-id')
        else:
            message = "Unrecognized protocol and access rules configuration."
            raise cls.skipException(message)

        return access_type, access_to

    @classmethod
    def create_share_network(cls, client=None,
                             cleanup_in_class=False,
                             add_security_services=True, **kwargs):

        if client is None:
            client = cls.shares_client
        share_network = client.create_share_network(**kwargs)
        resource = {
            "type": "share_network",
            "id": share_network["id"],
            "client": client,
        }

        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)

        if add_security_services:
            cls.provide_and_associate_security_services(
                client, share_network["id"], cleanup_in_class=cleanup_in_class)

        return share_network

    @classmethod
    def create_share_network_subnet(cls,
                                    client=None,
                                    cleanup_in_class=False,
                                    **kwargs):
        if client is None:
            client = cls.shares_v2_client
        share_network_subnet = client.create_subnet(**kwargs)
        resource = {
            "type": "share-network-subnet",
            "id": share_network_subnet["id"],
            "extra_params": {
                "share_network_id": share_network_subnet["share_network_id"]
            },
            "client": client,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return share_network_subnet

    @classmethod
    def create_security_service(cls, ss_type="ldap", client=None,
                                cleanup_in_class=False, **kwargs):
        if client is None:
            client = cls.shares_client
        security_service = client.create_security_service(ss_type, **kwargs)
        resource = {
            "type": "security_service",
            "id": security_service["id"],
            "client": client,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return security_service

    @classmethod
    def create_share_type(cls, name, is_public=True, client=None,
                          cleanup_in_class=True, **kwargs):
        if client is None:
            client = cls.shares_v2_client
        share_type = client.create_share_type(name, is_public, **kwargs)
        resource = {
            "type": "share_type",
            "id": share_type["share_type"]["id"],
            "client": client,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return share_type

    @classmethod
    def update_share_type(cls, share_type_id, name=None,
                          is_public=None, description=None,
                          client=None):
        if client is None:
            client = cls.shares_v2_client
        share_type = client.update_share_type(share_type_id, name,
                                              is_public, description)
        return share_type

    @classmethod
    def update_quotas(cls, project_id, user_id=None, cleanup=True,
                      client=None, **kwargs):
        client = client or cls.shares_v2_client
        updated_quotas = client.update_quotas(project_id,
                                              user_id=user_id,
                                              **kwargs)
        resource = {
            "type": "quotas",
            "id": project_id,
            "client": client,
            "user_id": user_id,
        }
        if cleanup:
            cls.method_resources.insert(0, resource)
        return updated_quotas

    @staticmethod
    def add_extra_specs_to_dict(extra_specs=None):
        """Add any required extra-specs to share type dictionary"""
        dhss = six.text_type(CONF.share.multitenancy_enabled)
        snapshot_support = six.text_type(
            CONF.share.capability_snapshot_support)
        create_from_snapshot_support = six.text_type(
            CONF.share.capability_create_share_from_snapshot_support)

        extra_specs_dict = {
            "driver_handles_share_servers": dhss,
        }

        optional = {
            "snapshot_support": snapshot_support,
            "create_share_from_snapshot_support": create_from_snapshot_support,
        }
        # NOTE(gouthamr): In micro-versions < 2.24, snapshot_support is a
        # required extra-spec
        extra_specs_dict.update(optional)

        if extra_specs:
            extra_specs_dict.update(extra_specs)

        return extra_specs_dict

    @classmethod
    def clear_share_replicas(cls, share_id, client=None):
        client = client or cls.shares_v2_client
        share_replicas = client.list_share_replicas(
            share_id=share_id)

        for replica in share_replicas:
            try:
                cls.delete_share_replica(replica['id'])
            except exceptions.BadRequest:
                # Ignore the exception due to deletion of last active replica
                pass

    @classmethod
    def clear_resources(cls, resources=None):
        """Deletes resources, that were created in test suites.

        This method tries to remove resources from resource list,
        if it is not found, assumed it was deleted in test itself.
        It is expected, that all resources were added as LIFO
        due to restriction of deletion resources, that is in the chain.

        :param resources: dict with keys 'type','id','client' and 'deleted'
        """
        if resources is None:
            resources = cls.method_resources
        for res in resources:
            if "deleted" not in res.keys():
                res["deleted"] = False
            if "client" not in res.keys():
                res["client"] = cls.shares_client
            if not(res["deleted"]):
                res_id = res['id']
                client = res["client"]
                with handle_cleanup_exceptions():
                    if res["type"] == "share":
                        cls.clear_share_replicas(res_id)
                        share_group_id = res.get('share_group_id')
                        if share_group_id:
                            params = {'share_group_id': share_group_id}
                            client.delete_share(res_id, params=params)
                        else:
                            client.delete_share(res_id)
                        client.wait_for_resource_deletion(share_id=res_id)
                    elif res["type"] == "snapshot":
                        client.delete_snapshot(res_id)
                        client.wait_for_resource_deletion(snapshot_id=res_id)
                    elif (res["type"] == "share_network" and
                            res_id != CONF.share.share_network_id):
                        client.delete_share_network(res_id)
                        client.wait_for_resource_deletion(sn_id=res_id)
                    elif res["type"] == "dissociate_security_service":
                        sn_id = res["extra_params"]["share_network_id"]
                        client.remove_sec_service_from_share_network(
                            sn_id=sn_id, ss_id=res_id
                        )
                    elif res["type"] == "security_service":
                        client.delete_security_service(res_id)
                        client.wait_for_resource_deletion(ss_id=res_id)
                    elif res["type"] == "share_type":
                        client.delete_share_type(res_id)
                        client.wait_for_resource_deletion(st_id=res_id)
                    elif res["type"] == "share_group":
                        client.delete_share_group(res_id)
                        client.wait_for_resource_deletion(
                            share_group_id=res_id)
                    elif res["type"] == "share_group_type":
                        client.delete_share_group_type(res_id)
                        client.wait_for_resource_deletion(
                            share_group_type_id=res_id)
                    elif res["type"] == "share_group_snapshot":
                        client.delete_share_group_snapshot(res_id)
                        client.wait_for_resource_deletion(
                            share_group_snapshot_id=res_id)
                    elif res["type"] == "share_replica":
                        client.delete_share_replica(res_id)
                        client.wait_for_resource_deletion(replica_id=res_id)
                    elif res["type"] == "share_network_subnet":
                        sn_id = res["extra_params"]["share_network_id"]
                        client.delete_subnet(sn_id, res_id)
                        client.wait_for_resource_deletion(
                            share_network_subnet_id=res_id,
                            sn_id=sn_id)
                    elif res["type"] == "quotas":
                        user_id = res.get('user_id')
                        client.reset_quotas(res_id, user_id=user_id)
                    else:
                        LOG.warning("Provided unsupported resource type for "
                                    "cleanup '%s'. Skipping.", res["type"])
                res["deleted"] = True

    @classmethod
    def generate_share_network_data(self):
        data = {
            "name": data_utils.rand_name("sn-name"),
            "description": data_utils.rand_name("sn-desc"),
            "neutron_net_id": data_utils.rand_name("net-id"),
            "neutron_subnet_id": data_utils.rand_name("subnet-id"),
        }
        return data

    @classmethod
    def generate_subnet_data(self):
        data = {
            "neutron_net_id": data_utils.rand_name("net-id"),
            "neutron_subnet_id": data_utils.rand_name("subnet-id"),
        }
        return data

    @classmethod
    def generate_security_service_data(self, set_ou=False):
        data = {
            "name": data_utils.rand_name("ss-name"),
            "description": data_utils.rand_name("ss-desc"),
            "dns_ip": utils.rand_ip(),
            "server": utils.rand_ip(),
            "domain": data_utils.rand_name("ss-domain"),
            "user": data_utils.rand_name("ss-user"),
            "password": data_utils.rand_name("ss-password"),
        }
        if set_ou:
            data["ou"] = data_utils.rand_name("ss-ou")

        return data

    # Useful assertions
    def assertDictMatch(self, d1, d2, approx_equal=False, tolerance=0.001):
        """Assert two dicts are equivalent.

        This is a 'deep' match in the sense that it handles nested
        dictionaries appropriately.

        NOTE:

            If you don't care (or don't know) a given value, you can specify
            the string DONTCARE as the value. This will cause that dict-item
            to be skipped.

        """
        def raise_assertion(msg):
            d1str = str(d1)
            d2str = str(d2)
            base_msg = ('Dictionaries do not match. %(msg)s d1: %(d1str)s '
                        'd2: %(d2str)s' %
                        {"msg": msg, "d1str": d1str, "d2str": d2str})
            raise AssertionError(base_msg)

        d1keys = set(d1.keys())
        d2keys = set(d2.keys())
        if d1keys != d2keys:
            d1only = d1keys - d2keys
            d2only = d2keys - d1keys
            raise_assertion('Keys in d1 and not d2: %(d1only)s. '
                            'Keys in d2 and not d1: %(d2only)s' %
                            {"d1only": d1only, "d2only": d2only})

        for key in d1keys:
            d1value = d1[key]
            d2value = d2[key]
            try:
                error = abs(float(d1value) - float(d2value))
                within_tolerance = error <= tolerance
            except (ValueError, TypeError):
                # If both values aren't convertible to float, just ignore
                # ValueError if arg is a str, TypeError if it's something else
                # (like None)
                within_tolerance = False

            if hasattr(d1value, 'keys') and hasattr(d2value, 'keys'):
                self.assertDictMatch(d1value, d2value)
            elif 'DONTCARE' in (d1value, d2value):
                continue
            elif approx_equal and within_tolerance:
                continue
            elif d1value != d2value:
                raise_assertion("d1['%(key)s']=%(d1value)s != "
                                "d2['%(key)s']=%(d2value)s" %
                                {
                                    "key": key,
                                    "d1value": d1value,
                                    "d2value": d2value
                                })

    def create_user_message(self):
        """Trigger a 'no valid host' situation to generate a message."""
        extra_specs = {
            'vendor_name': 'foobar',
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        share_type_name = data_utils.rand_name("share-type")

        bogus_type = self.create_share_type(
            client=self.admin_shares_v2_client,
            name=share_type_name,
            extra_specs=extra_specs)['share_type']

        params = {'share_type_id': bogus_type['id'],
                  'share_network_id': self.shares_v2_client.share_network_id}
        share = self.shares_v2_client.create_share(**params)
        self.addCleanup(self.shares_v2_client.delete_share, share['id'])
        self.shares_v2_client.wait_for_share_status(share['id'], "error")
        return self.shares_v2_client.wait_for_message(share['id'])

    def allow_access(self, share_id, client=None, access_type=None,
                     access_level='rw', access_to=None, status='active',
                     raise_rule_in_error_state=True, cleanup=True):

        client = client or self.shares_v2_client
        a_type, a_to = self._get_access_rule_data_from_config()
        access_type = access_type or a_type
        access_to = access_to or a_to

        rule = client.create_access_rule(share_id, access_type, access_to,
                                         access_level)
        client.wait_for_access_rule_status(share_id, rule['id'], status,
                                           raise_rule_in_error_state)
        if cleanup:
            self.addCleanup(client.wait_for_resource_deletion,
                            rule_id=rule['id'], share_id=share_id)
            self.addCleanup(client.delete_access_rule, share_id, rule['id'])
        return rule


class BaseSharesAltTest(BaseSharesTest):
    """Base test case class for all Shares Alt API tests."""
    credentials = ('alt', )


class BaseSharesAdminTest(BaseSharesTest):
    """Base test case class for all Shares Admin API tests."""
    credentials = ('admin', )

    @classmethod
    def setup_clients(cls):
        super(BaseSharesAdminTest, cls).setup_clients()
        # Initialise share clients
        cls.admin_shares_v2_client = cls.os_admin.share_v2.SharesV2Client()

    @classmethod
    def _create_share_type(cls, is_public=True, specs=None):
        name = data_utils.rand_name("unique_st_name")
        extra_specs = cls.add_extra_specs_to_dict(specs)
        return cls.create_share_type(
            name, extra_specs=extra_specs, is_public=is_public,
            client=cls.admin_shares_v2_client)['share_type']

    @classmethod
    def _create_share_group_type(cls):
        share_group_type_name = data_utils.rand_name("unique_sgtype_name")
        return cls.create_share_group_type(
            name=share_group_type_name, share_types=[cls.share_type_id],
            client=cls.admin_shares_v2_client)

    def _create_share_for_manage(self):
        creation_data = {
            'share_type_id': self.st['share_type']['id'],
            'share_protocol': self.protocol,
        }

        share = self.create_share(**creation_data)
        share = self.shares_v2_client.get_share(share['id'])

        if utils.is_microversion_ge(CONF.share.max_api_microversion, "2.9"):
            el = self.shares_v2_client.list_share_export_locations(share["id"])
            share["export_locations"] = el

        return share

    def _unmanage_share_and_wait(self, share):
        self.shares_v2_client.unmanage_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])

    def _reset_state_and_delete_share(self, share):
        self.shares_v2_client.reset_state(share['id'])
        self._delete_share_and_wait(share)

    def _delete_snapshot_and_wait(self, snap):
        self.shares_v2_client.delete_snapshot(snap['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            snapshot_id=snap['id']
        )
        self.assertRaises(exceptions.NotFound,
                          self.shares_v2_client.get_snapshot,
                          snap['id'])

    def _delete_share_and_wait(self, share):
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        self.assertRaises(exceptions.NotFound,
                          self.shares_v2_client.get_share,
                          share['id'])

    def _manage_share(self, share, name, description, share_server_id):
        managed_share = self.shares_v2_client.manage_share(
            service_host=share['host'],
            export_path=share['export_locations'][0],
            protocol=share['share_proto'],
            share_type_id=self.share_type['share_type']['id'],
            name=name,
            description=description,
            share_server_id=share_server_id
        )
        self.shares_v2_client.wait_for_share_status(
            managed_share['id'], constants.STATUS_AVAILABLE
        )

        return managed_share

    def _unmanage_share_server_and_wait(self, server):
        self.shares_v2_client.unmanage_share_server(server['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            server_id=server['id']
        )

    def _manage_share_server(self, share_server, fields=None):
        params = fields or {}
        subnet_id = params.get('share_network_subnet_id', None)
        managed_share_server = self.shares_v2_client.manage_share_server(
            params.get('host', share_server['host']),
            params.get('share_network_id', share_server['share_network_id']),
            params.get('identifier', share_server['identifier']),
            share_network_subnet_id=subnet_id,
        )
        self.shares_v2_client.wait_for_share_server_status(
            managed_share_server['id'],
            constants.SERVER_STATE_ACTIVE,
        )

        return managed_share_server

    def _delete_share_server_and_wait(self, share_server_id):
        self.shares_v2_client.delete_share_server(
            share_server_id
        )
        self.shares_v2_client.wait_for_resource_deletion(
            server_id=share_server_id)


class BaseSharesMixedTest(BaseSharesTest):
    """Base test case class for all Shares API tests with all user roles."""
    credentials = ('primary', 'alt', 'admin')

    # Will be cleaned up in resource_cleanup if the class
    class_project_users_created = []

    @classmethod
    def resource_cleanup(cls):
        cls.clear_project_users(cls.class_project_users_created)
        super(BaseSharesMixedTest, cls).resource_cleanup()

    @classmethod
    def clear_project_users(cls, users=None):
        users = users or cls.class_project_users_created
        for user in users:
            with handle_cleanup_exceptions():
                cls.os_admin.creds_client.delete_user(user['id'])

    @classmethod
    def setup_clients(cls):
        super(BaseSharesMixedTest, cls).setup_clients()
        # Initialise share clients
        cls.admin_shares_client = cls.os_admin.share_v1.SharesClient()
        cls.admin_shares_v2_client = cls.os_admin.share_v2.SharesV2Client()
        cls.alt_shares_client = cls.os_alt.share_v1.SharesClient()
        cls.alt_shares_v2_client = cls.os_alt.share_v2.SharesV2Client()
        # Initialise network clients
        cls.os_admin.networks_client = cls.os_admin.network.NetworksClient()
        cls.os_alt.networks_client = cls.os_alt.network.NetworksClient()
        # Initialise identity clients
        cls.admin_project = cls.os_admin.auth_provider.auth_data[1]['project']
        identity_clients = getattr(
            cls.os_admin, 'identity_%s' % CONF.identity.auth_version)
        cls.os_admin.identity_client = identity_clients.IdentityClient()
        cls.os_admin.projects_client = identity_clients.ProjectsClient()
        cls.os_admin.users_client = identity_clients.UsersClient()
        cls.os_admin.roles_client = identity_clients.RolesClient()
        cls.os_admin.domains_client = (
            cls.os_admin.identity_v3.DomainsClient() if
            CONF.identity.auth_version == 'v3' else None)
        cls.admin_project_member_client = cls.create_user_and_get_client()

        if CONF.share.multitenancy_enabled:
            admin_share_network_id = cls.provide_share_network(
                cls.admin_shares_v2_client, cls.os_admin.networks_client)
            cls.admin_shares_client.share_network_id = admin_share_network_id
            cls.admin_shares_v2_client.share_network_id = (
                admin_share_network_id)

            alt_share_network_id = cls.provide_share_network(
                cls.alt_shares_v2_client, cls.os_alt.networks_client)
            cls.alt_shares_client.share_network_id = alt_share_network_id
            cls.alt_shares_v2_client.share_network_id = alt_share_network_id

    @classmethod
    def create_user_and_get_client(cls, project=None):
        """Create a user in specified project & set share clients for user

        The user will have all roles specified in tempest.conf
        :param: project: a dictionary with project ID and name, if not
            specified, the value will be cls.admin_project
        """
        project_domain_name = (
            cls.os_admin.identity_client.auth_provider.credentials.get(
                'project_domain_name', 'Default'))
        cls.os_admin.creds_client = cred_client.get_creds_client(
            cls.os_admin.identity_client, cls.os_admin.projects_client,
            cls.os_admin.users_client, cls.os_admin.roles_client,
            cls.os_admin.domains_client, project_domain_name)

        # User info
        project = project or cls.admin_project
        username = data_utils.rand_name('manila_%s' % project['id'])
        password = data_utils.rand_password()
        email = '%s@example.org' % username

        user = cls.os_admin.creds_client.create_user(
            username, password, project, email)
        cls.class_project_users_created.append(user)

        for conf_role in CONF.auth.tempest_roles:
            cls.os_admin.creds_client.assign_user_role(
                user, project, conf_role)

        user_creds = cls.os_admin.creds_client.get_credentials(
            user, project, password)
        os = clients.Clients(user_creds)
        os.shares_v1_client = os.share_v1.SharesClient()
        os.shares_v2_client = os.share_v2.SharesV2Client()
        return os

    @classmethod
    def _create_share_type(cls, is_public=True, specs=None):
        name = data_utils.rand_name("unique_st_name")
        extra_specs = cls.add_extra_specs_to_dict(specs)
        return cls.create_share_type(
            name, extra_specs=extra_specs, is_public=is_public,
            client=cls.admin_shares_v2_client)['share_type']

    @classmethod
    def _create_share_group_type(cls):
        share_group_type_name = data_utils.rand_name("unique_sgtype_name")
        return cls.create_share_group_type(
            name=share_group_type_name, share_types=[cls.share_type_id],
            client=cls.admin_shares_v2_client)
