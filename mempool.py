"""mempool.py：内存池（句柄与槽号解耦，支持复用、整理、快照）。"""
from __future__ import annotations

import heapq
import json


class Pool:
    def __init__(self, block: int = 4, capacity: int = 8):
        self.block = block
        self.capacity = capacity
        self.slots = {}          # slot -> payload（仅存活槽）
        self.handles = {}        # handle -> slot
        self.next_handle = 1
        self.top = 0             # 高水位：从未使用过的下一个槽号
        self.free_slots = []     # 已释放槽号的最小堆（空洞索引）
        self.allocs = 0
        self.compactions = 0
        self.moved = 0

    def allocate(self, payload: str) -> dict:
        """取槽号最小的空洞；没有空洞则用高水位槽。"""
        if self.free_slots:
            index = heapq.heappop(self.free_slots)
        elif self.top < self.capacity:
            index = self.top
            self.top += 1
        else:
            raise RuntimeError("pool exhausted")
        self.slots[index] = payload
        self.allocs += 1
        handle = self.next_handle
        self.next_handle += 1
        self.handles[handle] = index
        return {"handle": handle, "slot": index}

    def free(self, handle: int) -> dict:
        index = self.handles.pop(handle, None)
        existed = index is not None
        if existed:
            self.slots.pop(index, None)
            heapq.heappush(self.free_slots, index)
        return {"freed": existed}

    def deref(self, handle: int) -> dict:
        index = self.handles.get(handle)
        return {"value": self.slots.get(index) if index is not None else None}

    def compact(self) -> dict:
        """存活块按槽号顺序搬到最前面，只换槽号不改数据。"""
        order = sorted((index, handle) for handle, index in self.handles.items())
        new_slots = {}
        moved = 0
        for new_index, (old_index, handle) in enumerate(order):
            new_slots[new_index] = self.slots[old_index]
            self.handles[handle] = new_index
            if new_index != old_index:
                moved += 1
        self.slots = new_slots
        self.top = len(order)
        self.free_slots = []
        self.compactions += 1
        self.moved += moved
        return {"moved": moved, "holes": self.capacity - self.top}

    def persist(self) -> bytes:
        state = {
            "block": self.block,
            "capacity": self.capacity,
            "slots": self.slots,
            "handles": self.handles,
            "next_handle": self.next_handle,
            "top": self.top,
            "allocs": self.allocs,
            "compactions": self.compactions,
            "moved": self.moved,
        }
        return json.dumps(state).encode("utf-8")

    def restore(self, blob: bytes = None) -> dict:
        state = json.loads(blob.decode("utf-8"))
        self.block = state["block"]
        self.capacity = state["capacity"]
        self.slots = {int(index): payload for index, payload in state["slots"].items()}
        self.handles = {int(handle): index for handle, index in state["handles"].items()}
        self.next_handle = state["next_handle"]
        self.top = state["top"]
        self.allocs = state["allocs"]
        self.compactions = state["compactions"]
        self.moved = state["moved"]
        used = set(self.slots)
        self.free_slots = [index for index in range(self.top) if index not in used]
        heapq.heapify(self.free_slots)
        return self.stats()

    def stats(self) -> dict:
        return {"slots": len(self.slots), "handles": len(self.handles),
                "allocs": self.allocs, "compactions": self.compactions, "moved": self.moved,
                "block": self.block, "capacity": self.capacity}
