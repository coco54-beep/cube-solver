# 不完整录入检查

10 个类型／阶数输入，10 个被求解入口拒绝。

普通及块形魔方删除一个块，多面体将一个贴纸置为未录入，SQ1 删除一个角度槽位。这只检查输入完整性，不替代排列奇偶性、块朝向等全部非法状态验证。

| 类型 | 阶数 | 结果 | 返回信息 |
|---|---:|---|---|
| 五魔方 | 4 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 5 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 6 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 7 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 8 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 9 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 10 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 11 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 12 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 13 | rejected | RuntimeError: Please enter every sticker |
