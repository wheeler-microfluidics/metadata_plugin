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
                                      ScheduleRequest, implements)
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
        self.meta_data_menu = gtk.MenuItem('Edit experiment metadata')
        self.meta_data_menu.connect('activate', self.on_meta_data_menu__activate)
        self.meta_data_menu.show()
        app = get_app()
        if not hasattr(app, 'experiment_log') or app.experiment_log is None:
            self.meta_data_menu.set_sensitive(False)
        app.main_window_controller.menu_tools.append(self.meta_data_menu)

    def destroy_ui(self):
        app = get_app()
        app.main_window_controller.menu_tools.remove(self.meta_data_menu)

    ###########################################################################
    # Mutator methods
    def edit_metadata(self):
        from pygtkhelpers.schema import schema_dialog

        app = get_app()
        if app.experiment_log is None:
            return
        metadata = app.experiment_log.data[0].get(self.name, {})
        schema = {'type': 'object',
                  'properties': {'device_id': {'type': 'string', 'default': '',
                                               'index': 0},
                                 'sample_id': {'type': 'string', 'default': '',
                                               'index': 1}}}
        try:
            data = schema_dialog(schema, data=metadata, max_width=320,
                                 max_fps=15, title='Edit metadata',
                                 parent=app.main_window_controller.view)
        except ValueError:
            pass
        except KeyError:
            pass
        else:
            app.experiment_log.data[0][self.name] = dict(data.items())

    ###########################################################################
    # Callback methods
    def on_experiment_log_changed(self, experiment_log):
        self.meta_data_menu.set_sensitive(True)
        experiment_log.add_data({}, self.name)
        self.edit_metadata()

    def on_meta_data_menu__activate(self, widget):
        self.edit_metadata()

    def on_plugin_enable(self):
        self.create_ui()

    def on_plugin_disable(self):
        self.destroy_ui()

    ###########################################################################
    # Accessor methods
    def get_schedule_requests(self, function_name):
        """
        Returns a list of scheduling requests (i.e., ScheduleRequest
        instances) for the function specified by function_name.
        """
        if function_name == 'on_experiment_log_changed':
            # Ensure that the app's reference to the new experiment log gets
            # set.
            return [ScheduleRequest('microdrop.app', self.name)]
        else:
            return []


PluginGlobals.pop_env()
