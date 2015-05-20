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

import mock
from mock import MagicMock

from cloudify_agent import VIRTUALENV
from cloudify_agent.tests.shell.commands import BaseCommandLineTestCase


@mock.patch('cloudify_agent.api.plugins.installer.PluginInstaller.install')
@mock.patch('cloudify_agent.shell.commands.plugins.DaemonFactory')
class TestConfigureCommandLine(BaseCommandLineTestCase):

    def test_install(self, factory, mock_install):
        daemon1 = MagicMock()
        daemon1.virtualenv = VIRTUALENV
        daemon2 = MagicMock()
        daemon2.virtualenv = VIRTUALENV
        factory.load_all.return_value = [daemon1, daemon2]
        self._run('cfy-agent plugins install --source=source --args=args')
        mock_install.assert_called_once_with('source', 'args')
        load_all = factory.load_all
        load_all.assert_called_once_with()
        daemons = load_all.return_value
        for daemon in daemons:
            register = daemon.register
            register.assert_called_once_with(mock_install.return_value)
