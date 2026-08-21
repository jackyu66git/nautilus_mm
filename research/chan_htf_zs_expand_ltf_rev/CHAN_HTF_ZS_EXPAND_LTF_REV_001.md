# CHAN_HTF_ZS_EXPAND_LTF_REV_001

位置切面已关（REV_001 / NO_STATE_CONTRAST）。本枪对象 = living 1H 中枢**递归扩张**，不是盒内/边界/盒外。

```
EXPAND   相对上一根 15m，同一 zs_id 的 n_bis 增加
STABLE   同一 zs_id，n_bis 不变
NEW_BOX  living zs_id 刚换成另一个
NONE     无 living 中枢
n_bis    整数原样，第二张单维表
Y        下一根 15m ltf_bi_dir 是否反转（与 REV_001 同一 Y，可对照）
```

n<30 的水平记 SAMPLE_THIN，不据此收紧。  
各充分样本水平 rev_share 相对总体差 < 2pp → NO_STATE_CONTRAST，关闭本切面。
