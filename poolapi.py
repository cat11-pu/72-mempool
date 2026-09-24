"""poolapi.py：对外门面（老接口 allocate/free/deref 不能改）。"""
from __future__ import annotations

from mempool import Pool


class Arena:
    def __init__(self, block: int = 4, capacity: int = 8):
        self.pool = Pool(block, capacity)

    def allocate(self, payload: str) -> dict:
        return self.pool.allocate(payload)

    def free(self, handle: int) -> dict:
        return self.pool.free(handle)

    def deref(self, handle: int) -> dict:
        return self.pool.deref(handle)

    def compact(self) -> dict:
        return self.pool.compact()

    def snapshot(self) -> bytes:
        return self.pool.persist()

    def rebuild(self, blob: bytes = None) -> dict:
        return self.pool.restore(blob)
