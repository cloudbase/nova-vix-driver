# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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
import shutil
import sys

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova import utils
from oslo.config import cfg

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('instances_path', 'nova.compute.manager')


class PathUtils(object):
    def open(self, path, mode):
        """Wrapper on __builin__.open used to simplify unit testing."""
        import __builtin__
        return __builtin__.open(path, mode)

    def exists(self, path):
        return os.path.exists(path)

    def makedirs(self, path):
        os.makedirs(path)

    def remove(self, path):
        os.remove(path)

    def rename(self, src, dest):
        os.rename(src, dest)

    def copyfile(self, src, dest):
        self.copy(src, dest)

    def copy(self, src, dest):
        # With large files this is 2x-3x faster than shutil.copy(src, dest),
        # especially when copying to a UNC target.
        # shutil.copyfileobj(...) with a proper buffer is better than
        # shutil.copy(...) but still 20% slower than a shell copy.
        # It can be replaced with Win32 API calls to avoid the process
        # spawning overhead.
        if sys.platform == "win32":
            output, ret = utils.execute('cmd.exe', '/C', 'copy', '/Y',
                                        src, dest)
        else:
            output, ret = utils.execute('/bin/cp', '-f', src, dest)
        if ret:
            raise IOError(_('The file copy from %(src)s to %(dest)s failed')
                          % {'src': src, 'dest': dest})

    def rmtree(self, path):
        shutil.rmtree(path)

    def get_instances_dir(self, remote_server=None):
        return os.path.normpath(CONF.instances_path)

    def _check_create_dir(self, path):
        if not self.exists(path):
            LOG.debug(_('Creating directory: %s') % path)
            self.makedirs(path)

    def _check_remove_dir(self, path):
        if self.exists(path):
            LOG.debug(_('Removing directory: %s') % path)
            self.rmtree(path)

    def _get_instances_sub_dir(self, dir_name, create_dir=False,
                               remove_dir=False):
        instances_path = self.get_instances_dir()
        path = os.path.join(instances_path, dir_name)
        if remove_dir:
            self._check_remove_dir(path)
        if create_dir:
            self._check_create_dir(path)
        return path

    def create_instance_dir(self, instance_name):
        self.get_instance_dir(instance_name, create_dir=True)

    def get_instance_dir(self, instance_name, create_dir=False,
                         remove_dir=False):
        return self._get_instances_sub_dir(instance_name, create_dir,
                                           remove_dir)

    def get_vmx_path(self, instance_name):
        instance_path = self.get_instance_dir(instance_name)
        return os.path.join(instance_path, '%s.vmx' % instance_name)

    def get_root_vmdk_path(self, instance_name):
        instance_path = self.get_instance_dir(instance_name)
        return os.path.join(instance_path, 'root.vmdk')

    def get_floppy_path(self, instance_name):
        instance_path = self.get_instance_dir(instance_name)
        return os.path.join(instance_path, 'floppy.flp')

    def get_base_vmdk_dir(self):
        return self._get_instances_sub_dir('_base')
