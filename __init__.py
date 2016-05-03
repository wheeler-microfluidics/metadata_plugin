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
import json
import logging

from flatland import Form, String
from microdrop.app_context import get_app
from microdrop.plugin_helpers import AppDataController, get_plugin_info
from noconflict import classmaker
from path_helpers import path
from pygtkhelpers.utils import gsignal
from redirect_io import nostderr
import gobject
import gtk
import jsonschema
import microdrop.plugin_manager as pm

pm.PluginGlobals.push_env('microdrop.managed')

logger = logging.getLogger(__name__)

class MetadataPlugin(pm.Plugin, gobject.GObject, AppDataController):
    """
    This class is automatically registered with the PluginManager.
    """
    # Without the follow line, cannot inherit from both `Plugin` and
    # `gobject.GObject`.  See [here][1] for more details.
    #
    # [1]: http://code.activestate.com/recipes/204197-solving-the-metaclass-conflict/
    __metaclass__ = classmaker()
    pm.implements(pm.IPlugin)
    gsignal('metadata-changed', object, object)
    version = get_plugin_info(path(__file__).parent).version
    plugin_name = get_plugin_info(path(__file__).parent).plugin_name

    AppFields = Form.of(String.named('video_config')
                        .using(default='null', optional=True,
                               properties={'show_in_gui': False}),
                        String.named('json_schema')
                        .using(optional=True,
                               default=json
                               .dumps({"type": "object", "properties":
                                       {"device_id": {"default": "device_id",
                                                      "index": 0, "type":
                                                      "string"},
                                        "sample_id": {"default": "sample_id",
                                                      "index": 1, "type":
                                                      "string"}}}),
                               properties={'show_in_gui': True}))

    def __init__(self):
        gobject.GObject.__init__(self)
        super(MetadataPlugin, self).__init__()
        self.name = self.plugin_name
        self.timeout_id = None
        self.start_time = None
        self.menu_item = None
        self.menu = None
        self.video_config_menu = None
        self.metadata_menu = None
        self.connect('metadata-changed', self.on_metadata_changed)
        self.connect('metadata-changed', lambda obj, original_metadata,
                     metadata: pm.emit_signal('on_metadata_changed',
                                              original_metadata, metadata))

    def create_ui(self):
        self.menu = gtk.Menu()
        self.menu_item = gtk.MenuItem(self.name)
        self.video_config_menu = gtk.MenuItem('Set barcode scanner video config...')
        self.video_config_menu.connect('activate', self.on_video_config_menu__activate)
        self.metadata_menu = gtk.MenuItem('Edit experiment metadata...')
        self.metadata_menu.connect('activate', self.on_metadata_menu__activate)
        app = get_app()
        if not hasattr(app, 'experiment_log') or app.experiment_log is None:
            self.metadata_menu.set_sensitive(False)
        self.menu.append(self.video_config_menu)
        self.menu.append(self.metadata_menu)
        self.menu.show_all()
        self.menu_item.set_submenu(self.menu)
        self.menu_item.show_all()
        app.main_window_controller.menu_tools.append(self.menu_item)

    def destroy_ui(self):
        app = get_app()
        app.main_window_controller.menu_tools.remove(self.menu_item)
        self.menu_item.destroy()
        self.menu.destroy()

    def get_label(self):
        app = get_app()

        vbox = app.main_window_controller.vbox2
        main_window_children = vbox.get_children()

        # Get reference to metadata label (or add it if necessary).
        labels = [widget for widget in main_window_children
                  if isinstance(widget, gtk.Label) and (widget.props.name ==
                                                        'metadata')]
        if labels:
            # Metadata label has already been added.  Use existing label.
            label_metadata = labels[0]
        else:
            # Metadata label has not been added.  Create new metadata label.
            label_metadata = gtk.Label()
            label_metadata.props.name = 'metadata'
            label_metadata.set_alignment(0, .5)  # Left, middle vertical align
            vbox.pack_start(label_metadata, False, False, 0)
            # Find position in main window `gtk.VBox` to insert metadata label
            # (after first set of labels).
            for i, child in enumerate(main_window_children):
                if not isinstance(child, gtk.Label):
                    break
            # Move metadata label to new position.
            vbox.reorder_child(label_metadata, i)
            # Display label
            label_metadata.show()
        return label_metadata

    ###########################################################################
    # Mutator methods
    def edit_metadata(self):
        from pygtkhelpers.schema import schema_dialog

        app = get_app()
        metadata = self.get_metadata()
        schema = json.loads(self.get_app_values()['json_schema'])
        video_config = json.loads(self.get_app_values().get('video_config',
                                                            'null'))
        if video_config is None:
            video_config = {}
        device_name = video_config.get('device_name')
        max_width = video_config.get('width', 320)
        max_fps = video_config.get('framerate', 15)
        try:
            data = schema_dialog(schema, data=metadata,
                                 device_name=device_name, max_width=max_width,
                                 max_fps=max_fps, title='Edit metadata',
                                 parent=app.main_window_controller.view)
        except (KeyError, ValueError):
            logger.error('Error setting metadata scanner video config.',
                         exc_info=True)
        else:
            self.set_metadata(data)

    def set_metadata(self, data):
        '''
        Args
        ----

            data (dict) : New metadata to replace existing metadata.

        Emits `metadata-changed` signal with original and new metadata.
        '''
        app = get_app()
        # Validate new metadata against schema.
        jsonschema.validate(data, self.schema)
        original_metadata = self.get_metadata()
        app.experiment_log.metadata[self.name] = data
        self.emit('metadata-changed', original_metadata,
                  app.experiment_log.metadata[self.name])

    def set_video_config(self, config):
        '''
        Args
        ----

            config (pandas.Series) : Video configuration (or `None`).
        '''
        app = get_app()
        app_values = self.get_app_values()
        config_json = (json.dumps(config) if config is None else
                       config.to_json())
        self.set_app_values({'video_config': config_json})

    def update_metadata(self, data):
        '''
        Args
        ----

            data (dict) : Partial metadata to update existing metadata.
                In other words, not all metadata keys are necessary in `data`.
        '''
        metadata = self.get_metadata()
        metadata.update(data.items())
        self.set_metadata(metadata)

    ###########################################################################
    # Callback methods
    def on_experiment_log_changed(self, experiment_log):
        self.metadata_menu.set_sensitive(True)
        experiment_log.add_data({}, self.name)
        self.edit_metadata()

    def on_metadata_menu__activate(self, widget):
        self.edit_metadata()

    def on_metadata_changed(self, obj, original_metadata, metadata):
        '''
        Update metadata label in GUI when metadata is changed.
        '''
        label_metadata = self.get_label()

        # Order metadata within label according to order in schema.
        ordered_schema = sorted(self.schema['properties'].items(),
                                key=lambda (k, v): (v.get('index', -1), k))
        # Set metadata label content.
        label_metadata.set_markup(' ' + '\t'
                                    .join(['<b>{}:</b> {}'
                                            .format(k.replace('_', ' '),
                                                    metadata[k])
                                            for k, v in ordered_schema]))

    def on_plugin_enable(self):
        self.create_ui()
        super(MetadataPlugin, self).on_plugin_enable()

    def on_plugin_disable(self):
        self.destroy_ui()

    def on_video_config_menu__activate(self, widget):
        with nostderr():
            from pygst_utils.video_view.mode import video_mode_dialog
            from pygst_utils.video_source import get_source_capabilities

        gtk.gdk.threads_init()
        df_video_configs = (get_source_capabilities()
                            .sort_values(['device_name', 'width', 'framerate'],
                                         ascending=[True, True, True]))
        df_video_configs = df_video_configs.loc[df_video_configs.width >= 320]
        try:
            config = video_mode_dialog(df_video_configs=df_video_configs,
                                       title='Select barcode scanner video '
                                       'config')
        except RuntimeError:
            # User cancelled dialog.  Do nothing.
            pass
        else:
            self.set_video_config(config)

    ###########################################################################
    # Accessor methods
    def get_metadata(self):
        app = get_app()
        if app.experiment_log is None:
            return {}
        return app.experiment_log.metadata.get(self.name, {}).copy()

    def get_schedule_requests(self, function_name):
        """
        Returns a list of scheduling requests (i.e., ScheduleRequest
        instances) for the function specified by function_name.
        """
        if function_name == 'on_experiment_log_changed':
            # Ensure that the app's reference to the new experiment log gets
            # set.
            return [pm.ScheduleRequest('microdrop.app', self.name)]
        else:
            return []

    ###########################################################################
    # Properties
    @property
    def schema(self):
        return json.loads(self.get_app_values()['json_schema'])


pm.PluginGlobals.pop_env()
