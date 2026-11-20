"""Wide test 5: odd requests and random multi-turn sequences sent to a running server.

    python app.py --port 8766 &        # from a scratch copy: reports and bookings are written to its logs
    python scripts/wide_tests/http_requests.py 8766

Every request must get a JSON reply (never a dropped connection), and every sentence on screen must
cite a passage that is shown."""
import http.client, json, random, sys
PORT = int(sys.argv[1])
FAIL = []


def raw(body, ctype="application/json", path="/", method="POST", headers=None):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    h = {"Content-Type": ctype}
    h.update(headers or {})
    try:
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        data = r.read()
        return r.status, data
    except Exception as e:
        return None, repr(e)


def post(payload):
    st, data = raw(json.dumps(payload).encode())
    if st != 200:
        return st, data
    return st, json.loads(data)


# 1. malformed requests: never a dropped connection, always a JSON error
odd = [b"", b"{", b"[]", b"null", b"123", b'"text"', b"\xff\xfe", b'{"action": "nope"}', b'{"action": null}',
       b'{"action": "report", "index": null}', b'{"action": "report", "index": "x"}', b'{"action": "report", "index": [1]}',
       b'{"action": "report", "index": 1e309}', b'{"action": "report", "index": NaN}',
       b'{"action": "correct", "fields": {"question_type": ["union"]}}',
       b'{"action": "correct", "fields": {"question_type": {"a": 1}, "values": {"P(A)": NaN}}}',
       b'{"action": "correct", "fields": {"question_type": "union", "values": {"P(A)": Infinity, "P(B)": [1]}}}',
       b'{"action": "correct", "fields": {"question_type": "union", "values": {"P(A)": true, "P(B)": {"x": 1}}}}',
       b'{"action": "ask", "message": null}', b'{"action": "ask", "message": {"a": 1}}', b'{"action": "ask", "message": 12}',
       b'{"action": "ask", "message": "' + b"P(A)=0.3 " * 2000 + b'"}',
       b'{"action": "clarify", "choice": "rephrase"}', b'{"action": "clarify"}',
       b'{"action": "confirm_slot"}', b'{"action": "cancel_slot"}', b'{"action": "ask", "simulate_overclaim": "yes", "message": "Are A and B independent?"}']
for body in odd:
    st, data = raw(body)
    if st is None:
        FAIL.append(("connection dropped", body[:80], data))
    elif st not in (200, 400):
        FAIL.append(("status", st, body[:80]))
    else:
        try:
            json.loads(data)
        except Exception:
            FAIL.append(("not JSON", st, body[:80], data[:100]))
# wrong lengths and paths
for path, method in (("/x", "GET"), ("/../app.py", "GET"), ("/index.html", "GET"), ("/", "GET"), ("/x", "POST")):
    st, data = raw(b'{"action":"ask","message":"hi"}', path=path, method=method)
    if st is None or (path in ("/", "/index.html") and method == "GET" and st != 200) or (path.startswith("/x") and st != 404):
        FAIL.append(("path", path, method, st))
st, data = raw(b"{}", headers={"Content-Length": "999999"})
if st is None: FAIL.append(("huge length dropped connection",))

# 2. multi-turn sequences
QS = ["P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?", "Are they independent?",
      "P(A)=0.3, P(B)=0.4. What is P(A∪B)?", "What is a Markov chain?", "P(A)=1.5. Are A and B independent?",
      "A and B are mutually exclusive. P(A)=0.2, P(B)=0.3. What is P(A∪B)?"]
ACTIONS = ["ask", "correct", "report", "report", "clarify", "propose_slot", "confirm_slot", "cancel_slot"]
random.seed(3)
for run in range(400):
    for step in range(random.randint(1, 8)):
        act = random.choice(ACTIONS)
        if act == "ask":
            p = {"action": "ask", "message": random.choice(QS), "simulate_overclaim": random.random() < 0.3}
        elif act == "correct":
            p = {"action": "correct", "fields": {"question_type": random.choice(["union", "independence", "conditional", "intersection", "exclusive", "exclusive_and_independent", "other"]),
                 "mutually_exclusive": random.random() < 0.3, "independent": random.random() < 0.3,
                 "values": {k: random.choice(["", "0.2", "0.3", "1/3", "50%", "0", "1"]) for k in ("P(A)", "P(B)", "P(A∩B)", "P(A∪B)", "P(A|B)")}}}
        elif act == "report":
            p = {"action": "report", "index": random.randint(-1, 4), "reason": "x"}
        elif act == "clarify":
            p = {"action": "clarify", "choice": "exclusive_and_independent"}
        else:
            p = {"action": act}
        st, d = post(p)
        if st != 200:
            FAIL.append(("sequence step failed", p, st, d if isinstance(d, (bytes, str)) else ""))
            continue
        if "status" in d:
            # every shown sentence cites a shown passage; removed sentences are not shown
            ids = {e["id"] for e in d.get("evidence", [])}
            for s in d.get("sentences", []):
                if s.get("passage_id") not in ids:
                    FAIL.append(("sentence cites a passage not shown", p, s.get("text")))
            if d["status"] == "checked" and d.get("removed") and not p.get("simulate_overclaim") and "report" not in d:
                FAIL.append(("removal without demo or report", p, d["removed"]))
print("failures:", len(FAIL))
for f in FAIL[:30]:
    print(f)
