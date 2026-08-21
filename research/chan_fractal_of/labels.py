"""Retrospective B1/B2 and bi-endpoint labels. Never written into OF."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from chanlun.core.ChanBSP import ChanBSP
from chanlun.core.ChanEnum import Chan_BI_DIR, Chan_BSP_DIR, Chan_BSP_TYPE, Chan_ZS_DIR
from chanlun.pipeline.timeframe import TF_DF


@dataclass
class TruthIndex:
    bi_endpoints: set[str] = field(default_factory=set)
    b1_fx: set[str] = field(default_factory=set)
    b1_b2_fx: set[str] = field(default_factory=set)
    s1_fx: set[str] = field(default_factory=set)
    s1_s2_fx: set[str] = field(default_factory=set)
    n_sure_bi: int = 0
    n_zs_sure: int = 0
    n_b1: int = 0
    n_b2: int = 0
    n_s1: int = 0
    n_s2: int = 0


def bars_to_label_engine(bar_15m: pd.DataFrame) -> TF_DF:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(bar_15m["open_ts"], utc=True).dt.tz_convert("UTC").dt.tz_localize(None),
            "open": bar_15m["open"].astype(float),
            "high": bar_15m["high"].astype(float),
            "low": bar_15m["low"].astype(float),
            "close": bar_15m["close"].astype(float),
            "volume": bar_15m["volume"].astype(float),
        }
    )
    return TF_DF(df, interval=1, timeframe="15m")


def _leave_bi(zs):
    last_zs_bi = zs.bi_list[-1]
    if last_zs_bi.dir == Chan_BI_DIR.UP:
        if last_zs_bi.is_sure and last_zs_bi.end_klc.high <= zs.zg or (
            last_zs_bi.next and last_zs_bi.next.is_sure and last_zs_bi.next.end_klc.low < zs.zd
        ):
            leave_bi = last_zs_bi.next
        else:
            leave_bi = last_zs_bi
    else:
        if last_zs_bi.is_sure and last_zs_bi.end_klc.low >= zs.zd or (
            last_zs_bi.next and last_zs_bi.next.is_sure and last_zs_bi.next.end_klc.high > zs.zg
        ):
            leave_bi = last_zs_bi.next
        else:
            leave_bi = last_zs_bi
    if leave_bi is None or not leave_bi.is_sure:
        return None
    if (zs.dir == Chan_ZS_DIR.UP and leave_bi.dir == Chan_BI_DIR.UP and leave_bi.end_klc.high < zs.zg and leave_bi.end_klc.high > zs.zd) or (
        zs.dir == Chan_ZS_DIR.DOWN and leave_bi.dir == Chan_BI_DIR.DOWN and leave_bi.end_klc.low < zs.zg and leave_bi.end_klc.low > zs.zd
    ):
        leave_bi = leave_bi.next
    if leave_bi is None or not leave_bi.is_sure:
        return None
    return leave_bi


def find_all_bsp_nonesafe(engine: TF_DF):
    """Same predicates as find_all_bsp. bounce/pullback None does not crash B2."""
    bi_list = engine.bi_list
    bi_zs_list = engine.bi_zs_list
    bsp_list = []
    if len(bi_list) < 4 or len(bi_zs_list) == 0:
        return bsp_list
    for zs in bi_zs_list:
        if not zs.is_sure or len(zs.bi_list) < 3:
            continue
        leave_bi = _leave_bi(zs)
        if leave_bi is None or not leave_bi.is_sure:
            continue
        if leave_bi.dir == Chan_BI_DIR.UP:
            first = engine.check_bi_div(zs, leave_bi)
            if first:
                bsp = ChanBSP(leave_bi, len(bsp_list), Chan_BSP_TYPE.S1, Chan_BSP_DIR.SELL, leave_bi.sure_time, zs.index + 1, zs, None)
                leave_bi.end_klc.set_bsp_type(Chan_BSP_TYPE.S1)
                bsp_list.append(bsp)
            pullback_bi = leave_bi.next
            if pullback_bi and pullback_bi.is_sure and pullback_bi.dir == Chan_BI_DIR.DOWN:
                if pullback_bi.low >= zs.zg:
                    bsp = ChanBSP(pullback_bi, len(bsp_list), Chan_BSP_TYPE.B3, Chan_BSP_DIR.BUY, pullback_bi.sure_time, zs.index + 1, zs, None)
                    pullback_bi.end_klc.set_bsp_type(Chan_BSP_TYPE.B3)
                    bsp_list.append(bsp)
            if first:
                second_bsp_bi = pullback_bi.next if pullback_bi is not None else None
                if second_bsp_bi and second_bsp_bi.is_sure and second_bsp_bi.end_klc.high < leave_bi.end_klc.high:
                    bsp = ChanBSP(second_bsp_bi, len(bsp_list), Chan_BSP_TYPE.S2, Chan_BSP_DIR.SELL, second_bsp_bi.sure_time, zs.index + 1, zs, None)
                    second_bsp_bi.end_klc.set_bsp_type(Chan_BSP_TYPE.S2)
                    bsp_list.append(bsp)
        elif leave_bi.dir == Chan_BI_DIR.DOWN:
            first = engine.check_bi_div(zs, leave_bi)
            if first:
                bsp = ChanBSP(leave_bi, len(bsp_list), Chan_BSP_TYPE.B1, Chan_BSP_DIR.BUY, leave_bi.sure_time, zs.index + 1, zs, None)
                leave_bi.end_klc.set_bsp_type(Chan_BSP_TYPE.B1)
                bsp_list.append(bsp)
            bounce_bi = leave_bi.next
            if bounce_bi and bounce_bi.is_sure and bounce_bi.dir == Chan_BI_DIR.UP:
                if bounce_bi.high <= zs.zd:
                    bsp = ChanBSP(bounce_bi, len(bsp_list), Chan_BSP_TYPE.S3, Chan_BSP_DIR.SELL, bounce_bi.sure_time, zs.index + 1, zs, None)
                    bounce_bi.end_klc.set_bsp_type(Chan_BSP_TYPE.S3)
                    bsp_list.append(bsp)
            if first:
                second_bsp_bi = bounce_bi.next if bounce_bi is not None else None
                if second_bsp_bi and second_bsp_bi.is_sure and second_bsp_bi.end_klc.low > leave_bi.end_klc.low:
                    bsp = ChanBSP(second_bsp_bi, len(bsp_list), Chan_BSP_TYPE.B2, Chan_BSP_DIR.BUY, second_bsp_bi.sure_time, zs.index + 1, zs, None)
                    second_bsp_bi.end_klc.set_bsp_type(Chan_BSP_TYPE.B2)
                    bsp_list.append(bsp)
    return bsp_list


def extract_truth(engine: TF_DF) -> TruthIndex:
    truth = TruthIndex()
    for bi in engine.bi_list:
        if not bi.is_sure:
            continue
        truth.n_sure_bi += 1
        if bi.start_klc is not None:
            truth.bi_endpoints.add(bi.start_klc.start_time)
        if bi.end_klc is not None:
            truth.bi_endpoints.add(bi.end_klc.start_time)
    truth.n_zs_sure = sum(1 for zs in engine.bi_zs_list if zs.is_sure)
    bsp_list = find_all_bsp_nonesafe(engine)
    b1_zs: dict[str, int] = {}
    b2_zs: set[int] = set()
    s1_zs: dict[str, int] = {}
    s2_zs: set[int] = set()
    for bsp in bsp_list:
        fx_id = bsp.klc.start_time
        zid = id(bsp.zs)
        if bsp.type == Chan_BSP_TYPE.B1:
            truth.n_b1 += 1
            truth.b1_fx.add(fx_id)
            b1_zs[fx_id] = zid
        elif bsp.type == Chan_BSP_TYPE.B2:
            truth.n_b2 += 1
            b2_zs.add(zid)
        elif bsp.type == Chan_BSP_TYPE.S1:
            truth.n_s1 += 1
            truth.s1_fx.add(fx_id)
            s1_zs[fx_id] = zid
        elif bsp.type == Chan_BSP_TYPE.S2:
            truth.n_s2 += 1
            s2_zs.add(zid)
    truth.b1_b2_fx = {fx for fx, zid in b1_zs.items() if zid in b2_zs}
    truth.s1_s2_fx = {fx for fx, zid in s1_zs.items() if zid in s2_zs}
    return truth


def attach_labels(fx_id: str, fx_side: str, truth: TruthIndex) -> dict:
    bi_ep = fx_id in truth.bi_endpoints
    if fx_side == "BOTTOM":
        lab_b1 = fx_id in truth.b1_fx
        lab_b12 = fx_id in truth.b1_b2_fx
    else:
        lab_b1 = False
        lab_b12 = False
    return {
        "label_bi_endpoint": int(bi_ep),
        "label_B1": int(lab_b1),
        "label_B1_B2": int(lab_b12),
    }
