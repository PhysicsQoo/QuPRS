# cache_manager/cache_decorator.py

from functools import lru_cache


def tracked_lru_cache(maxsize=128):

    def decorator(func):
        from . import cache_manager

        cached_func = lru_cache(maxsize=maxsize)(func)
        cache_manager.register(cached_func)

        # functools.lru_cache already preserves __wrapped__/__name__.
        # Returning it directly avoids an additional Python frame on every
        # RR cache hit/miss; the global cache manager still owns this object.
        return cached_func

    return decorator
