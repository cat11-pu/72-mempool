import unittest

from mempool import Pool
from poolapi import Arena


class TestPool(unittest.TestCase):
    def test_allocate_returns_handle(self):
        self.assertEqual(Pool().allocate("x")["handle"], 1)

    def test_deref_after_allocate(self):
        pool = Pool()
        handle = pool.allocate("x")["handle"]
        self.assertEqual(pool.deref(handle)["value"], "x")

    def test_deref_freed(self):
        pool = Pool()
        handle = pool.allocate("x")["handle"]
        pool.free(handle)
        self.assertIsNone(pool.deref(handle)["value"])

    def test_stats_shape(self):
        self.assertIn("block", Pool().stats())

    def test_arena_wraps_pool(self):
        arena = Arena()
        arena.allocate("x")
        self.assertEqual(arena.pool.stats()["allocs"], 1)


if __name__ == "__main__":
    unittest.main()
