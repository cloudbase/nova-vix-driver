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

import mock
import os
import unittest
import sys
if sys.platform == 'win32':
    import _winreg
    import win32api
from nova.image import glance
from nova.openstack.common import excutils
from nova.virt import images
from vix.compute import image_cache
from vix.compute import pathutils


class VixUtilsTestCase(unittest.TestCase):
    """Unit tests for utility class"""

    def setUp(self):
        self._image_cache = image_cache.ImageCache()
        self._pathutils = pathutils.PathUtils()

    def test_get_image_info(self):
        fake_context = mock.MagicMock()
        fake_image_service = mock.MagicMock()
        fake_image_id = "1"
        glance.get_remote_image_service = mock.MagicMock()
        glance.get_remote_image_service.return_value = \
            (fake_image_service, fake_image_id)

        response = self._image_cache.get_image_info(fake_context,
                                                    fake_image_id)

        glance.get_remote_image_service.assert_called_with(fake_context,
                                                           fake_image_id)
        self.assertEqual(response, fake_image_service.show(fake_context,
                                                           fake_image_id))
        fake_image_service.show.assert_called_with(fake_context, fake_image_id)

    def test_save_glance_image(self):
        fake_context = mock.MagicMock()
        fake_name = mock.MagicMock()
        fake_image_vmdk_path = mock.MagicMock()
        fake_image_metadata = {"is_public": False,
                               "disk_format": "vmdk",
                               "container_format": "bare",
                               "properties": {}}
        fake_glance_image_service = mock.MagicMock()
        fake_image_id = mock.MagicMock()

        glance.get_remote_image_service = mock.MagicMock(
            return_value=(fake_glance_image_service, fake_image_id))
        fake_glance_image_service.update = mock.MagicMock()

        with mock.patch('vix.compute.image_cache.open',
                        mock.mock_open(read_data='fake data'),
                        create=True) as m:
            self._image_cache.save_glance_image(fake_context, fake_name,
                                                fake_image_vmdk_path)
            fake_glance_image_service.update.assert_called_with(
                fake_context, fake_image_id, fake_image_metadata, m())

        glance.get_remote_image_service.assert_called_with(fake_context,
                                                           fake_name)

    def _test_get_cached_image(self, image_exists, exception=False,
                               image_path_exists=False):
        fake_context = mock.MagicMock()
        fake_image_id = mock.MagicMock()
        fake_user_id = mock.MagicMock()
        fake_project_id = mock.MagicMock()
        fake_disk_format = mock.MagicMock()
        fake_image_info = mock.MagicMock()
        fake_image_path = mock.MagicMock()
        fake_base_vmdk_dir = mock.MagicMock()
        self._image_cache.get_image_info = mock.MagicMock()
        self._image_cache.get_image_info.return_value = fake_image_info
        fake_image_info.get = mock.MagicMock()
        fake_image_info.get.return_value = fake_disk_format

        self._image_cache._pathutils.exists = mock.MagicMock()
        self._image_cache._pathutils.exists.return_value = image_exists
        self._image_cache._pathutils.get_base_vmdk_dir = mock.MagicMock(
            return_value=fake_base_vmdk_dir)

        os.path.join = mock.MagicMock()
        os.path.join.return_value = fake_image_path

        images.fetch = mock.MagicMock()
        if not image_exists:
            if exception:
                excutils.save_and_reraise_exception = mock.MagicMock()
                excutils.save_and_reraise_exception.side_effect = Exception
                images.fetch.side_effect = Exception
                self.assertRaises(Exception,
                                  self._image_cache.get_cached_image,
                                  fake_context, fake_image_id, fake_user_id,
                                  fake_project_id)
            else:
                response = self._image_cache.get_cached_image(
                    fake_context, fake_image_id, fake_user_id, fake_project_id)
                self.assertEqual(response, fake_image_path)
                #It cannot go here unless it s a race - this fails
            images.fetch.assert_called_with(fake_context, fake_image_id,
                                            fake_image_path, fake_user_id,
                                            fake_project_id)
        else:
            response = self._image_cache.get_cached_image(fake_context,
                                                          fake_image_id,
                                                          fake_user_id,
                                                          fake_project_id)
            self.assertEqual(response, fake_image_path)

        self._image_cache._pathutils.exists.assert_called_with(
            fake_image_path)
        self._image_cache.get_image_info.assert_called_with(fake_context,
                                                            fake_image_id)
        fake_image_info.get.assert_called_with("disk_format")
        self._image_cache._pathutils.get_base_vmdk_dir.assert_called_once()
        os.path.join.assert_called_with(fake_base_vmdk_dir,
                                        fake_image_id + "." + fake_disk_format)

    def test_get_cached_image_existent(self):
        self._test_get_cached_image(True)

    def test_get_cached_image_not_existent(self):
        self._test_get_cached_image(False)

    def test_get_cached_image_not_existent_and_exception(self):
        self._test_get_cached_image(False, True)

    def test_get_cached_image_not_existent_and_path_exists(self):
        self._test_get_cached_image(False, True, True)
