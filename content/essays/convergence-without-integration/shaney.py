# Published with "Convergence Without Integration" as the code behind its vault experiment.
# The data it reads (corpus.db: the agents' vault, revision by revision, attributed to models)
# is private and not included, so this code documents the method; it will not run as is.
"""Mark V. Shaney on the vault: an order-2 word chain per model, and a chorus of all of them.

Each prose sentence is credited to the model of the first revision it appears in. A chain's
state is the last two words and it picks the next in proportion to how often it followed, as
the original did. Three things are reported besides the samples:

  forced    how much of a model's text, at equal size, had only one continuation ever seen
  coverage  how many of model Y's held-out word triples a chain trained on model X contains
  chorus    sentences from a chain over equal shares of every model, cut into the fewest
            stretches a single model could have supplied, against shuffled labels

    python3 analysis/shaney.py [--seed N] [-n SAMPLES] [--save]

Samples are recombined vault text: they go to the screen and to shaney_samples.txt, which is
not committed. --save writes the numbers alone to analysis/results/<date>-shaney.txt.
"""
import argparse, datetime, json, os, re, sqlite3, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corpus, prose

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=1984)
ap.add_argument("-n", type=int, default=6)
ap.add_argument("--plain", action="store_true", help="samples without code spans or digits")
ap.add_argument("--author", action="store_true", help="add the author's own text (from hand.py) as a voice")
ap.add_argument("--by-document", action="store_true", help="with --author: each of his notes on its own line")
ap.add_argument("--save", action="store_true")
args = ap.parse_args()
rng = np.random.default_rng(args.seed)

MIN = 100_000        # prose words a model needs for a chain of its own
REPS = 5             # random equal-size samples behind each number
CHORUS = 3000        # chorus sentences cut into stretches
START, END, GLUE = 0, 1, corpus.GLUE
inline = corpus.inline

# ---- sentences, each credited to the first model to write it

db = sqlite3.connect(os.path.join(HERE, "..", "corpus.db"))
vocab, words = {"<s>": START, "</s>": END}, ["<s>", "</s>"]
models, units = {}, {}
flat, s_model, s_unit, s_len, s_group = [], [], [], [], []
groups = {}
author = json.load(open(os.path.join(HERE, "..", "author_sentences.json"))) if args.author else []
his = {sent for _, _, sent in author}


def take(sent, label, doc, group=-1):
    ids = []
    for t in sent.split():
        i = vocab.get(t)
        if i is None:
            i = vocab[t] = len(words)
            words.append(t)
        ids.append(i)
    m = models.setdefault(label, len(models))
    flat.extend((START, START, *ids, END))
    s_model.append(m)
    s_unit.append(units.setdefault((doc, m), len(units)))
    s_len.append(len(ids))
    s_group.append(group)


for path, _, model, _, sent in corpus.first_sentences(db, inline):
    if sent not in his:                  # a vault note quoting the author is not the model's text
        take(sent, model, path)
for source, doc, sent in author:
    g = doc if source == "essays" or args.by_document else "vault/" + (doc.split("/")[0] if "/" in doc else "(top level)")
    take(sent, "you: " + source, doc, groups.setdefault(g, len(groups)))
yours = [m for name, m in models.items() if name.startswith("you: ")]

V = len(words)
assert V ** 3 < 2 ** 63
flat = np.array(flat, dtype=np.int64)
s_model, s_unit, s_len, s_group = np.array(s_model), np.array(s_unit), np.array(s_len), np.array(s_group)
names = [re.sub(r"^claude-", "", m) for m in models]
unit_test = np.array([zlib.crc32(p.encode()) % 5 == 0 for p, _ in units])  # a fifth of notes held out

# one row per word: the triple ending at it, packed into an integer
third = flat[2:]
keep = third != START
key = ((flat[:-2] * V + flat[1:-1]) * V + third)[keep]
k_sent = (np.cumsum(flat == END) - (flat == END))[2:][keep]
originals = {flat[a + 2:a + 2 + n].tobytes()
             for a, n in zip(np.cumsum(s_len + 3) - (s_len + 3), s_len)}


def rows(sent_mask):
    return np.sort(key[sent_mask[k_sent]])


def sample(pool, size):
    """Random sentences from pool (indices) up to size words, as a sentence mask."""
    pool = rng.permutation(pool)
    take = pool[np.cumsum(s_len[pool] + 1) <= size]
    mask = np.zeros(len(s_len), bool)
    mask[take] = True
    return mask


