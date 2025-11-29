from typing import Dict, Type
from .openligadb import SportsProvider


_adapters: Dict[str, SportsProvider] = {}
_adapter_registry: Dict[str, Type[SportsProvider]] = {}


def register_adapter(name: str, adapter_class: Type[SportsProvider]):
    """Register adapter class."""
    _adapter_registry[name] = adapter_class


async def get_adapter(name: str, settings) -> SportsProvider:
    """Get or create adapter instance."""
    if name not in _adapters:
        _adapters[name] = _adapter_registry[name](settings)
    return _adapters[name]