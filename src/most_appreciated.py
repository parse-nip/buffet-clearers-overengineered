from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates

from chart_json import write_chart_spec
from graph_output import save_and_close_if_exporting

# ── Design tokens (match food_pattern.py) ────────────────────────────────────
VIZ_BG = "#1D1D20"
VIZ_TEXT = "#fbfbff"
VIZ_SEC = "#909094"
VIZ_COLORS = [
    "#A1C9F4",
    "#FFB482",
    "#8DE5A1",
    "#FF9F9B",
    "#D0BBFF",
    "#1F77B4",
    "#9467BD",
    "#8C564B",
    "#C49C94",
    "#E377C2",
]
VIZ_GOLD = "#ffd400"


def _get_text(msg: dict) -> str:
    raw = msg.get("text", "")
    if isinstance(raw, list):
        return "".join(
            t if isinstance(t, str) else t.get("text", "") for t in raw
        )
    return str(raw)


def _reaction_total(msg: dict) -> int:
    rx = msg.get("reactions") or []
    return sum(r.get("count", 0) for r in rx)


def _emoji_rows(msg: dict) -> list[tuple[str, int]]:
    rows = []
    for r in msg.get("reactions") or []:
        em = r.get("emoji") or "·"
        rows.append((em, r.get("count", 0)))
    rows.sort(key=lambda x: -x[1])
    return rows


# ── Peak single-post reactions (all user messages) ───────────────────────────
_rows = []
for msg in food_raw_messages:
    total = _reaction_total(msg)
    if total <= 0:
        continue
    sender = msg.get("from") or msg.get("from_id") or "Unknown"
    _rows.append(
        {
            "reactions": total,
            "sender": str(sender),
            "msg_id": msg.get("id"),
            "date": msg.get("date"),
            "msg": msg,
        }
    )

peak_df = pd.DataFrame(_rows)

if peak_df.empty:
    fig = plt.figure(figsize=(10, 5), facecolor=VIZ_BG)
    ax = fig.add_subplot(111)
    ax.set_facecolor(VIZ_BG)
    ax.text(
        0.5,
        0.5,
        "No reactions in export — nothing to plot.",
        ha="center",
        va="center",
        color=VIZ_TEXT,
        fontsize=14,
        transform=ax.transAxes,
    )
    ax.axis("off")
    save_and_close_if_exporting(
        fig,
        "most_appreciated",
        "most_appreciated_person_and_followers.png",
        facecolor=VIZ_BG,
    )
    write_chart_spec(
        "most_appreciated",
        "most_appreciated_person_and_followers.png",
        {
            "chart": "empty",
            "title": "Most appreciated",
            "message": "No reactions in export — nothing to plot.",
        },
    )
    print("most_appreciated: no reactions in export")
