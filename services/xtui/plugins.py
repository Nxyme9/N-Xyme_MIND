"""Plugin system for XTUI — add custom commands and handlers."""
import os, importlib.util, sys

class Plugin:
    name = "base"
    description = "Base plugin"
    
    def on_register(self, app):
        pass
    
    def on_command(self, cmd, args, app):
        return None  # Not handled
    
    def on_tool_result(self, server, tool, result, app):
        pass
    
    def on_agent_switch(self, agent, app):
        pass
    
    def on_startup(self, app):
        pass
    
    def on_shutdown(self, app):
        pass

class PluginManager:
    def __init__(self, app, dirs=None):
        self.app = app
        self.plugins = []
        dirs = dirs or [os.path.expanduser("~/.xtui/plugins")]
        for d in dirs:
            self._load_dir(d)
    
    def _load_dir(self, directory):
        if not os.path.isdir(directory):
            return
        for fname in sorted(os.listdir(directory)):
            if fname.endswith(".py") and not fname.startswith("_"):
                self._load_file(os.path.join(directory, fname))
    
    def _load_file(self, path):
        try:
            spec = importlib.util.spec_from_file_location(f"xtui_plugin_{os.path.basename(path)}", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod.__name__] = mod
                spec.loader.exec_module(mod)
                for attr in dir(mod):
                    cls = getattr(mod, attr)
                    if isinstance(cls, type) and issubclass(cls, Plugin) and cls is not Plugin:
                        p = cls()
                        p.on_register(self.app)
                        self.plugins.append(p)
        except Exception as e:
            print(f"[xtui] Plugin load error {path}: {e}")
    
    def dispatch(self, method, *args):
        for p in self.plugins:
            try:
                getattr(p, method)(*args)
            except:
                pass
