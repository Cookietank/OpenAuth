import os
import sys

class PluginBase:
    """Base class for all plugins."""
    def __init__(self, app):
        self.app = app

    def setup(self):
        """Called when the plugin is initialized."""
        pass

    def config_updated(self):
        """Called instantly when the user clicks 'Save & Apply'."""
        pass

    def get_resource_path(self, relative_path):
        """Safely gets absolute paths for resources, compatible with PyInstaller EXEs."""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins =[]

    def register_plugin(self, plugin_class):
        plugin_instance = plugin_class(self.app)
        plugin_instance.setup()
        self.plugins.append(plugin_instance)

    def broadcast(self, event_name, *args, **kwargs):
        """Fires an event across all loaded plugins."""
        for plugin in self.plugins:
            method = getattr(plugin, event_name, None)
            if callable(method):
                method(*args, **kwargs)