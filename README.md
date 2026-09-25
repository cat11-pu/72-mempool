# mempool

纯 Python 标准库的内存池：句柄与槽号解耦，支持空洞复用、碎片整理与快照恢复。

## 用法

    from mempool import Pool

    pool = Pool(block=4, capacity=8)
    handle = pool.allocate("payload")["handle"]  # 句柄单调递增，占用槽号最小的空洞
    pool.deref(handle)["value"]                  # 解引用；已释放返回 None
    pool.free(handle)                            # 释放对应槽
    pool.compact()                               # 存活块按槽号顺序搬到最前面
                                                 # 返回 {"moved": 搬迁块数, "holes": 碎片槽数}
    blob = pool.persist()                        # 落盘最近 compact 的一致性检查点
    pool.restore(blob)                           # 恢复槽内容、句柄映射与搬迁计数

- 对外只暴露句柄；`compact()` 只换槽号、不改数据，整理前后同一句柄解引用完全相同。
- 整理后新分配落在紧邻存活块的第一个空槽。
- 分配经空闲槽最小堆取槽号最小的空洞；整理耗时与存活块数同阶。
- 对外门面见 `poolapi.Arena`（`allocate/free/deref/compact/snapshot/rebuild`）。

## 测试

    python3 -m unittest discover -s tests -v

## 场景自检

    python3 check_sample.py
