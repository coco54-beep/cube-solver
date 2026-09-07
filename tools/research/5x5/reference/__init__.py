"""独立 5x5 降阶参考求解器（research oracle）。

与生产 `solver/edge5` 的贪心/beam/宏搜索**独立**的 reduction 实现，
用于生成参考完整解、挖掘「目标 A 翻转变为有效」的稳定区间。
"""
