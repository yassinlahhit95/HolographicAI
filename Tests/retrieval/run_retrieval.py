"""Banco de 105 preguntas sueltas + variantes de internet.  Uso: python run_retrieval.py [e5|fallback]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from common import load_assistant, docs_of
from questions import Q, Q_INTERNET
mode = sys.argv[1] if len(sys.argv) > 1 else "e5"
a = load_assistant(mode)
for name, bank in (("105 preguntas", Q), ("variantes internet", Q_INTERNET)):
    hit = top1 = chars = 0; miss = []
    for q, exp in bank:
        kb = a.retrieve_knowledge(q, []); d = docs_of(a, kb); chars += len(kb)
        ok = bool(exp & set(d)); hit += ok; top1 += bool(d and d[0] in exp)
        if not ok: miss.append((q, sorted(e[:2] for e in exp), [x[:2] for x in d]))
    n = len(bank)
    print("[%s] %s: entregado %d/%d = %.1f%% | top1 %.1f%% | %.0f car/pregunta" % (mode, name, hit, n, 100*hit/n, 100*top1/n, chars/n))
    for m in miss: print("   FALLO:", m[0], "esperado", m[1], "recibe", m[2])
