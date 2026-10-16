"""输入页共性动作（混入）。

各族的录入页（标准 N 阶、粽子/镜面/形状、异形、SQ1）都重复实现下面几件事：
    - 一键把魔方设为"已还原态"并写入 app（assign_initial）；
    - 空白录入时预置中心块（方便对位）；
    - 进入本族的拧动页（open_twist）。

把这些收进一个混入，各族只声明差异（钩子），避免以后再"满地开花"漏改。

子类需覆盖的钩子：
    entry_twist_screen           本族拧动页名（None 表示没有）
    entry_can_assign()           现在能否一键还原（默认可以）
    entry_reset_solved()         把工作状态重置为已还原态（不改 app）
    entry_commit_state()         把工作状态写入 app（cube / n / kind 等）
    entry_center_preset()        空白录入时要预置为"已录入"的中心集合
    entry_set_status(text, err)  显示一条状态（各族的状态栏不同）
    entry_can_twist()            现在能否进入拧动页（默认可以）
    entry_prepare_twist()        进入拧动页前的收尾（默认不做事）
"""


class EntryActionsMixin:
    entry_twist_screen = None

    # ---- 钩子（默认实现，供子类覆盖）----
    def entry_can_assign(self):
        return True

    def entry_reset_solved(self):
        raise NotImplementedError

    def entry_commit_state(self):
        pass

    def entry_center_preset(self):
        return set()

    def entry_set_status(self, text, error=False):
        pass

    def entry_can_twist(self):
        return True

    def entry_prepare_twist(self):
        pass

    # ---- 共性动作（只写一次）----
    def assign_initial(self):
        """一键把当前魔方设为已还原态（不跳转，成功不提示）。"""
        if not self.entry_can_assign():
            return
        self.entry_reset_solved()
        self.entry_commit_state()
        self.entry_set_status("")

    def open_twist(self):
        if not self.entry_twist_screen or not self.entry_can_twist():
            return
        self.entry_prepare_twist()
        self.manager.current = self.entry_twist_screen

    def center_preset(self, recorded):
        """把空白录入的中心块并入已录入集合。"""
        return set(recorded) | set(self.entry_center_preset())
