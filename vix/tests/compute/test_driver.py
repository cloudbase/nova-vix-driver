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
import platform
import unittest

from nova.compute import task_states
from nova.openstack.common import jsonutils
from oslo.config import cfg
from vix.compute import driver
from vix import utils
from vix import vixlib
from vix import vixutils


class VixDriverTestCase(unittest.TestCase):
    """Unit tests for Nova VIX driver"""

    def setUp(self):
        self.CONF = mock.MagicMock()
        cfg.CONF = mock.MagicMock(return_value=self.CONF)
        virtapi = mock.MagicMock()

        self._driver = driver.VixDriver(virtapi)
        self._driver._pathutils = mock.MagicMock()
        self._driver._image_cache = mock.MagicMock()
        self._driver._conn = mock.MagicMock()

    def test_list_instances(self):
        self._driver.list_instances()
        self._driver._conn.list_running_vms.assert_called_once()

    def test_delete_existing_instance(self):
        fake_instance_name = 'fake_name'
        fake_path = 'fake/path'
        self._driver._pathutils.get_vmx_path.return_value = fake_path

        self._driver._delete_existing_instance(fake_instance_name)

        self._driver._pathutils.get_vmx_path.assert_called_with('fake_name')
        self._driver._conn.vm_exists.assert_called_with(fake_path)
        self._driver._conn.unregister_vm_and_delete_files.assert_called_with(
            fake_path, True)

    @mock.patch('vix.vixutils.get_vmx_value')
    @mock.patch('vix.vixutils.set_vmx_value')
    def test_clone_vmdk_vm(self, mock_set_vmx_value, mock_get_vmx_value):
        fake_src_vmdk = 'src/fake.vmdk'
        fake_file_name = 'fake.vmdk'
        fake_root_vmdk_path = 'root/fake.vmdk'
        fake_dest_vmx_path = 'dest/fake.vmdk'
        fake_vmdk_path = 'path/fake.vmdk'
        fake_split = mock.MagicMock()
        fake_base = mock.MagicMock()

        os.path.basename = mock.MagicMock(return_value=fake_base)
        os.path.splitext = mock.MagicMock(return_value=fake_split)
        os.path.dirname = mock.MagicMock()
        os.path.join = mock.MagicMock(return_value=fake_vmdk_path)
        mock_get_vmx_value.return_value = fake_file_name

        self._driver._clone_vmdk_vm(fake_src_vmdk, fake_root_vmdk_path,
                                    fake_dest_vmx_path)

        self._driver._conn.create_vm.assert_called_once()
        self._driver._conn.clone_vm.assert_called_with(
            fake_split[0] + ".vmx", fake_dest_vmx_path, True)
        self._driver._pathutils.rename.assert_called_with(
            fake_vmdk_path, fake_root_vmdk_path)
        mock_set_vmx_value.assert_called_with(fake_split[0] + ".vmsd",
                                              "sentinel0", fake_base)

    @mock.patch('vix.vixutils.get_vix_host_type')
    def test_check_player_compatibility(self, mock_get_vix_host_type):
        mock_get_vix_host_type.return_value = vixutils.VIX_VMWARE_PLAYER
        self.assertRaises(NotImplementedError,
                          self._driver._check_player_compatibility, True)

    def _test_spawn(self, cow):

        fake_admin_password = 'fake password'
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_image_meta = mock.MagicMock()
        fake_injected_files = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        fake_block_device_info = mock.MagicMock()
        fake_image_info = mock.MagicMock()
        fake_iso_image_ids = ['fakeid']
        fake_b_path = 'fake/base/vmdk/path'
        fake_r_path = 'fake/root/vmdk/path'
        fake_vmx_path = 'fake/vmx/path'
        fake_floppy_path = 'fake/floppy/path'

        self._driver._image_cache.get_image_info.return_value = fake_image_info
        self._driver._check_player_compatibility = mock.MagicMock()
        self._driver._delete_existing_instance = mock.MagicMock()
        self._driver._clone_vmdk_vm = mock.MagicMock()
        self._driver._image_cache.get_cached_image.return_value = fake_b_path
        self._driver._pathutils.get_root_vmdk_path.return_value = fake_r_path
        self._driver._pathutils.get_vmx_path.return_value = fake_vmx_path
        self._driver._pathutils.get_floppy_path.return_value = fake_floppy_path
        os.path.join = mock.MagicMock(return_value=fake_b_path)
        fake_image_info.get().get().lower.return_value = str(cow).lower()
        fake_image_info.get().get().split.return_value = fake_iso_image_ids
        utils.get_free_port = mock.MagicMock()
        utils.get_free_port.return_value = 9999

        self._driver.spawn(context=fake_context, instance=fake_instance,
                           image_meta=fake_image_meta,
                           injected_files=fake_injected_files,
                           admin_password=fake_admin_password,
                           network_info=fake_network_info,
                           block_device_info=fake_block_device_info)
        print fake_image_info.get().get.mock_calls

        self._driver._image_cache.get_image_info.assert_called_with(
            fake_context, fake_instance['image_ref'])

        self._driver._check_player_compatibility.assert_called_with(cow)
        self._driver._delete_existing_instance.assert_called_with(
            fake_instance['name'])
        self._driver._pathutils.create_instance_dir.assert_called_with(
            fake_instance['name'])
        self.assertEqual(self._driver._image_cache.get_cached_image.call_count,
                         3)
        self._driver._pathutils.get_root_vmdk_path.assert_called_with(
            fake_instance['name'])
        self._driver._pathutils.get_vmx_path.assert_called_with(
            fake_instance['name'])
        if cow:
            self._driver._clone_vmdk_vm.assert_called_with(
                fake_b_path, fake_r_path, fake_vmx_path)
            self.assertEqual(self._driver._pathutils.copy.call_count, 1)
            self._driver._conn.update_vm.assert_called_with(
                vmx_path=fake_vmx_path,
                display_name=fake_instance.get("display_name"),
                guest_os=fake_image_info.get().get(),
                num_vcpus=fake_instance['vcpus'],
                mem_size_mb=fake_instance['memory_mb'],
                iso_paths=[fake_b_path, fake_b_path],
                floppy_path=fake_floppy_path,
                networks=[],
                boot_order=fake_image_info.get().get(),
                vnc_enabled=True,
                vnc_port=9999, nested_hypervisor=fake_image_info.get().get())
        else:
            self.assertEqual(self._driver._pathutils.copy.call_count, 2)
            self._driver._conn.create_vm.assert_called_with(
                vmx_path=fake_vmx_path,
                display_name=fake_instance.get("display_name"),
                guest_os=fake_image_info.get().get(),
                num_vcpus=fake_instance['vcpus'],
                mem_size_mb=fake_instance['memory_mb'],
                disk_paths=[fake_r_path],
                iso_paths=[fake_b_path, fake_b_path],
                floppy_path=fake_floppy_path,
                networks=[],
                boot_order=fake_image_info.get().get(),
                vnc_enabled=True,
                vnc_port=9999, nested_hypervisor=fake_image_info.get().get())

        os.path.join.assert_called_with(
            self._driver._conn.get_tools_iso_path(),
            "%s.iso" % fake_image_info.get().get())
        self._driver._pathutils.get_floppy_path.assert_called_with(
            fake_instance['name'])
        utils.get_free_port.assert_called_once()
        self._driver._conn.open_vm.assert_called_with(fake_vmx_path)

    def test_spawn_cow(self):
        self._test_spawn(cow=True)

    def test_spawn_no_cow(self):
        self._test_spawn(cow=False)

    def _test_exec_vm_action(self, vm_exists):
        fake_instance = mock.MagicMock()
        fake_action = mock.MagicMock()

        fake_path = 'fake/path'
        self._driver._pathutils.get_vmx_path.return_value = fake_path
        self._driver._conn.vm_exists.return_value = vm_exists
        if not vm_exists:
            self.assertRaises(Exception, self._driver._exec_vm_action,
                              fake_instance, fake_action)
        else:
            response = self._driver._exec_vm_action(fake_instance,
                                                    fake_action)
            self._driver._conn.open_vm.assert_called_with(fake_path)
            self.assertTrue(response is not None)

    def test_exec_vm_action_vm_exists_false(self):
        self._test_exec_vm_action(False)

    def test_exec_vm_action_vm_exists_true(self):
        self._test_exec_vm_action(True)

    @mock.patch('vix.vixutils.VixVM.reboot')
    def test_reboot(self, mock_reboot):
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        self._driver.reboot(fake_context, fake_instance,
                            fake_network_info, reboot_type=None)
        mock_reboot.assert_called_once()

    def test_destroy(self):
        fake_instance = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        self._driver._delete_existing_instance = mock.MagicMock()
        self._driver.destroy(fake_instance, fake_network_info)
        self._driver._delete_existing_instance.assert_called_with(
            fake_instance['name'], True)

    @mock.patch('vix.vixutils.VixVM.get_power_state')
    def test_get_info(self, mock_get_power_state):
        fake_instance = mock.MagicMock()

        mock_get_power_state.return_value = vixlib.VIX_POWERSTATE_POWERED_ON

        response = self._driver.get_info(fake_instance)
        print response
        mock_get_power_state.assert_called_once()
        self.assertTrue(response is not None)

    def test_attach_volume(self):
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_connection_info = mock.MagicMock()
        fake_mountpoint = mock.MagicMock()

        self.assertRaises(NotImplementedError,
                          self._driver.attach_volume, fake_context,
                          fake_connection_info, fake_instance,
                          fake_mountpoint)

    def test_deattach_volume(self):
        fake_instance = mock.MagicMock()
        fake_connection_info = mock.MagicMock()
        fake_mountpoint = mock.MagicMock()

        self.assertRaises(NotImplementedError,
                          self._driver.detach_volume,
                          fake_connection_info,  fake_instance,
                          fake_mountpoint)

    def test_get_volume_connector(self):
        fake_instance = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._driver.get_volume_connector,
                          fake_instance)

    def test_get_host_memory_info(self):
        total_mem = 2147483648
        free_mem = 1073741824
        utils.get_host_memory_info = mock.MagicMock()
        utils.get_host_memory_info.return_value = (total_mem, free_mem)
        response = self._driver._get_host_memory_info()
        utils.get_host_memory_info.assert_called_once()
        self.assertEqual(response, (2048, 1024, 1024))

    def test_get_local_hdd_info_gb(self):
        total_disk = 2147483648
        free_disk = 1073741824
        fake_dir = 'fake dir'
        utils.get_disk_info = mock.MagicMock()
        utils.get_disk_info.return_value = (total_disk, free_disk)
        self._driver._pathutils.get_instances_dir = mock.MagicMock()
        self._driver._pathutils.get_instances_dir.return_value = fake_dir
        response = self._driver._get_local_hdd_info_gb()
        utils.get_disk_info.assert_called_once_with(fake_dir)
        self.assertEqual(response, (2, 1, 1))

    def test_get_hypervisor_version(self):
        self._driver._conn.get_software_version.return_value = 10
        response = self._driver._get_hypervisor_version()
        self._driver._conn.get_software_version.assert_called_once()
        self.assertEqual(response, 10)

    def test_get_available_resource(self):
        fake_nodename = 'fake_name'
        total_disk = 2 * 1024 * 1024 * 1024
        free_disk = 1 * 1024 * 1024 * 1024
        total_mem = 2048 * 1024 * 1024
        free_mem = 1024 * 1024 * 1024
        vcpus = 2
        fake_dir = 'fake dir'
        compare_dict = {'vcpus': vcpus,
                        'memory_mb': 2048,
                        'memory_mb_used': 1024,
                        'local_gb': 2,
                        'local_gb_used': 1,
                        'hypervisor_type': "vix",
                        'hypervisor_version': 10,
                        'hypervisor_hostname': 'fake_hostname',
                        'vcpus_used': 0,
                        'cpu_info': 0,
                        'supported_instances': 0}

        jsonutils.dumps = mock.MagicMock()
        jsonutils.dumps.return_value = 0
        platform.node = mock.MagicMock()
        platform.node.return_value = 'fake_hostname'
        self._driver._conn.get_software_version = mock.MagicMock()
        self._driver._conn.get_software_version.return_value = 10
        utils.get_host_memory_info = mock.MagicMock()
        utils.get_host_memory_info.return_value = (total_mem, free_mem)
        utils.get_disk_info = mock.MagicMock()
        utils.get_disk_info.return_value = (total_disk, free_disk)
        self._driver._pathutils.get_instances_dir = mock.MagicMock()
        self._driver._pathutils.get_instances_dir.return_value = fake_dir
        utils.get_cpu_count = mock.MagicMock()
        utils.get_cpu_count.return_value = vcpus

        response = self._driver.get_available_resource(fake_nodename)
        utils.get_host_memory_info.assert_called_once()
        utils.get_disk_info.assert_called_once_with(fake_dir)
        self._driver._conn.get_software_version.assert_called_once()
        platform.node.assert_called_once()
        self.assertEqual(jsonutils.dumps.call_count, 2)
        self.assertEqual(response, compare_dict)

    def test_update_stats(self):
        total_disk = 2 * 1024 * 1024 * 1024
        free_disk = 1 * 1024 * 1024 * 1024
        total_mem = 2048 * 1024 * 1024
        free_mem = 1024 * 1024 * 1024
        fake_dir = 'fake dir'
        compare_dict = {'host_memory_total': 2048,
                        'host_memory_overhead': 1024,
                        'host_memory_free': 1024,
                        'host_memory_free_computed': 1024,
                        'disk_total': 2,
                        'disk_used': 1,
                        'disk_available': 1,
                        'hypervisor_hostname': 'fake_hostname',
                        'supported_instances': [('i686', 'vix', 'hvm'),
                                                ('x86_64', 'vix', 'hvm')]}
        platform.node = mock.MagicMock()
        platform.node.return_value = 'fake_hostname'
        utils.get_host_memory_info = mock.MagicMock()
        utils.get_host_memory_info.return_value = (total_mem, free_mem)
        utils.get_disk_info = mock.MagicMock()
        utils.get_disk_info.return_value = (total_disk, free_disk)
        self._driver._pathutils.get_instances_dir = mock.MagicMock()
        self._driver._pathutils.get_instances_dir.return_value = fake_dir

        self._driver._update_stats()

        utils.get_host_memory_info.assert_called_once()
        utils.get_disk_info.assert_called_once_with(fake_dir)
        platform.node.assert_called_once()
        self.assertEqual(self._driver._stats, compare_dict)

    def _test_get_host_stats(self, refresh):
        self._driver.get_host_stats(refresh=refresh)
        self.assertTrue(self._driver._stats is not None)

    def test_get_host_stats_refresh_true(self):
        self._test_get_host_stats(True)

    def test_get_host_stats_refresh_false(self):
        self._test_get_host_stats(False)

    @mock.patch('vix.vixutils.VixVM.create_snapshot')
    @mock.patch('vix.vixutils.VixVM.remove_snapshot')
    @mock.patch('vix.vixutils.get_vix_host_type')
    def _test_snapshot(self, feature_supported, mock_get_vix_host_type,
                       mock_remove_snapshot, mock_create_snapshot):
        fake_name = 'fake name'
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_update_task_state = mock.MagicMock()
        fake_path = 'fake/path'
        fake_r_path = 'fake/root/vmdk/path'
        fake_vm = mock.MagicMock()
        self._driver._conn.open_vm.return_value = fake_vm
        self._driver._pathutils.get_root_vmdk_path.return_value = fake_r_path
        self._driver._pathutils.get_vmx_path.return_value = fake_path

        if not feature_supported:
            host_type = vixutils.VIX_VMWARE_PLAYER
            mock_get_vix_host_type.return_value = host_type
            self.assertRaises(NotImplementedError, self._driver.snapshot,
                              fake_context, fake_instance, fake_name,
                              fake_update_task_state)
        else:
            self._driver.snapshot(fake_context, fake_instance, fake_name,
                                  fake_update_task_state)

            mock_get_vix_host_type.assert_called_once()
            self._driver._pathutils.get_vmx_path.assert_called_with(
                fake_instance['name'])
            self._driver._conn.open_vm.assert_called_with(fake_path)
            print self._driver._conn.open_vm.mock_calls
            self.assertEqual(fake_update_task_state.call_count, 2)
            fake_vm.__enter__().create_snapshot.assert_called_with(
                name="Nova snapshot")
            self._driver._image_cache.save_glance_image.assert_called_with(
                fake_context, fake_name, fake_r_path)
            mock_remove_snapshot.assert_called_once()

    def test_snapshot_not_implemented(self):
        self._test_snapshot(False)

    def test_snapshot(self):
        self._test_snapshot(True)

    @mock.patch('vix.vixutils.VixVM.pause')
    def test_pause(self, mock_pause):
        fake_instance = mock.MagicMock()
        self._driver.pause(fake_instance)
        mock_pause.assert_called_once()

    @mock.patch('vix.vixutils.VixVM.unpause')
    def test_unpause(self, mock_unpause):
        fake_instance = mock.MagicMock()
        self._driver.unpause(fake_instance)
        mock_unpause.assert_called_once()

    @mock.patch('vix.vixutils.VixVM.suspend')
    def test_suspend(self, mock_suspend):
        fake_instance = mock.MagicMock()
        self._driver.suspend(fake_instance)
        mock_suspend.assert_called_once()

    @mock.patch('vix.vixutils.VixVM.power_on')
    def test_resume(self, mock_power_on):
        fake_instance = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        self._driver.resume(fake_instance, fake_network_info)
        mock_power_on.assert_called_once()

    @mock.patch('vix.vixutils.VixVM.power_off')
    def test_power_off(self, mock_power_off):
        fake_instance = mock.MagicMock()
        self._driver.power_off(fake_instance)
        mock_power_off.assert_called_once()

    @mock.patch('vix.vixutils.VixVM.power_on')
    def test_power_on(self, mock_power_on):
        fake_instance = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        self._driver.power_on(fake_instance, fake_context,
                              fake_network_info)
        mock_power_on.assert_called_once()

    def test_live_migration(self):
        fake_context = mock.MagicMock()
        fake_recover_method = mock.MagicMock()
        fake_dest = 'fake/dest'
        fake_post_method = mock.MagicMock()
        fake_instance = mock.MagicMock()
        self.assertRaises(NotImplementedError, self._driver.live_migration,
                          fake_context, fake_instance, fake_dest,
                          fake_post_method, fake_recover_method)

    def test_pre_live_migration(self):
        fake_context = mock.MagicMock()
        fake_block_device_info = mock.MagicMock()
        fake_disk = 'fake/dest'
        fake_network_info = mock.MagicMock()
        fake_instance = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._driver.pre_live_migration, fake_context,
                          fake_instance, fake_block_device_info,
                          fake_network_info, fake_disk)

    def test_post_live_migration_at_destination(self):
        fake_context = mock.MagicMock()
        fake_network_info = mock.MagicMock()
        fake_instance_ref = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._driver.post_live_migration_at_destination,
                          fake_context, fake_instance_ref, fake_network_info)

    def test_check_can_live_migrate_destination(self):
        fake_context = mock.MagicMock()
        fake_src_computer = mock.MagicMock()
        fake_dest_computer = mock.MagicMock()
        fake_instance_ref = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._driver.check_can_live_migrate_destination,
                          fake_context, fake_instance_ref,
                          fake_src_computer, fake_dest_computer)

    def test_check_can_live_migrate_destination_cleanup(self):
        fake_context = mock.MagicMock()
        fake_dest_data = mock.MagicMock()
        self.assertRaises(
            NotImplementedError,
            self._driver.check_can_live_migrate_destination_cleanup,
            fake_context, fake_dest_data)

    def test_check_can_live_migrate_source(self):
        fake_context = mock.MagicMock()
        fake_instance_ref = mock.MagicMock()
        fake_dest_data = mock.MagicMock()
        self.assertRaises(NotImplementedError,
                          self._driver.check_can_live_migrate_source,
                          fake_context, fake_instance_ref, fake_dest_data)

    def test_get_host_ip_addr(self):
        response = self._driver.get_host_ip_addr()
        self.assertTrue(response is not None)

    def _test_get_vnc_console(self, vnc_enabled):
        fake_instance = mock.MagicMock()
        fake_path = 'fake/path'
        vnc_port = 9999
        open_vm_enter = mock.MagicMock()
        self._driver._conn.open_vm().__enter__.return_value = open_vm_enter
        open_vm_enter.get_vnc_settings.return_value = (
            vnc_enabled, vnc_port)
        self._driver._pathutils.get_vmx_path.return_value = fake_path

        if vnc_enabled:
            response = self._driver.get_vnc_console(fake_instance)
            self._driver._pathutils.get_vmx_path.assert_called_with(
                fake_instance['name'])
            self._driver._conn.open_vm.assert_called_with(fake_path)
            open_vm_enter.get_vnc_settings.assert_called_once()

            self.assertTrue(response is not None)
        else:
            self.assertRaises(utils.VixException,
                              self._driver.get_vnc_console, fake_instance)

    def test_get_vnc_console(self):
        self._test_get_vnc_console(True)

    def test_get_vnc_console_disabled(self):
        self._test_get_vnc_console(False)

    def test_get_console_output(self):
        fake_instance = mock.MagicMock()
        reponse = self._driver.get_console_output(fake_instance)
        self.assertEqual(reponse, '')
