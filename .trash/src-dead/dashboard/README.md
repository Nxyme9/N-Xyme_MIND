# N-Xyme MIND Dashboard — Modular System

A **modular, frictionless, and moddable** dashboard system for the N-Xyme MIND ecosystem.

## Architecture

```
src/dashboard/
├── __init__.py              # Package init
├── hot_reload.py            # Hot-reload system
├── panels/                  # Panel modules
│   ├── __init__.py
│   ├── overview.py          # Overview panel
│   ├── memory.py            # Memory panel
│   ├── intelligence.py      # Intelligence panel
│   └── registry.py          # Panel registry helper
├── plugins/                 # Plugin system
│   ├── __init__.py          # Re-exports
│   ├── plugin_system.py     # Core plugin system
│   └── example_plugin.py    # Example plugin
├── themes/                  # Theme system
│   ├── __init__.py          # Re-exports
│   └── theme_system.py      # Core theme system
└── config/                  # Configuration
    ├── __init__.py          # Re-exports
    └── dashboard_config.py  # Dashboard configuration
```

## Quick Start

### 1. Create a Plugin

```python
# src/dashboard/plugins/my_plugin.py
from src.dashboard.plugins import DashboardPlugin, PanelRegistry, CommandRegistry

class MyPlugin(DashboardPlugin):
    name = "my-plugin"
    version = "1.0.0"
    description = "My custom plugin"
    
    def register_panels(self, registry: PanelRegistry):
        registry.add_panel("my-panel", self._get_content)
    
    def register_commands(self, registry: CommandRegistry):
        registry.add_command("my-command", self._run_command)
    
    def _get_content(self, dashboard) -> str:
        return "My panel content"
    
    def _run_command(self, dashboard):
        dashboard.notify("My command executed")
```

### 2. Create a Theme

```python
# src/dashboard/themes/my_theme.py
from src.dashboard.themes.theme_system import Theme

class MyTheme(Theme):
    name = "my-theme"
    description = "My custom theme"
    dark_mode = True
    
    def get_css(self) -> str:
        return """
Screen { background: #1a1a1a; }
#sidebar { background: #2a2a2a; }
"""
```

### 3. Add a Panel

```python
# src/dashboard/panels/my_panel.py
from typing import Any

def get_content(dashboard: Any) -> str:
    """Get panel content."""
    d = dashboard.live_data
    return f"My Panel\n\nData: {d.get('my_key', 'N/A')}"
```

### 4. Configure Dashboard

```python
# .sisyphus/dashboard-config.json
{
  "panels": [
    {"name": "overview", "title": "Overview", "enabled": true, "order": 0},
    {"name": "my-panel", "title": "My Panel", "enabled": true, "order": 1}
  ],
  "settings": {
    "refresh_rate": 10,
    "theme": "my-theme",
    "dark_mode": true
  },
  "plugins": {
    "my-plugin": true
  }
}
```

## Plugin System

### Plugin Lifecycle

1. **Discovery**: Plugins are automatically discovered from `src/dashboard/plugins/*.py`
2. **Registration**: Each plugin registers panels, commands, and themes
3. **Loading**: Plugin's `on_load()` is called with dashboard instance
4. **Running**: Plugin responds to events via `on_event()`
5. **Unloading**: Plugin's `on_unload()` is called for cleanup

### Plugin API

```python
class DashboardPlugin:
    name: str = "unnamed-plugin"
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    
    def register_panels(self, registry: PanelRegistry): ...
    def register_commands(self, registry: CommandRegistry): ...
    def register_themes(self, registry: ThemeRegistry): ...
    def on_load(self, dashboard): ...
    def on_unload(self, dashboard): ...
    def on_event(self, event: str, data: Any): ...
```

## Theme System

### Theme API

