# CHAN_PENETRATION_CENSUS_001

```
Track:     Invalidation。结构确认后的反向穿透普查
Phase:     描述性 Census。不是止损。不是 Fate。不是 Continuation
Input:     冻结 47 事件（B1=18 B2=9 B3=20）。同一 90 天窗口
           CHAN_DESK_REPLAY_001。不准扩窗、不准改买卖点
```

本树 Fate → Continuation → Location → EMA52 已封存。本 ID 另立，不改旧数字。

问的是：确认之后，价格向反方向走多深，结构锚有没有被碰到。
不问：会不会继续涨、哪条均线、最佳止损、收益率。

## 冻结锚（不准为对齐穿透率而改）

| 家族 | 反向 | 主锚 | 远锚 | 离开笔范围 |
|------|------|------|------|------------|
| B1/B2 买 | 下 | 一类低 = leave_low | 无（T0 多已在盒外下方） | [leave_low, leave_high] |
| B1/B2 卖 | 上 | 一类高 = leave_high | 无 | 同上 |
| B3 买 | 下 | 近盒沿 zg | 远盒沿 zd | 同上 |
| B3 卖 | 上 | 近盒沿 zd | 远盒沿 zg | 同上 |

二类失效锚 = 一类高低（已冻）。三类 = 冻结 [zd, zg]。不准换成 ATR。

## 只在 T0 之后量

T0 = 冻结确认 K（CONT tape_row）。不含 T0 自身。扫到样本末。不设 horizon。
`hours_*` = 判定延迟（15m×0.25h），不是持仓。

买：
- mae_close = max(0, T0.close − min low after)
- mae_bar = max(0, T0.low − min low after)
- pierce_leave_ext = 某根 low < leave_low
- enter_box_ext = 某根 low ≤ zg 且 high ≥ zd
- through_far_ext = 某根 low < zd

卖对偶。另报 close 穿锚（不用于定层）。无 ATR。尺度只用 box_w、leave_w 做连续分位，不分桶。

## 预注册层（不是参数搜索）

B1/B2：
```
NONE     mae_bar = 0
SHALLOW  mae_bar > 0 且未 pierce_leave_ext
PRIMARY  pierce_leave_ext
```

B3：
```
NONE     mae_bar = 0
SHALLOW  mae_bar > 0 且未 enter_box_ext
BOX      enter_box_ext 且未 through_far_ext
THROUGH  through_far_ext
```

B2 n=9 只报告，不单独定层级。
家族有层级 ⟺ 至少 2 个桶 n≥3 且最大桶 < 90%。
B1 或 B3 有层级 → `HIERARCHY_CANDIDATE`。否则 `HOLD_NO_HIERARCHY`。

`HIERARCHY_CANDIDATE` ≠ 失效边界已找到 ≠ 开止损。第二闸另授权。
`HOLD_NO_HIERARCHY` → 本线 HOLD/CLOSE。不准补 ATR。

## 冻结结果

`PASS / HIERARCHY_CANDIDATE`。n=47 clock OK。B2 不定层。

| 家族 | 层 | 主锚首次穿 | 首次穿 p50 |
|------|----|------------|------------|
| B1 n=18 | SHALLOW 4 · PRIMARY 14 | leave 14/18 | 10.0h |
| B2 n=9 | SHALLOW 7 · PRIMARY 2 | leave 2/9 | n=2 不报 |
| B3 n=20 | NONE 1 · BOX 3 · THROUGH 16 | box 19/20 · far 16/20 | box 20.75h · far 64.25h |

假设中的「多数很浅 / 极少数破坏」不成立。B1/B3 质量在深侧。
`hours_to_mae` p50=175.5h = 扫到样本末，不是局部失效深度。不准用 mae/box p50。
B1 through_far 18/18 且 p50=0.25h = T0 已在盒外，不是反向失效。合样本 pierce/box/far 不准当层。
本枪停。第二闸另授权。不准 ATR、不准止损、不准收益率。

## 禁止

止损优化、收益率、EMA、OF、Trend Age、新买卖点、扩窗、0.5/1 ATR 失效、
用 Fate/Continuation 数字回调本枪、把 BROKE_FIRST 当失败、改二类锚为中枢盒子。
