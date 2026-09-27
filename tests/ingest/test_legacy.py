"""Legacy Votes.svc loader over the recorded v4 slice plus synthetic legacy rows shaped like the real ones
(field names, zero-padded kmmbr_id, reason=5 semantics from docs/audit/source-audit.md §4)."""

from __future__ import annotations

import copy
import datetime as dt

import psycopg
import pytest
from fastapi.testclient import TestClient

from hkv.api.app import create_app
from hkv.ingest.legacy import LegacyLoader, norm_tokens
from tests.ingest.test_loader import SLICE, FixtureSource, ingest, one, table_counts

DAY = dt.date(2022, 12, 13)
LEGACY_ONLY = 99001


def header(vote_id: int, f: int, a: int, ab: int, item: str) -> dict:
    return {"vote_id": vote_id, "knesset_num": 25, "session_id": "2198208", "sess_item_nbr": 3, "sess_item_id": "2196976",
            "sess_item_dscr": "הצעת חוק לדוגמה ", "vote_item_id": "121", "vote_item_dscr": item, "vote_date": "2022-12-13T00:00:00",
            "vote_time": "21:40", "is_elctrnc_vote": 1, "vote_type": 1, "is_accepted": 1, "total_for": f, "total_against": a,
            "total_abstain": ab, "vote_stat": 1, "session_num": 5, "vote_nbr_in_sess": 7, "reason": None, "modifier": None, "remark": None}


def shadow(vote_id: int, vip: int, name: str, result: int, reason: int | None = None) -> dict:
    return {"vote_id": vote_id, "kmmbr_id": f"{vip:09d}", "kmmbr_name": name, "vote_result": result, "knesset_num": 25,
            "faction_id": 1, "faction_name": "x", "reason": reason, "modifier": "Unknown" if reason else None, "remark": None}


def legacy_data() -> dict:
    v4_for = sum(1 for r in SLICE["KNS_PlenumVoteResult"] if r["VoteID"] == 37689 and r["ResultCode"] == 7)  # 62
    return {
        "View_vote_rslts_hdr_Approved": [
            header(37689, v4_for - 1, 52, 0, "אישור החוק"),   # one v4 'for' ballot is flagged reason=5 below
            header(LEGACY_ONLY, 2, 1, 0, "הסתייגות"),
        ],
        "vote_rslts_kmmbr_shadow": [
            shadow(37689, 30749, "משה אבוטבול", 1, reason=5),   # vip == KNS_Person.Id, name agrees
            shadow(LEGACY_ONLY, 532, "יולי יואל אדלשטיין", 1),  # id_and_name
            shadow(LEGACY_ONLY, 30369, "אמיר אוחנה", 1),          # vip differs from Person 30300 -> full_name (real case)
            shadow(LEGACY_ONLY, 31000, "ינון אזולאי", 2),
            shadow(LEGACY_ONLY, 39999, "פלוני כהן", 2),           # several MKs named כהן -> unresolved, never guessed
        ],
    }


def run_legacy(url: str, data: dict) -> dict:
    with psycopg.connect(url) as conn:
        return LegacyLoader(conn, FixtureSource(data), FixtureSource(SLICE)).load(DAY, DAY)


@pytest.fixture
def loaded(new_database):
    url = new_database()
    ingest(url, SLICE)
    run_legacy(url, legacy_data())
    return url


def test_name_tokens_ignore_punctuation():
    assert norm_tokens("מיקי חיימוביץ`") == norm_tokens("מיקי חיימוביץ'") == frozenset({"מיקי", "חיימוביץ"})


def test_reason5_ballot_excluded_and_totals_match(loaded):
    assert one(loaded, """SELECT b.legacy_reason, b.counted_in_official_total FROM ballot b JOIN person p ON p.id = b.person_id
                          JOIN vote v ON v.id = b.vote_id WHERE v.knesset_vote_id = 37689 AND p.knesset_person_id = 30749""") == (5, False)
    assert one(loaded, """SELECT count(*) FROM ballot b JOIN vote v ON v.id = b.vote_id
                          WHERE v.knesset_vote_id = 37689 AND b.counted_in_official_total IS TRUE""") == (113,)
    assert one(loaded, "SELECT count(*) FROM data_issue WHERE issue_type = 'totals_mismatch'") == (0,)
    assert one(loaded, "SELECT present_in FROM vote WHERE knesset_vote_id = 37689") == (["knesset_odata_v4", "knesset_votes_legacy"],)


