"""mempool.py：内存池（句柄与槽号解耦，支持空洞复用、碎片整理、快照恢复）。"""
from __future__ import annotations

import heapq
import json


class Pool:
    def __init__(self, block: int = 4, capacity: int = 8):
        self.block = block
        self.capacity = capacity
        self.slots = {}          # 槽号 -> 数据（只保存活块）
        self.handles = {}        # 句柄 -> 槽号（对外只暴露句柄）
        self.next_handle = 1
        self.allocs = 0
        self.compactions = 0
        self.moved = 0
        self._free = []          # 空闲槽最小堆（空洞索引）
        self._high_water = 0     # 下一个从未使用过的槽号
        self._checkpoint = None  # 最近一次 compact 形成的一致性检查点

    def allocate(self, payload: str) -> dict:
        """占用槽号最小的空洞；没有空洞时顺序使用新槽。"""
        if self._free:
            index = heapq.heappop(self._free)
        elif self._high_water < self.capacity:
            index = self._high_water
            self._high_water += 1
        else:
            raise RuntimeError("mempool: capacity exhausted")
        self.slots[index] = payload
        self.allocs += 1
        handle = self.next_handle
        self.next_handle += 1
        self.handles[handle] = index
        return {"handle": handle, "slot": index}

    def free(self, handle: int) -> dict:
        index = self.handles.pop(handle, None)
        if index is None:
            return {"freed": False}
        del self.slots[index]
        heapq.heappush(self._free, index)
        return {"freed": True}

    def deref(self, handle: int) -> dict:
        index = self.handles.get(handle)
        return {"value": self.slots.get(index) if index is not None else None}

    def compact(self) -> dict:
        """把存活块按槽号顺序搬到最前面，只换槽号、不改数据。"""
        live = sorted(self.slots)
        remap = {old: new for new, old in enumerate(live)}
        moved = sum(1 for old, new in remap.items() if old != new)
        self.slots = {new: self.slots[old] for old, new in remap.items()}
        self.handles = {handle: remap[index] for handle, index in self.handles.items()}
        self._free = []
        self._high_water = len(live)
        self.compactions += 1
        self.moved += moved
        self._checkpoint = self._snapshot()
        return {"moved": moved, "holes": self.capacity - len(live)}

    def persist(self) -> bytes:
        """落盘最近一次 compact 的一致性检查点；尚未 compact 时快照当前状态。"""
        state = self._checkpoint if self._checkpoint is not None else self._snapshot()
        return json.dumps(state).encode("utf-8")

    def restore(self, blob: bytes = None) -> dict:
        if blob is not None:
            text = blob.decode("utf-8") if isinstance(blob, (bytes, bytearray)) else blob
            state = json.loads(text)
            self.slots = {int(k): v for k, v in state["slots"].items()}
            self.handles = {int(k): v for k, v in state["handles"].items()}
            self.next_handle = state["next_handle"]
            self.allocs = state["allocs"]
            self.compactions = state["compactions"]
            self.moved = state["moved"]
            self._free = list(state["free"])
            heapq.heapify(self._free)
            self._high_water = state["high_water"]
            self._checkpoint = state
        return {"slots": len(self.slots), "handles": len(self.handles),
                "allocs": self.allocs, "compactions": self.compactions,
                "moved": self.moved}

    def stats(self) -> dict:
        return {"slots": len(self.slots), "handles": len(self.handles),
                "allocs": self.allocs, "compactions": self.compactions, "moved": self.moved,
                "block": self.block, "capacity": self.capacity}

    def _snapshot(self) -> dict:
        return {
            "block": self.block,
            "capacity": self.capacity,
            "slots": dict(self.slots),
            "handles": dict(self.handles),
            "next_handle": self.next_handle,
            "allocs": self.allocs,
            "compactions": self.compactions,
            "moved": self.moved,
            "free": list(self._free),
            "high_water": self._high_water,
        }