```python
class Theme:
    name: str = "unnamed-theme"
    description: str = ""
    dark_mode: bool = True
    author: str = ""
    version: str = "0.0.0"
    
    def get_css(self) -> str: ...
    def get_color_palette(self) -> Dict[str, str]: ...
    def get_font_settings(self) -> Dict[str, str]: ...
```

## Hot-Reload

The dashboard automatically reloads:
- **Plugins**: When `src/dashboard/plugins/*.py` changes
- **Themes**: When `src/dashboard/themes/*.py` changes
- **Panels**: When `src/dashboard/panels/*.py` changes
- **Config**: When `src/dashboard/config/*.py` changes

Enable/disable hot-reload:
```python
from src.dashboard.hot_reload import start_hot_reload, stop_hot_reload

start_hot_reload(dashboard, interval=2.0)
stop_hot_reload()
```

## Configuration

### Dashboard Config

```python
from src.dashboard.config.dashboard_config import config, load_config, save_config

load_config()
config.set_setting("refresh_rate", 5)
config.set_preference("last_view", "memory")
save_config()
```

### Panel Definitions

```python
from src.dashboard.config.dashboard_config import PanelDefinition

panel = PanelDefinition(
    name="my-panel",
    title="My Panel",
    description="My custom panel",
    icon="🎨",
    enabled=True,
    order=5,
    module="src.dashboard.panels.my_panel",
    function="get_content"
)

config.add_panel(panel)
```

## File Structure

```
src/dashboard/
├── __init__.py              # Package init
├── hot_reload.py            # Hot-reload system (247 lines)
├── panels/                  # Panel modules
│   ├── __init__.py
│   ├── overview.py          # Overview panel (53 lines)
│   ├── memory.py            # Memory panel (57 lines)
│   ├── intelligence.py      # Intelligence panel (40 lines)
│   └── registry.py          # Panel registry helper (33 lines)
├── plugins/                 # Plugin system
│   ├── __init__.py          # Re-exports (27 lines)
│   ├── plugin_system.py     # Core plugin system (380 lines)
│   └── example_plugin.py    # Example plugin (127 lines)
├── themes/                  # Theme system
│   ├── __init__.py          # Re-exports (3 lines)
│   └── theme_system.py      # Core theme system (204 lines)
└── config/                  # Configuration
    ├── __init__.py          # Re-exports (3 lines)
    └── dashboard_config.py  # Dashboard configuration (264 lines)
```

**Total**: ~1,438 lines of modular, extensible code

## Extending the Dashboard

### Add a New Panel

1. Create `src/dashboard/panels/my_panel.py`
2. Implement `get_content(dashboard) -> str`
3. Register in `src/dashboard/panels/registry.py`
4. Add to `.sisyphus/dashboard-config.json`

### Add a New Plugin

1. Create `src/dashboard/plugins/my_plugin.py`
2. Subclass `DashboardPlugin`
3. Implement `register_panels()` and/or `register_commands()`
4. Plugin is automatically loaded on dashboard start

### Add a New Theme

1. Create `src/dashboard/themes/my_theme.py`
2. Subclass `Theme`
3. Implement `get_css()`
4. Theme is automatically loaded on dashboard start

## Best Practices

1. **Keep panels small**: Each panel should be <100 lines
2. **Use plugins for behavior**: Don't modify core dashboard code
3. **Use themes for appearance**: Don't hardcode colors in panels
4. **Use config for settings**: Don't hardcode values in code
5. **Test hot-reload**: Verify changes reload correctly

## Troubleshooting

### Plugin not loading
- Check file is in `src/dashboard/plugins/`
- Check file doesn't start with `_`
- Check plugin class subclasses `DashboardPlugin`
- Check plugin is enabled in config

### Theme not applying
- Check file is in `src/dashboard/themes/`
- Check theme class subclasses `Theme`
- Check theme is set in config

### Panel not showing
- Check file is in `src/dashboard/panels/`
- Check panel is registered in registry
- Check panel is enabled in config
