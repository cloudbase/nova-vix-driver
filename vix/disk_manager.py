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

import os
import subprocess
import sys

from vix import vixutils
from vix import utils

DISK_TYPE_VMDK = "vmdk"
DISK_TYPE_VHD = "vpc"
DISK_TYPE_QCOW2 = "qcow2"
DISK_TYPE_RAW = "raw"


class DiskManager(object):
    def _get_vdisk_man_path(self):
        vdisk_man_path = os.path.join(vixutils.get_vix_bin_path(),
                                      "vmware-vdiskmanager")
        if sys.platform == "win32":
            vdisk_man_path += ".exe"
        return vdisk_man_path

    def _check_vdisk_man_exists(self):
        return os.path.exists(self._get_vdisk_man_path())

    def _create_disk_vdisk_man(self, disk_path, size_mb):
        vdisk_man_path = self._get_vdisk_man_path()

        args = [vdisk_man_path, "-c", "-s", "%sMB" % size_mb, "-a",
                "lsilogic", "-t", "0", disk_path]
        self._exec_cmd(args)

    def _exec_cmd(self, args):
        p = subprocess.Popen(args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
        if p.returncode:
            raise utils.StackOMatickException("Command failed: %s" % args)

    def _create_disk_qemu(self, disk_path, size_mb, disk_type):
        args = ["qemu-img", "create", "-f", disk_type, disk_path,
                "%sM" % size_mb]
        self._exec_cmd(args)

    def create_disk(self, disk_path, size_mb, disk_type):

        if disk_type == DISK_TYPE_VMDK and self._check_vdisk_man_exists():
            self._create_disk_vdisk_man(disk_path, size_mb)
        else:
            self._create_disk_qemu(disk_path, size_mb, disk_type)

    def _resize_disk_vdisk_man(self, disk_path, new_size_mb):
        vdisk_man_path = self._get_vdisk_man_path()

        args = [vdisk_man_path, "-x", "%sMB" % new_size_mb, disk_path]
        self._exec_cmd(args)

    def _resize_disk_qemu(self, disk_path, new_size_mb, new_disk_type):
        tmp_disk_path = "%s.raw" & disk_path
        try:
            args = ["qemu-img", "convert", "-O", DISK_TYPE_RAW, disk_path,
                    tmp_disk_path]
            self._exec_cmd(args)

            args = ["qemu-img", "resize", tmp_disk_path, "%sM" % new_size_mb]
            self._exec_cmd(args)

            args = ["qemu-img", "convert", "-f", DISK_TYPE_RAW, "-O",
                    new_disk_type, tmp_disk_path, disk_path]
            self._exec_cmd(args)
        finally:
            if os.path.exists(tmp_disk_path):
                os.remove(tmp_disk_path)

    def resize_disk(self, disk_path, new_size_mb, new_disk_type):
        if new_disk_type == DISK_TYPE_VMDK and self._check_vdisk_man_exists():
            self._resize_disk_vdisk_man(disk_path, new_size_mb)
        else:
            self._resize_disk_qemu(disk_path, new_size_mb, new_disk_type)
