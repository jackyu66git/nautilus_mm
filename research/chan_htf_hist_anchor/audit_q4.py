"""Q4: B1-event unit. Hist spatial vs B2 overlay. No pair duplication. No P&L."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass

import pandas as pd

from chan_htf_hist_anchor.phase0_schema import assert_no_htf_bsp, rail_side
from chan_htf_hist_anchor.replay import leftover_at

RAILS = ("zg", "zd", "gg", "dd")


def _utc(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        return t.tz_localize("UTC")
    return t.tz_convert("UTC")


def collapse_to_b1(pair_rows: list[dict], b2_by_leave: dict[str, bool]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    order = []
    for r in pair_rows:
        k = r["LTF_B1"]
        if k not in groups:
            order.append(k)
            groups[k] = []
        groups[k].append(r)
    out = []
    for k in order:
        rs = groups[k]
        hist = [r for r in rs if not r.get("NO_HIST_ANCHOR")]
        n = int(hist[0]["n_hist_zs"]) if hist else 0
        if hist and n != len(hist):
            n = len(hist)
        contact = {rail: False for rail in RAILS}
        contact_any = False
        for r in hist:
            for rail in RAILS:
                if r.get(f"side_{rail}") == "CONTACT":
                    contact[rail] = True
                    contact_any = True
        latest = (
            max(hist, key=lambda x: str(x.get("T_ZS_COMPLETE") or "")) if hist else None
        )
        rec = {
            "LTF_B1": k,
            "T_LTF_B1": rs[0]["T_LTF_B1"],
            "B1_bar": rs[0].get("B1_bar"),
            "leave_low": rs[0]["leave_low"],
            "leave_high": rs[0]["leave_high"],
            "anchor_count_at_B1": n,
            "contact_any": contact_any,
            "zg_contact_any": contact["zg"],
            "zd_contact_any": contact["zd"],
            "gg_contact_any": contact["gg"],
            "dd_contact_any": contact["dd"],
            "latest_zs_id": latest["zs_id"] if latest else None,
            "latest_side_zg": latest.get("side_zg") if latest else None,
            "latest_side_zd": latest.get("side_zd") if latest else None,
            "latest_side_gg": latest.get("side_gg") if latest else None,
            "latest_side_dd": latest.get("side_dd") if latest else None,
            "LTF_B2": bool(b2_by_leave[k]) if k in b2_by_leave else None,
        }
        assert_no_htf_bsp(rec)
        if rec["LTF_B2"] is None:
            raise ValueError(f"missing retrospective LTF_B2 for {k}")
        out.append(rec)
    return out


def _bar_contacts(hist: list[dict], low: float, high: float) -> bool:
    for h in hist:
        for rail in RAILS:
            if not h.get(f"{rail}_ok"):
                continue
            if rail_side(low, high, h[rail]) == "CONTACT":
                return True
    return False


def count_matched_contact_rate(bar_15m: pd.DataFrame, book, b1_closes: set) -> dict[int, dict]:
    """P(contact_any) among non-B1 15m bars, keyed by leftover count."""
    hits = defaultdict(lambda: {"n": 0, "contact": 0})
    closes = {_utc(t) for t in b1_closes}
    for i in range(len(bar_15m)):
        close_ts = _utc(bar_15m.iloc[i]["close_ts"])
        if close_ts in closes:
            continue
        hist = leftover_at(book, close_ts)
        n = len(hist)
        low = float(bar_15m.iloc[i]["low"])
        high = float(bar_15m.iloc[i]["high"])
        touched = _bar_contacts(hist, low, high)
        hits[n]["n"] += 1
        hits[n]["contact"] += int(touched)
        if (i + 1) % 1000 == 0:
            print(f"Q4 baseline bars {i + 1}/{len(bar_15m)}", flush=True)
    out = {}
    for n, d in hits.items():
        out[int(n)] = {
            "n_bars": d["n"],
            "n_contact": d["contact"],
            "rate": d["contact"] / d["n"] if d["n"] else float("nan"),
        }
    return out


@dataclass
class Gate:
    name: str
    verdict: str
    detail: str


def audit_q4(b1_rows: list[dict], baseline: dict[int, dict]) -> dict:
    for r in b1_rows:
        assert_no_htf_bsp(r)
    n = len(b1_rows)
    ids = [r["LTF_B1"] for r in b1_rows]
    gates: list[Gate] = []
    if n < 1 or len(set(ids)) != n:
        gates.append(Gate("C0", "FAIL", f"unit is not unique B1 n={n} unique={len(set(ids))}"))
        for name in ("C1", "C2", "C3"):
            gates.append(Gate(name, "NOT_RUN", "C0 FAIL"))
        return _pack(b1_rows, gates, "FAIL", "CLOCK", baseline)
    gates.append(Gate("C0", "PASS", f"unit=B1 n={n} (not pair)"))

    if any(r.get("LTF_B2") is None for r in b1_rows):
        gates.append(Gate("C1", "FAIL", "B2 overlay missing"))
        gates.extend([Gate("C2", "NOT_RUN", "C1 FAIL"), Gate("C3", "NOT_RUN", "C1 FAIL")])
        return _pack(b1_rows, gates, "FAIL", "CLOCK", baseline)
    n_b2 = sum(int(bool(r["LTF_B2"])) for r in b1_rows)
    n_contact = sum(int(bool(r["contact_any"])) for r in b1_rows)
    counts = [int(r["anchor_count_at_B1"]) for r in b1_rows]
    gates.append(
        Gate(
            "C1",
            "PASS",
            f"LTF_B2={n_b2}/{n} contact_any={n_contact}/{n} "
            f"zg={sum(int(r['zg_contact_any']) for r in b1_rows)} "
            f"zd={sum(int(r['zd_contact_any']) for r in b1_rows)} "
            f"gg={sum(int(r['gg_contact_any']) for r in b1_rows)} "
            f"dd={sum(int(r['dd_contact_any']) for r in b1_rows)} "
            f"counts={counts}",
        )
    )

    lifts = []
    for r in b1_rows:
        k = int(r["anchor_count_at_B1"])
        base = baseline.get(k, {"rate": float("nan"), "n_bars": 0, "n_contact": 0})
        lifts.append(
            {
                "LTF_B1": r["LTF_B1"],
                "anchor_count_at_B1": k,
                "b1_contact": bool(r["contact_any"]),
                "base_rate": base.get("rate"),
                "base_n": base.get("n_bars"),
            }
        )
    matched = [x["base_rate"] for x in lifts if x["base_rate"] == x["base_rate"]]
    if not matched:
        gates.append(Gate("C2", "FAIL", "no count-matched baseline"))
        gates.append(Gate("C3", "NOT_RUN", "C2 FAIL"))
        return _pack(b1_rows, gates, "FAIL", "CLOCK", baseline, lifts)
    b1_rate = n_contact / n
    exp = float(sum(matched) / len(matched))
    higher = b1_rate > exp
    gates.append(
        Gate(
            "C2",
            "PASS",
            f"P(contact|B1)={b1_rate:.3f} count-matched baseline={exp:.3f} B1_higher={higher}",
        )
    )

    n_no_b2 = n - n_b2
    if n_no_b2 == 0 or n_b2 == 0:
        gates.append(Gate("C3", "FAIL", f"B2 has no variation  B2={n_b2} no_B2={n_no_b2}"))
        return _pack(b1_rows, gates, "FAIL", "NO_FATE_CONTRAST", baseline, lifts)

    cells = {(True, True): 0, (True, False): 0, (False, True): 0, (False, False): 0}
    for r in b1_rows:
        cells[(bool(r["contact_any"]), bool(r["LTF_B2"]))] += 1
    gates.append(
        Gate(
            "C3",
            "PASS",
            f"contact×B2 yes/yes={cells[(True, True)]} yes/no={cells[(True, False)]} "
            f"no/yes={cells[(False, True)]} no/no={cells[(False, False)]}",
        )
    )
    kind = "STRUCTURE_CONTRAST" if higher else "FATE_ONLY"
    return _pack(b1_rows, gates, "PASS", kind, baseline, lifts)


def _pack(rows, gates, decision, kind, baseline, lifts=None) -> dict:
    by_count: dict[str, dict] = {}
    for r in rows:
        if r.get("anchor_count_at_B1") is None:
            continue
        k = str(int(r["anchor_count_at_B1"]))
        slot = by_count.setdefault(k, {"n_b1": 0, "n_b1_contact": 0})
        slot["n_b1"] += 1
        slot["n_b1_contact"] += int(bool(r["contact_any"]))
    for k, v in (baseline or {}).items():
        slot = by_count.setdefault(str(int(k)), {"n_b1": 0, "n_b1_contact": 0})
        slot["n_bars"] = v.get("n_bars")
        slot["n_bar_contact"] = v.get("n_contact")
        slot["bar_rate"] = v.get("rate")
    return {
        "experiment": "CHAN_HTF_HIST_ANCHOR_LTF_B1_001",
        "phase": "4",
        "decision": decision,
        "kind": kind,
        "n_events": len(rows),
        "gates": [asdict(g) for g in gates],
        "summary": {
            "b1": [
                {
                    "LTF_B1": r.get("LTF_B1"),
                    "anchor_count_at_B1": r.get("anchor_count_at_B1"),
                    "contact_any": r.get("contact_any"),
                    "zg_contact_any": r.get("zg_contact_any"),
                    "zd_contact_any": r.get("zd_contact_any"),
                    "gg_contact_any": r.get("gg_contact_any"),
                    "dd_contact_any": r.get("dd_contact_any"),
                    "latest_side_zg": r.get("latest_side_zg"),
                    "latest_side_zd": r.get("latest_side_zd"),
                    "latest_side_gg": r.get("latest_side_gg"),
                    "latest_side_dd": r.get("latest_side_dd"),
                    "LTF_B2": r.get("LTF_B2"),
                }
                for r in rows
                if r.get("anchor_count_at_B1") is not None
            ],
            "lifts": lifts or [],
            "by_count": dict(sorted(by_count.items(), key=lambda kv: int(kv[0]))),
            "baseline_by_count": {str(k): v for k, v in sorted((baseline or {}).items())},
        },
        "blocked": "≠Edge 不准 OF SMC MACD MFE MAE 换TF pair复制 组合特征 Entry",
    }


def load_b2_from_early(path) -> dict[str, bool]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    out = {}
    for r in rows:
        leave = r["case_id"].split("|", 1)[1]
        out[leave] = r.get("state") == "B2_TRUTH"
    return out
