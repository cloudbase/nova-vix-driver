# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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
"""
Image caching and management.
"""
import os

from nova.compute import flavors
from nova.image import glance
from nova.openstack.common import excutils
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova import utils
from nova.virt import images
from oslo.config import cfg

from vix.compute import pathutils

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('use_cow_images', 'nova.virt.driver')


class ImageCache(object):
    def __init__(self):
        self._pathutils = pathutils.PathUtils()

    def get_image_info(self, context, image_id):
        (image_service, image_id) = glance.get_remote_image_service(context,
                                                                    image_id)
        return image_service.show(context, image_id)

    def get_cached_image(self, context, image_id, user_id, project_id):
        base_vmdk_dir = self._pathutils.get_base_vmdk_dir()
        vmdk_path = os.path.join(base_vmdk_dir, image_id + ".vmdk")

        @utils.synchronized(vmdk_path)
        def fetch_image_if_not_existing():
            if not self._pathutils.exists(vmdk_path):
                try:
                    images.fetch(context, image_id, vmdk_path,
                                 user_id, project_id)
                except Exception:
                    with excutils.save_and_reraise_exception():
                        if self._pathutils.exists(vmdk_path):
                            self._pathutils.remove(vmdk_path)

            return vmdk_path

        return fetch_image_if_not_existing()
