"""Banco de conversaciones con contexto.  Uso: python run_context.py [margen ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
from common import load_assistant, docs_of, as_history
from context_cases import CASES
a = load_assistant("e5")
margins = [float(x) for x in sys.argv[1:]] or [a.CONTEXT_MARGIN]
for mg in margins:
    a.CONTEXT_MARGIN = mg
    by = defaultdict(lambda: [0, 0, 0]); fails = []
    for hist, q, exp, kind in CASES:
        d = docs_of(a, a.retrieve_knowledge(q, as_history(hist)))
        ok = bool(exp & set(d)); t1 = bool(d and d[0] in exp)
        by[kind][0] += ok; by[kind][1] += t1; by[kind][2] += 1
        if not ok: fails.append((kind, q, sorted(e[:2] for e in exp), [x[:2] for x in d]))
    tot = [sum(v[i] for v in by.values()) for i in range(3)]
    print("CONTEXT_MARGIN=%.3f  entregado %d/%d | top1 %d/%d   " % (mg, tot[0], tot[2], tot[1], tot[2])
          + "  ".join("%s %d/%d(top1 %d)" % (k, v[0], v[2], v[1]) for k, v in by.items()))
    for f in fails: print("   FALLO [%s] %s esperado %s recibe %s" % f)