def test_legacy_only_vote_is_created_with_ballots(loaded):
    at, on, motion, stage, present = one(loaded, "SELECT occurred_at, occurred_on, motion_type, stage, present_in FROM vote WHERE knesset_vote_id = %s", LEGACY_ONLY)
    assert on == DAY and at.isoformat().startswith("2022-12-13T19:40") and (motion, stage) == ("reservation", "second")
    assert present == ["knesset_votes_legacy"]
    rows = psycopg.connect(loaded).execute(
        """SELECT p.knesset_person_id, b.choice, b.source, b.faction_id IS NOT NULL FROM ballot b JOIN person p ON p.id = b.person_id
           JOIN vote v ON v.id = b.vote_id WHERE v.knesset_vote_id = %s ORDER BY 1""", (LEGACY_ONLY,)).fetchall()
    assert rows == [(532, "for", "knesset_votes_legacy", True), (30300, "for", "knesset_votes_legacy", True),
                    (30601, "against", "knesset_votes_legacy", True)]
    methods = dict(psycopg.connect(loaded).execute("SELECT vip_id, method FROM legacy_person_map").fetchall())
    assert methods[532] == "id_and_name" and methods[30369] == "full_name" and methods[31000] == "full_name"
    assert one(loaded, "SELECT count(*) FROM data_issue WHERE issue_type = 'legacy_person_unresolved' AND external_ref = 'vip:39999'") == (1,)


def test_rerun_is_idempotent(loaded):
    before = table_counts(loaded)
    run_legacy(loaded, legacy_data())
    assert table_counts(loaded) == before  # includes row_revision


def test_mismatch_becomes_issue(new_database):
    url = new_database()
    ingest(url, SLICE)
    data = legacy_data()
    data["View_vote_rslts_hdr_Approved"][0]["total_against"] = 40
    run_legacy(url, data)
    assert one(url, "SELECT details->'official' FROM data_issue WHERE issue_type = 'totals_mismatch'") == ([61, 40, 0],)


def test_api_reports_totals_against_counted_records(loaded):
    with TestClient(create_app(loaded)) as c:
        v = c.get("/api/v1/votes/37689").json()["data"]
        assert v["official_totals"]["for"] == 61 and v["roll_call"]["for"] == 62
        assert v["totals_match"] is True and v["excluded_from_official_total"] == 1
        legacy = c.get(f"/api/v1/votes/{LEGACY_ONLY}").json()["data"]
        assert (legacy["stage"], legacy["motion_type"], legacy["question_he"]) == ("second", "reservation", "הסתייגות")
        assert {b["source"] for b in c.get(f"/api/v1/votes/{LEGACY_ONLY}/ballots").json()["data"]} == {"knesset_votes_legacy"}
        assert [x["id"] for x in c.get("/api/v1/votes", params={"stage": "second", "date_to": "2022-12-31"}).json()["data"]] == [LEGACY_ONLY]


def test_spelling_variants_resolve_and_close_issues(new_database):
    """Real cases: legacy 'נעמה לזמי' is KNS 'נעמה לזימי'; a first run without the variant rule left an issue."""
    from hkv.ingest.legacy import skeleton
    assert skeleton(norm_tokens("דן סידה")) == skeleton(norm_tokens("דן סיידה"))
    url = new_database()
    ingest(url, SLICE)
    data = legacy_data()
    data["vote_rslts_kmmbr_shadow"][3] = shadow(LEGACY_ONLY, 31000, "ינון אזלאי", 2)  # defective spelling of אזולאי
    with psycopg.connect(url) as conn:
        conn.autocommit = True
        conn.execute("""INSERT INTO data_issue (external_ref, issue_type, severity) VALUES ('vip:31000', 'legacy_person_unresolved', 'error')""")
    run_legacy(url, data)
    assert one(url, "SELECT method FROM legacy_person_map WHERE vip_id = 31000") == ("spelling_variant",)
    assert one(url, "SELECT status FROM data_issue WHERE external_ref = 'vip:31000'") == ("resolved",)


def test_legacy_title_cleanup():
    from hkv.ingest.legacy import clean_title
    assert clean_title("הצעת חוק-יסוד: הכנסת (תיקון מס` 50 ? הוראת שעה) ") == "הצעת חוק-יסוד: הכנסת (תיקון מס' 50 – הוראת שעה)"
