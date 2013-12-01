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

import multiprocessing
import psutil
import re
import socket

from nova import exception


class VixException(exception.NovaException):
    pass


def get_host_memory_info():
    mem_info = psutil.phymem_usage()
    return (mem_info.total, mem_info.free)


def get_disk_info(path):
    disk_info = psutil.disk_usage(path)
    return (disk_info.total, disk_info.free)


def get_cpu_count():
    return multiprocessing.cpu_count()


def get_free_port():
    sock = socket.socket()
    try:
        sock.bind(('', 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def remove_lines(file_name, pattern):
    lines = []
    found = False
    with open(file_name, 'r') as f:
        for s in f.readlines():
            if re.match(pattern, s):
                found = True
            else:
                lines.append(s)
    if found:
        with open(file_name, 'w') as f:
            f.writelines(lines)
    return found


def get_text(file_name, pattern):
    with open(file_name, 'r') as f:
        for s in f.readlines():
            m = re.match(pattern, s)
            if m:
                return m.groups()


def replace_text(file_name, pattern, replacement):
    lines = []
    found = False
    with open(file_name, 'r') as f:
        for s in f.readlines():
            if re.match(pattern, s):
                found = True
                new_s = re.sub(pattern, replacement, s)
            else:
                new_s = s
            lines.append(new_s)
    if found:
        with open(file_name, 'w') as f:
            f.writelines(lines)
    return found
