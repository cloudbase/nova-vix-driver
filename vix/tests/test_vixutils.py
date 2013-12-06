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
import re
import unittest
import sys

if sys.platform == 'win32':
    import _winreg
    import win32api

from vix import utils
from vix import vixutils
from vix import vixlib


class VixUtilsTestCase(unittest.TestCase):
    """Unit tests for utility class"""

    def test_check_job_err_code(self):
        fake_err = 1
        vixlib.Vix_GetErrorText = mock.MagicMock()

        self.assertRaises(utils.VixException, vixutils._check_job_err_code,
                          fake_err)

    def test_load_config_file_values(self):
        fake_path = 'fake/path'
        match_mock = mock.MagicMock()

        re.match = mock.MagicMock()
        re.match.return_value = match_mock

        with mock.patch('vix.vixutils.open',
                        mock.mock_open(read_data='fake data'),
                        create=True) as m:
            response = vixutils.load_config_file_values(fake_path)
            print m.mock_calls
            m.assert_called_with('fake/path', 'rb')
            m().readlines.assert_called_once()

        self.assertTrue(response is not None)

    def _test_get_player_preferences_file_path(self, platform):
        sys.platform = platform
        os.getenv = mock.MagicMock()
        os.getenv.return_value = 'APPDATA'
        os.path.join = mock.MagicMock()
        os.path.join.return_value = 'APPDATA/VMWare/preferences.ini'
        os.path.expanduser = mock.MagicMock()
        os.path.expanduser.return_value = "~/.vmware/preferences"

        response = vixutils._get_player_preferences_file_path()

        if platform == "win32":
            os.getenv.assert_called_with('APPDATA')
            os.path.join.assert_called_with('APPDATA', "VMWare",
                                            "preferences.ini")
            self.assertEqual(response, 'APPDATA/VMWare/preferences.ini')
        else:
            os.path.expanduser.assert_called_with("~/.vmware/preferences")
            self.assertEqual(response, "~/.vmware/preferences")

    def test_get_player_preferences_file_path_win(self):
        self._test_get_player_preferences_file_path('win32')

    def test_get_player_preferences_file_path_darwin(self):
        self._test_get_player_preferences_file_path('linux')

    def _test_get_install_dir(self, platform):
        fake_key = mock.MagicMock()
        fake_query_response = mock.MagicMock()

        sys.platform = platform
        _winreg.OpenKey = mock.MagicMock()
        _winreg.OpenKey.return_value = fake_key
        _winreg.QueryValueEx = mock.MagicMock()
        _winreg.QueryValueEx.return_value = fake_query_response

        if platform == "darwin":
            response = vixutils._get_install_dir()
            self.assertEqual(response, "/Applications/VMware Fusion.app")
        elif platform == "win32":
            response = vixutils._get_install_dir()
            _winreg.OpenKey.assert_called_with(
                _winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\VMware, Inc.\VMware "
                                            "Workstation")
            _winreg.QueryValueEx.assert_called_with(fake_key.__enter__(),
                                                    "InstallPath")
            self.assertEqual(response, fake_query_response[0])
        else:
            self.assertRaises(NotImplementedError, vixutils._get_install_dir)

    def test_get_install_dir_win(self):
        self._test_get_install_dir(platform="win32")

    def test_get_install_dir_darwin(self):
        self._test_get_install_dir(platform="darwin")

    def test_get_install_dir_other(self):
        self._test_get_install_dir(platform=None)

    @mock.patch('vix.vixutils._get_install_dir')
    def _test_get_vix_bin_path(self, platform, mock_get_install_dir):
        sys.platform = platform

        os.path.join = mock.MagicMock()
        os.path.join.return_value = 'fake/path/' + 'Contents/Library'
        response = vixutils.get_vix_bin_path()
        if platform == "darwin":
            self.assertEqual(response, os.path.join(mock_get_install_dir(),
                                                    "Contents/Library"))
        elif platform == "win32":
            os.path.join.assert_called_once()
            self.assertEqual(response, mock_get_install_dir())
        else:
            response = vixutils.get_vix_bin_path()
            self.assertEqual(response, "/usr/bin")

    def test_get_vix_bin_path_win(self):
        self._test_get_vix_bin_path("win32")

    def test_get_vix_bin_path_darwin(self):
        self._test_get_vix_bin_path("darwin")

    def test_get_vix_bin_path_other(self):
        self._test_get_vix_bin_path('linux')

    def test_remove_vmx_value(self):
        fake_path = 'fake/path'
        fake_name = 'fake_name'
        utils.remove_lines = mock.MagicMock()
        vixutils.remove_vmx_value(fake_path, fake_name)
        utils.remove_lines.assert_called_with(fake_path,
                                              r"^%s\s*=\s*.*$" % fake_name)

    def test_set_vmx_value(self):
        fake_path = 'fake/path'
        fake_name = 'fake_name'
        fake_value = 'fake_value'
        utils.replace_text = mock.MagicMock()
        utils.replace_text.return_value = False
        with mock.patch('vix.vixutils.open', mock.mock_open(),
                        create=True) as m:

            vixutils.set_vmx_value(fake_path, fake_name, fake_value)

            m.assert_called_with(fake_path, "ab")
            m().write.assert_called_with(
                "%(name)s = \"%(value)s\"" %
                {'name': fake_name, 'value': fake_value} + os.linesep)
        utils.replace_text.assert_called_with(
            fake_path, r"^(%s\s*=\s*)(.*)$" % fake_name,
            "\\1\"%s\"" % fake_value)

    def test_get_vmx_value(self):
        fake_path = 'fake/path'
        fake_name = 'fake_name'
        pattern = r"^%s\s*=\s*\"(.*)\"$" % fake_name
        fake_value = mock.MagicMock()

        utils.get_text = mock.MagicMock()
        utils.get_text.return_value = fake_value
        response = vixutils.get_vmx_value(fake_path, fake_name)
        utils.get_text.assert_called_with(fake_path,
                                          pattern)
        self.assertEqual(response, fake_value[0])

    @mock.patch('vix.vixutils.get_vmx_value')
    def _test_get_vix_host_type(self, mock_get_vmx_value,
                                platform,
                                path_exists=False,
                                fake_key=None, product_name=None):
        fake_value = mock.MagicMock()
        sys.platform = platform

        os.path.exists = mock.MagicMock()
        os.path.exists.return_value = path_exists

        _winreg.EnumValue = mock.MagicMock()
        _winreg.EnumValue.return_value = fake_value
        _winreg.QueryValueEx = mock.MagicMock()
        _winreg.QueryValueEx.return_value = product_name

        if platform == 'darwin' and path_exists:
            vixutils._host_type = None
            response = vixutils.get_vix_host_type()
            os.path.exists.assert_called_with(
                "/Applications/VMware Fusion.app")
            self.assertEqual(response,
                             vixlib.VIX_SERVICEPROVIDER_VMWARE_WORKSTATION)

        elif platform == 'win32' and fake_key is not None:
            vixutils._host_type = None
            response = vixutils.get_vix_host_type()
            _winreg.OpenKey = mock.MagicMock(return_value=fake_key)
            print response
            self.assertEqual(_winreg.OpenKey.call_count, 2)
            _winreg.EnumValue.assert_called_with(fake_key, 0)
            _winreg.QueryValueEx.assert_called_with(fake_key, "ProductName")
            self.assertEqual(response, product_name)

        elif platform == 'linux' and product_name == "VMware Player":
            vixutils._host_type = None
            mock_get_vmx_value.return_value = product_name
            response = vixutils.get_vix_host_type()
            print response
            self.assertEqual(response, 3)

    def test_get_vix_host_darwin_path_exists(self):
        self._test_get_vix_host_type('darwin', path_exists=True)

    def test_get_vix_host_win(self):
        fake_key = mock.MagicMock()
        self._test_get_vix_host_type('win32', fake_key=fake_key,
                                     path_exists=True,
                                     product_name="VMware Player")

    def test_get_vix_host_other_VMware_player(self):
        self._test_get_vix_host_type('linux', path_exists=True,
                                     product_name="VMware Player")
