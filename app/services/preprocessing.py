"""2. 전처리 표준 출력 규격 구현

원본 엑셀(가로형 시간대 컬럼)을 표준 세로형 구조로 변환합니다.

# 원본 파일 가정
실제 원본 파일의 컬럼명을 확인하지 못했기 때문에, 아래와 같은 흔한 형태를 기본으로 가정하고
정규식 기반으로 유연하게 컬럼을 탐지합니다. 실제 파일이 다르면 `_detect_columns()`의
패턴만 조정하면 됩니다.

가정하는 원본 컬럼 예시:
- 날짜 컬럼: "날짜", "수집일자", "date" 중 하나
- 게이트명 컬럼: "게이트", "게이트명", "gate" 중 하나 (값 예: "자료실.정문", "자료실.후문")
- 통로ID 컬럼: "통로ID", "passage_id" 중 하나
- 시간대별 IN/OUT 컬럼: "8_IN", "8시_IN", "08_IN", "8_OUT" 형태 (8~23시)
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pandas as pd

from app.core.config import GATE_NAME_MAP
from app.core.errors import ExcelFormatError
from app.models.schemas import PreprocessError, StandardRecord

_HOUR_COL_PATTERN = re.compile(r"(?P<hour>\d{1,2})\s*시?\s*[_\-]?\s*(?P<dir>IN|OUT)", re.IGNORECASE)

_DATE_COL_CANDIDATES = ["날짜", "수집일자", "date", "Date"]
_GATE_COL_CANDIDATES = ["게이트", "게이트명", "gate", "gate_name"]
_PASSAGE_COL_CANDIDATES = ["통로ID", "통로id", "passage_id", "passageId"]


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in columns:
            return c
    return None


def _detect_columns(df: pd.DataFrame) -> dict[str, Any]:
    columns = list(df.columns.astype(str))

    date_col = _find_column(columns, _DATE_COL_CANDIDATES)
    gate_col = _find_column(columns, _GATE_COL_CANDIDATES)
    passage_col = _find_column(columns, _PASSAGE_COL_CANDIDATES)

    if not date_col or not gate_col:
        raise ExcelFormatError(
            "필수 컬럼(날짜, 게이트명)을 찾을 수 없습니다. "
            f"현재 컬럼: {columns}"
        )

    hour_cols: dict[int, dict[str, str]] = {}
    for col in columns:
        m = _HOUR_COL_PATTERN.search(col)
        if not m:
            continue
        hour = int(m.group("hour"))
        direction = m.group("dir").upper()
        if not (8 <= hour <= 23):
            continue
        hour_cols.setdefault(hour, {})[direction] = col

    if not hour_cols:
        raise ExcelFormatError("시간대별 IN/OUT 컬럼을 찾을 수 없습니다 (예: '8_IN', '8_OUT').")

    return {
        "date_col": date_col,
        "gate_col": gate_col,
        "passage_col": passage_col,
        "hour_cols": hour_cols,
    }


def _normalize_date(raw_value: Any) -> str | None:
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return None
    if isinstance(raw_value, (datetime, pd.Timestamp)):
        return raw_value.strftime("%Y-%m-%d")
    s = str(raw_value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _normalize_gate(raw_value: Any) -> tuple[str | None, str]:
    gate_name = str(raw_value).strip() if raw_value is not None else ""
    gate = GATE_NAME_MAP.get(gate_name)
    return gate, gate_name


def _to_nonneg_int(raw_value: Any) -> tuple[int | None, str | None]:
    """(값, 오류사유) 반환. 빈 셀/숫자 변환 불가/음수는 오류로 처리."""
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)) or str(raw_value).strip() == "":
        return None, "empty_cell"
    try:
        val = int(float(raw_value))
    except (ValueError, TypeError):
        return None, "not_a_number"
    if val < 0:
        return None, "negative_value"
    return val, None


def preprocess_dataframe(
    df: pd.DataFrame, source_file: str, latest_known_date: str | None = None
) -> tuple[list[StandardRecord], list[PreprocessError]]:
    """원본 DataFrame을 표준 세로형 레코드 목록 + 오류 목록으로 변환.

    latest_known_date: 이미 처리된 데이터 중 최신 날짜(오늘 진행 중 데이터 판단에 사용).
      오늘 날짜(로컬 today)와 같은 date가 있으면 is_partial=True로 표시합니다.
    """
    cols = _detect_columns(df)
    date_col, gate_col, passage_col, hour_cols = (
        cols["date_col"],
        cols["gate_col"],
        cols["passage_col"],
        cols["hour_cols"],
    )

    today_str = datetime.now().strftime("%Y-%m-%d")

    records: list[StandardRecord] = []
    errors: list[PreprocessError] = []

    for row_idx, row in df.iterrows():
        row_ref = f"row:{row_idx + 2}"  # +2: 1-index + header row 보정

        date_val = _normalize_date(row.get(date_col))
        if date_val is None:
            errors.append(
                PreprocessError(
                    source_file=source_file,
                    row_ref=row_ref,
                    reason="invalid_date_format",
                    raw_value=str(row.get(date_col)),
                )
            )
            continue

        gate, gate_name_raw = _normalize_gate(row.get(gate_col))
        if gate is None:
            errors.append(
                PreprocessError(
                    source_file=source_file,
                    row_ref=row_ref,
                    reason="unknown_gate_name",
                    raw_value=gate_name_raw,
                )
            )
            continue

        passage_id = str(row.get(passage_col)).strip() if passage_col else ""
        day_of_week = datetime.strptime(date_val, "%Y-%m-%d").strftime("%a")
        is_partial = date_val == today_str

        total_in = 0
        total_out = 0
        row_records: list[StandardRecord] = []
        row_had_error = False

        for hour in sorted(hour_cols):
            dirs = hour_cols[hour]
            in_col = dirs.get("IN")
            out_col = dirs.get("OUT")

            in_val, in_err = _to_nonneg_int(row.get(in_col)) if in_col else (None, "missing_in_column")
            out_val, out_err = _to_nonneg_int(row.get(out_col)) if out_col else (None, "missing_out_column")

            if in_err:
                errors.append(
                    PreprocessError(
                        source_file=source_file,
                        row_ref=f"{row_ref} hour:{hour} IN",
                        reason=in_err,
                        raw_value=str(row.get(in_col)) if in_col else None,
                    )
                )
                row_had_error = True
                continue
            if out_err:
                errors.append(
                    PreprocessError(
                        source_file=source_file,
                        row_ref=f"{row_ref} hour:{hour} OUT",
                        reason=out_err,
                        raw_value=str(row.get(out_col)) if out_col else None,
                    )
                )
                row_had_error = True
                continue

            total_in += in_val
            total_out += out_val
            row_records.append(
                StandardRecord(
                    date=date_val,
                    day_of_week=day_of_week,
                    gate=gate,
                    gate_name=gate_name_raw,
                    passage_id=passage_id,
                    hour=hour,
                    in_count=in_val,
                    out_count=out_val,
                    total_in=0,  # 아래에서 total 재기입
                    total_out=0,
                    is_partial=is_partial,
                    source_file=source_file,
                )
            )

        for rec in row_records:
            rec.total_in = total_in
            rec.total_out = total_out
        records.extend(row_records)

    return records, errors


def read_raw_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    try:
        if filename.lower().endswith((".xlsx", ".xls")):
            import io

            return pd.read_excel(io.BytesIO(file_bytes))
        elif filename.lower().endswith((".csv",)):
            import io

            return pd.read_csv(io.BytesIO(file_bytes))
        else:
            raise ExcelFormatError(f"지원하지 않는 파일 형식입니다: {filename}")
    except ExcelFormatError:
        raise
    except Exception as e:
        raise ExcelFormatError(f"파일을 읽는 중 오류가 발생했습니다: {e}")
