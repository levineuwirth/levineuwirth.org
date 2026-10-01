"""Extract the R6 figure data from Proof Broker's frozen analysis.

Run by hand, never at build time; the figure scripts read only the CSVs
this writes into data/. The source is the r6 tag of
https://github.com/levineuwirth/proof-broker, file
experiments/r6/reviews/2026-09-29/R6-014-BLOCK2-ANALYSIS.json, and the
reviewed declaration families in experiments/r6/analysis_r6.py; runs.csv
reads each run's ledger reconciliation under experiments/r6/cohort-live-v9/.

    python3 figures/extract_r6_data.py <proof-broker checkout at r6>

Every total the essay states is asserted before anything is written, so a
different input fails here rather than drawing a different figure.
timeline.csv is not extracted: it is compiled by hand from the records
named in its own source column.
"""

import ast
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ANALYSIS = "experiments/r6/reviews/2026-09-29/R6-014-BLOCK2-ANALYSIS.json"
ANALYSIS_SHA256 = "7322b996fb69843680f51e678fac87baa44c6f231f1b4b2bcd6cdd5405f725e8"
ANALYSIS_PROGRAM = "experiments/r6/analysis_r6.py"
COLLECTION = "experiments/r6/cohort-live-v9"
DRAWS = range(1, 9)
OUT = Path(__file__).resolve().parent / "data"


def reviewed_families(program: Path) -> dict[str, str]:
    """REVIEWED_FAMILIES, read from the frozen program without running it."""
    tree = ast.parse(program.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "REVIEWED_FAMILIES" for t in node.targets
        ):
            # The literal mixes dict comprehensions and plain keys; evaluate it
            # alone, with no names in scope.
            families = eval(compile(ast.Expression(node.value), str(program), "eval"),
                            {"__builtins__": {}}, {})
            return {site: fam.removeprefix("Bracket.") for site, fam in families.items()}
    raise SystemExit(f"REVIEWED_FAMILIES not found in {program}")


def line(site: str) -> str:
    return "l" + site.removeprefix("bracket-l")


