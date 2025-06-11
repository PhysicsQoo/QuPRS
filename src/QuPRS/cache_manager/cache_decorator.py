# cache_manager/cache_decorator.py

from functools import lru_cache, wraps


def tracked_lru_cache(maxsize=128):
    
    def decorator(func):
        from . import cache_manager
        cached_func = lru_cache(maxsize=maxsize)(func)
        cache_manager.register(cached_func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cached_func(*args, **kwargs)
        
        return wrapper
    return decorator