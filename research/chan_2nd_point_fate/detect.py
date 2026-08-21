"""Online 2nd-class BSP. Engine find_second_bsp. No zs.is_sure. No EMA."""
from __future__ import annotations

from chan_fractal_of.labels import _leave_bi
from chanlun.core.ChanEnum import Chan_BI_DIR


def zid_of(zs) -> str:
    return str(zs.start_bi.start_time)


def _sure(bi) -> bool:
    return bi is not None and bool(bi.is_sure)


def first_leave(zs):
    if zs.zg is None or zs.zd is None or len(zs.bi_list) < 3:
        return None
    leave = _leave_bi(zs)
    if not _sure(leave):
        return None
    if leave.dir == Chan_BI_DIR.UP:
        return leave, "UP"
    if leave.dir == Chan_BI_DIR.DOWN:
        return leave, "DOWN"
    return None


def classify_second(tf, zs, leave, side: str) -> dict | None:
    """B2/S2. Requires 一类 (check_bi_div). Second bi must be sure. No later bars."""
    if not tf.check_bi_div(zs, leave):
        return {"kind": "NO_FIRST"}
    mid = leave.next
    if not _sure(mid):
        return None
    sec = mid.next
    if not _sure(sec):
        return None
    if side == "DOWN":
        if mid.dir != Chan_BI_DIR.UP or sec.dir != Chan_BI_DIR.DOWN:
            return {"kind": "WRONG_DIR"}
        if float(sec.low) > float(leave.low):
            return {"kind": "B2", "mid": mid, "second": sec, "leave": leave}
        return {"kind": "BROKE_FIRST"}
    if mid.dir != Chan_BI_DIR.DOWN or sec.dir != Chan_BI_DIR.UP:
        return {"kind": "WRONG_DIR"}
    if float(sec.high) < float(leave.high):
        return {"kind": "S2", "mid": mid, "second": sec, "leave": leave}
    return {"kind": "BROKE_FIRST"}


def find_bi(tf, start_time: str):
    for bi in tf.bi_list:
        if str(bi.start_time) == str(start_time):
            return bi
    return None
