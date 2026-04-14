import time
from shared import cache


class TestCache:
    def setup_method(self):
        cache.invalidate()

    def test_set_and_get(self):
        cache.set("key1", {"data": [1, 2, 3]})
        assert cache.get("key1") == {"data": [1, 2, 3]}

    def test_get_missing_key(self):
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache.set("short", "value", ttl=0)
        time.sleep(0.01)
        assert cache.get("short") is None

    def test_invalidate_single_key(self):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate("a")
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_invalidate_all(self):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate()
        assert cache.get("a") is None
        assert cache.get("b") is None
