# 不完整录入检查

87 个类型／阶数输入，86 个被求解入口拒绝。

普通及块形魔方删除一个块，多面体将一个贴纸置为未录入，SQ1 删除一个角度槽位。这只检查输入完整性，不替代排列奇偶性、块朝向等全部非法状态验证。

| 类型 | 阶数 | 结果 | 返回信息 |
|---|---:|---|---|
| 普通魔方 | 2 | rejected | RuntimeError: unsupported operand type(s) for >>: 'NoneType' and 'int' |
| 普通魔方 | 3 | rejected | RuntimeError: None |
| 普通魔方 | 4 | rejected | RuntimeError: '' |
| 普通魔方 | 5 | rejected | RuntimeError: None |
| 普通魔方 | 6 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 7 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 8 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 9 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 10 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 11 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 12 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 13 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 普通魔方 | 14 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 金字塔 | 2 | rejected | RuntimeError: Please enter every sticker |
| 金字塔 | 3 | rejected | RuntimeError: Please enter every sticker |
| 金字塔 | 4 | rejected | RuntimeError: Please enter every sticker |
| 金字塔 | 5 | rejected | RuntimeError: Please enter every sticker |
| 金字塔 | 6 | rejected | RuntimeError: Please enter every sticker |
| 金字塔 | 7 | rejected | RuntimeError: Please enter every sticker |
| 粽子 | 2 | rejected | RuntimeError: unsupported operand type(s) for >>: 'NoneType' and 'int' |
| 粽子 | 3 | rejected | RuntimeError: incomplete |
| 粽子 | 4 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 粽子 | 5 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 粽子 | 6 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 粽子 | 7 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 粽子 | 8 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 粽子 | 9 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 斜转 | 3 | rejected | RuntimeError: Please enter every sticker |
| 斜转 | 5 | rejected | RuntimeError: Please enter every sticker |
| 斜转 | 7 | rejected | RuntimeError: Please enter every sticker |
| 恐龙／格子 | 2 | rejected | RuntimeError: Please enter every sticker |
| 恐龙／格子 | 4 | rejected | RuntimeError: Please enter every sticker |
| 恐龙／格子 | 6 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 2 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 3 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 4 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 5 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 6 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 7 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 8 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 9 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 10 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 11 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 12 | rejected | RuntimeError: Please enter every sticker |
| 五魔方 | 13 | timeout | RuntimeError: InterruptedError |
| 魔塔 | 3 | rejected | RuntimeError: Please enter every sticker |
| 魔塔 | 4 | rejected | RuntimeError: Please enter every sticker |
| 魔塔 | 5 | rejected | RuntimeError: Please enter every sticker |
| 魔塔 | 6 | rejected | RuntimeError: Please enter every sticker |
| 魔塔 | 7 | rejected | RuntimeError: Please enter every sticker |
| 镜面 | 2 | rejected | RuntimeError: '<' not supported between instances of 'NoneType' and 'NoneType' |
| 镜面 | 3 | rejected | RuntimeError: None |
| 镜面 | 4 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 镜面 | 5 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 镜面 | 6 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 镜面 | 7 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 镜面 | 8 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 镜面 | 9 | rejected | RuntimeError: 角块或中棱的配色、方向不正确，请检查录入。 |
| 转面八面体 | 2 | rejected | RuntimeError: Please enter every sticker |
| 转面八面体 | 3 | rejected | RuntimeError: Please enter every sticker |
| 转面八面体 | 4 | rejected | RuntimeError: Please enter every sticker |
| 足球 | 3 | rejected | RuntimeError: Please enter every sticker |
| 足球 | 5 | rejected | RuntimeError: Please enter every sticker |
| 二十面体 | 2 | rejected | RuntimeError: Please enter every sticker |
| 二十面体 | 3 | rejected | RuntimeError: Please enter every sticker |
| 二十面体 | 4 | rejected | RuntimeError: Please enter every sticker |
| 二十面体 | 5 | rejected | RuntimeError: Please enter every sticker |
| 战鼓 | 2 | rejected | RuntimeError: Please enter every sticker |
| 战鼓 | 3 | rejected | RuntimeError: Please enter every sticker |
| 战鼓 | 4 | rejected | RuntimeError: Please enter every sticker |
| 战鼓 | 5 | rejected | RuntimeError: Please enter every sticker |
| 五面体 | 2 | rejected | RuntimeError: Please enter every sticker |
| 五面体 | 3 | rejected | RuntimeError: Please enter every sticker |
| 五面体 | 4 | rejected | RuntimeError: Please enter every sticker |
| 五面体 | 5 | rejected | RuntimeError: Please enter every sticker |
| 八叶花 | 3 | rejected | RuntimeError: Please enter every sticker |
| 四叶草 | 3 | rejected | RuntimeError: Please enter every sticker |
| 繁花五魔方 | 3 | rejected | RuntimeError: Please enter every sticker |
| SQ1 | 3 | rejected | ValueError: square1.error.incomplete |
| 空心三阶 | 3 | rejected | RuntimeError: Please enter every sticker |
| 空心魔塔 | 3 | rejected | RuntimeError: Please enter every sticker |
| 镜面魔塔 | 3 | rejected | ValueError: Incomplete mirror piece state |
| 变形金刚 | 3 | rejected | RuntimeError: shape.error.duplicate |
| 潘多拉 | 3 | rejected | RuntimeError: shape.error.duplicate |
| 风火轮 | 3 | rejected | RuntimeError: shape.error.duplicate |
| 移棱 | 3 | rejected | RuntimeError: shape.error.duplicate |
| 枫叶 | 3 | rejected | RuntimeError: Please enter every sticker |
