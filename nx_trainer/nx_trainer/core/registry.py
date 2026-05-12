"""Plugin registry system with Protocol contracts."""
from typing import Dict, Type, Optional, Callable
from collections import defaultdict
import inspect


class PluginRegistry:
    _optimizers: Dict[str, Type] = {}
    _methods: Dict[str, Type] = {}
    _backends: Dict[str, Type] = {}
    _data_loaders: Dict[str, Type] = {}
    _exporters: Dict[str, Type] = {}
    _hooks: Dict[str, list] = defaultdict(list)

    @classmethod
    def register_optimizer(cls, name: str):
        def decorator(optimizer_cls: Type) -> Type:
            cls._optimizers[name.lower()] = optimizer_cls
            return optimizer_cls
        return decorator

    @classmethod
    def register_method(cls, name: str):
        def decorator(method_cls: Type) -> Type:
            cls._methods[name.lower()] = method_cls
            return method_cls
        return decorator

    @classmethod
    def register_backend(cls, name: str):
        def decorator(backend_cls: Type) -> Type:
            cls._backends[name.lower()] = backend_cls
            return backend_cls
        return decorator

    @classmethod
    def register_data_loader(cls, name: str):
        def decorator(loader_cls: Type) -> Type:
            cls._data_loaders[name.lower()] = loader_cls
            return loader_cls
        return decorator

    @classmethod
    def register_exporter(cls, name: str):
        def decorator(exporter_cls: Type) -> Type:
            cls._exporters[name.lower()] = exporter_cls
            return exporter_cls
        return decorator

    @classmethod
    def register_hook(cls, event: str):
        def decorator(func: Callable) -> Callable:
            cls._hooks[event].append(func)
            return func
        return decorator

    @classmethod
    def get_optimizer(cls, name: str) -> Optional[Type]:
        return cls._optimizers.get(name.lower())

    @classmethod
    def get_method(cls, name: str) -> Optional[Type]:
        return cls._methods.get(name.lower())

    @classmethod
    def get_backend(cls, name: str) -> Optional[Type]:
        return cls._backends.get(name.lower())

    @classmethod
    def get_data_loader(cls, name: str) -> Optional[Type]:
        return cls._data_loaders.get(name.lower())

    @classmethod
    def get_exporter(cls, name: str) -> Optional[Type]:
        return cls._exporters.get(name.lower())

    @classmethod
    def list_optimizers(cls) -> list:
        return list(cls._optimizers.keys())

    @classmethod
    def list_methods(cls) -> list:
        return list(cls._methods.keys())

    @classmethod
    def list_backends(cls) -> list:
        return list(cls._backends.keys())

    @classmethod
    def trigger_hook(cls, event: str, *args, **kwargs):
        for hook in cls._hooks.get(event, []):
            hook(*args, **kwargs)

    @classmethod
    def discover_plugins(cls, package: str):
        import importlib
        try:
            module = importlib.import_module(package)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    for attr in dir(obj):
                        if attr.startswith("_registry_"):
                            getattr(obj, attr)(cls)
        except ImportError:
            pass