else:
    peak_df = peak_df.sort_values("reactions", ascending=False)
    winner = peak_df.iloc[0]
    wmsg = winner["msg"]

    # Top N single-post peaks (context around the champion)
    top_n = min(12, len(peak_df))
    head = peak_df.head(top_n).copy()
    head["label"] = head.apply(
        lambda r: f"{r['sender'][:28]}{'…' if len(str(r['sender'])) > 28 else ''} (#{r['msg_id']})",
        axis=1,
    )

    # ── Cumulative “followers up”: joins + invites from service messages ───────
    all_msgs = _chat_export["messages"]
    chat_start = min(
        pd.to_datetime(m["date"])
        for m in all_msgs
        if m.get("date")
    )
    growth_events = []
    for m in all_msgs:
        if m.get("type") != "service":
            continue
        act = m.get("action")
        if act == "join_group_by_link":
            growth_events.append(
                {"date": m["date"], "add": 1, "kind": "join", "who": m.get("actor")}
            )
        elif act == "invite_members":
            n = len(m.get("members") or [])
            if n:
                growth_events.append(
                    {
                        "date": m["date"],
                        "add": n,
                        "kind": "invite",
                        "who": m.get("actor"),
                    }
                )

    growth_df = pd.DataFrame(growth_events)
    if not growth_df.empty:
        growth_df["datetime"] = pd.to_datetime(growth_df["date"])
        growth_df = growth_df.sort_values("datetime")
        growth_df["cumulative"] = growth_df["add"].cumsum()

    # Chat end date (for extending the followers line to “now” in export)
    msg_dates = [
        pd.to_datetime(m["date"])
        for m in all_msgs
        if m.get("date") and m.get("type") == "message"
    ]
    export_end = max(msg_dates) if msg_dates else pd.Timestamp.now(tz=None)

    fig = plt.figure(figsize=(13, 10), facecolor=VIZ_BG)
    gs = gridspec.GridSpec(
        2,
        2,
        figure=fig,
        height_ratios=[1.35, 1],
        hspace=0.38,
        wspace=0.28,
        left=0.08,
        right=0.96,
        top=0.92,
        bottom=0.07,
    )

    # ── Top: peak reactions per post (runners-up) ─────────────────────────────
    ax_top = fig.add_subplot(gs[0, :])
    ax_top.set_facecolor(VIZ_BG)
    y_pos = range(len(head))
    cols = [VIZ_GOLD if i == 0 else VIZ_COLORS[i % len(VIZ_COLORS)] for i in range(len(head))]
    bars = ax_top.barh(
        list(y_pos)[::-1],
        head["reactions"].values[::-1],
        color=cols[::-1],
        height=0.72,
        zorder=3,
    )
    ax_top.set_yticks(list(y_pos))
    ax_top.set_yticklabels(head["label"].values[::-1], color=VIZ_SEC, fontsize=8)
    ax_top.set_xlabel("Reactions on that one post", color=VIZ_SEC, fontsize=11)
    for sp in ax_top.spines.values():
        sp.set_edgecolor("#3a3a3d")
    ax_top.tick_params(colors=VIZ_SEC, labelsize=9)
    ax_top.xaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
    ax_top.set_axisbelow(True)

    preview = _get_text(wmsg).strip().replace("\n", " ")
    if len(preview) > 120:
        preview = preview[:117] + "…"
    photo_note = " [photo / media]" if wmsg.get("photo") and not preview else ""

    ax_top.set_title(
        f'Most appreciated in {food_chat_name}\n'
        f"🏆 {winner['sender']} — {int(winner['reactions'])} reactions on a single post"
        f" — {pd.to_datetime(winner['date']).date()}{photo_note}",
        color=VIZ_TEXT,
        fontsize=13,
        fontweight="bold",
        pad=14,
    )
    if preview:
        ax_top.text(
            0,
            1.02,
            f'"{preview}"',
            transform=ax_top.transAxes,
            ha="left",
            va="bottom",
            color=VIZ_SEC,
            fontsize=8,
            style="italic",
            wrap=True,
        )

    for bar in bars:
        w = bar.get_width()
        ax_top.text(
            w + max(head["reactions"]) * 0.02,
            bar.get_y() + bar.get_height() / 2,
            str(int(w)),
            va="center",
            ha="left",
            color=VIZ_TEXT,
            fontsize=8,
        )

    # ── Bottom left: emoji mix on the winning post ─────────────────────────────
    ax_emoji = fig.add_subplot(gs[1, 0])
    ax_emoji.set_facecolor(VIZ_BG)
    em_rows = _emoji_rows(wmsg)
    if em_rows:
        emo = [e[0] for e in em_rows]
        ecnts = [e[1] for e in em_rows]
        ey = range(len(emo))
        ax_emoji.barh(
            list(ey)[::-1],
            ecnts[::-1],
            color=[VIZ_COLORS[i % len(VIZ_COLORS)] for i in range(len(emo))][::-1],
            height=0.65,
            zorder=3,
        )
        ax_emoji.set_yticks(list(ey))
        ax_emoji.set_yticklabels(emo[::-1], color=VIZ_SEC, fontsize=10)
    ax_emoji.set_xlabel("Count", color=VIZ_SEC, fontsize=10)
    ax_emoji.set_title(
        "Reaction mix on that post",
        color=VIZ_TEXT,
        fontsize=11,
        fontweight="bold",
        pad=8,
    )
    for sp in ax_emoji.spines.values():
        sp.set_edgecolor("#3a3a3d")
    ax_emoji.tick_params(colors=VIZ_SEC)
    ax_emoji.xaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
    ax_emoji.set_axisbelow(True)

    # ── Bottom right: followers up (cumulative joins from export) ───────────────
    ax_f = fig.add_subplot(gs[1, 1])
    ax_f.set_facecolor(VIZ_BG)
    if growth_df.empty:
        ax_f.text(
            0.5,
            0.55,
            "No join/invite service events\nin this export.",
            ha="center",
            va="center",
            color=VIZ_SEC,
            fontsize=11,
            transform=ax_f.transAxes,
        )
    else:
        g = growth_df.copy()
        cum = g["cumulative"].tolist()
        dts = g["datetime"].tolist()
        x_step = [chat_start] + dts + [pd.Timestamp(export_end)]
        y_step = [0] + cum + [cum[-1]]
        ax_f.fill_between(
            x_step,
            0,
            y_step,
            step="post",
            alpha=0.14,
            color=VIZ_COLORS[2],
            zorder=1,
        )
        ax_f.step(
            x_step,
            y_step,
            where="post",
            color=VIZ_COLORS[0],
            linewidth=2.2,
            zorder=3,
        )
        ax_f.scatter(
            g["datetime"],
            g["cumulative"],
            color=VIZ_GOLD,
            s=36,
            zorder=4,
            edgecolors=VIZ_BG,
            linewidths=0.8,
        )
        ax_f.set_ylabel("Cumulative new members (from export)", color=VIZ_SEC, fontsize=10)
        ax_f.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax_f.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax_f.xaxis.get_majorticklabels(), rotation=30, ha="right", color=VIZ_SEC, fontsize=8)
    ax_f.set_title(
        "Followers up (group growth)",
        color=VIZ_TEXT,
        fontsize=11,
        fontweight="bold",
        pad=8,
    )
    for sp in ax_f.spines.values():
        sp.set_edgecolor("#3a3a3d")
    ax_f.tick_params(colors=VIZ_SEC)
    ax_f.yaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
    ax_f.set_axisbelow(True)
    if not growth_df.empty:
        ax_f.set_ylim(bottom=0)

    # --- Interactive spec (composite: peaks + emoji + growth) ----------------
    _panels: list[dict] = [
        {
            "chart": "barh",
            "title": "Top single-post reaction peaks",
            "highlight": "first",
            "reverseY": True,
            "categories": [str(x) for x in head["label"].tolist()],
            "values": [int(x) for x in head["reactions"].tolist()],
        }
    ]
    if em_rows:
        _panels.append(
            {
                "chart": "barh",
                "title": "Reaction mix on champion post",
                "highlight": "first",
                "reverseY": True,
                "categories": [str(e[0]) for e in em_rows],
                "values": [int(e[1]) for e in em_rows],
            }
        )
    if growth_df.empty:
        _panels.append(
            {
                "chart": "message",
                "title": "Followers up (group growth)",
                "message": "No join/invite service events in this export.",
            }
        )
    else:
        _g = growth_df.copy()
        _cum = _g["cumulative"].tolist()
        _dts = [pd.Timestamp(t).isoformat() for t in _g["datetime"].tolist()]
        _x_step = [pd.Timestamp(chat_start).isoformat()] + _dts + [pd.Timestamp(export_end).isoformat()]
        _y_step = [0] + _cum + [_cum[-1]]
        _panels.append(
            {
                "chart": "stepLine",
                "title": "Followers up (cumulative joins + invites)",
                "dates": _x_step,
                "values": [int(v) for v in _y_step],
            }
        )

    write_chart_spec(
        "most_appreciated",
        "most_appreciated_person_and_followers.png",
        {
            "chart": "composite",
            "title": f"Most appreciated in {food_chat_name}",
            "subtitle": (
                f"{winner['sender']} — {int(winner['reactions'])} reactions on one post · "
                f"{pd.to_datetime(winner['date']).date()}"
            ),
            "quote": preview or "",
            "panels": _panels,
        },
    )

    save_and_close_if_exporting(
        fig,
        "most_appreciated",
        "most_appreciated_person_and_followers.png",
        facecolor=VIZ_BG,
    )
    print(
        f"most_appreciated: champion {winner['sender']} with {int(winner['reactions'])} "
        f"reactions on msg {winner['msg_id']}"
    )

print("\n✅ Most appreciated + followers chart rendered.")