def generate(keys, lo=12, hi=40):
    """One sentence that is not in the vault, or None."""
    a = b = START
    out = []
    while len(out) <= hi:
        s = (a * V + b) * V
        i, j = np.searchsorted(keys, [s, s + V])
        c = int(keys[rng.integers(i, j)] % V)
        if c == END:
            ok = len(out) >= lo and np.array(out, dtype=np.int64).tobytes() not in originals
            return out if ok else None
        out.append(c)
        a, b = b, c
    return None


def several(keys, n, plain=False, **kw):
    out = []
    while len(out) < n:
        s = generate(keys, **kw)
        if s and not (plain and messy[s].any()):
            out.append(s)
    return out


def text(ids):
    return " ".join(words[i] for i in ids).replace(GLUE, " ")


def triples(ids):
    p = np.array([START, START, *ids, END], dtype=np.int64)
    return (p[:-2] * V + p[1:-1]) * V + p[2:]


messy = np.array([bool(re.search(r"[`$\d_/#]", w)) for w in words])
count = np.bincount(flat, minlength=V)
count[[START, END]] = count.max() + 1
common = np.zeros(V, bool)
common[np.argsort(-count)[:302]] = True     # the 300 most frequent word forms, and the two ends


def plain_rows(k):
    """The triples made only of common words: closer to manner than to subject."""
    return k[common[k // V // V] & common[k // V % V] & common[k % V]]


stats, samples = [], []
def say(s=""): print(s); stats.append(s)
def show(s=""): print(s); samples.append(s)

# ---- what there is

size = np.bincount(s_model, weights=s_len + 1, minlength=len(models)).astype(int)
big = [m for m in np.argsort(-size) if size[m] >= MIN and m not in yours]
say(f"{len(s_len):,} distinct prose sentences, {int(s_len.sum()):,} words, {V:,} distinct word forms")
say(f"chains for models with at least {MIN:,} words:")
for m in np.argsort(-size):
    say(f"  {names[m]:<16}{size[m]:>10,}" + ("   (the author)" if m in yours else "" if size[m] >= MIN else "   (too few)"))

# ---- forced, and coverage of held-out text, at equal size

sents = {m: np.flatnonzero(s_model == m) for m in big}
train = {m: sents[m][~unit_test[s_unit[sents[m]]]] for m in big}
test = {m: rows(np.isin(np.arange(len(s_len)), sents[m][unit_test[s_unit[sents[m]]]])) for m in big}
N = min(int((s_len[train[m]] + 1).sum()) for m in big)
forced = {m: [] for m in big}
cover = np.zeros((len(big), len(big)))
cover_plain = np.zeros((len(big), len(big)))
his_text = {"all of it": rows(np.isin(s_model, yours))} if yours else {}
his_text.update({names[m]: rows(s_model == m) for m in yours})
his_text.update({g: rows(s_group == i) for g, i in groups.items()})
his_all = {g: np.zeros(len(big)) for g in his_text}
his_plain = {g: np.zeros(len(big)) for g in his_text}
for _ in range(REPS):
    for i, x in enumerate(big):
        k = rows(sample(train[x], N))
        u = np.unique(k)
        state, fan = np.unique(u // V, return_counts=True)
        forced[x].append((fan[np.searchsorted(state, k // V)] == 1).mean())
        for j, y in enumerate(big):
            cover[i, j] += np.isin(test[y], u).mean() / REPS
            cover_plain[i, j] += np.isin(plain_rows(test[y]), u).mean() / REPS
        for g, k in his_text.items():
            his_all[g][i] += np.isin(k, u).mean() / REPS
            his_plain[g][i] += np.isin(plain_rows(k), u).mean() / REPS if len(plain_rows(k)) else 0

say(f"\nAt {N:,} training words each, mean of {REPS} random samples; a fifth of notes held out.")
say("\nforced: words that were the only continuation their two predecessors ever had")
for m in big:
    say(f"  {names[m]:<16}{np.mean(forced[m]):6.1%}")
for title, table in (("all triples", cover), ("triples of the 300 most frequent word forms only", cover_plain)):
    say(f"\ncoverage, {title}: share of the column model's held-out triples in the row model's chain")
    say("  " + " " * 16 + "".join(f"{names[m][:11]:>12}" for m in big))
    for i, x in enumerate(big):
        say(f"  {names[x]:<16}" + "".join(f"{table[i, j]:>12.1%}" for j in range(len(big))))
say(f"  (common-word triples are {np.mean([len(plain_rows(test[m])) / len(test[m]) for m in big]):.0%} of held-out triples)")

if yours:
    say("\nthe author's text against each model's chain (same chains as above; none of his text is in them)")
    say("share of his triples made of the 300 most frequent word forms that the chain holds; * marks the nearest")
    say(f"  {'':<44}{'words':>8}" + "".join(f"{names[m][:11]:>12}" for m in big))
    for g, k in his_text.items():
        if len(k) < 1500:
            continue
        best = int(np.argmax(his_plain[g]))
        say(f"  {g[:43]:<44}{len(k):>8,}" + "".join(f"{f'{v:.1%}' + ('*' if i == best else ' '):>12}" for i, v in enumerate(his_plain[g])))
    say("all his triples, not only the common-word ones:")
    for g in list(his_text)[:1 + len(yours)]:
        say(f"  {g[:43]:<44}{len(his_text[g]):>8,}" + "".join(f"{f'{v:.1%} ':>12}" for v in his_all[g]))

# ---- samples, one chain per model on everything it wrote

show("Sentences from each model's own chain (none is in the vault):")
for m in big:
    keys = rows(s_model == m)
    show(f"\n[{names[m]}]")
    for s in several(keys, args.n, args.plain):
        show("  " + text(s))

if yours:
    show("\n[you]")
    for s in several(rows(np.isin(s_model, yours)), args.n, args.plain):
        show("  " + text(s))

# ---- the chorus: equal shares of every model

NC = min(size[m] for m in big)
chosen = np.zeros(len(s_len), bool)
for m in big:
    chosen |= sample(sents[m], NC)
in_chorus = chosen[k_sent]
ckey, csent = key[in_chorus], k_sent[in_chorus]
order = np.argsort(ckey, kind="stable")
ckey, csent = ckey[order], csent[order]
ukey, inv = np.unique(ckey, return_inverse=True)
rank = {m: i for i, m in enumerate(big)}


def masks(label_of_sentence):
    """For each distinct triple, the set of labels whose text contains it, as bits."""
    out = np.zeros(len(ukey), dtype=np.int64)
    np.bitwise_or.at(out, inv, np.int64(1) << label_of_sentence[csent])
    return out


def stretches(ids, mask):
    """Fewest runs of words such that some one label supplies every triple in a run."""
    bits = mask[np.searchsorted(ukey, triples(ids))]
    cuts, owners = [0], [int(bits[0])]
    for i, b in enumerate(bits[1:], 1):
        if owners[-1] & int(b):
            owners[-1] &= int(b)
        else:
            cuts.append(i); owners.append(int(b))
    return cuts, owners


true = np.array([rank.get(m, 0) for m in s_model])
by_sentence = true.copy()
idx = np.flatnonzero(chosen)
by_sentence[idx] = rng.permutation(true[idx])
by_note = true.copy()
u = np.unique(s_unit[idx])
load, relabel = np.zeros(len(big)), {}
weight = np.bincount(s_unit[idx], weights=s_len[idx], minlength=len(units))
for x in rng.permutation(u):                 # notes in random order, each to the lightest label
    relabel[x] = int(np.argmin(load))
    load[relabel[x]] += weight[x]
by_note[idx] = [relabel[x] for x in s_unit[idx]]

chorus = several(ckey, CHORUS, lo=8, hi=40)
say(f"\nchorus: {NC:,} words from each of {len(big)} models; {CHORUS:,} generated sentences, "
    f"mean {np.mean([len(s) for s in chorus]):.1f} words")
say("  labels                 stretches per sentence   one model could say it whole")
for title, lab in (("true", true), ("shuffled by note", by_note), ("shuffled by sentence", by_sentence)):
    mk = masks(lab)
    n = np.array([len(stretches(s, mk)[0]) for s in chorus])
    say(f"  {title:<22}{n.mean():>12.2f}{(n == 1).mean():>30.1%}")

show("\nChorus sentences, cut where no single model could have carried on:")
mk = masks(true)
shown = 0
for s in chorus:
    cuts, owners = stretches(s, mk)
    if len(cuts) < 2 or len(s) < 14 or (args.plain and messy[s].any()):
        continue
    parts = []
    for a, b, own in zip(cuts, cuts[1:] + [len(s)], owners):
        who = "/".join(names[m] for m in big if own >> rank[m] & 1)
        if s[a:b]:
            parts.append(f"<{who}> " + text(s[a:b]))
    show("  " + " ".join(parts))
    shown += 1
    if shown == args.n:
        break

with open(os.path.join(HERE, "..", "shaney_samples.txt"), "w") as f:
    f.write("\n".join(samples) + "\n")
if args.save:
    out = os.path.join(HERE, "results", f"{datetime.date.today()}-{'voice' if args.author else 'shaney'}.txt")
    with open(out, "w") as f:
        f.write(f"seed {args.seed}\n" + "\n".join(stats) + "\n")
    print(f"\nwrote {out}", file=sys.stderr)
