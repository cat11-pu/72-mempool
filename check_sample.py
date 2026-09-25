"""check_sample.py：按 sample/ops.json 走一圈，打印验收面。"""
import json
import os
import sys

from mempool import Pool


def live_derefs(pool, handles):
    result = {}
    for name, handle in sorted(handles.items()):
        value = pool.deref(handle)["value"]
        if value is not None:
            result[name] = value
    return result


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("sample", "ops.json")
    with open(path, encoding="utf-8") as handle:
        spec = json.load(handle)
    pool = Pool(spec["block"], spec["capacity"])
    handles = {}
    for step in spec["ops"]:
        if step["op"] == "alloc":
            handles[step["name"]] = pool.allocate(step["payload"])["handle"]
        elif step["op"] == "free":
            pool.free(handles[step["name"]])
    before = live_derefs(pool, handles)
    compacted = pool.compact()
    after = live_derefs(pool, handles)
    blob = pool.persist()
    reborn = Pool(spec["block"], spec["capacity"])
    restored = reborn.restore(blob)
    reused = pool.allocate(spec["probe_payload"])
    invariant = before == after
    print("整理前句柄解引用 =", before)
    print("整理搬迁的块数 =", compacted.get("moved"))
    print("整理后碎片槽数 =", compacted.get("holes"))
    print("整理后句柄解引用 =", after)
    print("整理后新分配落在 =", reused.get("slot"))
    print("恢复后的槽数与句柄数 =", (restored.get("slots"), restored.get("handles")))
    print("恢复后的搬迁计数 =", restored.get("moved"))
    print("不变量（整理后句柄仍指向原数据） =", invariant)
    print("池容量 =", spec["capacity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
