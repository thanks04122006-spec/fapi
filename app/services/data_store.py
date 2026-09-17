"""DB 없이 표준 세로형 CSV로 데이터를 적재/조회하는 저장소.

- 같은 date + gate + hour 조합이 이미 있으면 자동 합산하지 않고 duplicate 로 표시합니다.
- 결측값은 임의로 0으로 채우지 않습니다 (전처리 단계에서 오류로 분리되어 저장되지 않음).
"""
from __future__ import annotations

import pandas as pd

from app.core.config import STANDARD_CSV_PATH
from app.models.schemas import StandardRecord

_COLUMNS = [
    "date",
    "day_of_week",
    "gate",
    "gate_name",
    "passage_id",
    "hour",
    "in_count",
    "out_count",
    "total_in",
    "total_out",
    "is_partial",
    "source_file",
    "is_duplicate",
]


def _load_existing() -> pd.DataFrame:
    if STANDARD_CSV_PATH.exists():
        return pd.read_csv(STANDARD_CSV_PATH, dtype={"date": str, "gate": str})
    return pd.DataFrame(columns=_COLUMNS)


def append_records(records: list[StandardRecord]) -> tuple[int, int]:
    """레코드를 표준 CSV에 추가. (신규 저장 건수, 중복으로 표시된 건수) 반환."""
    existing = _load_existing()
    existing_keys = set(zip(existing.get("date", []), existing.get("gate", []), existing.get("hour", [])))

    new_rows = []
    duplicate_count = 0
    seen_in_batch = set()

    for rec in records:
        key = (rec.date, rec.gate, rec.hour)
        is_dup = key in existing_keys or key in seen_in_batch
        if is_dup:
            duplicate_count += 1
        else:
            seen_in_batch.add(key)
        row = rec.model_dump()
        row["is_duplicate"] = is_dup
        new_rows.append(row)

    new_df = pd.DataFrame(new_rows, columns=_COLUMNS)
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined.to_csv(STANDARD_CSV_PATH, index=False)

    inserted = len(new_rows) - duplicate_count
    return inserted, duplicate_count


def load_all() -> pd.DataFrame:
    df = _load_existing()
    if df.empty:
        return df
    df["date"] = df["date"].astype(str)
    df["hour"] = df["hour"].astype(int)
    df["in_count"] = df["in_count"].astype(int)
    df["out_count"] = df["out_count"].astype(int)
    df["is_partial"] = df["is_partial"].astype(bool)
    if "is_duplicate" in df.columns:
        df["is_duplicate"] = df["is_duplicate"].astype(bool)
    else:
        df["is_duplicate"] = False
    return df


def load_non_duplicate() -> pd.DataFrame:
    df = load_all()
    if df.empty:
        return df
    return df[~df["is_duplicate"]].copy()


def latest_date() -> str | None:
    df = load_all()
    if df.empty:
        return None
    return sorted(df["date"].unique())[-1]
