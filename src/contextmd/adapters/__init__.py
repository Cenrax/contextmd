"""Provider adapters for ContextMD."""

from contextmd.adapters.base import ProviderAdapter
from contextmd.adapters.registry import AdapterRegistry, detect_provider

__all__ = ["ProviderAdapter", "AdapterRegistry", "detect_provider"]
