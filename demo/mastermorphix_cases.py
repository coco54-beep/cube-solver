"""Shape-aware teaching examples using the same mechanism as the solver.

Every initial state is constructed by reversing its displayed formula.
These are independent examples, rather than a solve of the user's draft.
"""


def _text(zh, en, ja):
    return {"zh": zh, "en": en, "ja": ja}


def _case(name, moves, tip):
    tokens = moves.split()
    return {"name": name, "moves": tokens, "text": " ".join(tokens), "tip": tip}


CASE_MASTERMORPHIX = [
    {
        "title": _text("认识转轴与变形", "Axes and shape changes", "回転軸と変形"),
        "desc": _text(
            "四个外表颜色面对应三阶的六个转轴。U/D、F/B、R/L 分别是上/下、前/后、右/左轴；"
            "字母不代表四面体的颜色面。按下一步观察一层怎样回到原位，带撇号表示逆时针，2 表示半圈。",
            "Four colored surfaces share a 3×3 mechanism with six axes: U/D, F/B and R/L. "
            "Letters name axes, not the four colored surfaces. A prime means counterclockwise; 2 means a half turn.",
            "外側の4色面に対し、機構には U/D・F/B・R/L の6軸があります。文字は色面ではなく回転軸を示します。"
            "プライムは反時計回り、2 は半回転です。"),
        "cases": [
            _case(_text("右轴四分之一圈", "Right-axis quarter turn", "右軸を90度回転"), "R",
                  _text("正对右轴观察时顺时针转 90°；注意双色中心也随层转动。",
                        "Turn 90° clockwise when looking directly at R. Its two-color center turns too.",
                        "R軸を正面から見て時計回りに90度。双色中心も回転します。")),
            _case(_text("上轴逆时针", "Counterclockwise upper turn", "上軸を反時計回り"), "U'",
                  _text("带撇号的动作反向转动；左右箭头用于步骤的撤回和执行。",
                        "The prime reverses the turn. Left undoes one move; right performs one move.",
                        "プライムは逆方向の回転。左は1動作戻し、右は1動作進めます。")),
            _case(_text("前轴半圈", "Front-axis half turn", "前軸を半回転"), "F2",
                  _text("180° 算一个公式动作，可观察梯形块和角块的外形变化。",
                        "A 180° turn counts as one move. Watch the wedges and corner shapes.",
                        "180度は1動作として数えます。台形と角の変形を観察しましょう。")),
        ],
    },
    {
        "title": _text("角块与梯形块复位示例", "Corner and wedge examples", "角と台形を戻す例"),
        "desc": _text(
            "三色尖角与单色小三角都属于角块，单色梯形属于棱块。每个案例都从当前公式的逆序状态开始；"
            "执行完整公式会恢复该案例，可用上一步反复观察块的位置和朝向。",
            "Three-color tips and single-color triangles are corners; single-color wedges are edges. "
            "Each example begins with the inverse of its formula. Finish the formula to restore that example.",
            "三色の頂点と単色の小三角は角、単色の台形はエッジです。各例は表示公式の逆操作で作った状態から始まり、"
            "公式を最後まで実行すると元に戻ります。"),
        "cases": [
            _case(_text("右侧插入动作", "Right-side insertion moves", "右側への挿入動作"), "R U R'",
                  _text("逐步观察三个动作；这是独立示例，不能对任意打乱直接使用。",
                        "Observe each of the three moves. This independent example is not a formula for every scramble.",
                        "3動作を順番に観察します。任意のスクランブルにそのまま使う公式ではありません。")),
            _case(_text("前侧插入动作", "Front-side insertion moves", "前側への挿入動作"), "F' U' F",
                  _text("对比尖角、小三角与梯形随层移动的轨迹。",
                        "Compare the paths of tips, small triangles and wedges.",
                        "頂点・小三角・台形の移動を比較します。")),
            _case(_text("角块朝向组合", "Corner orientation sequence", "角の向きの連続操作"), "R U R' U R U2 R'",
                  _text("同一三阶公式在粽子上会产生变形；完成该案例后颜色和形状一起复原。",
                        "A 3×3 sequence changes this puzzle's shape. Finishing this example restores both shape and color.",
                        "三階の公式でも形が変わります。この例を完了すると形と色が戻ります。")),
        ],
    },
    {
        "title": _text("校正双色中心", "Correct two-color centers", "双色中心の向きを直す"),
        "desc": _text(
            "角块和梯形复位后，双色中心仍可能方向不对，外形也可能没有恢复。以下使用求解器同源的中心公式；"
            "中途会暂时打乱活动块，整组完成后活动块归位，同时校正中心朝向。",
            "After corners and wedges return, two-color centers may still be misoriented. These are the solver's "
            "center sequences: movable pieces shift during the formula and return when the whole sequence is complete.",
            "角と台形が戻っても双色中心の向きが残る場合があります。ソルバーと同じ中心公式を使います。"
            "途中で動くピースも、公式を最後まで実行すると元の位置に戻ります。"),
        "cases": [
            _case(_text("中心半圈校正", "Center half-turn correction", "中心の半回転補正"),
                  "R L U2 R' L' U R L U2 R' L' U",
                  _text("完成整组后检查双色分界线和四面体外形。",
                        "After the whole sequence, inspect center seams and the tetrahedral shape.",
                        "全動作の後に双色の境界と四面体の形を確認します。")),
            _case(_text("成对中心校正", "Paired center correction", "2つの中心を補正"),
                  "R L' F B' U D' R' U' D F' B R' L U",
                  _text("校正两个中心的朝向；可重置到开头，逐步查看每个动作。",
                        "Correct two center orientations. Restart and step through each move.",
                        "2つの中心の向きを補正します。最初に戻して1動作ずつ確認できます。")),
        ],
    },
]
