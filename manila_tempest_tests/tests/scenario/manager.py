# Copyright 2012 OpenStack Foundation
# Copyright 2013 IBM Corp.
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

from oslo_log import log
from oslo_utils import uuidutils
from tempest.common import image as common_image
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc
from tempest.scenario import manager

CONF = config.CONF

LOG = log.getLogger(__name__)


class ScenarioTest(manager.NetworkScenarioTest):
    """Base class for scenario tests. Uses tempest own clients. """

    # ## Test functions library
    #
    # The create_[resource] functions only return body and discard the
    # resp part which is not used in scenario tests

    def _image_create(self, name, fmt, path,
                      disk_format=None, properties=None):
        if properties is None:
            properties = {}
        name = data_utils.rand_name('%s-' % name)
        params = {
            'name': name,
            'container_format': fmt,
            'disk_format': disk_format or fmt,
        }
        if CONF.image_feature_enabled.api_v1:
            params['is_public'] = 'False'
            params['properties'] = properties
            params = {'headers': common_image.image_meta_to_headers(**params)}
        else:
            params['visibility'] = 'private'
            # Additional properties are flattened out in the v2 API.
            params.update(properties)
        body = self.image_client.create_image(**params)
        image = body['image'] if 'image' in body else body
        self.addCleanup(self.image_client.delete_image, image['id'])
        self.assertEqual("queued", image['status'])
        with open(path, 'rb') as image_file:
            if CONF.image_feature_enabled.api_v1:
                self.image_client.update_image(image['id'], data=image_file)
            else:
                self.image_client.store_image_file(image['id'], image_file)
        return image['id']

    def glance_image_create(self):
        img_path = CONF.scenario.img_file
        img_container_format = CONF.scenario.img_container_format
        img_disk_format = CONF.scenario.img_disk_format
        img_properties = CONF.scenario.img_properties
        LOG.debug("paths: img: %s, container_format: %s, disk_format: %s, "
                  "properties: %s",
                  img_path, img_container_format, img_disk_format,
                  img_properties)
        image = self._image_create('scenario-img',
                                   img_container_format,
                                   img_path,
                                   disk_format=img_disk_format,
                                   properties=img_properties)
        LOG.debug("image:%s", image)

        return image

    def _log_net_info(self, exc):
        # network debug is called as part of ssh init
        if not isinstance(exc, lib_exc.SSHTimeout):
            LOG.debug('Network information on a devstack host')


class NetworkScenarioTest(ScenarioTest):
    """Base class for network scenario tests.

    This class provide helpers for network scenario tests, using the neutron
    API. Helpers from ancestor which use the nova network API are overridden
    with the neutron API.

    This Class also enforces using Neutron instead of novanetwork.
    Subclassed tests will be skipped if Neutron is not enabled

    """

    @classmethod
    def skip_checks(cls):
        super(NetworkScenarioTest, cls).skip_checks()
        if not CONF.service_available.neutron:
            raise cls.skipException('Neutron not available')

    def _get_network_by_name_or_id(self, identifier):

        if uuidutils.is_uuid_like(identifier):
            return self.os_admin.networks_client.show_network(
                identifier)['network']

        networks = self.os_admin.networks_client.list_networks(
            name=identifier)['networks']
        self.assertNotEqual(len(networks), 0,
                            "Unable to get network by name: %s" % identifier)
        return networks[0]

    def create_floating_ip(self, thing, external_network_id=None,
                           port_id=None, ip_addr=None, client=None):
        """Create a floating IP and associates to a resource/port on Neutron"""
        if not external_network_id:
            external_network_id = CONF.network.public_network_id
        if not client:
            client = self.floating_ips_client
        if not port_id:
            port_id, ip4 = self.get_server_port_id_and_ip4(thing,
                                                           ip_addr=ip_addr)
        else:
            ip4 = None
        result = client.create_floatingip(
            floating_network_id=external_network_id,
            port_id=port_id,
            tenant_id=thing['tenant_id'],
            fixed_ip_address=ip4
        )
        floating_ip = result['floatingip']
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        client.delete_floatingip,
                        floating_ip['id'])
        return floating_ip

    def create_loginable_secgroup_rule(self, security_group_rules_client=None,
                                       secgroup=None,
                                       security_groups_client=None):
        """Create loginable security group rule

        This function will create:
        1. egress and ingress tcp port 22 allow rule in order to allow ssh
        access for ipv4.
        2. egress and ingress ipv6 icmp allow rule, in order to allow icmpv6.
        3. egress and ingress ipv4 icmp allow rule, in order to allow icmpv4.
        """

        if security_group_rules_client is None:
            security_group_rules_client = self.security_group_rules_client
        if security_groups_client is None:
            security_groups_client = self.security_groups_client
        rules = []
        rulesets = [
            dict(
                # ssh
                protocol='tcp',
                port_range_min=22,
                port_range_max=22,
            ),
            dict(
                # ipv6-ssh
                protocol='tcp',
                port_range_min=22,
                port_range_max=22,
                ethertype='IPv6',
            ),
            dict(
                # ping
                protocol='icmp',
            ),
            dict(
                # ipv6-icmp for ping6
                protocol='icmp',
                ethertype='IPv6',
            )
        ]
        sec_group_rules_client = security_group_rules_client
        for ruleset in rulesets:
            for r_direction in ['ingress', 'egress']:
                ruleset['direction'] = r_direction
                try:
                    sg_rule = self.create_security_group_rule(
                        sec_group_rules_client=sec_group_rules_client,
                        secgroup=secgroup,
                        security_groups_client=security_groups_client,
                        **ruleset)
                except lib_exc.Conflict as ex:
                    # if rule already exist - skip rule and continue
                    msg = 'Security group rule already exists'
                    if msg not in ex._error_string:
                        raise ex
                else:
                    self.assertEqual(r_direction, sg_rule['direction'])
                    rules.append(sg_rule)

        return rules
