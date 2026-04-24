
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import boto3


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_chat_export_from_path(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_chat_export_from_s3() -> dict:
    _metadata_api = os.environ.get("BUFFET_METADATA_API", "http://127.0.0.1:9001")
    _req = urllib.request.Request(
        f"{_metadata_api}/2018-06-01/runtime/invocation/next", method="GET"
    )
    with urllib.request.urlopen(_req, timeout=5) as _resp:
        _event = json.loads(_resp.read().decode("utf-8"))

    _creds = _event["assume_role_credentials"]
    _s3 = boto3.client(
        "s3",
        region_name="eu-west-1",
        aws_access_key_id=_creds["AccessKeyId"],
        aws_secret_access_key=_creds["SecretAccessKey"],
        aws_session_token=_creds["SessionToken"],
    )
    _bucket = _event["bucket_name"]
    _canvas_id = _event["id"]
    _file_key = (
        f"canvases/{_canvas_id}/agents/"
        "5dca49f0-c0c0-4652-8406-4e24669f3e90/76856ea1-8008-460f-8738-fb9cec55b1c0.json"
    )
    _obj = _s3.get_object(Bucket=_bucket, Key=_file_key)
    return json.loads(_obj["Body"].read().decode("utf-8"))


def _load_chat_export() -> dict:
    _data_dir = _project_root() / "data"
    _env_path = os.environ.get("BUFFET_CHAT_EXPORT")

    if _env_path:
        _chat_path = Path(_env_path).expanduser().resolve()
        if not _chat_path.is_file():
            raise FileNotFoundError(
                f"BUFFET_CHAT_EXPORT is set but file not found: {_chat_path}"
            )
        print(f"Loading chat export from BUFFET_CHAT_EXPORT={_chat_path}")
        return _load_chat_export_from_path(_chat_path)

    _default_local = _data_dir / "chat_export.json"
    _telegram_result = _data_dir / "result.json"
    _sample_fixture = _data_dir / "chat_export.sample.json"

    if _default_local.is_file():
        print(f"Loading chat export from {_default_local}")
        return _load_chat_export_from_path(_default_local)
    if _telegram_result.is_file():
        print(f"Loading chat export from {_telegram_result}")
        return _load_chat_export_from_path(_telegram_result)
    if _sample_fixture.is_file():
        print(
            f"Loading bundled sample data from {_sample_fixture} "
            "(add data/chat_export.json or set BUFFET_CHAT_EXPORT for your real export)"
        )
        return _load_chat_export_from_path(_sample_fixture)

    try:
        print("Loading chat export from S3 (Lambda metadata API + boto3)…")
        return _load_chat_export_from_s3()
    except (urllib.error.URLError, OSError, ConnectionRefusedError) as e:
        raise RuntimeError(
            "Cannot load chat data: no local export found and metadata service unreachable "
            "(port 9001). Put Telegram export at data/result.json or data/chat_export.json, "
            "set BUFFET_CHAT_EXPORT, or add data/chat_export.sample.json."
        ) from e


# ── Parse messages ────────────────────────────────────────────────────────────
_chat_export = _load_chat_export()
_all_msgs = _chat_export["messages"]
food_raw_messages = [m for m in _all_msgs if m.get("type") == "message"]
food_chat_name = _chat_export["name"]
food_total_count = len(food_raw_messages)

# ── Basic overview ────────────────────────────────────────────────────────────
print("=" * 60)
print("DATASET: result.json — Telegram Chat Export")
print("=" * 60)
print(f"Group Name       : {food_chat_name}")
print(f"Group Type       : {_chat_export['type']}")
print(f"Total Records    : {len(_all_msgs):,}")
print(f"User Messages    : {food_total_count:,}")
print(f"Service Messages : {len(_all_msgs) - food_total_count:,}")

# ── Schema ────────────────────────────────────────────────────────────────────
_all_keys = set()
for _m in food_raw_messages:
    _all_keys.update(_m.keys())

print(f"\nSCHEMA — Message Fields:")
print(f"  {sorted(_all_keys)}")
print(f"\nField presence (% non-empty):")
for _k in sorted(_all_keys):
    _cnt = sum(1 for _m in food_raw_messages if _m.get(_k) not in (None, "", [], {}))
    print(f"  {_k:<28} {_cnt:>5,}/{food_total_count:,} ({_cnt/food_total_count*100:.1f}%)")

# ── Date range ────────────────────────────────────────────────────────────────
_dates = [_m["date"] for _m in food_raw_messages if "date" in _m]
print(f"\nDate range: {min(_dates)} → {max(_dates)}")

# ── 5 sample messages ─────────────────────────────────────────────────────────
print(f"\nSAMPLE MESSAGES (first 5 with substantive text):")
_shown = 0
for _m in food_raw_messages:
    _raw = _m.get("text", "")
    _txt = (
        "".join(_t if isinstance(_t, str) else _t.get("text", "") for _t in _raw)
        if isinstance(_raw, list)
        else str(_raw)
    )
    if len(_txt.strip()) > 10:
        print(f"  [{_m['date']}] {_m.get('from','?')}: {_txt[:200]}")
        _shown += 1
        if _shown >= 5:
            break

print(f"\n✓ Exported: food_raw_messages ({food_total_count:,}), food_chat_name, food_total_count")
