# cache_manager/__init__.py
from .global_cache_manager import GlobalCacheManager
from .cache_decorator import tracked_lru_cache

cache_manager = GlobalCacheManager()
