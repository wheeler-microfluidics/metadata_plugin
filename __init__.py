"""
Copyright 2015 Christian Fobel

This file is part of metadata_plugin.

metadata_plugin is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

metadata_plugin is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with metadata_plugin.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging

from path_helpers import path
from flatland import Form, String
from microdrop.plugin_helpers import AppDataController, get_plugin_info
from microdrop.plugin_manager import (PluginGlobals, Plugin, IPlugin,
                                      implements)
from microdrop.app_context import get_app
import gtk

PluginGlobals.push_env('microdrop.managed')

logger = logging.getLogger(__name__)

class MetadataPlugin(Plugin, AppDataController):
    """
    This class is automatically registered with the PluginManager.
    """
    implements(IPlugin)
    version = get_plugin_info(path(__file__).parent).version
    plugin_name = get_plugin_info(path(__file__).parent).plugin_name

    AppFields = Form.of(String.named('json_schema')
                        .using(optional=True,
                               properties={'show_in_gui': False}))

    def __init__(self):
        self.name = self.plugin_name
        self.timeout_id = None
        self.start_time = None
        self.meta_data_menu = None

    def create_ui(self):
        self.meta_data_menu = gtk.MenuItem("DMF control board")
        self.meta_data_menu.connect('activate', self.on_meta_data_menu__activate)
        app = get_app()
        app.main_window_controller.menu_tools.append(self.meta_data_menu)

    def destroy_ui(self):
        app = get_app()
        app.main_window_controller.menu_tools.remove(self.meta_data_menu)

    def on_meta_data_menu__activate(self, widget, data):
        import pdb; pdb.set_trace()

    def on_plugin_enable(self):
        self.create_ui()

    def on_plugin_disable(self):
        self.destroy_ui()

    def on_experiment_log_changed(self, experiment_log):
        experiment_log.add_data({}, self.name)
        import pdb; pdb.set_trace()

PluginGlobals.pop_env()
