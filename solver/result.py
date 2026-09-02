"""求解结果与阶段数据结构。"""

from dataclasses import dataclass, field


@dataclass
class SolveStage:
    """一个求解阶段（4阶降阶法的各阶段、3阶的阶段划分）。"""
    name: str
    description: str
    moves: list = field(default_factory=list)


@dataclass
class SolveResult:
    success: bool
    moves: list
    message: str
    elapsed_ms: int
    move_count: int
    stages: list = field(default_factory=list)
