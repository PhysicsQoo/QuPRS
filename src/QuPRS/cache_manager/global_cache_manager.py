# cache_manager/global_cache_manager.py


class GlobalCacheManager:
    def __init__(self):
        self._caches = []

    def register(self, func):
        self._caches.append(func)

    def __repr__(self) -> str:
        return str(self.cache_info)

    @property
    def cache(self):
        return self._caches

    @property
    def cache_info(self):
        return {f"{item.__name__}": item.cache_info() for item in self._caches}

    @property
    def hit_rate(self):
        return {
            f"{item.__name__}": (
                item.cache_info().hits
                / (item.cache_info().misses + item.cache_info().hits)
                if item.cache_info().misses + item.cache_info().hits > 0
                else 0
            )
            for item in self._caches
        }

    def clear_all_caches(self):
        for func in self._caches:
            func.cache_clear()

    def clear_cache(self, func):
        func.cache_clear()
