"""One tool, with the checks from Lecture 12 and a log.

A2: book_slot now carries the topic just studied, so the confirmation names what the slot is for.

    python tools.py --selftest

book_slot is deliberately narrow: it adds one revision slot to a local schedule file. It is enough to
practise the boundary on, and it cannot touch anything outside this folder.
"""
import json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "tool_log.jsonl")
SCHEDULE = os.path.join(HERE, "schedule.json")

TOOL = {"name": "book_slot",
        "description": "Add one revision slot to the local schedule. Does not contact anyone.",
        "args": {"date": "YYYY-MM-DD", "minutes": "integer 15..180", "topic": "optional text, up to 60 characters"}}

NEEDS_CONFIRMATION = True   # it writes a file the user can see: not reversible without an undo


def valid(call):
    """Check 1, shape. Returns (ok, reason) so the reason can be shown to a person."""
    if not isinstance(call, dict) or call.get("name") != TOOL["name"]:
        return False, "not a book_slot call"
    a = call.get("arguments")
    if not isinstance(a, dict):
        return False, "arguments must be an object"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(a.get("date", ""))):
        return False, "date must be YYYY-MM-DD"
    try:
        datetime.date.fromisoformat(a["date"])
    except (ValueError, TypeError):
        return False, "date is not a valid calendar date"
    raw_minutes = a.get("minutes")
    if isinstance(raw_minutes, bool) or not (isinstance(raw_minutes, int) or (isinstance(raw_minutes, str) and raw_minutes.isdecimal())):
        return False, "minutes must be an integer"
    m = int(raw_minutes)
    if not 15 <= m <= 180:
        return False, "minutes must be between 15 and 180"
    topic = a.get("topic", "")
    if not isinstance(topic, str) or len(topic) > 60:
        return False, "topic must be text of at most 60 characters"
    return True, ""


def describe(call):
    """What the confirmation shows: the arguments, in words, not the identifier."""
    a = call["arguments"]
    d = datetime.date.fromisoformat(a["date"])
    topic = (' for "%s"' % a["topic"]) if a.get("topic") else ""
    return "Add a %d-minute revision slot%s on %s to your local study schedule?" % (
        int(a["minutes"]), topic, d.strftime("%a %d %b %Y"))


def log_outcome(call, confirmed, result):
    """Log every finalized proposal, including refusals and cancellations."""
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": datetime.datetime.now().isoformat(timespec="minutes"),
                            "tool": call.get("name"), "args": call.get("arguments"),
                            "confirmed": bool(confirmed),
                            "confirmed_by": "user" if confirmed else None,
                            "result": result}) + "\n")


def run(call, confirmed_by="user"):

    """Execute, append to the log, and return what actually happened."""
    ok, reason = valid(call)
    if not ok:
        return {"status": "refused", "reason": reason}
    slots = []
    if os.path.exists(SCHEDULE):
        with open(SCHEDULE, encoding="utf-8") as f:
            slots = json.load(f)
    a = call["arguments"]
    if any(s["date"] == a["date"] and s["minutes"] == int(a["minutes"]) and s.get("topic", "") == a.get("topic", "")
           for s in slots):
        # confirming the same slot twice adds it once; another topic on the same day is a new slot
        result = {"status": "ok", "id": None,
                  "note": "This %d-minute slot on %s is already in your schedule; nothing added."
                          % (int(a["minutes"]), a["date"])}
    else:
        slot = {"id": "slot_%d" % (len(slots) + 1), "date": a["date"], "minutes": int(a["minutes"]),
                "topic": a.get("topic", "")}
        slots.append(slot)
        with open(SCHEDULE, "w", encoding="utf-8") as f:
            json.dump(slots, f, indent=1)
        result = {"status": "ok", "id": slot["id"], "total_slots": len(slots)}
    log_outcome(call, confirmed=bool(confirmed_by), result=result)
    return result


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        good = {"name": "book_slot", "arguments": {"date": "2026-11-14", "minutes": 90}}
        bad = {"name": "book_slot", "arguments": {"date": "2026-11-14", "minutes": 900}}
        assert valid(good)[0] and not valid(bad)[0]
        print("ok: valid call accepted, 900-minute call refused (%s)" % valid(bad)[1])
