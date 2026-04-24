
import re
from collections import Counter

import numpy as np
import pandas as pd


def _get_text(msg):
    raw = msg.get('text', '')
    if isinstance(raw, list):
        return ''.join(t if isinstance(t, str) else t.get('text', '') for t in raw)
    return str(raw)


def _extract_locations(text):
    locs = []
    at = re.findall(r'[@＠]\s*([^\n\r,!?]{3,50})', text)
    locs.extend([a.strip() for a in at if len(a.strip()) > 2])
    codes = re.findall(r'\b(SOE|SCIS|SIS|SOA|SOG|LKCSB|SOSS|SOLM|CIS)\b', text, re.IGNORECASE)
    locs.extend(codes)
    floors = re.findall(r'\b(?:level|lvl|floor|L)\s*([0-9B]{1,2})\b', text, re.IGNORECASE)
    if floors:
        locs.extend([f'Level {f}' for f in floors])
    return '; '.join(set(locs)) if locs else None


def _build_food_df(messages):
    records = []
    for msg in messages:
        txt = _get_text(msg)
        dt = pd.to_datetime(msg['date'])
        records.append({
            'msg_id':        msg['id'],
            'datetime':      dt,
            'date':          dt.date(),
            'hour':          dt.hour,
            'day_of_week':   dt.strftime('%A'),
            'day_of_week_n': dt.dayofweek,
            'month':         dt.month,
            'year':          dt.year,
            'sender':        msg.get('from', 'Unknown'),
            'has_photo':     bool(msg.get('photo')),
            'has_location':  bool(msg.get('location_information')),
            'text_length':   len(txt),
            'text':          txt,
            'reaction_count': sum(r['count'] for r in msg.get('reactions', [])) if msg.get('reactions') else 0,
            'is_reply':      bool(msg.get('reply_to_message_id')),
            'is_edited':     bool(msg.get('edited')),
            'is_forwarded':  bool(msg.get('forwarded_from')),
        })

    df = pd.DataFrame(records)

    # Location features
    df['location_extracted'] = df['text'].apply(_extract_locations)
    df['has_at_location'] = df['text'].str.contains(r'[@＠]', na=False)

    # Food cleared / available indicators
    _cleared_patterns = r'\b(cleared|gone|finished|done|all taken|no more|empty|finished)\b'
    _available_patterns = r'\b(available|left|remaining|more|free food|buffet|food alert)\b'
    df['is_cleared'] = df['text'].str.contains(_cleared_patterns, case=False, na=False)
    df['is_available'] = df['text'].str.contains(_available_patterns, case=False, na=False)
    df['is_food_post'] = (
        df['has_photo'] |
        df['has_at_location'] |
        df['is_cleared'] |
        df['is_available'] |
        df['text'].str.contains(
            r'\b(food|eat|pizza|cake|noodle|rice|lunch|dinner|breakfast|snack|drink|dessert)\b',
            case=False, na=False,
        )
    )

    # Time-based features
    df['time_bucket'] = pd.cut(
        df['hour'],
        bins=[0, 9, 12, 14, 17, 20, 24],
        labels=['Early Morning (0-9)', 'Morning (9-12)', 'Lunch (12-14)',
                'Afternoon (14-17)', 'Evening (17-20)', 'Night (20-24)'],
        right=False,
    )
    df['is_weekend'] = df['day_of_week_n'] >= 5

    return df


food_df = _build_food_df(food_raw_messages)

# ── Summary statistics ─────────────────────────────────────────────────────────
print("=" * 65)
print("FEATURE EXTRACTION SUMMARY")
print("=" * 65)
print(f"\nTotal messages parsed : {len(food_df):,}")
print(f"Date range            : {food_df['date'].min()} → {food_df['date'].max()}")
print(f"Unique senders        : {food_df['sender'].nunique():,}")

