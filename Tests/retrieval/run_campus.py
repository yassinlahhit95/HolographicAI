"""Bancos con SECCION esperada.  Uso: python run_campus.py [e5|fallback] [campus|equipo]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
from common import load_assistant, docs_of, sections_of
from questions import Q_CAMPUS, Q_EQUIPO
mode = sys.argv[1] if len(sys.argv) > 1 else "e5"
bank_name = sys.argv[2] if len(sys.argv) > 2 else "campus"
BANK = {"campus": Q_CAMPUS, "equipo": Q_EQUIPO}[bank_name]
a = load_assistant(mode)
by = defaultdict(lambda: [0, 0, 0, 0]); fails = []
for q, exp, sec, kind in BANK:
    kb = a.retrieve_knowledge(q, []); d = docs_of(a, kb); s = sections_of(kb)
    ok = bool(exp & set(d)); t1 = bool(d and d[0] in exp)
    sok = ok and (sec is None or any(alt.lower() in x.lower() for alt in sec.split("|") for x in s))
    v = by[kind]; v[0] += ok; v[1] += t1; v[2] += sok; v[3] += 1
    if not sok: fails.append((kind, q, sorted(e[:2] for e in exp), sec, [x[:2] for x in d], [x[:28] for x in s]))
tot = [sum(v[i] for v in by.values()) for i in range(4)]
print("[%s] %s: modulo %d/%d | top1 %d/%d | seccion correcta %d/%d   " % (mode, bank_name, tot[0], tot[3], tot[1], tot[3], tot[2], tot[3])
      + "  ".join("%s %d/%d" % (k, v[2], v[3]) for k, v in by.items()))
for f in fails: print("   FALLO [%s] %s esperado %s/%s recibe %s %s" % f)
