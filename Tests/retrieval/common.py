"""Carga Scripts/assistant.py sin arrancar nada (solo conocimiento + buscador E5)."""
import os, sys, importlib.util
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def load_assistant(mode="e5", src=None):
    sys.path.insert(0, os.path.join(ROOT, "Scripts"))
    src = src or os.path.join(ROOT, "Scripts", "assistant.py")
    spec = importlib.util.spec_from_file_location("asst_test", src)
    a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
    a.KNOWLEDGE_DIR = os.path.join(ROOT, "Knowledge")
    a.log = lambda m: None
    if mode == "fallback":
        a._init_semantic_retriever = lambda: None
    a.load_knowledge()
    if mode == "fallback":
        a.SEM_MODEL = None
    return a

def docs_of(a, kb):
    """Modulos (por orden) de los fragmentos entregados al LLM."""
    out = []
    for blk in kb.split("[Tema: ")[1:]:
        f = blk.split("Fuente: ", 1)[1].split("]", 1)[0].strip()
        if f not in out:
            out.append(f)
    return out

def as_history(pairs):
    h = []
    for q, r in pairs:
        h += [{"role": "user", "content": "[Answer in Spanish, 1-3 natural spoken sentences.]\n" + q},
              {"role": "assistant", "content": r}]
    return h

def sections_of(kb):
    """Titulos de seccion (por orden) de los fragmentos entregados al LLM."""
    return [blk.split("|", 1)[0].strip() for blk in kb.split("[Tema: ")[1:]]
