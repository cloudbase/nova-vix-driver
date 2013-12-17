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
import subprocess
import sys

if sys.platform == 'win32':
    import _winreg
    import win32api

from vix import disk_manager
from vix import vixutils
from vix import utils


class DiskManagerTestCase(unittest.TestCase):
    """Unit tests for the DiskManager class"""

    def setUp(self):
        self._disk_manager = disk_manager.DiskManager()

    @mock.patch('vix.vixutils.get_vix_bin_path')
    def _test_get_vdisk_man_path(self, mock_get_vix_bin_path, platform_win32):

        fake_vdisk_man_path = 'fake/path'
        fake_vix_result = mock.MagicMock()
        os.path.join = mock.MagicMock()
        os.path.join.return_value = fake_vdisk_man_path
        mock_get_vix_bin_path.return_value = fake_vix_result
        if platform_win32:
            sys.platform = 'win32'
            fake_vdisk_man_path += ".exe"
        else:
            sys.platform = 'not_win32'

        response = self._disk_manager._get_vdisk_man_path()
        vixutils.get_vix_bin_path.assert_called_once()
        os.path.join.assert_called_with(fake_vix_result, 'vmware-vdiskmanager')
        self.assertEqual(response, fake_vdisk_man_path)

    def test_get_vdisk_man_path(self):
        self._test_get_vdisk_man_path(platform_win32=False)

    def test_get_vdisk_man_path_win32(self):
        self._test_get_vdisk_man_path(platform_win32=True)

    @mock.patch('vix.vixutils.get_vix_bin_path')
    def test_check_vdisk_man_exists(self, mock_get_vix_bin_path):
        os.path.join = mock.MagicMock()
        fake_check_vdisk_man_exists = mock.MagicMock()
        self._disk_manager._get_vdisk_man_path = mock.MagicMock()
        fake_vdisk_man = mock.MagicMock()
        self._disk_manager._get_vdisk_man_path.return_value = fake_vdisk_man
        os.path.exists = mock.MagicMock()
        os.path.exists.return_value = fake_check_vdisk_man_exists

        response = self._disk_manager._check_vdisk_man_exists()
        self.assertEqual(response, fake_check_vdisk_man_exists)
        self._disk_manager._get_vdisk_man_path.assert_called_once()
        os.path.exists.assert_called_with(fake_vdisk_man)

    def test_create_disk_vdisk_man(self):
        self._disk_manager._get_vdisk_man_path = mock.MagicMock()
        fake_vdisk_man = 'fake/path'
        self._disk_manager._get_vdisk_man_path.return_value = fake_vdisk_man
        fake_size_mb = "1"
        fake_disk_path = "fake/disk/path"
        fake_args = [fake_vdisk_man, "-c", "-s", "%sMB" % fake_size_mb,
                     "-a", "lsilogic", "-t", "0", fake_disk_path]
        self._disk_manager._exec_cmd = mock.MagicMock()

        self._disk_manager._create_disk_vdisk_man(fake_disk_path, fake_size_mb)
        self._disk_manager._get_vdisk_man_path.assert_called_once()
        self._disk_manager._exec_cmd.assert_called_with(fake_args)

    def _test_exec_cmd(self, exception=False):
        fake_args = 'fake args'
        fake_process = mock.MagicMock()
        subprocess.Popen = mock.MagicMock()
        subprocess.Popen.return_value = fake_process
        fake_process.communicate = mock.MagicMock()
        fake_out = mock.MagicMock()
        fake_error = mock.MagicMock()
        fake_process.communicate = mock.MagicMock()
        fake_process.communicate.return_value = (fake_out, fake_error)
        fake_process.returncode = exception

        if exception:
            self.assertRaises(utils.VixException, self._disk_manager._exec_cmd,
                              fake_args)
        else:
            response = self._disk_manager._exec_cmd(fake_args)
            self.assertEqual(response, (fake_out, fake_error))

        fake_process.Popen.assert_called_once()
        fake_process.communicate.assert_called_once()

    def test_exec_cmd(self):
        self._test_exec_cmd()

    def test_exec_cmd_exception(self):
        self._test_exec_cmd(True)

    def _test_get_disk_info(self, exception=False):
        fake_disk_path = "disk\path"
        fake_args = ["qemu-img", "info", fake_disk_path]
        fake_format = 'qcow2'
        fake_internal_size = 21474836480
        fake_out = mock.MagicMock()
        fake_err = mock.MagicMock()
        self._disk_manager._exec_cmd = mock.MagicMock()
        self._disk_manager._exec_cmd.return_value = fake_out, fake_err
        fake_file_size = mock.MagicMock()
        fake_out.split = mock.MagicMock()
        fake_out.split.return_value = [
            'file format: qcow2', 'virtual size: 20G (21474836480 bytes)']
        os.path.getsize = mock.MagicMock()
        os.path.getsize.return_value = fake_file_size

        if exception:
            fake_out.split.return_value = ['file format: qcow2']
            self.assertRaises(utils.VixException,
                              self._disk_manager.get_disk_info,
                              fake_disk_path)
        else:
            response = self._disk_manager.get_disk_info(fake_disk_path)
            self.assertEqual(response, (fake_format, fake_internal_size,
                                        fake_file_size))
            os.path.getsize.assert_called_with(fake_disk_path)

        self._disk_manager._exec_cmd.assert_called_with(fake_args)
        fake_out.split.assert_called_with(os.linesep)

    def test_get_disk_info(self):
        self._test_get_disk_info()

    def test_get_disk_info_exception(self):
        self._test_get_disk_info(exception=True)

    def test_create_disk_qemu(self):
        fake_disk_type = "disk type"
        fake_disk_path = "disk_path"
        fake_size_mb = "1"
        fake_args = ["qemu-img", "create", "-f", fake_disk_type,
                     fake_disk_path, "%sM" % fake_size_mb]
        self._disk_manager._exec_cmd = mock.MagicMock()

        self._disk_manager._create_disk_qemu(fake_disk_path, fake_size_mb,
                                             fake_disk_type)
        self._disk_manager._exec_cmd.assert_called_with(fake_args)

    def _test_create_disk(self, disk_exists=True):
        fake_disk_type = disk_manager.DISK_TYPE_VMDK
        fake_disk_path = "disk_path"
        fake_size_mb = "1"
        self._disk_manager._check_vdisk_man_exists = mock.MagicMock()
        self._disk_manager._check_vdisk_man_exists.return_value = disk_exists
        if disk_exists:
            self._disk_manager._create_disk_vdisk_man = mock.MagicMock()
            self._disk_manager.create_disk(fake_disk_path, fake_size_mb,
                                           fake_disk_type)
            self._disk_manager._create_disk_vdisk_man.assert_called_with(
                fake_disk_path, fake_size_mb)
        else:
            self._disk_manager._create_disk_qemu = mock.MagicMock()
            self._disk_manager.create_disk(fake_disk_path, fake_size_mb,
                                           fake_disk_type)
            self._disk_manager._create_disk_qemu.assert_called_with(
                fake_disk_path, fake_size_mb, fake_disk_type)

    def test_create_disk_with_vdisk_man(self):
        self._test_create_disk()

    def test_create_disk_with_qemu(self):
        self._test_create_disk()

    def test_resize_disk_vdisk_man(self):
        fake_disk_path = "disk_path"
        fake_new_size_mb = "1"
        fake_vdisk_man = "disk_path_man"
        self._disk_manager._get_vdisk_man_path = mock.MagicMock()
        self._disk_manager._get_vdisk_man_path.return_value = fake_vdisk_man
        fake_args = [fake_vdisk_man, "-x", "%sMB" % fake_new_size_mb,
                     fake_disk_path]
        self._disk_manager._exec_cmd = mock.MagicMock()

        self._disk_manager._resize_disk_vdisk_man(fake_disk_path,
                                                  fake_new_size_mb)
        self._disk_manager._exec_cmd.assert_called_with(fake_args)
        self._disk_manager._get_vdisk_man_path.assert_called_once()

    def _test_resize_disk_vdisk_qemu(self, path_exists=True, exception=False):
        fake_new_disk_type = disk_manager.DISK_TYPE_VMDK
        fake_disk_path = "disk_path"
        fake_new_size_mb = "1"
        fake_tmp_disk_path = "%s.raw" % fake_disk_path
        os.path.exists = mock.MagicMock()
        os.path.exists.return_value = path_exists
        os.remove = mock.MagicMock()

        fake_args_3 = ["qemu-img", "convert", "-f", disk_manager.DISK_TYPE_RAW,
                       "-O", fake_new_disk_type, fake_tmp_disk_path,
                       fake_disk_path]
        self._disk_manager._exec_cmd = mock.MagicMock()

        if exception:
            self._disk_manager._exec_cmd.side_effect = Exception
            self.assertRaises(Exception, self._disk_manager._resize_disk_qemu,
                              fake_disk_path, fake_new_size_mb,
                              fake_new_disk_type)
        else:
            self._disk_manager._resize_disk_qemu(fake_disk_path,
                                                 fake_new_size_mb,
                                                 fake_new_disk_type)
            self._disk_manager._exec_cmd.assert_called_with(fake_args_3)

        os.path.exists.assert_called_with(fake_tmp_disk_path)
        if path_exists:
            os.remove.assert_called_with(fake_tmp_disk_path)

    def test_resize_disk_vdisk_qemu_path_exists(self):
        self._test_resize_disk_vdisk_qemu()

    def test_resize_disk_vdisk_qemu_path_does_not_exist(self):
        self._test_resize_disk_vdisk_qemu(False)

    def test_resize_disk_vdisk_qemu_path_exists_with_exception(self):
        self._test_resize_disk_vdisk_qemu(exception=True)

    def _test_resize_disk(self, disk_exists=True):
        fake_new_disk_type = disk_manager.DISK_TYPE_VMDK
        fake_disk_path = "disk_path"
        fake_new_size_mb = "1"
        self._disk_manager._check_vdisk_man_exists = mock.MagicMock()
        self._disk_manager._check_vdisk_man_exists.return_value = disk_exists
        if disk_exists:
            self._disk_manager._resize_disk_vdisk_man = mock.MagicMock()
            self._disk_manager.resize_disk(fake_disk_path, fake_new_size_mb,
                                           fake_new_disk_type)
            self._disk_manager._resize_disk_vdisk_man.assert_called_with(
                fake_disk_path, fake_new_size_mb)
        else:
            self._disk_manager._resize_disk_qemu = mock.MagicMock()
            self._disk_manager.resize_disk(fake_disk_path, fake_new_size_mb,
                                           fake_new_disk_type)
            self._disk_manager._resize_disk_qemu.assert_called_with(
                fake_disk_path, fake_new_size_mb, fake_new_disk_type)

    def test_resize_disk(self):
        self._test_resize_disk()

    def test_resize_disku(self):
        self._test_resize_disk()
