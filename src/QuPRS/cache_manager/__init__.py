# cache_manager/__init__.py
from .cache_decorator import tracked_lru_cache
from .global_cache_manager import GlobalCacheManager

cache_manager = GlobalCacheManager()