def write(name: str, header: list[str], rows: list[list]) -> None:
    with open(OUT / name, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    root = Path(sys.argv[1]).expanduser()
    raw = (root / ANALYSIS).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == ANALYSIS_SHA256, f"analysis digest {digest} is not the r6 record's"
    a = json.loads(raw)
    families = reviewed_families(root / ANALYSIS_PROGRAM)

    pops = a["populations"]
    primary, posed = pops["primary"], pops["posed"]
    feasible, control = pops["certificate_feasible"], pops["negative_control"]
    not_posed = pops["not_posed"]
    assert (len(primary), len(posed), len(feasible), len(control), len(not_posed)) == (15, 11, 10, 1, 4)
    assert sorted(families) == sorted(primary)

    # ---- per slot: 15 obligations x 8 draws ------------------------------
    slots, count = [], {"posed": 0, "verified": 0, "proved": 0, "refused": 0, "rejected": 0}
    for site in primary:
        for d in DRAWS:
            if site in not_posed:
                slots.append([line(site), families[site], d, "not_posed", "", ""])
                continue
            s = a["per_slot"][f"{site}/{d}"]
            assert s["disposition"] == "sent_with_response" and s["returned"]
            count["posed"] += 1
            if s["whole"]:
                assert s["verified"] and s["consumed"] and s["local"] and s["axioms"]
                stage = "proved"
            elif s["verified"]:
                stage = "refused"
            else:
                stage = "rejected"
            count["verified"] += bool(s["verified"])
            count[stage] += 1
            slots.append([line(site), families[site], d, stage,
                          s.get("closer") or "", s.get("refusal") or ""])
    assert count == {"posed": 88, "verified": 80, "proved": 48, "refused": 32, "rejected": 8}, count
    assert len(a["per_slot"]) == 88

    by_stage = {}
    for row in slots:
        by_stage.setdefault(row[0], set()).add(row[3])
    proved = sorted(k for k, v in by_stage.items() if v == {"proved"})
    refused = sorted(k for k, v in by_stage.items() if v == {"refused"})
    assert proved == ["l069", "l070", "l071", "l078", "l096", "l099"], proved
    assert refused == ["l166", "l175", "l178", "l204"], refused
    assert by_stage["l170"] == {"rejected"}
    assert {r[5] for r in slots if r[3] == "refused"} == {"nat_closer_int_goal"}
    assert not a["negative_control"]["false_certificate_acceptances"]
    assert a["contradictory_observations"] == {}

    # Coverage never moved: six whole-validated slots per draw.
    for d in DRAWS:
        whole = a["prefixes"][f"draws_1_to_{d}"]["stages_over_sent"]["whole"]["true"]
        assert whole == 6 * d, (d, whole)

    write("slots.csv", ["site", "family", "draw", "stage", "closer", "refusal"], slots)

    # ---- per site: arms and witness diversity ---------------------------
    learned = a["arms"]["learned"]["by_site"]
    det = a["arms"]["deterministic"]["by_site"]
    ref = a["arms"]["deterministic_reference"]["by_site"]
    sites = []
    for site in primary:
        role = ("not_posed" if site in not_posed else
                "negative_control" if site in control else "feasible")
        ls = learned.get(site, {})
        sites.append([line(site), families[site], role,
                      ls.get("stages_over_sent", {}).get("whole", {}).get("true", ""),
                      ls.get("distinct_verified_witnesses", ""),
                      ls.get("verified_matching_classification_certificate", ""),
                      det[site], ref[site]])
    div = {r[0]: (r[4], r[5]) for r in sites if r[2] == "feasible"}
    assert div.pop("l070") == (4, 3) and div.pop("l071") == (2, 0), "witness diversity"
    assert all(v == (1, 8) for v in div.values()), div
    assert [line(s) for s in primary if det[s] == "proof"] == ["l069", "l070", "l071", "l078"]
    assert [line(s) for s in primary if ref[s] == "closed_and_validated"] == \
        ["l069", "l070", "l071", "l078", "l166", "l175", "l178", "l204"]

    write("sites.csv", ["site", "family", "role", "learned_whole_slots",
                        "distinct_verified_witnesses", "matching_classification",
                        "deterministic", "reference"], sites)

    # ---- the two ladders -------------------------------------------------
    st = a["strata"]["posed"]["stages_over_sent"]
    ladder = [
        ["slots", "returned", st["returned"]["true"]],
        ["slots", "verified", st["verified"]["true"]],
        ["slots", "consumed", st["consumed"]["true"]],
        ["slots", "whole_validated", st["whole"]["true"]],
        ["obligations", "primary", len(primary)],
        ["obligations", "posed", len(posed)],
        ["obligations", "certificate_feasible", len(feasible)],
        ["obligations", "proved", len(proved)],
    ]
    assert [r[2] for r in ladder] == [88, 80, 48, 48, 15, 11, 10, 6]
    write("ladder.csv", ["panel", "stage", "count"], ladder)

    # ---- when each run's reservation was reconciled ---------------------
    runs = []
    for rec in sorted((root / COLLECTION).glob("*/campaign-reconciliation.json")):
        r = json.loads(rec.read_text(encoding="utf-8"))
        when = datetime.fromtimestamp(r["reconciled_at_unix"], timezone.utc)
        runs.append([when.strftime("%Y-%m-%dT%H:%M:%SZ"), rec.parent.name,
                     line(r["task_id"]), r["draw"], r["kind"]])
    runs.sort()
    kinds = [r[4] for r in runs]
    assert len(runs) == 89 and kinds.count("send_grant") == 88 and kinds.count("release") == 1
    assert [r[1] for r in runs if r[4] == "release"] == ["l204-draw6"]
    write("runs.csv", ["reconciled_utc", "run", "site", "draw", "kind"], runs)

    print(f"wrote slots.csv, sites.csv, ladder.csv, runs.csv from {ANALYSIS} ({digest[:16]}…)")


if __name__ == "__main__":
    main()
