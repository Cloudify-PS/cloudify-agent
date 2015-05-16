#########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import shutil
import os

from cloudify.utils import setup_logger
from cloudify.utils import LocalCommandRunner

from cloudify_agent.api import utils
from cloudify_agent import VIRTUALENV


default_logger = setup_logger('cloudify_agent.api.plugins.installer')


class PluginInstaller(object):

    def __init__(self, logger=None):
        self.logger = logger or default_logger
        self.runner = LocalCommandRunner(logger=self.logger)

    def install(self, source, args=''):

        """
        Install the plugin to the current virtualenv.

        :param source: URL to the plugin source code.
        :type source: str
        :param args: extra installation arguments passed to the pip command
        :type args: str
        """

        plugin_dir = None
        try:
            plugin_dir = utils.extract_package_to_dir(source)
            self._install_package(plugin_dir, args)
            plugin_name = utils.extract_package_name(plugin_dir)
        finally:
            if plugin_dir:
                shutil.rmtree(plugin_dir)

        return plugin_name

    def _install_package(self, plugin_dir, args):
        command = '{0} install {1} {2}'.format(
            os.path.join(VIRTUALENV, 'bin', 'pip'), args, plugin_dir)
        self.runner.run(command, cwd=plugin_dir)
