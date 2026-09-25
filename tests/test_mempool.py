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


class TestPoolReuse(unittest.TestCase):
    def test_allocate_reuses_smallest_hole(self):
        pool = Pool()
        first = pool.allocate("a")["handle"]
        pool.allocate("b")
        pool.free(first)
        self.assertEqual(pool.allocate("c")["slot"], 0)

    def test_double_free_is_noop(self):
        pool = Pool()
        handle = pool.allocate("x")["handle"]
        self.assertTrue(pool.free(handle)["freed"])
        self.assertFalse(pool.free(handle)["freed"])
        self.assertIsNone(pool.deref(handle)["value"])


class TestPoolCompact(unittest.TestCase):
    def test_compact_preserves_deref_and_reports(self):
        pool = Pool()
        handles = [pool.allocate(p)["handle"] for p in "abcde"]
        pool.free(handles[1])
        pool.free(handles[3])
        before = {h: pool.deref(h)["value"] for h in handles}
        result = pool.compact()
        after = {h: pool.deref(h)["value"] for h in handles}
        self.assertEqual(before, after)
        self.assertEqual(result, {"moved": 2, "holes": 5})

    def test_allocate_after_compact_uses_first_hole(self):
        pool = Pool()
        handles = [pool.allocate(p)["handle"] for p in "abcde"]
        pool.free(handles[0])
        pool.free(handles[1])
        pool.compact()
        self.assertEqual(pool.allocate("f")["slot"], 3)


class TestPoolPersist(unittest.TestCase):
    def test_restore_matches_checkpoint_after_compact(self):
        pool = Pool()
        doomed = pool.allocate("a")["handle"]
        keep = pool.allocate("b")["handle"]
        pool.free(doomed)
        pool.compact()
        reborn = Pool()
        info = reborn.restore(pool.persist())
        self.assertEqual((info["slots"], info["handles"]), (1, 1))
        self.assertEqual(info["moved"], pool.stats()["moved"])
        self.assertEqual(reborn.deref(keep)["value"], "b")

    def test_restore_without_compact_roundtrips_current_state(self):
        pool = Pool()
        handle = pool.allocate("x")["handle"]
        reborn = Pool()
        reborn.restore(pool.persist())
        self.assertEqual(reborn.deref(handle)["value"], "x")

    def test_arena_snapshot_rebuild(self):
        arena = Arena()
        handle = arena.allocate("x")["handle"]
        arena.compact()
        clone = Arena()
        clone.rebuild(arena.snapshot())
        self.assertEqual(clone.deref(handle)["value"], "x")