print(f"\n{'─'*65}")
print("KEY PREDICTION FEATURES")
print('─'*65)
print(f"\n🕐 TIMING FEATURES:")
print(f"  Messages with photo   : {food_df['has_photo'].sum():,} ({food_df['has_photo'].mean()*100:.1f}%)")
print(f"  Food posts (estimated): {food_df['is_food_post'].sum():,} ({food_df['is_food_post'].mean()*100:.1f}%)")
print(f"  'CLEARED' messages    : {food_df['is_cleared'].sum():,} ({food_df['is_cleared'].mean()*100:.1f}%)")
print(f"  'Available' messages  : {food_df['is_available'].sum():,} ({food_df['is_available'].mean()*100:.1f}%)")
print(f"  Weekend messages      : {food_df['is_weekend'].sum():,} ({food_df['is_weekend'].mean()*100:.1f}%)")

print(f"\n📅 DAY OF WEEK DISTRIBUTION (food posts only):")
_food_only = food_df[food_df['is_food_post']]
_dow = _food_only['day_of_week'].value_counts()
_dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
for _day in _dow_order:
    _cnt = _dow.get(_day, 0)
    _bar = '█' * (_cnt // 5)
    print(f"  {_day:<12} {_cnt:>4} {_bar}")

print(f"\n⏰ HOUR OF DAY DISTRIBUTION (food posts only):")
_hour_counts = _food_only['hour'].value_counts().sort_index()
for _hr, _cnt in _hour_counts.items():
    _bar = '█' * (_cnt // 5)
    print(f"  {_hr:02d}:00  {_cnt:>4} {_bar}")

print(f"\n🕑 TIME BUCKET DISTRIBUTION (food posts only):")
_tb = _food_only['time_bucket'].value_counts()
for _tb_name, _cnt in _tb.sort_index().items():
    print(f"  {str(_tb_name):<28} {_cnt:>4}")

print(f"\n📍 LOCATION FEATURES:")
_with_loc = food_df['location_extracted'].notna().sum()
print(f"  Messages with extracted location : {_with_loc:,} ({_with_loc/len(food_df)*100:.1f}%)")
print(f"  Messages with @ location         : {food_df['has_at_location'].sum():,} ({food_df['has_at_location'].mean()*100:.1f}%)")
print(f"  Messages with GPS location       : {food_df['has_location'].sum():,} ({food_df['has_location'].mean()*100:.1f}%)")

# Top locations from text
_all_locs = []
for _loc_str in food_df['location_extracted'].dropna():
    _all_locs.extend([_l.strip() for _l in _loc_str.split(';') if _l.strip()])
_top_locs = Counter(_all_locs).most_common(20)
print(f"\n  Top 20 extracted locations:")
for _loc, _cnt in _top_locs:
    print(f"    {_loc:<40} {_cnt:>4}")

print(f"\n👤 TOP 10 SENDERS (food posts):")
_top_senders = _food_only['sender'].value_counts().head(10)
for _sender, _cnt in _top_senders.items():
    print(f"  {_sender:<30} {_cnt:>4}")

print(f"\n{'─'*65}")
print("FEATURE SUMMARY FOR PREDICTION MODEL")
print('─'*65)
print("""
Key features identified for predicting food availability/location:

TEMPORAL FEATURES (when food appears):
  • hour             — Hour of day (0–23)
  • day_of_week_n    — Day of week (0=Mon, 6=Sun)
  • is_weekend       — Boolean weekend indicator
  • time_bucket      — Categorical time of day
  • month            — Month (seasonality)
  • year             — Year

CONTENT FEATURES (nature of post):
  • has_photo        — 40.3% of messages include a photo
  • has_at_location  — Post contains '@' location marker
  • is_food_post     — Estimated food-related message
  • is_cleared       — Food has been cleared/taken
  • is_available     — Food is available/remaining
  • text_length      — Length of message text
  • reaction_count   — Number of emoji reactions

LOCATION FEATURES (where food is):
  • location_extracted — NLP-extracted location from text
  • has_location        — Has GPS coordinates (rare: 0.03%)

SOCIAL FEATURES:
  • sender           — Who posted (some users post more food alerts)
  • is_reply         — Is this a reply to another message
""")

print(f"✓ Exported: food_df ({len(food_df):,} rows × {len(food_df.columns)} cols)")
print(f"  Columns: {list(food_df.columns)}")
