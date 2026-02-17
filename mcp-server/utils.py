from datetime import date, datetime

def _normalize_hired_on(value: str) -> str:
    if not isinstance(value, str):
        return value

    s = value.strip()
    if not s:
        return value

    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.date().isoformat()
        return date.fromisoformat(s).isoformat()
    except Exception:
        return value
