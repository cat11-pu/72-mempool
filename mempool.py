"""mempool.py：内存池（基线：每次新分配，无复用、无整理）。"""
from __future__ import annotations


class Pool:
    def __init__(self, block: int = 4, capacity: int = 8):
        self.block = block
        self.capacity = capacity
        self.slots = {}
        self.handles = {}
        self.next_handle = 1
        self.allocs = 0
        self.compactions = 0
        self.moved = 0

    def allocate(self, payload: str) -> dict:
        """基线：顺序往后放，从不复用空洞。"""
        index = len(self.slots)
        self.slots[index] = payload
        self.allocs += 1
        handle = self.next_handle
        self.next_handle += 1
        self.handles[handle] = index
        return {"handle": handle, "slot": index}

    def free(self, handle: int) -> dict:
        existed = handle in self.handles
        self.handles.pop(handle, None)
        return {"freed": existed}

    def deref(self, handle: int) -> dict:
        index = self.handles.get(handle)
        return {"value": self.slots.get(index) if index is not None else None}

    def compact(self) -> dict:
        raise NotImplementedError("碎片整理还没实现")

    def persist(self) -> bytes:
        raise NotImplementedError("快照还没实现")

    def restore(self, blob: bytes = None) -> dict:
        raise NotImplementedError("重启恢复还没实现")

    def stats(self) -> dict:
        return {"slots": len(self.slots), "handles": len(self.handles),
                "allocs": self.allocs, "compactions": self.compactions, "moved": self.moved,
                "block": self.block, "capacity": self.capacity}
