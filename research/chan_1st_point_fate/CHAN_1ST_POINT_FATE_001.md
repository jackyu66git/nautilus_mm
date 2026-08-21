# CHAN_1ST_POINT_FATE_001

```
Track:     一类买卖点 Fate Census。独立。B2/B3 HOLD 不动
Phase:     只用引擎已冻结的确认对象。无 EMA / OF / Trend Age
Input:     同一 90 天 1m 窗口。15m。不准扩窗、不准改定义
```

PRECHECK：确认对象已存在，不是临时造的。

```
find_all_bsp_nonesafe
  leave = _leave_bi(zs) 且 sure
  check_bi_div(zs, leave)
  zs.is_sure
  leave ∉ zs.bi_list          与 B1_LOCK 同一可见性
T_1_VISIBLE = 第一次发出 B1 或 S1 的 15m 收盘
```

禁止 `find_first_bsp`（另一套背驰，研究已禁）。
不准为了和二买对齐改失效锚。一类失效 = 打穿离开笔高低。
不准放宽背驰。不准加 EMA/OF/Trend Age。

问的是：短期 continuation signature 是二买/三买独有，还是确认事件普遍有。
不是把一二三买铺完。

Census（冻结）：n_b1=8（=B1_LOCK）n_s1=10 n_1=18。in_box_at_t1=0。
Fate：RESUME=16 REENTRY=0 REVERSE=2。14/18 下一根。p50=0.25h。
hours_to_fate = 判定延迟，≠持仓。
16/18 不是成功率。与 B2/B3 同构 continuation ≠ 一类独有/更强/可交易。
HOLD。不准改一类。不准 find_first_bsp。B2/B3 不动。
