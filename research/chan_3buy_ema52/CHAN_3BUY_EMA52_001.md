# CHAN_3BUY_EMA52_001

```
Track:     15m 第三类买卖点 × 15m EMA52 回撤位置
Phase:     一个问题。不改 EMA。不加 OF。不扩 30m/1H
Input:     母集 = CHAN_3RD_POINT_001 的 20 个事件。同一 1m 窗口
```

三买定义不准改。EMA 不定义三买。WHERE / STATE 数字不可变。

```
T_3_VISIBLE
      ↓
其后第一笔反向 15m 摆动确认          T_PB_VISIBLE
      ↓
该回撤是否进入 15m EMA52 附近
  ENTERED     触及或穿越（≤ 0.5 ATR 或穿过均线）
  NOT_ENTERED 没有回到附近
      ↓
T_PB 之后结构命运（不是涨跌）
  RESUME     原方向再创新高/低
  REENTRY    收盘回到冻结中枢 [zd, zg]
  REVERSE    收盘打穿中枢另一侧
```

核心对照：`三买/三卖 + ENTERED` vs `三买/三卖 + NOT_ENTERED`。

不问「EMA52 是不是支撑」。若有 Fate Contrast，才允许后续等效尺度（30m EMA52 / 1H EMA26）。本枪不做。

---

## 封存语义（数字不可变）

`SAMPLE_INSUFFICIENT` **不是**「EMA52 没用」。本枪只问有没有**进入**均线附近，不够判断均线有没有**挡住**结构失效。

三个对象必须分开，不准混：

```
ENTERED     回撤触及/穿过 15m EMA52（位置）
RESPONSE    在均线附近获得承接/压制（本枪未测）
REENTRY     收盘回到冻结中枢（结构失败，比没撑住均线更严重）
```

REENTRY ≠ ENTERED。2 个 REENTRY 全在 ENTERED=9 里，只能说：这 2 次均线没有阻止中枢被重新进入。11 个 NOT_ENTERED 没有 REENTRY。n=9/11 不够 Fate Contrast。

三买之后价格本应离开均线。EMA52 研究的是后续回撤里它是否充当动态支撑/压力，不是「有没有摸到均线」。

下一问若重开 EMA52：只问对这 20 个基线事件的**增量解释力**（解释 2 个 REENTRY，或区分 RESUME 质量）。不准再发现 90% 延续。不准换周期。

## 有效范围

```
VALID FOR LOCATION DIAGNOSTIC     在冻结的 20 个事件上，15m EMA52 位置观察有效
NOT VALID FOR 15m SAMPLE-EXPANSION  不能用来声称「15m 三买/三卖只有 20 个」
```

母集是加载 `CHAN_3RD_POINT_001` 的 EVENTS，不是本枪在 15m 上独立重识别。9 vs 11 数字不可变，但不进样本扩张结论。


