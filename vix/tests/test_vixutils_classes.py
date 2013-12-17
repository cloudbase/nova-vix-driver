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

import ctypes
import mock
import os
import re
import unittest
import shutil
import sys
import time

if sys.platform == 'win32':
    import _winreg
    import win32api

from vix import vixutils
from vix import vixlib


class VixUtilsTestCase(unittest.TestCase):
    """Unit tests for utility class"""

    def setUp(self):
        self.ctypes_handle = mock.MagicMock()
        self._VixVM = vixutils.VixVM(self.ctypes_handle)
        self._VixSnapshot = vixutils.VixSnapshot(self.ctypes_handle)
        self._VixConnection = vixutils.VixConnection()

    ########### TESTING VixVM CLASS ###########
    def test_close_VixVM(self):
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.close()

        vixlib.Vix_ReleaseHandle.assert_called_once()
        self.assertIsNone(self._VixVM._vm_handle)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_get_power_state(self, mock_check_job_err_code):
        fake_power_state = mock.MagicMock()
        ctypes_mock = mock.Mock()
        ctypes.c_int = mock.MagicMock()
        ctypes.c_int.return_value = fake_power_state
        vixlib.Vix_GetProperties = mock.MagicMock()
        vixlib.Vix_GetProperties.return_value = None
        ctypes.byref = mock.MagicMock()
        ctypes.byref.return_value = ctypes_mock

        self._VixVM.get_power_state()

        vixlib.Vix_GetProperties.assert_called_with(
            self._VixVM._vm_handle, vixlib.VIX_PROPERTY_VM_POWER_STATE,
            ctypes_mock, vixlib.VIX_PROPERTY_NONE)
        ctypes.byref.assert_called_once()
        mock_check_job_err_code.assert_called_once_with(None)

    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_power_on(self, show_gui, mock_check_job_err_code):
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_PowerOn = mock.MagicMock()
        vixlib.VixVM_PowerOn.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.power_on(show_gui)
        if show_gui:
            options = vixlib.VIX_VMPOWEROP_LAUNCH_GUI
        else:
            options = vixlib.VIX_VMPOWEROP_NORMAL
        vixlib.VixVM_PowerOn.assert_called_with(self._VixVM._vm_handle,
                                                options,
                                                vixlib.VIX_INVALID_HANDLE,
                                                None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_once_with(None)

    def test_power_on_with_gui(self):
        self._test_power_on(True)

    def test_power_on_without_gui(self):
        self._test_power_on(False)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_pause(self, mock_check_job_err_code):
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_Pause = mock.MagicMock()
        vixlib.VixVM_Pause.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.pause()

        vixlib.VixVM_Pause.assert_called_with(self._VixVM._vm_handle, 0,
                                              vixlib.VIX_INVALID_HANDLE,
                                              None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_once_with(None)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_unpause(self, mock_check_job_err_code):
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_Unpause = mock.MagicMock()
        vixlib.VixVM_Unpause.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.unpause()

        vixlib.VixVM_Unpause.assert_called_with(self._VixVM._vm_handle, 0,
                                                vixlib.VIX_INVALID_HANDLE,
                                                None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_once_with(None)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_suspend(self, mock_check_job_err_code):
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_Suspend = mock.MagicMock()
        vixlib.VixVM_Suspend.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.suspend()

        vixlib.VixVM_Suspend.assert_called_with(self._VixVM._vm_handle, 0,
                                                None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_once_with(None)

    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_reboot(self, soft, mock_check_job_err_code):
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_Reset = mock.MagicMock()
        vixlib.VixVM_Reset.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.reboot(soft)

        if soft:
            power_op = vixlib.VIX_VMPOWEROP_FROM_GUEST
        else:
            power_op = vixlib.VIX_VMPOWEROP_NORMAL

        vixlib.VixVM_Reset.assert_called_with(self._VixVM._vm_handle,
                                              power_op,
                                              None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_once_with(None)

    def test_reboot_soft(self):
        self._test_reboot(True)

    def test_reboot_hard(self):
        self._test_reboot(False)

    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_power_off(self, soft, mock_check_job_err_code):
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_PowerOff = mock.MagicMock()
        vixlib.VixVM_PowerOff.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.power_off(soft)

        if soft:
            power_op = vixlib.VIX_VMPOWEROP_FROM_GUEST
        else:
            power_op = vixlib.VIX_VMPOWEROP_NORMAL

        vixlib.VixVM_PowerOff.assert_called_with(self._VixVM._vm_handle,
                                                 power_op, None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_once_with(None)

    def test_power_off_soft(self):
        self._test_reboot(True)

    def test_power_off_hard(self):
        self._test_reboot(False)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_wait_for_tools_in_guest(self, mock_check_job_err_code):
        timeout_seconds = 99999
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_WaitForToolsInGuest = mock.MagicMock()
        vixlib.VixVM_WaitForToolsInGuest.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.wait_for_tools_in_guest(timeout_seconds)

        vixlib.VixVM_WaitForToolsInGuest.assert_called_with(
            self._VixVM._vm_handle, timeout_seconds, None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_once_with(None)

    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_get_guest_ip_address(self, mock_check_job_err_code):
        #1)ALWAYS time.sleep(3)

        #2)cannot mock time.time()
        #need something like testfixtures or another repository

        fake_job_handle = mock.MagicMock()
        read_value = mock.MagicMock()
        ctypes_byref_mock = mock.MagicMock()
        fake_ip = '10.10.10.10'

        vixlib.VixVM_WaitForToolsInGuest = mock.MagicMock()
        vixlib.VixVM_ReadVariable = mock.MagicMock()
        vixlib.VixVM_ReadVariable.return_value = fake_job_handle
        ctypes.c_char_p = mock.MagicMock()
        ctypes.c_char_p.return_value = read_value
        read_value.value = mock.MagicMock()
        read_value.value.return_value = fake_ip
        ctypes.byref = mock.MagicMock()
        ctypes.byref.return_value = ctypes_byref_mock
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()
        vixlib.Vix_FreeBuffer = mock.MagicMock()

        response = self._VixVM.get_guest_ip_address()

        vixlib.Vix_FreeBuffer.assert_called_with(read_value)
        vixlib.VixVM_WaitForToolsInGuest.assert_called_with(
            self._VixVM._vm_handle, 600, None, None)
        time.time.assert_called_once()
        vixlib.VixVM_ReadVariable.assert_called_with(
            self._VixVM._vm_handle, vixlib.VIX_VM_GUEST_VARIABLE, "ip", 0,
            None, None)
        vixlib.VixJob_Wait.assert_called_with(
            fake_job_handle,
            vixlib.VIX_PROPERTY_JOB_RESULT_VM_VARIABLE_STRING,
            ctypes_byref_mock, vixlib.VIX_PROPERTY_NONE)
        ctypes.byref.assert_called_with(read_value)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_with(None)
        self.assertEqual(response, read_value.value)

    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_delete(self, mock_check_job_err_code, delete_disk_files):
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_Delete = mock.MagicMock()
        vixlib.VixVM_Delete.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.delete(delete_disk_files)

        if delete_disk_files:
            delete_options = vixlib.VIX_VMDELETE_DISK_FILES
        else:
            delete_options = 0

        vixlib.VixVM_Delete.assert_called_with(self.ctypes_handle,
                                               delete_options, None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        self.assertEqual(vixlib.Vix_ReleaseHandle.call_count, 2)
        mock_check_job_err_code.assert_called_once_with(None)

    def test_delete_disk_files_True(self):
        self._test_delete(delete_disk_files=True)

    def test_delete_disk_files_False(self):
        self._test_delete(delete_disk_files=False)

    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_create_snapshot(self, mock_check_job_err_code, include_memory):
        fake_job_handle = mock.MagicMock()
        fake_name = 'fake name'
        fake_description = 'fake description'
        fake_snapshot_handle = mock.MagicMock()
        ctypes_byref_mock = mock.MagicMock()

        vixlib.VixVM_CreateSnapshot = mock.MagicMock()
        vixlib.VixVM_CreateSnapshot.return_value = fake_job_handle
        vixlib.VixHandle = mock.MagicMock()
        vixlib.VixHandle.return_value = fake_snapshot_handle
        ctypes.byref = mock.MagicMock()
        ctypes.byref.return_value = ctypes_byref_mock
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixVM.create_snapshot(include_memory=include_memory,
                                    name=fake_name,
                                    description=fake_description)
        if include_memory:
            options = vixlib.VIX_SNAPSHOT_INCLUDE_MEMORY
        else:
            options = 0

        vixlib.VixVM_CreateSnapshot.assert_called_with(
            self._VixVM._vm_handle, fake_name, fake_description, options,
            vixlib.VIX_INVALID_HANDLE, None, None)
        vixlib.VixHandle.assert_called_once()
        ctypes.byref.assert_called_with(fake_snapshot_handle)
        vixlib.VixJob_Wait.assert_called_with(
            fake_job_handle, vixlib.VIX_PROPERTY_JOB_RESULT_HANDLE,
            ctypes_byref_mock, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_with(None)

    def test_create_snapshot_include_memory_true(self):
        self._test_create_snapshot(include_memory=True)

    def test_create_snapshot_include_memory_false(self):
        self._test_create_snapshot(include_memory=True)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_remove_snapshot(self, mock_check_job_err_code):
        fake_snapshot = mock.MagicMock()
        fake_job_handle = mock.MagicMock()

        vixlib.VixVM_RemoveSnapshot = mock.MagicMock()
        vixlib.VixVM_RemoveSnapshot.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None

        self._VixVM.remove_snapshot(fake_snapshot)

        vixlib.VixVM_RemoveSnapshot.assert_called_with(
            self._VixVM._vm_handle, fake_snapshot._snapshot_handle, 0, None,
            None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        mock_check_job_err_code.assert_called_once_with(None)
        fake_snapshot.close.assert_called_once()

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_get_vmx_path(self, mock_check_job_err_code):
        fake_vmx_path = mock.MagicMock()
        mock_ctypes_byref = mock.MagicMock()

        ctypes.c_char_p = mock.MagicMock()
        ctypes.c_char_p.return_value = fake_vmx_path
        ctypes.byref = mock.MagicMock()
        ctypes.byref.return_value = mock_ctypes_byref
        vixlib.Vix_GetProperties = mock.MagicMock()
        vixlib.Vix_GetProperties.return_value = None
        vixlib.Vix_FreeBuffer = mock.MagicMock()

        response = self._VixVM.get_vmx_path()

        ctypes.c_char_p.assert_called_once()
        vixlib.Vix_GetProperties.assert_called_with(
            self._VixVM._vm_handle, vixlib.VIX_PROPERTY_VM_VMX_PATHNAME,
            mock_ctypes_byref, vixlib.VIX_PROPERTY_NONE)
        mock_check_job_err_code.assert_called_with(None)
        vixlib.Vix_FreeBuffer.assert_called_with(fake_vmx_path)
        self.assertTrue(response is not None)

    @mock.patch('vix.vixutils.get_vmx_value')
    @mock.patch('vix.vixutils.VixVM.get_vmx_path')
    def test_get_vnc_settings(self, mock_get_vmx_path, mock_get_vmx_value):
        fake_path = 'fake/path'
        mock_get_vmx_path.return_value = fake_path
        mock_get_vmx_value.side_effect = ['True', '9999']

        response = self._VixVM.get_vnc_settings()

        mock_get_vmx_path.assert_called_once()
        self.assertEqual(response, (True, 9999))

    ########### TESTING VixSnapshot CLASS ###########
    def test_close_VixSnapshot(self):
        vixlib.Vix_ReleaseHandle = mock.MagicMock()
        self._VixSnapshot.close()
        vixlib.Vix_ReleaseHandle.assert_called_once()
        self.assertIsNone(self._VixSnapshot._snapshot_handle)

    ########### TESTING VixConnection CLASS ###########
    @mock.patch('vix.vixutils.VixConnection.delete_vm_files')
    @mock.patch('vix.vixutils.VixConnection.unregister_vm')
    @mock.patch('vix.vixutils.VixConnection.open_vm')
    def _test_unregister_vm_and_delete_files(self, mock_open_vm,
                                             mock_unregister_vm,
                                             mock_delete_vm_files,
                                             destroy_disks):
        fake_path = 'fake/path'
        mock_vm = mock.MagicMock()
        mock_open_vm.return_value = mock_vm
        mock_vm.get_power_state = mock.MagicMock(
            return_value=vixlib.VIX_POWERSTATE_POWERED_OFF)

        self._VixConnection.unregister_vm_and_delete_files(fake_path,
                                                           destroy_disks)

        mock_unregister_vm.assert_called_with(fake_path)
        if destroy_disks:
            mock_delete_vm_files.assert_called_with(fake_path)

    def test_unregister_vm_and_delete_files_destroy_disks(self):
        self._test_unregister_vm_and_delete_files(destroy_disks=True)

    def test_unregister_vm_and_delete_files_no_destroy_disks(self):
        self._test_unregister_vm_and_delete_files(destroy_disks=False)

    @mock.patch('vix.vixutils._check_job_err_code')
    @mock.patch('vix.vixutils.get_vix_host_type')
    def test_connect(self, mock_get_vix_host_type, mock_check_job_err_code):
        job_handle = mock.MagicMock()
        host_handle = mock.MagicMock()
        ctypes_handle = mock.MagicMock()

        ctypes.byref = mock.MagicMock(return_value=ctypes_handle)
        vixlib.VixHost_Connect = mock.MagicMock()
        vixlib.VixHost_Connect.return_value = job_handle
        vixlib.VixHandle = mock.MagicMock()
        vixlib.VixHandle.return_value = host_handle

        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixConnection.connect()
        vixlib.VixHost_Connect.assert_called_with(vixlib.VIX_API_VERSION,
                                                  mock_get_vix_host_type(),
                                                  None, 0, None, None, 0,
                                                  vixlib.VIX_INVALID_HANDLE,
                                                  None, None)
        vixlib.Vix_ReleaseHandle.assert_called_with(job_handle)
        mock_check_job_err_code.assert_called_with(None)

        self.assertEqual(self._VixConnection._host_handle, host_handle)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_open_vm(self, mock_check_job_err_code):
        fake_path = 'fake/path'
        mock_job_handle = mock.MagicMock()
        mock_vm_handle = mock.MagicMock()
        ctypes.byref = mock.MagicMock()

        vixlib.VixVM_Open = mock.MagicMock()
        vixlib.VixVM_Open.return_value = mock_job_handle
        vixlib.VixHandle = mock.MagicMock()
        vixlib.VixHandle.return_value = mock_vm_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        #TODO: with side effect for getting and error than continue
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        response = self._VixConnection.open_vm(fake_path)

        vixlib.VixVM_Open.assert_called_with(
            self._VixConnection._host_handle, fake_path, None, None)
        vixlib.VixJob_Wait.assert_called_with(
            mock_job_handle, vixlib.VIX_PROPERTY_JOB_RESULT_HANDLE,
            ctypes.byref(mock_vm_handle), vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(mock_job_handle)
        mock_check_job_err_code.assert_called_with(None)
        self.assertIsInstance(response, vixutils.VixVM)

    def test_create_vm(self):
        fake_path = 'fake/path'
        display_name = 'fake_name'
        guest_os = 'guest_os'
        disk_paths = ['fake/disk/path']
        iso_paths = ['fake/iso/path']
        floppy_path = 'fake/floppy/path'
        networks = [('eth', 'mac')]
        nested_hypervisor = True
        vnc_enabled = True
        vnc_port = 9999

        self._VixConnection._get_scsi_config = mock.MagicMock()
        self._VixConnection._get_ide_config = mock.MagicMock()
        self._VixConnection._get_networks_config = mock.MagicMock()
        self._VixConnection._get_nested_hypervisor_config = mock.MagicMock()
        self._VixConnection._get_vnc_config = mock.MagicMock()
        os.path.dirname = mock.MagicMock()
        os.path.dirname.return_value = 'fake_dir'
        os.path.exists = mock.MagicMock()
        os.path.exists.return_value = False
        os.makedirs = mock.MagicMock()
        os.linesep = mock.MagicMock()

        with mock.patch('vix.vixutils.open', mock.mock_open(),
                        create=True) as m:
            self._VixConnection.create_vm(vmx_path=fake_path,
                                          display_name=display_name,
                                          guest_os=guest_os,
                                          disk_paths=disk_paths,
                                          iso_paths=iso_paths,
                                          floppy_path=floppy_path,
                                          networks=networks,
                                          nested_hypervisor=nested_hypervisor,
                                          vnc_enabled=vnc_enabled,
                                          vnc_port=vnc_port)
            m.assert_called_with('fake/path', 'wb')

        self._VixConnection._get_scsi_config.assert_called_with(disk_paths)
        self._VixConnection._get_ide_config.assert_called_with(iso_paths)
        self._VixConnection._get_networks_config.assert_called_with(networks)
        self._VixConnection._get_nested_hypervisor_config.assert_called_once()
        self._VixConnection._get_vnc_config.assert_called_with(vnc_enabled,
                                                               vnc_port)
        os.path.dirname.assert_called_with(fake_path)
        os.path.exists.assert_called_with('fake_dir')
        os.makedirs.assert_called_with('fake_dir')

    @mock.patch('vix.vixutils.set_vmx_value')
    @mock.patch('vix.vixutils.remove_vmx_value')
    def test_update_vm(self, remove_vmx_value, set_vmx_value):
        fake_path = 'fake/path'
        display_name = 'fake_name'
        guest_os = 'guest_os'
        virtual_hw_version = 10
        num_vcpus = 1
        cores_per_socket = 1
        mem_size_mb = 1024
        disk_paths = ['fake/disk/path']
        iso_paths = ['fake/iso/path']
        floppy_path = 'fake/floppy/path'
        networks = [('eth', 'mac')]
        boot_order = "hdd,cdrom,floppy"
        nested_hypervisor = True
        vnc_enabled = True
        vnc_port = mock.MagicMock()
        additional_config = {"fake_config": "fake_value"}

        self._VixConnection._get_scsi_config = mock.MagicMock()
        self._VixConnection._get_scsi_config.return_value = {
            "fake disk": "fake path"}
        self._VixConnection._get_ide_config = mock.MagicMock()
        self._VixConnection._get_ide_config.return_value = {
            "fake iso": "fake path"}
        self._VixConnection._get_floppy_config = mock.MagicMock()
        self._VixConnection._get_floppy_config.return_value = {
            "fake floppy": "fake path"}
        self._VixConnection._get_nested_hypervisor_config = mock.MagicMock()
        self._VixConnection._get_nested_hypervisor_config.return_value = {
            "fake hypervisor": "fake value"}
        self._VixConnection._get_networks_config = mock.MagicMock()
        self._VixConnection._get_networks_config.return_value = {
            "fake network": "fake mac"}
        self._VixConnection._get_vnc_config = mock.MagicMock()
        self._VixConnection._get_vnc_config.return_value = {"enabled": True,
                                                            "port": 9999,
                                                            }

        self._VixConnection.update_vm(
            vmx_path=fake_path, display_name=display_name,
            guest_os=guest_os, virtual_hw_version=virtual_hw_version,
            num_vcpus=num_vcpus, cores_per_socket=cores_per_socket,
            mem_size_mb=mem_size_mb, disk_paths=disk_paths,
            iso_paths=iso_paths, floppy_path=floppy_path, networks=networks,
            boot_order=boot_order, nested_hypervisor=nested_hypervisor,
            vnc_enabled=vnc_enabled, vnc_port=vnc_port,
            additional_config=additional_config)

        self._VixConnection._get_scsi_config.assert_called_with(disk_paths)
        self._VixConnection._get_floppy_config.assert_called_with(floppy_path)
        self._VixConnection._get_ide_config.assert_called_with(iso_paths)
        self._VixConnection._get_networks_config.assert_called_with(networks)
        self._VixConnection._get_nested_hypervisor_config.assert_called_once()
        self._VixConnection._get_vnc_config.assert_called_with(vnc_enabled,
                                                               vnc_port)

        remove_vmx_value.assert_called_with(
            fake_path, r"ethernet[\d]+\.[a-zA-Z]+")
        self.assertEqual(set_vmx_value.call_count, 15)

    def test_get_vnc_config(self):
        vnc_enabled = True
        vnc_port = 9999

        response = self._VixConnection._get_vnc_config(vnc_enabled, vnc_port)

        self.assertEqual(response, {'RemoteDisplay.vnc.enabled': True,
                                    'RemoteDisplay.vnc.port': 9999})

    def test_get_scsi_config(self):
        disk_paths = ['fake/disk/path']

        response = self._VixConnection._get_scsi_config(disk_paths)

        self.assertEqual(response, {'scsi0:0.present': 'TRUE',
                                    'scsi0.sharedBus': 'none',
                                    'scsi0:0.fileName': 'fake/disk/path',
                                    'scsi0.present': 'TRUE',
                                    'scsi0:0.deviceType': 'scsi-hardDisk',
                                    'scsi0.virtualDev': 'lsisas1068'})

    def test_get_scsi_disk_config(self):
        ctrl_idx = 9999
        disk_idx = 9999
        path = 'fake/path'

        response = self._VixConnection._get_scsi_disk_config(ctrl_idx,
                                                             disk_idx, path)

        self.assertEqual(response,
                         {'scsi9999:9999.present': 'TRUE',
                          'scsi9999:9999.fileName': 'fake/path',
                          'scsi9999:9999.deviceType': 'scsi-hardDisk'})

    def test_get_ide_config(self):
        iso_paths = ['fake/iso/path']

        response = self._VixConnection._get_ide_config(iso_paths)

        self.assertEqual(response, {'ide1:0.deviceType': 'cdrom-image',
                                    'ide1:0.present': 'TRUE',
                                    'ide1:0.clientDevice': 'FALSE',
                                    'ide1:0.startConnected': True,
                                    'ide1:0.fileName': 'fake/iso/path'})

    def test_get_ide_iso_config(self):
        ctrl_idx = 9999
        disk_idx = 9999
        fake_path = 'fake/path'

        response = self._VixConnection._get_ide_iso_config(ctrl_idx,
                                                           disk_idx,
                                                           fake_path)

        self.assertEqual(response, {'ide9999:9999.fileName': 'fake/path',
                                    'ide9999:9999.deviceType': 'cdrom-image',
                                    'ide9999:9999.startConnected': True,
                                    'ide9999:9999.present': 'TRUE',
                                    'ide9999:9999.clientDevice': 'FALSE'})

    def test_get_floppy_config(self):
        floppy_path = 'fake/floppy/path'

        response = self._VixConnection._get_floppy_config(floppy_path)

        self.assertEqual(response, {'floppy0.fileType': 'file',
                                    'floppy0.clientDevice': 'FALSE',
                                    'floppy0.present': 'TRUE',
                                    'floppy0.fileName': 'fake/floppy/path'})

    def test_get_nested_hypervisor_config(self):
        response = self._VixConnection._get_nested_hypervisor_config()
        self.assertEqual(response, {'vhv.enable': 'TRUE',
                                    'vcpu.hotadd': 'FALSE',
                                    'featMask.vm.hv.capable': 'Min:1'})

    def test_get_networks_config(self):
        networks = [('eth', 'mac')]

        response = self._VixConnection._get_networks_config(networks)

        self.assertEqual(response['ethernet0.networkName'], 'eth')
        self.assertEqual(response['ethernet0.address'], 'mac')

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_register_vm(self, mock_check_job_err_code):
        fake_path = 'fake/path'
        fake_job_handle = mock.MagicMock()

        vixlib.VixHost_RegisterVM = mock.MagicMock()
        vixlib.VixHost_RegisterVM.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixConnection.register_vm(fake_path)

        vixlib.VixHost_RegisterVM.assert_called_with(
            self._VixConnection._host_handle, fake_path, None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_with(None)

    @mock.patch('vix.vixutils._get_player_preferences_file_path')
    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_unregister_vm_local(self, mock_check_job_err_code,
                                  mock_get_player_preferences_file_path,
                                  platform):
        fake_path = 'fake/path'
        pref_file_path = 'fake_file'
        other_fake_path = 'other/fake/path'
        fake_vmx_path_norm = 'fake/vmx/path'
        some_object = mock.Mock()

        sys.platform = mock.MagicMock()
        sys.platform.return_value = platform
        mock_get_player_preferences_file_path.return_value = pref_file_path
        os.path.exists = mock.MagicMock()
        os.path.exists.return_value = True
        win32api.GetLongPathName = mock.MagicMock()
        win32api.GetLongPathName.return_value = fake_path
        os.path.abspath = mock.MagicMock()
        os.path.abspath.return_value = other_fake_path
        os.path.normcase = mock.MagicMock()
        os.path.normcase.return_value = fake_vmx_path_norm
        re.match = mock.MagicMock()
        re.match.return_value = some_object

        with mock.patch('vix.vixutils.open', mock.mock_open(read_data=''),
                        create=True) as m:
            print m.mock_calls
            self._VixConnection._unregister_vm_local(fake_path)
            m.assert_called_with(pref_file_path, 'r')

        if platform == 'win32':
            win32api.GetLongPathName.assert_called_with(fake_path)
            self.assertEqual(os.path.exists.call_count, 2)
        else:
            os.path.exists.assert_called_once()
        os.path.abspath.assert_called_with(fake_path)
        os.path.normcase.assert_called_with(other_fake_path)

    def _test_unregister_vm_local_platform_windows(self):
        self._test_unregister_vm_local(platform='win32')

    def test_unregister_vm_local_other_platform(self):
        self._test_unregister_vm_local(platform='linux')

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_unregister_vm_server(self, mock_check_job_err_code):
        fake_path = 'fake/path'
        fake_job_handle = mock.MagicMock()
        vixlib.VixHost_UnregisterVM = mock.MagicMock()
        vixlib.VixHost_UnregisterVM.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        self._VixConnection._unregister_vm_server(fake_path)

        vixlib.VixHost_UnregisterVM.assert_called_with(
            self._VixConnection._host_handle, fake_path, None, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_with(None)

    @mock.patch('vix.vixutils.VixConnection._unregister_vm_server')
    @mock.patch('vix.vixutils.VixConnection._unregister_vm_local')
    @mock.patch('vix.vixutils.get_vix_host_type')
    def _test_unregister_vm(self, mock_get_vix_host_type,
                            mock_unregister_vm_local,
                            mock_unregister_vm_server, vmware):
        fake_path = 'fake/path'

        mock_get_vix_host_type.return_value = vmware

        if vmware == 1:
            self.assertRaises(Exception, self._VixConnection.unregister_vm)
        else:
            self._VixConnection.unregister_vm(fake_path)

        mock_get_vix_host_type.assert_called_once()
        if vmware == 3 or 4:
            mock_unregister_vm_local.assert_called_with(fake_path)
        else:
            mock_unregister_vm_server.assert_called_with(fake_path)

    def test_unregister_vm_VMWARE_WORKSTATION(self):
        self._test_unregister_vm(vmware=3)

    def test_unregister_vm_VMWARE_PLAYER(self):
        self._test_unregister_vm(vmware=4)

    def _test_unregister_vm_default(self):
        #not called ??get_vix_host_type raises exception??
        self._test_unregister_vm(vmware=1)

    def test_disconnect(self):
        vixlib.VixHost_Disconnect = mock.MagicMock()
        self._VixConnection.disconnect()
        vixlib.VixHost_Disconnect.assert_called_once()
        self.assertIsNone(self._VixConnection._host_handle)

    def test_vm_exists(self):
        fake_path = 'fake/path'
        os.path.exists = mock.MagicMock()
        os.path.exists.return_value = True

        response = self._VixConnection.vm_exists(fake_path)

        os.path.exists.assert_called_with(fake_path)
        self.assertEqual(response, True)

    def test_delete_vm_files(self):
        fake_path = 'fake/path'
        fake_name = 'fake_name'
        os.path.dirname = mock.MagicMock()
        os.path.dirname.return_value = fake_name
        os.path.exists = mock.MagicMock()
        os.path.exists.return_value = True
        shutil.rmtree = mock.MagicMock()

        self._VixConnection.delete_vm_files(fake_path)

        os.path.dirname.assert_called_with(fake_path)
        os.path.exists.assert_called_with(fake_name)
        shutil.rmtree.assert_called_with(fake_name)

    def test_list_running_vms(self):
        fake_job_handle = mock.MagicMock()
        cb = mock.MagicMock()

        #cannot get inside nested callback method
        vixlib.VixEventProc = mock.MagicMock()
        vixlib.VixEventProc.return_value = cb
        vixlib.VixHost_FindItems = mock.MagicMock()
        vixlib.VixHost_FindItems.return_value = fake_job_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        response = self._VixConnection.list_running_vms()

        vixlib.VixEventProc.assert_called_once()
        vixlib.VixHost_FindItems.assert_called_with(
            self._VixConnection._host_handle, vixlib.VIX_FIND_RUNNING_VMS,
            vixlib.VIX_INVALID_HANDLE, -1, cb, None)
        vixlib.VixJob_Wait.assert_called_with(fake_job_handle,
                                              vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        self.assertTrue(response is not None)

    @mock.patch('vix.vixutils._get_install_dir')
    def _test_get_tools_iso_path(self, mock_get_install_dir, platform):
        fake_dir = 'fake_dir'

        sys.platform = platform
        os.path.join = mock.MagicMock()
        os.path.join.return_value = 'fake_dir/Contents/Library/isoimages'
        mock_get_install_dir.return_value = fake_dir

        response = self._VixConnection.get_tools_iso_path()

        if platform == "darwin":
            self.assertEqual(response, 'fake_dir/Contents/Library/isoimages')
        elif platform == "win32":
            self.assertEqual(response, fake_dir)
        else:
            self.assertEqual(response, "/usr/lib/vmware/isoimages")

    def test_get_tools_iso_path_darwin(self):
        self._test_get_tools_iso_path(platform="darwin")

    def test_get_tools_iso_path_win32(self):
        self._test_get_tools_iso_path(platform="win32")

    def test_get_tools_iso_path_linux(self):
        self._test_get_tools_iso_path(platform="linux")

    @mock.patch('vix.vixutils._check_job_err_code')
    def _test_clone_vm(self, mock_check_job_err_code, linked_clone):
        fake_src_vmx_path = 'fake_src_path'
        fake_dest_vmx_path = 'fake_dest_path'
        fake_job_handle = mock.MagicMock()
        cloned_vm_handle = mock.MagicMock()
        fake_vm = mock.MagicMock()
        byref_mock = mock.MagicMock()
        if linked_clone:
            clone_type = vixlib.VIX_CLONETYPE_LINKED
        else:
            clone_type = vixlib.VIX_CLONETYPE_FULL

        self._VixConnection.open_vm = mock.MagicMock()
        self._VixConnection.open_vm.return_value = fake_vm
        vixlib.VixVM_Clone = mock.MagicMock()
        vixlib.VixVM_Clone.return_value = fake_job_handle
        vixlib.VixHandle = mock.MagicMock()
        vixlib.VixHandle.return_value = cloned_vm_handle
        vixlib.VixJob_Wait = mock.MagicMock()
        vixlib.VixJob_Wait.return_value = None
        ctypes.byref = mock.MagicMock()
        ctypes.byref.return_value = byref_mock
        vixlib.Vix_ReleaseHandle = mock.MagicMock()

        response = self._VixConnection.clone_vm(fake_src_vmx_path,
                                                fake_dest_vmx_path,
                                                linked_clone)

        self._VixConnection.open_vm.assert_called_with(fake_src_vmx_path)
        vixlib.VixVM_Clone.assert_called_with(fake_vm.__enter__()._vm_handle,
                                              vixlib.VIX_INVALID_HANDLE,
                                              clone_type,
                                              fake_dest_vmx_path, 0,
                                              vixlib.VIX_INVALID_HANDLE,
                                              None, None)
        vixlib.VixHandle.assert_called_once()
        vixlib.VixJob_Wait.assert_called_with(
            fake_job_handle, vixlib.VIX_PROPERTY_JOB_RESULT_HANDLE,
            byref_mock, vixlib.VIX_PROPERTY_NONE)
        ctypes.byref.assert_called_with(cloned_vm_handle)
        vixlib.Vix_ReleaseHandle.assert_called_with(fake_job_handle)
        mock_check_job_err_code.assert_called_with(None)
        self.assertIsInstance(response, vixutils.VixVM)

    def test_clone_vm_linked_clone_true(self):
        self._test_clone_vm(linked_clone=True)

    def test_clone_vm_linked_clone_false(self):
        self._test_clone_vm(linked_clone=False)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_get_software_version(self, mock_check_job_err_code):
        version = mock.MagicMock()
        byref_mock = mock.MagicMock()

        ctypes.c_char_p = mock.MagicMock()
        ctypes.c_char_p.return_value = version
        vixlib.Vix_GetProperties = mock.MagicMock()
        vixlib.Vix_GetProperties.return_value = None
        vixlib.Vix_FreeBuffer = mock.MagicMock()
        ctypes.byref = mock.MagicMock()
        ctypes.byref.return_value = byref_mock

        response = self._VixConnection.get_software_version()

        ctypes.c_char_p.assert_called_once()
        vixlib.Vix_GetProperties.assert_called_with(
            self._VixConnection._host_handle,
            vixlib.VIX_PROPERTY_HOST_SOFTWARE_VERSION, byref_mock,
            vixlib.VIX_PROPERTY_NONE)
        mock_check_job_err_code.assert_called_with(None)
        vixlib.Vix_FreeBuffer.assert_called_with(version)
        self.assertTrue(response is not None)

    @mock.patch('vix.vixutils._check_job_err_code')
    def test_get_host_type(self, mock_check_job_err_code):
        host_type = mock.MagicMock()
        byref_mock = mock.MagicMock()
        ctypes.c_int = mock.MagicMock()
        ctypes.c_int.return_value = host_type
        vixlib.Vix_GetProperties = mock.MagicMock()
        vixlib.Vix_GetProperties.return_value = None
        ctypes.byref = mock.MagicMock()
        ctypes.byref.return_value = byref_mock

        response = self._VixConnection.get_host_type()

        vixlib.Vix_GetProperties.assert_called_with(
            self._VixConnection._host_handle,
            vixlib.VIX_PROPERTY_HOST_HOSTTYPE, byref_mock,
            vixlib.VIX_PROPERTY_NONE)
        mock_check_job_err_code.assert_called_with(None)
        self.assertTrue(response is not None)
