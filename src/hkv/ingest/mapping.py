"""Pure mappings from Knesset source codes to schema values (db/migrations/0001_core.sql)."""

from __future__ import annotations

from typing import NamedTuple

# KNS_PlenumVoteResult.ResultCode -> (choice, participation). See docs/audit/source-audit.md §3.
RESULT_CODES: dict[int, tuple[str | None, str]] = {
    7: ("for", "cast"),
    8: ("against", "cast"),
    9: ("abstain", "cast"),
    6: (None, "present_not_voting"),
    11: (None, "participated_choice_unavailable"),
    10: (None, "absent_reported"),
}

# KNS_PlenumVote.VoteMethodID
VOTE_METHODS = {1: "electronic", 2: "roll_call", 3: "secret", 4: "show_of_hands_counted", 5: "show_of_hands"}

GENDERS = {"זכר": "male", "נקבה": "female"}
BILL_ORIGINS = {"פרטית": "private", "ממשלתית": "government", "ועדה": "committee"}

MANDATE_POSITIONS = {43, 61}   # חבר הכנסת / חברת הכנסת
FACTION_MEMBER_POSITION = 54   # חבר/ת סיעה


class OptionKind(NamedTuple):
    motion_type: str
    stage: str


# KNS_PlenumVote.ForOptionID -> what the question was. Curated from all options seen 2015-2026;
# stored with reviewed=false until a human checks it. Unlisted IDs -> unknown/unknown.
FOR_OPTIONS: dict[int, OptionKind] = {
    7: OptionKind("reservation", "second"),              # לקבל את ההסתייגות
    6: OptionKind("adopt_section", "second"),            # לקבל בקריאה שנייה
    8: OptionKind("adopt_bill", "third"),                # לקבל את הצעת החוק בקריאה שלישית
    1: OptionKind("adopt_bill", "first"),                # להעביר ... לוועדה להכנה לקריאה שניה ושלישית
    2: OptionKind("adopt_bill", "first"),                # ... לוועדה שתקבע ועדת הכנסת להכנה לקריאה שניה ושלישית
    33: OptionKind("adopt_bill", "first"),               # ... שתקבע הוועדה המסדרת להכנה לקריאה שניה ושלישית
    12: OptionKind("adopt_bill", "preliminary"),         # להעביר ... לוועדה להכנה לקריאה ראשונה
    13: OptionKind("adopt_bill", "preliminary"),         # ... שתקבע ועדת הכנסת להכנה לקריאה ראשונה
    32: OptionKind("adopt_bill", "preliminary"),         # ... שתקבע הוועדה המסדרת להכנה לקריאה ראשונה
    4: OptionKind("reject_bill", "unknown"),             # להסיר את הצעת החוק מסדר-היום
    16: OptionKind("no_confidence", "not_applicable"),   # להביע אי-אמון בממשלה
    23: OptionKind("secondary_legislation", "not_applicable"),
    17: OptionKind("agenda", "not_applicable"),          # להעביר את הנושא לדיון בוועדה
    18: OptionKind("agenda", "not_applicable"),
    19: OptionKind("agenda", "not_applicable"),          # לכלול את הנושא בסדר-היום
    20: OptionKind("agenda", "not_applicable"),
    21: OptionKind("agenda", "not_applicable"),          # הצעת סיכום הדיון
    9: OptionKind("procedural", "not_applicable"),       # להחיל דין רציפות
    3: OptionKind("procedural", "not_applicable"),
    14: OptionKind("procedural", "not_applicable"),
    22: OptionKind("procedural", "not_applicable"),
    27: OptionKind("procedural", "not_applicable"),
    28: OptionKind("procedural", "not_applicable"),
    29: OptionKind("procedural", "not_applicable"),
    35: OptionKind("procedural", "not_applicable"),
    36: OptionKind("procedural", "not_applicable"),
    37: OptionKind("procedural", "not_applicable"),
    39: OptionKind("procedural", "not_applicable"),      # תיקון טעות בחוק שהתקבל
    15: OptionKind("other", "not_applicable"),
    25: OptionKind("other", "not_applicable"),
    26: OptionKind("other", "not_applicable"),
    31: OptionKind("other", "not_applicable"),
    38: OptionKind("other", "not_applicable"),
}


def option_kind(option_id: int | None) -> OptionKind:
    return FOR_OPTIONS.get(option_id, OptionKind("unknown", "unknown")) if option_id is not None else OptionKind("unknown", "unknown")


def ballot_values(result_code: int) -> tuple[str | None, str]:
    """(choice, participation); unknown codes never become a choice or 'absent'."""
    return RESULT_CODES.get(result_code, (None, "unknown"))


def day(ts: str | None) -> str | None:
    """Source date-times carry the local (Israel) offset, so the date part is the local date."""
    return ts[:10] if ts else None


def vote_time(ts: str) -> tuple[str | None, str]:
    """(occurred_at, occurred_on). Some votes carry only a date, published as local midnight
    ('2022-12-13T00:00:00+02:00'); that is not a real time, so occurred_at is None."""
    return (None if ts[11:19] == "00:00:00" else ts), ts[:10]


def strip(s: str | None) -> str | None:
    return s.strip() if s is not None else None


def file_url(path: str) -> str:
    """KNS_Document*.FilePath uses Windows separators ('https://fs.knesset.gov.il/\\25\\law\\x.docx'); the server
    accepts forward slashes, which every browser and HTTP client handles."""
    host, _, rest = path.strip().partition("fs.knesset.gov.il")
    return host + "fs.knesset.gov.il/" + rest.replace("\\", "/").lstrip("/") if rest else path.strip()
