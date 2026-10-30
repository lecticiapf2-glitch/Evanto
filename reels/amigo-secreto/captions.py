# Groups the word-timed transcript into short Reels caption chunks.
import json, re
from plan_v2 import DROP, DROP_AT, REPLACE

MAX_WORDS, MAX_CHARS, GAP = 4, 22, 0.35


def chunks(path):
    words = [w for w in json.load(open(path))["words"] if w.get("type", "word") == "word"]
    words = [dict(w, text=REPLACE.get(w["text"], w["text"])) for w in words if w["text"] not in DROP and round(w["start"], 2) not in DROP_AT]
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        txt = " ".join(x["text"] for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_sentence = re.search(r"[.,?!:]\"?$", w["text"])
        if (nxt is None or end_sentence or len(cur) >= MAX_WORDS
                or len(txt) + 1 + len(nxt["text"]) > MAX_CHARS or nxt["start"] - w["end"] > GAP):
            out.append(cur); cur = []
    res = []
    for k, c in enumerate(out):
        text = " ".join(x["text"] for x in c)
        text = re.sub(r"[\"“”]", "", text)
        text = re.sub(r"[.,:;]+(?=\s|$)", "", text).strip()       # Reels style: no commas/periods
        start, end = c[0]["start"], c[-1]["end"]
        nxt_start = out[k + 1][0]["start"] if k + 1 < len(out) else end + 0.6
        end = max(end + 0.12, start + 0.45)
        end = min(end, nxt_start) if nxt_start - end < 0.25 else end
        res.append((round(start - 0.03, 3), round(min(end, nxt_start), 3), text))
    return res


if __name__ == "__main__":
    import sys
    for s, e, t in chunks(sys.argv[1]):
        print(f"{s:6.2f}-{e:6.2f}  {t}")
