"""Online 3rd-class BSP. Freeze zg/zd at leave. Never use later re-entry."""
from __future__ import annotations

from chan_fractal_of.labels import _leave_bi
from chanlun.core.ChanEnum import Chan_BI_DIR


def zid_of(zs) -> str:
    return str(zs.start_bi.start_time)


def _sure(bi) -> bool:
    return bi is not None and bool(bi.is_sure)


def first_leave(zs):
    """Engine leave bi. Do not wait for a fully-outside bar — that is the pullback."""
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


def classify_pullback(leave, zg: float, zd: float, side: str) -> dict | None:
    """Use leave.next only. Future bars after the pullback are not inputs."""
    pb = leave.next
    if not _sure(pb):
        return None
    if side == "UP":
        if pb.dir != Chan_BI_DIR.DOWN:
            return {"kind": "WRONG_DIR", "side": "B3", "pullback": pb}
        if float(pb.low) < zg:
            return {"kind": "PULLBACK_IN", "side": "B3", "pullback": pb}
        return {"kind": "B3", "side": "B3", "pullback": pb}
    if pb.dir != Chan_BI_DIR.UP:
        return {"kind": "WRONG_DIR", "side": "S3", "pullback": pb}
    if float(pb.high) > zd:
        return {"kind": "PULLBACK_IN", "side": "S3", "pullback": pb}
    return {"kind": "S3", "side": "S3", "pullback": pb}


def find_bi(tf, start_time: str):
    for bi in tf.bi_list:
        if str(bi.start_time) == str(start_time):
            return bi
    return None
