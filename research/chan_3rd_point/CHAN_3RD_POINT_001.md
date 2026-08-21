# CHAN_3RD_POINT_001

```
Track:     第三类买卖点（新轨）。HTF-ZS-reversal 已关闭
Phase:     在线定义 + 因果审计 + Census。无收益 / OF / SMC / 交易
Input:     与 Fact Tape 同一 1m 窗口。15m 同级别中枢（不是 1H×15m 混搭）
```

三买/三卖不是天然 Setup。本枪只问：引擎能否在线、无未来函数地标出这个结构。

```
T_ZS_VISIBLE  ≤  T_LEAVE_VISIBLE  <  T_3_VISIBLE
```

离开当下冻结 zg/zd。活中枢之后的扩张不得改写该冻结，也不得用来「确认从未再进中枢」。

`T_3_VISIBLE` 只用到回抽笔确认那一根已收盘 15m。不准用其后是否再次进入中枢来定义事件。

```
中枢 zg/zd 已在当时可见
        ↓
成员后引擎 `_leave_bi` 确认（可与中枢重叠）     T_LEAVE
        ↓
下一笔反向回抽已确认
        ↓
回抽未进入中枢：
  上离开 + 回抽 low ≥ zg  → B3
  下离开 + 回抽 high ≤ zd → S3
        ↓
T_3_VISIBLE = 该回抽确认所在 15m 收盘
```

不准用 `zs.is_sure`（可能绑到全图最后一笔）。zg/zd 在 T_LEAVE 冻结。一个 (zs_id, B3|S3) 只计一次。

本枪报告：n_zs、n_leave、n_B3、n_S3、回抽失败（进入中枢）、右删失、三钟间隔。不看 MFE。
