# Copyright 2015 Andrew Kerr
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

import json
import re
import time
from urllib import parse

from tempest import config
from tempest.lib.common import rest_client
from tempest.lib.common.utils import data_utils

from manila_tempest_tests.common import constants
from manila_tempest_tests.services.share.json import shares_client
from manila_tempest_tests import share_exceptions
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion
EXPERIMENTAL = {'X-OpenStack-Manila-API-Experimental': 'True'}


class SharesV2Client(shares_client.SharesClient):
    """Tempest REST client for Manila.

    It handles shares and access to it in OpenStack.
    """
    api_version = 'v2'

    def __init__(self, auth_provider, **kwargs):
        super(SharesV2Client, self).__init__(auth_provider, **kwargs)
        self.API_MICROVERSIONS_HEADER = 'x-openstack-manila-api-version'

    def inject_microversion_header(self, headers, version,
                                   extra_headers=False):
        """Inject the required manila microversion header."""
        new_headers = self.get_headers()
        new_headers[self.API_MICROVERSIONS_HEADER] = version
        if extra_headers and headers:
            new_headers.update(headers)
        elif headers:
            new_headers = headers
        return new_headers

    def verify_request_id(self, response):
        response_headers = [r.lower() for r in response.keys()]
        assert_msg = ("Response is missing request ID. Response "
                      "headers are: %s") % response
        assert 'x-compute-request-id' in response_headers, assert_msg

    # Overwrite all http verb calls to inject the micro version header
    def post(self, url, body, headers=None, extra_headers=False,
             version=LATEST_MICROVERSION):
        headers = self.inject_microversion_header(headers, version,
                                                  extra_headers=extra_headers)
        resp, body = super(SharesV2Client, self).post(url, body,
                                                      headers=headers)
        self.verify_request_id(resp)
        return resp, body

    def get(self, url, headers=None, extra_headers=False,
            version=LATEST_MICROVERSION):
        headers = self.inject_microversion_header(headers, version,
                                                  extra_headers=extra_headers)
        resp, body = super(SharesV2Client, self).get(url, headers=headers)
        self.verify_request_id(resp)
        return resp, body

    def delete(self, url, headers=None, body=None, extra_headers=False,
               version=LATEST_MICROVERSION):
        headers = self.inject_microversion_header(headers, version,
                                                  extra_headers=extra_headers)
        resp, body = super(SharesV2Client, self).delete(url, headers=headers,
                                                        body=body)
        self.verify_request_id(resp)
        return resp, body

    def patch(self, url, body, headers=None, extra_headers=False,
              version=LATEST_MICROVERSION):
        headers = self.inject_microversion_header(headers, version,
                                                  extra_headers=extra_headers)
        return super(SharesV2Client, self).patch(url, body, headers=headers)

    def put(self, url, body, headers=None, extra_headers=False,
            version=LATEST_MICROVERSION):
        headers = self.inject_microversion_header(headers, version,
                                                  extra_headers=extra_headers)
        resp, body = super(SharesV2Client, self).put(url, body,
                                                     headers=headers)
        self.verify_request_id(resp)
        return resp, body

    def head(self, url, headers=None, extra_headers=False,
             version=LATEST_MICROVERSION):
        headers = self.inject_microversion_header(headers, version,
                                                  extra_headers=extra_headers)
        resp, body = super(SharesV2Client, self).head(url, headers=headers)
        self.verify_request_id(resp)
        return resp, body

    def copy(self, url, headers=None, extra_headers=False,
             version=LATEST_MICROVERSION):
        headers = self.inject_microversion_header(headers, version,
                                                  extra_headers=extra_headers)
        resp, body = super(SharesV2Client, self).copy(url, headers=headers)
        self.verify_request_id(resp)
        return resp, body

    def reset_state(self, s_id, status="error", s_type="shares",
                    headers=None, version=LATEST_MICROVERSION,
                    action_name=None):
        """Resets the state of a share, snapshot, cg, or a cgsnapshot.

        status: available, error, creating, deleting, error_deleting
        s_type: shares, share_instances, snapshots, consistency-groups,
            cgsnapshots.
        """
        if action_name is None:
            if utils.is_microversion_gt(version, "2.6"):
                action_name = 'reset_status'
            else:
                action_name = 'os-reset_status'
        body = {action_name: {"status": status}}
        body = json.dumps(body)
        resp, body = self.post("%s/%s/action" % (s_type, s_id), body,
                               headers=headers, extra_headers=True,
                               version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def force_delete(self, s_id, s_type="shares", headers=None,
                     version=LATEST_MICROVERSION, action_name=None):
        """Force delete share or snapshot.

        s_type: shares, snapshots
        """
        if action_name is None:
            if utils.is_microversion_gt(version, "2.6"):
                action_name = 'force_delete'
            else:
                action_name = 'os-force_delete'
        body = {action_name: None}
        body = json.dumps(body)
        resp, body = self.post("%s/%s/action" % (s_type, s_id), body,
                               headers=headers, extra_headers=True,
                               version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    @staticmethod
    def _get_base_url(endpoint):
        url = parse.urlparse(endpoint)
        # Get any valid path components before the version string
        # regex matches version str & everything after (examples: v1, v2, v1.2)
        base_path = re.split(r'(^|/)+v\d+(\.\d+)?', url.path)[0]
        base_url = url._replace(path=base_path)
        return parse.urlunparse(base_url) + '/'

    def send_microversion_request(self, version=None, script_name=None):
        """Prepare and send the HTTP GET Request to the base URL.

        Extracts the base URL from the shares_client endpoint and makes a GET
        request with the microversions request header.
        :param version: The string to send for the value of the microversion
                        header, or None to omit the header.
        :param script_name: The first part of the URL (v1 or v2), or None to
                            omit it.
        """

        headers = self.get_headers()
        url, headers, body = self.auth_provider.auth_request(
            'GET', 'shares', headers, None, self.filters)
        url = self._get_base_url(url)
        if script_name:
            url += script_name + '/'
        if version:
            headers[self.API_MICROVERSIONS_HEADER] = version

        # Handle logging because raw_request doesn't log anything
        start = time.time()
        self._log_request_start('GET', url)
        resp, resp_body = self.raw_request(url, 'GET', headers=headers)
        end = time.time()
        self._log_request(
            'GET', url, resp, secs=(end - start), resp_body=resp_body)
        self.response_checker('GET', resp, resp_body)
        resp_body = json.loads(resp_body)
        return resp, resp_body

    def is_resource_deleted(self, *args, **kwargs):
        """Verifies whether provided resource deleted or not.

        :param kwargs: dict with expected keys 'share_id', 'snapshot_id',
        :param kwargs: 'sn_id', 'ss_id', 'vt_id' and 'server_id'
        :raises share_exceptions.InvalidResource
        """
        if "share_instance_id" in kwargs:
            return self._is_resource_deleted(
                self.get_share_instance, kwargs.get("share_instance_id"))
        elif "share_group_id" in kwargs:
            return self._is_resource_deleted(
                self.get_share_group, kwargs.get("share_group_id"))
        elif "share_group_snapshot_id" in kwargs:
            return self._is_resource_deleted(
                self.get_share_group_snapshot,
                kwargs.get("share_group_snapshot_id"))
        elif "share_group_type_id" in kwargs:
            return self._is_resource_deleted(
                self.get_share_group_type, kwargs.get("share_group_type_id"))
        elif "replica_id" in kwargs:
            return self._is_resource_deleted(
                self.get_share_replica, kwargs.get("replica_id"))
        elif "message_id" in kwargs:
            return self._is_resource_deleted(
                self.get_message, kwargs.get("message_id"))
        elif "share_network_subnet_id" in kwargs:
            subnet_kwargs = {
                "sn_id": kwargs["extra_params"]["share_network_id"]}
            return self._is_resource_deleted(
                self.get_subnet, kwargs.get("share_network_subnet_id"),
                **subnet_kwargs
            )
        else:
            return super(SharesV2Client, self).is_resource_deleted(
                *args, **kwargs)

###############

    def create_share(self, share_protocol=None, size=None,
                     name=None, snapshot_id=None, description=None,
                     metadata=None, share_network_id=None,
                     share_type_id=None, is_public=False,
                     share_group_id=None, availability_zone=None,
                     version=LATEST_MICROVERSION, experimental=False,
                     scheduler_hints=None):
        headers = EXPERIMENTAL if experimental else None
        metadata = metadata or {}
        scheduler_hints = scheduler_hints or {}
        if name is None:
            name = data_utils.rand_name("tempest-created-share")
        if description is None:
            description = data_utils.rand_name("tempest-created-share-desc")
        if size is None:
            size = self.share_size
        if share_protocol is None:
            share_protocol = self.share_protocol
        if share_protocol is None:
            raise share_exceptions.ShareProtocolNotSpecified()
        post_body = {
            "share": {
                "share_proto": share_protocol,
                "description": description,
                "snapshot_id": snapshot_id,
                "name": name,
                "size": size,
                "metadata": metadata,
                "is_public": is_public,
            }
        }
        if availability_zone:
            post_body["share"]["availability_zone"] = availability_zone
        if share_network_id:
            post_body["share"]["share_network_id"] = share_network_id
        if share_type_id:
            post_body["share"]["share_type"] = share_type_id
        if share_group_id:
            post_body["share"]["share_group_id"] = share_group_id
        if scheduler_hints:
            post_body["share"]["scheduler_hints"] = scheduler_hints

        body = json.dumps(post_body)
        resp, body = self.post("shares", body, headers=headers,
                               extra_headers=experimental, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_shares(self, detailed=False, params=None,
                    version=LATEST_MICROVERSION, experimental=False):
        """Get list of shares w/o filters."""
        headers = EXPERIMENTAL if experimental else None
        uri = 'shares/detail' if detailed else 'shares'
        uri += '?%s' % parse.urlencode(params) if params else ''
        resp, body = self.get(uri, headers=headers, extra_headers=experimental,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_shares_in_recycle_bin(self, detailed=False,
                                   params=None, version=LATEST_MICROVERSION,
                                   experimental=False):
        """Get list of shares in recycle bin with w/o filters."""
        headers = EXPERIMENTAL if experimental else None
        uri = 'shares/detail' if detailed else 'shares'
        uri += '?is_soft_deleted=true'
        uri += '&%s' % parse.urlencode(params) if params else ''
        resp, body = self.get(uri, headers=headers, extra_headers=experimental,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_shares_with_detail(self, params=None,
                                version=LATEST_MICROVERSION,
                                experimental=False):
        """Get detailed list of shares w/o filters."""
        return self.list_shares(detailed=True, params=params,
                                version=version, experimental=experimental)

    def get_share(self, share_id, version=LATEST_MICROVERSION,
                  experimental=False):
        headers = EXPERIMENTAL if experimental else None
        resp, body = self.get("shares/%s" % share_id, headers=headers,
                              extra_headers=experimental, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_export_location(
            self, share_id, export_location_uuid, version=LATEST_MICROVERSION):
        resp, body = self.get(
            "shares/%(share_id)s/export_locations/%(el_uuid)s" % {
                "share_id": share_id, "el_uuid": export_location_uuid},
            version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_export_locations(
            self, share_id, version=LATEST_MICROVERSION):
        resp, body = self.get(
            "shares/%(share_id)s/export_locations" % {"share_id": share_id},
            version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share(self, share_id, params=None,
                     version=LATEST_MICROVERSION):
        uri = "shares/%s" % share_id
        uri += '?%s' % (parse.urlencode(params) if params else '')
        resp, body = self.delete(uri, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def soft_delete_share(self, share_id, version=LATEST_MICROVERSION):
        post_body = {"soft_delete": None}
        body = json.dumps(post_body)
        resp, body = self.post(
            "shares/%s/action" % share_id, body, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def restore_share(self, share_id, version=LATEST_MICROVERSION):
        post_body = {"restore": None}
        body = json.dumps(post_body)
        resp, body = self.post(
            "shares/%s/action" % share_id, body, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

###############
    def create_share_transfer(self, share_id, name=None,
                              version=LATEST_MICROVERSION):
        if name is None:
            name = data_utils.rand_name("tempest-created-share-transfer")
        post_body = {
            "transfer": {
                "share_id": share_id,
                "name": name
            }
        }
        body = json.dumps(post_body)
        resp, body = self.post("share-transfers", body, version=version)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_transfer(self, transfer_id, version=LATEST_MICROVERSION):
        resp, body = self.delete("share-transfers/%s" % transfer_id,
                                 version=version)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def list_share_transfers(self, detailed=False, params=None,
                             version=LATEST_MICROVERSION):
        """Get list of share transfers w/o filters."""
        uri = 'share-transfers/detail' if detailed else 'share-transfers'
        uri += '?%s' % parse.urlencode(params) if params else ''
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_transfer(self, transfer_id, version=LATEST_MICROVERSION):
        resp, body = self.get("share-transfers/%s" % transfer_id,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def accept_share_transfer(self, transfer_id, auth_key,
                              clear_access_rules=False,
                              version=LATEST_MICROVERSION):
        post_body = {
            "accept": {
                "auth_key": auth_key,
                "clear_access_rules": clear_access_rules
            }
        }
        body = json.dumps(post_body)
        resp, body = self.post("share-transfers/%s/accept" % transfer_id,
                               body, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def get_instances_of_share(self, share_id, version=LATEST_MICROVERSION):
        resp, body = self.get("shares/%s/instances" % share_id,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_instances(self, version=LATEST_MICROVERSION,
                             params=None):
        uri = 'share_instances'
        uri += '?%s' % parse.urlencode(params) if params else ''
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_instance(self, instance_id, version=LATEST_MICROVERSION):
        resp, body = self.get("share_instances/%s" % instance_id,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_instance_export_location(
            self, instance_id, export_location_uuid,
            version=LATEST_MICROVERSION):
        resp, body = self.get(
            "share_instances/%(instance_id)s/export_locations/%(el_uuid)s" % {
                "instance_id": instance_id, "el_uuid": export_location_uuid},
            version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_instance_export_locations(
            self, instance_id, version=LATEST_MICROVERSION):
        resp, body = self.get(
            "share_instances/%s/export_locations" % instance_id,
            version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def extend_share(self, share_id, new_size, version=LATEST_MICROVERSION,
                     action_name=None, force=False):
        if action_name is None:
            if utils.is_microversion_gt(version, "2.6"):
                action_name = 'extend'
            else:
                action_name = 'os-extend'

        post_body = {
            action_name: {
                "new_size": new_size,
            }
        }

        if utils.is_microversion_gt(version, "2.63"):
            post_body[action_name]["force"] = force

        body = json.dumps(post_body)
        resp, body = self.post(
            "shares/%s/action" % share_id, body, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def shrink_share(self, share_id, new_size, version=LATEST_MICROVERSION,
                     action_name=None):
        if action_name is None:
            if utils.is_microversion_gt(version, "2.6"):
                action_name = 'shrink'
            else:
                action_name = 'os-shrink'
        post_body = {
            action_name: {
                "new_size": new_size,
            }
        }
        body = json.dumps(post_body)
        resp, body = self.post(
            "shares/%s/action" % share_id, body, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def manage_share(self, service_host, protocol, export_path,
                     share_type_id, name=None, description=None,
                     is_public=False, version=LATEST_MICROVERSION,
                     url=None, share_server_id=None):
        post_body = {
            "share": {
                "export_path": export_path,
                "service_host": service_host,
                "protocol": protocol,
                "share_type": share_type_id,
                "name": name,
                "description": description,
                "is_public": is_public,
            }
        }
        if share_server_id is not None:
            post_body['share']['share_server_id'] = share_server_id
        if url is None:
            if utils.is_microversion_gt(version, "2.6"):
                url = 'shares/manage'
            else:
                url = 'os-share-manage'
        body = json.dumps(post_body)
        resp, body = self.post(url, body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def unmanage_share(self, share_id, version=LATEST_MICROVERSION, url=None,
                       action_name=None, body=None):
        if url is None:
            if utils.is_microversion_gt(version, "2.6"):
                url = 'shares'
            else:
                url = 'os-share-unmanage'
        if action_name is None:
            if utils.is_microversion_gt(version, "2.6"):
                action_name = 'action'
            else:
                action_name = 'unmanage'
        if body is None and utils.is_microversion_gt(version, "2.6"):
            body = json.dumps({'unmanage': {}})
        resp, body = self.post(
            "%(url)s/%(share_id)s/%(action_name)s" % {
                'url': url, 'share_id': share_id, 'action_name': action_name},
            body,
            version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def create_snapshot(self, share_id, name=None, description=None,
                        force=False, metadata=None,
                        version=LATEST_MICROVERSION):
        if name is None:
            name = data_utils.rand_name("tempest-created-share-snap")
        if description is None:
            description = data_utils.rand_name(
                "tempest-created-share-snap-desc")
        post_body = {
            "snapshot": {
                "name": name,
                "force": force,
                "description": description,
                "share_id": share_id,
            }
        }
        if utils.is_microversion_ge(version, "2.73") and metadata:
            post_body["snapshot"]["metadata"] = metadata

        body = json.dumps(post_body)
        resp, body = self.post("snapshots", body, version=version)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_snapshot(self, snapshot_id, version=LATEST_MICROVERSION):
        resp, body = self.get("snapshots/%s" % snapshot_id, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_snapshots(self, detailed=False, params=None,
                       version=LATEST_MICROVERSION):
        """Get list of share snapshots w/o filters."""
        uri = 'snapshots/detail' if detailed else 'snapshots'
        uri += '?%s' % parse.urlencode(params) if params else ''
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_snapshots_for_share(self, share_id, detailed=False,
                                 version=LATEST_MICROVERSION):
        """Get list of snapshots for given share."""
        uri = ('snapshots/detail?share_id=%s' % share_id
               if detailed else 'snapshots?share_id=%s' % share_id)
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_snapshots_with_detail(self, params=None,
                                   version=LATEST_MICROVERSION):
        """Get detailed list of share snapshots w/o filters."""
        return self.list_snapshots(detailed=True, params=params,
                                   version=version)

    def delete_snapshot(self, snap_id, version=LATEST_MICROVERSION):
        resp, body = self.delete("snapshots/%s" % snap_id, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def manage_snapshot(self, share_id, provider_location,
                        name=None, description=None,
                        version=LATEST_MICROVERSION,
                        driver_options=None):
        if name is None:
            name = data_utils.rand_name("tempest-manage-snapshot")
        if description is None:
            description = data_utils.rand_name("tempest-manage-snapshot-desc")
        post_body = {
            "snapshot": {
                "share_id": share_id,
                "provider_location": provider_location,
                "name": name,
                "description": description,
                "driver_options": driver_options if driver_options else {},
            }
        }
        url = 'snapshots/manage'
        body = json.dumps(post_body)
        resp, body = self.post(url, body, version=version)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def unmanage_snapshot(self, snapshot_id, version=LATEST_MICROVERSION,
                          body=None):
        url = 'snapshots'
        action_name = 'action'
        if body is None:
            body = json.dumps({'unmanage': {}})
        resp, body = self.post(
            "%(url)s/%(snapshot_id)s/%(action_name)s" % {
                'url': url, 'snapshot_id': snapshot_id,
                'action_name': action_name},
            body,
            version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def snapshot_reset_state(self, snapshot_id,
                             status=constants.STATUS_AVAILABLE,
                             version=LATEST_MICROVERSION):
        return self.reset_state(
            snapshot_id, status=status, s_type='snapshots', version=version)

###############

    def revert_to_snapshot(self, share_id, snapshot_id,
                           version=LATEST_MICROVERSION):
        url = 'shares/%s/action' % share_id
        body = json.dumps({'revert': {'snapshot_id': snapshot_id}})
        resp, body = self.post(url, body, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def create_share_type_extra_specs(self, share_type_id, extra_specs,
                                      version=LATEST_MICROVERSION):
        url = "types/%s/extra_specs" % share_type_id
        post_body = json.dumps({'extra_specs': extra_specs})
        resp, body = self.post(url, post_body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_type_extra_spec(self, share_type_id, extra_spec_name,
                                  version=LATEST_MICROVERSION):
        uri = "types/%s/extra_specs/%s" % (share_type_id, extra_spec_name)
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_type_extra_specs(self, share_type_id, params=None,
                                   version=LATEST_MICROVERSION):
        uri = "types/%s/extra_specs" % share_type_id
        if params is not None:
            uri += '?%s' % parse.urlencode(params)
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_type_extra_spec(self, share_type_id, spec_name,
                                     spec_value, version=LATEST_MICROVERSION):
        uri = "types/%s/extra_specs/%s" % (share_type_id, spec_name)
        extra_spec = {spec_name: spec_value}
        post_body = json.dumps(extra_spec)
        resp, body = self.put(uri, post_body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_type_extra_specs(self, share_type_id, extra_specs,
                                      version=LATEST_MICROVERSION):
        uri = "types/%s/extra_specs" % share_type_id
        extra_specs = {"extra_specs": extra_specs}
        post_body = json.dumps(extra_specs)
        resp, body = self.post(uri, post_body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_type_extra_spec(self, share_type_id, extra_spec_name,
                                     version=LATEST_MICROVERSION):
        uri = "types/%s/extra_specs/%s" % (share_type_id, extra_spec_name)
        resp, body = self.delete(uri, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def show_share_server(self, share_server_id, version=LATEST_MICROVERSION):
        """Get share server info."""
        uri = "share-servers/%s" % share_server_id
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def get_snapshot_instance(self, instance_id, version=LATEST_MICROVERSION):
        resp, body = self.get("snapshot-instances/%s" % instance_id,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_snapshot_instances(self, detail=False, snapshot_id=None,
                                version=LATEST_MICROVERSION):
        """Get list of share snapshot instances."""
        uri = "snapshot-instances%s" % ('/detail' if detail else '')
        if snapshot_id is not None:
            uri += '?snapshot_id=%s' % snapshot_id
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def reset_snapshot_instance_status(self, instance_id,
                                       status=constants.STATUS_AVAILABLE,
                                       version=LATEST_MICROVERSION):
        """Reset the status."""
        uri = 'snapshot-instances/%s/action' % instance_id
        post_body = {
            'reset_status': {
                'status': status
            }
        }
        body = json.dumps(post_body)
        resp, body = self.post(uri, body, extra_headers=True, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def get_snapshot_instance_export_location(
            self, instance_id, export_location_uuid,
            version=LATEST_MICROVERSION):
        resp, body = self.get(
            "snapshot-instances/%(instance_id)s/export-locations/%("
            "el_uuid)s" % {
                "instance_id": instance_id,
                "el_uuid": export_location_uuid},
            version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_snapshot_instance_export_locations(
            self, instance_id, version=LATEST_MICROVERSION):
        resp, body = self.get(
            "snapshot-instances/%s/export-locations" % instance_id,
            version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def _get_access_action_name(self, version, action):
        if utils.is_microversion_gt(version, "2.6"):
            return action.split('os-')[-1]
        return action

    def create_access_rule(self, share_id, access_type="ip",
                           access_to="0.0.0.0", access_level=None,
                           version=LATEST_MICROVERSION, metadata=None,
                           action_name=None, lock_visibility=False,
                           lock_deletion=False):
        post_body = {
            self._get_access_action_name(version, 'os-allow_access'): {
                "access_type": access_type,
                "access_to": access_to,
                "access_level": access_level,
            }
        }
        if metadata is not None:
            post_body['allow_access']['metadata'] = metadata
        if lock_visibility:
            post_body['allow_access']['lock_visibility'] = True
        if lock_deletion:
            post_body['allow_access']['lock_deletion'] = True
        body = json.dumps(post_body)
        resp, body = self.post(
            "shares/%s/action" % share_id, body, version=version,
            extra_headers=True)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_access_rules(self, share_id, version=LATEST_MICROVERSION,
                          metadata=None, action_name=None):
        if utils.is_microversion_lt(version, "2.45"):
            body = {
                self._get_access_action_name(version, 'os-access_list'): None
            }
            resp, body = self.post(
                "shares/%s/action" % share_id, json.dumps(body),
                version=version)
            self.expected_success(200, resp.status)
        else:
            return self.list_access_rules_with_new_API(
                share_id, metadata=metadata, version=version,
                action_name=action_name)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_access_rules_with_new_API(self, share_id, metadata=None,
                                       version=LATEST_MICROVERSION,
                                       action_name=None):
        metadata = metadata or {}
        query_string = ''

        params = sorted(
            [(k, v) for (k, v) in list(metadata.items()) if v])
        if params:
            query_string = "&%s" % parse.urlencode(params)

        url = 'share-access-rules?share_id=%s' % share_id + query_string
        resp, body = self.get(url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_access_rule(self, share_id, rule_id,
                           version=LATEST_MICROVERSION, action_name=None,
                           unrestrict=False):
        post_body = {
            self._get_access_action_name(version, 'os-deny_access'): {
                "access_id": rule_id,
            }
        }
        if unrestrict:
            post_body['deny_access']['unrestrict'] = True
        body = json.dumps(post_body)
        resp, body = self.post(
            "shares/%s/action" % share_id, body, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def get_access_rule(self, access_id, version=LATEST_MICROVERSION):
        resp, body = self.get("share-access-rules/%s" % access_id,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_access_rule(self, access_id, access_level,
                           version=LATEST_MICROVERSION):
        url = 'share-access-rules/%s' % access_id
        body = {'update_access': {"access_level": access_level}}
        resp, body = self.put(url, json.dumps(body), version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_access_metadata(self, access_id, metadata,
                               version=LATEST_MICROVERSION):
        url = 'share-access-rules/%s/metadata' % access_id
        body = {"metadata": metadata}
        resp, body = self.put(url, json.dumps(body), version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_access_metadata(self, access_id, key,
                               version=LATEST_MICROVERSION):
        url = "share-access-rules/%s/metadata/%s" % (access_id, key)
        resp, body = self.delete(url, version=version)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def list_availability_zones(self, url='availability-zones',
                                version=LATEST_MICROVERSION):
        """Get list of availability zones."""
        if url is None:
            if utils.is_microversion_gt(version, "2.6"):
                url = 'availability-zones'
            else:
                url = 'os-availability-zone'
        resp, body = self.get(url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def list_services(self, params=None, url=None,
                      version=LATEST_MICROVERSION):
        """List services."""
        if url is None:
            if utils.is_microversion_gt(version, "2.6"):
                url = 'services'
            else:
                url = 'os-services'
        if params:
            url += '?%s' % parse.urlencode(params)
        resp, body = self.get(url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def list_share_types(self, params=None, default=False,
                         version=LATEST_MICROVERSION):
        uri = 'types'
        if default:
            uri += '/default'
        if params is not None:
            uri += '?%s' % parse.urlencode(params)
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def create_share_type(self, name, is_public=True,
                          version=LATEST_MICROVERSION, **kwargs):
        if utils.is_microversion_gt(version, "2.6"):
            is_public_keyname = 'share_type_access:is_public'
        else:
            is_public_keyname = 'os-share-type-access:is_public'
        post_body = {
            'name': name,
            'extra_specs': kwargs.get('extra_specs'),
            is_public_keyname: is_public,
        }
        if kwargs.get('description'):
            post_body['description'] = kwargs.get('description')
        post_body = json.dumps({'share_type': post_body})
        resp, body = self.post('types', post_body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_type(self, share_type_id, name=None,
                          is_public=None, description=None,
                          version=LATEST_MICROVERSION):
        post_body = {}
        if is_public is not None:
            post_body.update({"share_type_access:is_public": is_public})
        if name is not None:
            post_body.update({"name": name})
        if description is not None:
            post_body.update({"description": description})
        post_body = json.dumps({'share_type': post_body})
        resp, body = self.put("types/%s" % share_type_id, post_body,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_type(self, share_type_id, version=LATEST_MICROVERSION):
        resp, body = self.delete("types/%s" % share_type_id, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def get_share_type(self, share_type_id, version=LATEST_MICROVERSION):
        resp, body = self.get("types/%s" % share_type_id, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_access_to_share_type(self, share_type_id,
                                  version=LATEST_MICROVERSION,
                                  action_name=None):
        if action_name is None:
            if utils.is_microversion_gt(version, "2.6"):
                action_name = 'share_type_access'
            else:
                action_name = 'os-share-type-access'
        url = 'types/%(st_id)s/%(action_name)s' % {
            'st_id': share_type_id, 'action_name': action_name}
        resp, body = self.get(url, version=version)
        # [{"share_type_id": "%st_id%", "project_id": "%project_id%"}, ]
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    @staticmethod
    def _get_quotas_url(version):
        if utils.is_microversion_gt(version, "2.6"):
            return 'quota-sets'
        return 'os-quota-sets'

    @staticmethod
    def _get_quotas_url_arguments_as_str(user_id=None, share_type=None):
        args_str = ''
        if not (user_id is None or share_type is None):
            args_str = "?user_id=%s&share_type=%s" % (user_id, share_type)
        elif user_id is not None:
            args_str = "?user_id=%s" % user_id
        elif share_type is not None:
            args_str = "?share_type=%s" % share_type
        return args_str

    def default_quotas(self, tenant_id, url=None, version=LATEST_MICROVERSION):
        if url is None:
            url = self._get_quotas_url(version)
        url += '/%s' % tenant_id
        resp, body = self.get("%s/defaults" % url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def show_quotas(self, tenant_id, user_id=None, share_type=None, url=None,
                    version=LATEST_MICROVERSION):
        if url is None:
            url = self._get_quotas_url(version)
        url += '/%s' % tenant_id
        url += self._get_quotas_url_arguments_as_str(user_id, share_type)
        resp, body = self.get(url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def reset_quotas(self, tenant_id, user_id=None, share_type=None, url=None,
                     version=LATEST_MICROVERSION):
        if url is None:
            url = self._get_quotas_url(version)
        url += '/%s' % tenant_id
        url += self._get_quotas_url_arguments_as_str(user_id, share_type)
        resp, body = self.delete(url, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def detail_quotas(self, tenant_id, user_id=None, share_type=None, url=None,
                      version=LATEST_MICROVERSION):
        if url is None:
            url = self._get_quotas_url(version)
        url += '/%s/detail' % tenant_id
        url += self._get_quotas_url_arguments_as_str(user_id, share_type)
        resp, body = self.get(url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_quotas(self, tenant_id, user_id=None, shares=None,
                      snapshots=None, gigabytes=None, snapshot_gigabytes=None,
                      share_networks=None,
                      share_groups=None, share_group_snapshots=None,
                      force=True, share_type=None, share_replicas=None,
                      replica_gigabytes=None, url=None,
                      version=LATEST_MICROVERSION):
        if url is None:
            url = self._get_quotas_url(version)
        url += '/%s' % tenant_id
        url += self._get_quotas_url_arguments_as_str(user_id, share_type)

        put_body = {"tenant_id": tenant_id}
        if force:
            put_body["force"] = "true"
        if shares is not None:
            put_body["shares"] = shares
        if snapshots is not None:
            put_body["snapshots"] = snapshots
        if gigabytes is not None:
            put_body["gigabytes"] = gigabytes
        if snapshot_gigabytes is not None:
            put_body["snapshot_gigabytes"] = snapshot_gigabytes
        if share_networks is not None:
            put_body["share_networks"] = share_networks
        if share_groups is not None:
            put_body["share_groups"] = share_groups
        if share_group_snapshots is not None:
            put_body["share_group_snapshots"] = share_group_snapshots
        if share_replicas is not None:
            put_body["share_replicas"] = share_replicas
        if replica_gigabytes is not None:
            put_body["replica_gigabytes"] = replica_gigabytes
        put_body = json.dumps({"quota_set": put_body})

        resp, body = self.put(url, put_body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def create_share_group(self, name=None, description=None,
                           share_group_type_id=None, share_type_ids=(),
                           share_network_id=None,
                           source_share_group_snapshot_id=None,
                           availability_zone=None,
                           version=LATEST_MICROVERSION):
        """Create a new share group."""
        uri = 'share-groups'
        post_body = {}
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        if name:
            post_body['name'] = name
        if description:
            post_body['description'] = description
        if share_group_type_id:
            post_body['share_group_type_id'] = share_group_type_id
        if share_type_ids:
            post_body['share_types'] = share_type_ids
        if source_share_group_snapshot_id:
            post_body['source_share_group_snapshot_id'] = (
                source_share_group_snapshot_id)
        if share_network_id:
            post_body['share_network_id'] = share_network_id
        if availability_zone:
            post_body['availability_zone'] = availability_zone
        body = json.dumps({'share_group': post_body})

        resp, body = self.post(uri, body, headers=headers,
                               extra_headers=extra_headers, version=version)

        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_group(self, share_group_id, version=LATEST_MICROVERSION):
        """Delete a share group."""
        uri = 'share-groups/%s' % share_group_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.delete(uri, headers=headers,
                                 extra_headers=extra_headers, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def list_share_groups(self, detailed=False, params=None,
                          version=LATEST_MICROVERSION):
        """Get list of share groups w/o filters."""
        uri = 'share-groups%s' % ('/detail' if detailed else '')
        uri += '?%s' % (parse.urlencode(params) if params else '')
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_group(self, share_group_id, version=LATEST_MICROVERSION):
        """Get share group info."""
        uri = 'share-groups/%s' % share_group_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_group(self, share_group_id, name=None, description=None,
                           version=LATEST_MICROVERSION, **kwargs):
        """Update an existing share group."""
        uri = 'share-groups/%s' % share_group_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        post_body = {}
        if name:
            post_body['name'] = name
        if description:
            post_body['description'] = description
        if kwargs:
            post_body.update(kwargs)
        body = json.dumps({'share_group': post_body})

        resp, body = self.put(uri, body, headers=headers,
                              extra_headers=extra_headers, version=version)

        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def share_group_reset_state(self, share_group_id, status='error',
                                version=LATEST_MICROVERSION):
        headers, _junk = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        return self.reset_state(
            share_group_id, status=status, s_type='share-groups',
            headers=headers, version=version)

    def share_group_force_delete(self, share_group_id,
                                 version=LATEST_MICROVERSION):
        headers, _junk = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        return self.force_delete(
            share_group_id, s_type='share-groups', headers=headers,
            version=version)

###############

    def create_share_group_type(self, name=None, share_types=(),
                                is_public=None, group_specs=None,
                                version=LATEST_MICROVERSION):
        """Create a new share group type."""
        uri = 'share-group-types'
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        post_body = {}
        if isinstance(share_types, (tuple, list)):
            share_types = list(share_types)
        else:
            share_types = [share_types]
        if name is not None:
            post_body['name'] = name
        if share_types:
            post_body['share_types'] = share_types
        if is_public is not None:
            post_body['is_public'] = is_public
        if group_specs:
            post_body['group_specs'] = group_specs
        body = json.dumps({'share_group_type': post_body})
        resp, body = self.post(uri, body, headers=headers,
                               extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_group_types(self, detailed=False, params=None,
                               version=LATEST_MICROVERSION):
        """Get list of share group types."""
        uri = 'share-group-types%s' % ('/detail' if detailed else '')
        uri += '?%s' % (parse.urlencode(params) if params else '')
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_group_type(self, share_group_type_id,
                             version=LATEST_MICROVERSION):
        """Get share group type info."""
        uri = 'share-group-types/%s' % share_group_type_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_default_share_group_type(self, version=LATEST_MICROVERSION):
        """Get default share group type info."""
        uri = 'share-group-types/default'
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_group_type(self, share_group_type_id,
                                version=LATEST_MICROVERSION):
        """Delete an existing share group type."""
        uri = 'share-group-types/%s' % share_group_type_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.delete(uri, headers=headers,
                                 extra_headers=extra_headers, version=version)
        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)

    def add_access_to_share_group_type(self, share_group_type_id, project_id,
                                       version=LATEST_MICROVERSION):
        uri = 'share-group-types/%s/action' % share_group_type_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        post_body = {'project': project_id}
        post_body = json.dumps({'addProjectAccess': post_body})
        resp, body = self.post(uri, post_body, headers=headers,
                               extra_headers=extra_headers, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def remove_access_from_share_group_type(self, share_group_type_id,
                                            project_id,
                                            version=LATEST_MICROVERSION):
        uri = 'share-group-types/%s/action' % share_group_type_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        post_body = {'project': project_id}
        post_body = json.dumps({'removeProjectAccess': post_body})
        resp, body = self.post(uri, post_body, headers=headers,
                               extra_headers=extra_headers, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def list_access_to_share_group_type(self, share_group_type_id,
                                        version=LATEST_MICROVERSION):
        uri = 'share-group-types/%s/access' % share_group_type_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def create_share_group_type_specs(self, share_group_type_id,
                                      group_specs_dict,
                                      version=LATEST_MICROVERSION):
        url = "share-group-types/%s/group-specs" % share_group_type_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        post_body = json.dumps({'group_specs': group_specs_dict})
        resp, body = self.post(url, post_body, headers=headers,
                               extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_group_type_spec(self, share_group_type_id, group_spec_key,
                                  version=LATEST_MICROVERSION):
        uri = "share-group-types/%s/group-specs/%s" % (
            share_group_type_id, group_spec_key)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_group_type_specs(self, share_group_type_id, params=None,
                                   version=LATEST_MICROVERSION):
        uri = "share-group-types/%s/group-specs" % share_group_type_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        if params is not None:
            uri += '?%s' % parse.urlencode(params)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_group_type_spec(self, share_group_type_id, group_spec_key,
                                     group_spec_value,
                                     version=LATEST_MICROVERSION):
        uri = "share-group-types/%s/group-specs/%s" % (
            share_group_type_id, group_spec_key)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        group_spec = {group_spec_key: group_spec_value}
        post_body = json.dumps(group_spec)
        resp, body = self.put(uri, post_body, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_group_type_specs(self, share_group_type_id,
                                      group_specs_dict,
                                      version=LATEST_MICROVERSION):
        return self.create_share_group_type_specs(
            share_group_type_id, group_specs_dict, version=version)

    def delete_share_group_type_spec(self, share_group_type_id, group_spec_key,
                                     version=LATEST_MICROVERSION):
        uri = "share-group-types/%s/group-specs/%s" % (
            share_group_type_id, group_spec_key)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.delete(uri, headers=headers,
                                 extra_headers=extra_headers, version=version)
        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def create_share_group_snapshot(self, share_group_id, name=None,
                                    description=None,
                                    version=LATEST_MICROVERSION):
        """Create a new share group snapshot of an existing share group."""
        uri = 'share-group-snapshots'
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        post_body = {'share_group_id': share_group_id}
        if name:
            post_body['name'] = name
        if description:
            post_body['description'] = description
        body = json.dumps({'share_group_snapshot': post_body})
        resp, body = self.post(uri, body, headers=headers,
                               extra_headers=extra_headers, version=version)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_group_snapshot(self, share_group_snapshot_id,
                                    version=LATEST_MICROVERSION):
        """Delete an existing share group snapshot."""
        uri = 'share-group-snapshots/%s' % share_group_snapshot_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.delete(uri, headers=headers,
                                 extra_headers=extra_headers, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def list_share_group_snapshots(self, detailed=False, params=None,
                                   version=LATEST_MICROVERSION):
        """Get list of share group snapshots w/o filters."""
        uri = 'share-group-snapshots%s' % ('/detail' if detailed else '')
        uri += '?%s' % (parse.urlencode(params) if params else '')
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_group_snapshot(self, share_group_snapshot_id,
                                 version=LATEST_MICROVERSION):
        """Get share group snapshot info."""
        uri = 'share-group-snapshots/%s' % share_group_snapshot_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_group_snapshot(self, share_group_snapshot_id, name=None,
                                    description=None,
                                    version=LATEST_MICROVERSION):
        """Update an existing share group snapshot."""
        uri = 'share-group-snapshots/%s' % share_group_snapshot_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        post_body = {}
        if name:
            post_body['name'] = name
        if description:
            post_body['description'] = description
        body = json.dumps({'share_group_snapshot': post_body})
        resp, body = self.put(uri, body, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def share_group_snapshot_reset_state(self, share_group_snapshot_id,
                                         status='error',
                                         version=LATEST_MICROVERSION):
        headers, _junk = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        return self.reset_state(
            share_group_snapshot_id, status=status, headers=headers,
            s_type='group-snapshots', version=version)

    def share_group_snapshot_force_delete(self, share_group_snapshot_id,
                                          version=LATEST_MICROVERSION):
        headers, _junk = utils.get_extra_headers(
            version, constants.SHARE_GROUPS_GRADUATION_VERSION)
        return self.force_delete(
            share_group_snapshot_id, s_type='share-group-snapshots',
            headers=headers, version=version)

###############

    def manage_share_server(self, host, share_network_id, identifier,
                            driver_options=None, version=LATEST_MICROVERSION,
                            share_network_subnet_id=None):
        body = {
            'share_server': {
                'host': host,
                'share_network_id': share_network_id,
                'identifier': identifier,
                'driver_options': driver_options if driver_options else {},
            }
        }
        if share_network_subnet_id:
            body['share_server']['share_network_subnet_id'] = (
                share_network_subnet_id)

        body = json.dumps(body)
        resp, body = self.post('share-servers/manage', body,
                               extra_headers=True, version=version)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def unmanage_share_server(self, share_server_id,
                              version=LATEST_MICROVERSION):
        body = json.dumps({'unmanage': None})
        resp, body = self.post('share-servers/%s/action' % share_server_id,
                               body, extra_headers=True, version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def share_server_reset_state(self, share_server_id,
                                 status=constants.SERVER_STATE_ACTIVE,
                                 version=LATEST_MICROVERSION):
        return self.reset_state(
            share_server_id, status=status, s_type='share-servers',
            version=version)

###############

    def migrate_share(self, share_id, host,
                      force_host_assisted_migration=False,
                      new_share_network_id=None, writable=False,
                      preserve_metadata=False, preserve_snapshots=False,
                      nondisruptive=False, new_share_type_id=None,
                      version=LATEST_MICROVERSION):

        body = {
            'migration_start': {
                'host': host,
                'force_host_assisted_migration': force_host_assisted_migration,
                'new_share_network_id': new_share_network_id,
                'new_share_type_id': new_share_type_id,
                'writable': writable,
                'preserve_metadata': preserve_metadata,
                'preserve_snapshots': preserve_snapshots,
                'nondisruptive': nondisruptive,
            }
        }

        body = json.dumps(body)
        resp, body = self.post('shares/%s/action' % share_id, body,
                               headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        return rest_client.ResponseBody(resp, body)

    def migration_complete(self, share_id, version=LATEST_MICROVERSION,
                           action_name='migration_complete'):
        post_body = {
            action_name: None,
        }
        body = json.dumps(post_body)
        resp, body = self.post('shares/%s/action' % share_id, body,
                               headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        return rest_client.ResponseBody(resp, body)

    def migration_cancel(self, share_id, version=LATEST_MICROVERSION,
                         action_name='migration_cancel'):
        post_body = {
            action_name: None,
        }
        body = json.dumps(post_body)
        resp, body = self.post('shares/%s/action' % share_id, body,
                               headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        return rest_client.ResponseBody(resp, body)

    def migration_get_progress(self, share_id, version=LATEST_MICROVERSION,
                               action_name='migration_get_progress'):
        post_body = {
            action_name: None,
        }
        body = json.dumps(post_body)
        resp, body = self.post('shares/%s/action' % share_id, body,
                               headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def reset_task_state(
            self, share_id, task_state, version=LATEST_MICROVERSION,
            action_name='reset_task_state'):
        post_body = {
            action_name: {
                'task_state': task_state,
            }
        }
        body = json.dumps(post_body)
        resp, body = self.post('shares/%s/action' % share_id, body,
                               headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        return rest_client.ResponseBody(resp, body)

    def create_share_replica(self, share_id, availability_zone=None,
                             scheduler_hints=None, share_network_id=None,
                             version=LATEST_MICROVERSION):
        """Add a share replica of an existing share."""
        uri = "share-replicas"
        post_body = {
            'share_id': share_id,
            'availability_zone': availability_zone,
        }

        if scheduler_hints:
            post_body["scheduler_hints"] = scheduler_hints
        if share_network_id:
            post_body['share_network_id'] = share_network_id

        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        body = json.dumps({'share_replica': post_body})
        resp, body = self.post(uri, body,
                               headers=headers,
                               extra_headers=extra_headers,
                               version=version)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_replica(self, replica_id, version=LATEST_MICROVERSION):
        """Get the details of share_replica."""
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.get("share-replicas/%s" % replica_id,
                              headers=headers,
                              extra_headers=extra_headers,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_replicas(self, share_id=None, version=LATEST_MICROVERSION):
        """Get list of replicas."""
        uri = "share-replicas/detail"
        uri += ("?share_id=%s" % share_id) if share_id is not None else ''
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_replicas_summary(self, share_id=None,
                                    version=LATEST_MICROVERSION):
        """Get summary list of replicas."""
        uri = "share-replicas"
        uri += ("?share_id=%s" % share_id) if share_id is not None else ''
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_replica(self, replica_id, version=LATEST_MICROVERSION):
        """Delete share_replica."""
        uri = "share-replicas/%s" % replica_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.delete(uri,
                                 headers=headers,
                                 extra_headers=extra_headers,
                                 version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def promote_share_replica(self, replica_id, expected_status=202,
                              version=LATEST_MICROVERSION):
        """Promote a share replica to active state."""
        uri = "share-replicas/%s/action" % replica_id
        post_body = {
            'promote': None,
        }
        body = json.dumps(post_body)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.post(uri, body,
                               headers=headers,
                               extra_headers=extra_headers,
                               version=version)
        self.expected_success(expected_status, resp.status)
        try:
            body = json.loads(body)
        except json.decoder.JSONDecodeError:
            pass
        return rest_client.ResponseBody(resp, body)

    def list_share_replica_export_locations(self, replica_id,
                                            expected_status=200,
                                            version=LATEST_MICROVERSION):
        uri = "share-replicas/%s/export-locations" % replica_id
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(expected_status, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_share_replica_export_location(self, replica_id,
                                          export_location_id,
                                          expected_status=200,
                                          version=LATEST_MICROVERSION):
        uri = "share-replicas/%s/export-locations/%s" % (replica_id,
                                                         export_location_id)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.get(uri, headers=headers,
                              extra_headers=extra_headers, version=version)
        self.expected_success(expected_status, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def reset_share_replica_status(self, replica_id,
                                   status=constants.STATUS_AVAILABLE,
                                   version=LATEST_MICROVERSION):
        """Reset the status."""
        uri = 'share-replicas/%s/action' % replica_id
        post_body = {
            'reset_status': {
                'status': status
            }
        }
        body = json.dumps(post_body)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.post(uri, body,
                               headers=headers,
                               extra_headers=extra_headers,
                               version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def reset_share_replica_state(self, replica_id,
                                  state=constants.REPLICATION_STATE_ACTIVE,
                                  version=LATEST_MICROVERSION):
        """Reset the replication state of a replica."""
        uri = 'share-replicas/%s/action' % replica_id
        post_body = {
            'reset_replica_state': {
                'replica_state': state
            }
        }
        body = json.dumps(post_body)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.post(uri, body,
                               headers=headers,
                               extra_headers=extra_headers,
                               version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def resync_share_replica(self, replica_id, expected_result=202,
                             version=LATEST_MICROVERSION):
        """Force an immediate resync of the replica."""
        uri = 'share-replicas/%s/action' % replica_id
        post_body = {
            'resync': None
        }
        body = json.dumps(post_body)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.post(uri, body,
                               headers=headers,
                               extra_headers=extra_headers,
                               version=version)
        self.expected_success(expected_result, resp.status)
        return rest_client.ResponseBody(resp, body)

    def force_delete_share_replica(self, replica_id,
                                   version=LATEST_MICROVERSION):
        """Force delete a replica."""
        uri = 'share-replicas/%s/action' % replica_id
        post_body = {
            'force_delete': None
        }
        body = json.dumps(post_body)
        headers, extra_headers = utils.get_extra_headers(
            version, constants.SHARE_REPLICA_GRADUATION_VERSION)
        resp, body = self.post(uri, body,
                               headers=headers,
                               extra_headers=extra_headers,
                               version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def list_share_networks(self, detailed=False, params=None,
                            version=LATEST_MICROVERSION):
        """Get list of share networks w/o filters."""
        uri = 'share-networks/detail' if detailed else 'share-networks'
        uri += '?%s' % parse.urlencode(params) if params else ''
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_networks_with_detail(self, params=None,
                                        version=LATEST_MICROVERSION):
        """Get detailed list of share networks w/o filters."""
        return self.list_share_networks(
            detailed=True, params=params, version=version)

    def get_share_network(self, share_network_id, version=LATEST_MICROVERSION):
        resp, body = self.get("share-networks/%s" % share_network_id,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def get_share_backup(self, backup_id, version=LATEST_MICROVERSION):
        """Returns the details of a single backup."""
        resp, body = self.get("share-backups/%s" % backup_id,
                              headers=EXPERIMENTAL,
                              extra_headers=True,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_share_backups(self, share_id=None, version=LATEST_MICROVERSION):
        """Get list of backups."""
        uri = "share-backups/detail"
        if share_id:
            uri += (f'?share_id={share_id}')
        resp, body = self.get(uri, headers=EXPERIMENTAL,
                              extra_headers=True, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def create_share_backup(self, share_id, name=None, description=None,
                            backup_options=None, version=LATEST_MICROVERSION):
        """Create a share backup."""
        if name is None:
            name = data_utils.rand_name("tempest-created-share-backup")
        if description is None:
            description = data_utils.rand_name(
                "tempest-created-share-backup-desc")
        post_body = {
            'share_backup': {
                'name': name,
                'description': description,
                'share_id': share_id,
                'backup_options': backup_options,
            }
        }
        body = json.dumps(post_body)
        resp, body = self.post('share-backups', body,
                               headers=EXPERIMENTAL,
                               extra_headers=True,
                               version=version)

        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_share_backup(self, backup_id, version=LATEST_MICROVERSION):
        """Delete share backup."""
        uri = "share-backups/%s" % backup_id
        resp, body = self.delete(uri,
                                 headers=EXPERIMENTAL,
                                 extra_headers=True,
                                 version=version)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def restore_share_backup(self, backup_id, version=LATEST_MICROVERSION):
        """Restore share backup."""
        uri = "share-backups/%s/action" % backup_id
        body = {'restore': None}
        resp, body = self.post(uri, json.dumps(body),
                               headers=EXPERIMENTAL,
                               extra_headers=True,
                               version=version)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_share_backup(self, backup_id, name=None, description=None,
                            version=LATEST_MICROVERSION):
        """Update share backup."""
        uri = "share-backups/%s" % backup_id
        post_body = {}
        if name:
            post_body['name'] = name
        if description:
            post_body['description'] = description

        body = json.dumps({'share_backup': post_body})
        resp, body = self.put(uri, body,
                              headers=EXPERIMENTAL,
                              extra_headers=True,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def reset_state_share_backup(self, backup_id,
                                 status=constants.STATUS_AVAILABLE,
                                 version=LATEST_MICROVERSION):

        uri = "share-backups/%s/action" % backup_id
        body = {'reset_status': {'status': status}}
        resp, body = self.post(uri, json.dumps(body),
                               headers=EXPERIMENTAL,
                               extra_headers=True,
                               version=LATEST_MICROVERSION)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

################

    def create_snapshot_access_rule(self, snapshot_id, access_type="ip",
                                    access_to="0.0.0.0/0"):
        body = {
            "allow_access": {
                "access_type": access_type,
                "access_to": access_to
            }
        }
        resp, body = self.post("snapshots/%s/action" % snapshot_id,
                               json.dumps(body), version=LATEST_MICROVERSION)
        self.expected_success(202, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_snapshot_access_rules(self, snapshot_id,
                                   version=LATEST_MICROVERSION):
        resp, body = self.get("snapshots/%s/access-list" % snapshot_id,
                              version=version)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_snapshot_access_rule(self, snapshot_id, rule_id,
                                 version=LATEST_MICROVERSION):
        resp, body = self.get("snapshots/%s/access-list" % snapshot_id,
                              version=version)
        body = json.loads(body)
        body = rest_client.ResponseBody(resp, body)
        found_rules = [
            r for r in body['snapshot_access_list'] if r['id'] == rule_id
        ]
        return found_rules[0] if len(found_rules) > 0 else None

    def delete_snapshot_access_rule(self, snapshot_id, rule_id):
        body = {
            "deny_access": {
                "access_id": rule_id,
            }
        }
        resp, body = self.post("snapshots/%s/action" % snapshot_id,
                               json.dumps(body), version=LATEST_MICROVERSION)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def get_snapshot_export_location(self, snapshot_id, export_location_uuid,
                                     version=LATEST_MICROVERSION):
        resp, body = self.get(
            "snapshots/%(snapshot_id)s/export-locations/%(el_uuid)s" % {
                "snapshot_id": snapshot_id, "el_uuid": export_location_uuid},
            version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_snapshot_export_locations(
            self, snapshot_id, version=LATEST_MICROVERSION):
        resp, body = self.get(
            "snapshots/%s/export-locations" % snapshot_id, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def get_message(self, message_id, version=LATEST_MICROVERSION):
        """Show details for a single message."""
        url = 'messages/%s' % message_id
        resp, body = self.get(url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_messages(self, params=None, version=LATEST_MICROVERSION):
        """List all messages."""
        url = 'messages'
        url += '?%s' % parse.urlencode(params) if params else ''
        resp, body = self.get(url, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_message(self, message_id, version=LATEST_MICROVERSION):
        """Delete a single message."""
        url = 'messages/%s' % message_id
        resp, body = self.delete(url, version=version)
        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)

###############

    def create_security_service(self, ss_type="ldap",
                                version=LATEST_MICROVERSION, **kwargs):
        """Creates Security Service.

        :param ss_type: ldap, kerberos, active_directory
        :param version: microversion string
        :param kwargs: name, description, dns_ip, server, ou, domain, user,
        :param kwargs: password
        """
        post_body = {"type": ss_type}
        post_body.update(kwargs)
        body = json.dumps({"security_service": post_body})
        resp, body = self.post("security-services", body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_security_service(self, ss_id, version=LATEST_MICROVERSION,
                                **kwargs):
        """Updates Security Service.

        :param ss_id: id of security-service entity
        :param version: microversion string
        :param kwargs: dns_ip, server, ou, domain, user, password, name,
        :param kwargs: description
        :param kwargs: for 'active' status can be changed
        :param kwargs: only 'name' and 'description' fields
        """
        body = json.dumps({"security_service": kwargs})
        resp, body = self.put("security-services/%s" % ss_id, body,
                              version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_security_service(self, ss_id, version=LATEST_MICROVERSION):
        resp, body = self.get("security-services/%s" % ss_id, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_security_services(self, detailed=False, params=None,
                               version=LATEST_MICROVERSION):
        uri = "security-services"
        if detailed:
            uri += '/detail'
        if params:
            uri += "?%s" % parse.urlencode(params)
        resp, body = self.get(uri, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def create_subnet(
            self, share_network_id, availability_zone=None,
            neutron_net_id=None, neutron_subnet_id=None):
        body = {'share_network_id': share_network_id}

        if availability_zone:
            body['availability_zone'] = availability_zone
        if neutron_net_id:
            body['neutron_net_id'] = neutron_net_id
        if neutron_subnet_id:
            body['neutron_subnet_id'] = neutron_subnet_id
        body = json.dumps({"share-network-subnet": body})
        url = '/share-networks/%s/subnets' % share_network_id
        resp, body = self.post(url, body, version=LATEST_MICROVERSION)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_subnet(self, share_network_subnet_id, share_network_id):
        url = ('share-networks/%(network)s/subnets/%(subnet)s' % {
            'network': share_network_id,
            'subnet': share_network_subnet_id}
        )
        resp, body = self.get(url)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_subnet(self, share_network_id, share_network_subnet_id):
        url = ('share-networks/%(network)s/subnets/%(subnet)s' % {
            'network': share_network_id,
            'subnet': share_network_subnet_id}
        )
        resp, body = self.delete(url)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def subnet_create_check(
        self, share_network_id, neutron_net_id=None,
        neutron_subnet_id=None, availability_zone=None,
        reset=False, version=LATEST_MICROVERSION):
        body = {
            'share_network_subnet_create_check': {
                'neutron_net_id': neutron_net_id,
                'neutron_subnet_id': neutron_subnet_id,
                'availability_zone': availability_zone,
                'reset': reset,
            }
        }

        body = json.dumps(body)
        resp, body = self.post(
            f'share-networks/{share_network_id}/action',
            body, headers=EXPERIMENTAL, extra_headers=True,
            version=version)
        self.expected_success(202, resp.status)

        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

###############

    def share_server_migration_check(
        self, share_server_id, host, writable=False,
        preserve_snapshots=False, nondisruptive=False,
        new_share_network_id=None, version=LATEST_MICROVERSION):
        body = {
            'migration_check': {
                'host': host,
                'writable': writable,
                'preserve_snapshots': preserve_snapshots,
                'nondisruptive': nondisruptive,
                'new_share_network_id': new_share_network_id,
            }
        }

        body = json.dumps(body)
        resp, body = self.post('share-servers/%s/action' % share_server_id,
                               body, headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        self.expected_success(200, resp.status)

        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def share_server_migration_start(self, share_server_id, host,
                                     writable=False, new_share_network_id=None,
                                     preserve_snapshots=False,
                                     nondisruptive=False,
                                     version=LATEST_MICROVERSION):
        body = {
            'migration_start': {
                'host': host,
                'writable': writable,
                'preserve_snapshots': preserve_snapshots,
                'nondisruptive': nondisruptive,
                'new_share_network_id': new_share_network_id,
            }
        }

        body = json.dumps(body)
        resp, body = self.post('share-servers/%s/action' % share_server_id,
                               body, headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        self.expected_success(202, resp.status)

        return rest_client.ResponseBody(resp, body)

    def share_server_migration_complete(self, share_server_id,
                                        version=LATEST_MICROVERSION):
        body = {
            'migration_complete': None
        }

        body = json.dumps(body)
        resp, body = self.post('share-servers/%s/action' % share_server_id,
                               body, headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        self.expected_success(200, resp.status)

        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def share_server_migration_cancel(self, share_server_id,
                                      version=LATEST_MICROVERSION):
        body = {
            'migration_cancel': None
        }

        body = json.dumps(body)
        resp, body = self.post('share-servers/%s/action' % share_server_id,
                               body, headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        self.expected_success(202, resp.status)

        return rest_client.ResponseBody(resp, body)

    def share_server_migration_get_progress(self, share_server_id,
                                            version=LATEST_MICROVERSION):
        body = {
            'migration_get_progress': None
        }

        body = json.dumps(body)
        resp, body = self.post('share-servers/%s/action' % share_server_id,
                               body, headers=EXPERIMENTAL, extra_headers=True,
                               version=version)
        self.expected_success(200, resp.status)

        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

#################

    def _update_metadata(self, resource, resource_id, metadata=None,
                         method="post", parent_resource=None, parent_id=None):
        if parent_resource is None:
            uri = f'{resource}s/{resource_id}/metadata'
        else:
            uri = (f'{parent_resource}/{parent_id}'
                   f'/{resource}s/{resource_id}/metadata')
        if metadata is None:
            metadata = {}
        post_body = {"metadata": metadata}
        body = json.dumps(post_body)
        if method == "post":
            resp, body = self.post(uri, body)
        if method == "put":
            resp, body = self.put(uri, body)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def set_metadata(self, resource_id, metadata=None, resource='share',
                     parent_resource=None, parent_id=None):
        return self._update_metadata(resource, resource_id, metadata,
                                     method="post",
                                     parent_resource=parent_resource,
                                     parent_id=parent_id)

    def update_all_metadata(self, resource_id, metadata=None,
                            resource='share', parent_resource=None,
                            parent_id=None):
        return self._update_metadata(resource, resource_id, metadata,
                                     method="put",
                                     parent_resource=parent_resource,
                                     parent_id=parent_id)

    def delete_metadata(self, resource_id, key, resource='share',
                        parent_resource=None, parent_id=None):
        if parent_resource is None:
            uri = f'{resource}s/{resource_id}/metadata/{key}'
        else:
            uri = (f'{parent_resource}/{parent_id}'
                   f'/{resource}s/{resource_id}/metadata/{key}')
        resp, body = self.delete(uri)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def get_metadata(self, resource_id, resource='share',
                     parent_resource=None, parent_id=None):
        if parent_resource is None:
            uri = f'{resource}s/{resource_id}/metadata'
        else:
            uri = (f'{parent_resource}/{parent_id}'
                   f'/{resource}s/{resource_id}/metadata')
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_metadata_item(self, resource_id, key, resource='share',
                          parent_resource=None, parent_id=None):
        if parent_resource is None:
            uri = f'{resource}s/{resource_id}/metadata/{key}'
        else:
            uri = (f'{parent_resource}/{parent_id}'
                   f'/{resource}s/{resource_id}/metadata/{key}')
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

#################

    def create_resource_lock(self, resource_id, resource_type,
                             resource_action='delete', lock_reason=None,
                             version=LATEST_MICROVERSION):
        body = {
            "resource_lock": {
                'resource_id': resource_id,
                'resource_type': resource_type,
                'resource_action': resource_action,
                'lock_reason': lock_reason,
            },
        }
        body = json.dumps(body)
        resp, body = self.post("resource-locks", body, version=version)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def get_resource_lock(self, lock_id, version=LATEST_MICROVERSION):
        resp, body = self.get("resource-locks/%s" % lock_id, version=version)

        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def list_resource_locks(self, filters=None, version=LATEST_MICROVERSION):
        uri = (
            "resource-locks?%s" % parse.urlencode(filters)
            if filters else "resource-locks"
        )

        resp, body = self.get(uri, version=version)

        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def update_resource_lock(self,
                             lock_id,
                             resource_action=None,
                             lock_reason=None,
                             version=LATEST_MICROVERSION):
        uri = 'resource-locks/%s' % lock_id
        post_body = {}
        if resource_action:
            post_body['resource_action'] = resource_action
        if lock_reason:
            post_body['lock_reason'] = lock_reason
        body = json.dumps({'resource_lock': post_body})

        resp, body = self.put(uri, body, version=version)

        self.expected_success(200, resp.status)
        body = json.loads(body)
        return rest_client.ResponseBody(resp, body)

    def delete_resource_lock(self, lock_id, version=LATEST_MICROVERSION):
        uri = "resource-locks/%s" % lock_id

        resp, body = self.delete(uri, version=version)

        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)
