"""Mineração de texto — backend (Flask). Execute: python app.py  →  http://127.0.0.1:5000"""
import io, math, os, re, unicodedata
from collections import Counter
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
STATE = {}  # último corpus analisado (app local, um usuário)

STOP = set("""a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sob sobre entre até ao aos à às e ou mas
que se como mais menos muito muita já não nem também só são é foi ser era ter tem têm há isso isto esse essa esses essas este esta
estes estas seu sua seus suas meu minha nosso quando onde qual quais cada outro outra outros outras pelo pela pelos pelas num numa
the of and to in is are for on with as by an be this that from at or it its was were has have not""".split())

norm = lambda w: unicodedata.normalize("NFD", w).encode("ascii", "ignore").decode()
toks = lambda t: [w for w in re.findall(r"[^\W\d_]+", t.lower()) if len(w) > 1]
content = lambda t: [w for w in toks(t) if w not in STOP]

def sents(t):
    t = re.sub(r"[ \t]+", " ", t)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", t) if len(s.strip()) > 20]

def extract(f):
    n, raw = f.filename.lower(), f.read()
    if n.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)
    if n.endswith(".docx"):
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
    try: return raw.decode("utf-8")
    except UnicodeDecodeError: return raw.decode("latin-1")

# ---------- Sentimento (léxico + negação + intensificadores) ----------
POS = """bom boa ótimo ótima ótimos excelente maravilhoso maravilhosa incrível perfeito perfeita adorei amei gostei gostou gostamos recomendo rápido rápida
eficiente útil satisfeito feliz melhor legal lindo qualidade confiável fácil sucesso vantagem good great excellent love best amazing
helpful fast easy""".split()
NEG = """ruim péssimo péssima horrível terrível odiei decepcionante decepcionado demora demorou lento lenta caro defeito quebrou problema
problemas erro falha difícil pior fraco fraca atraso cancelar insatisfeito bad terrible worst slow broken awful hate poor""".split()
LEX = {**{norm(w): 1 for w in POS}, **{norm(w): -1 for w in NEG}}
NEGATORS, BOOST = {"nao", "nem", "nunca", "jamais", "sem", "not", "no"}, {"muito", "super", "extremamente", "bastante", "very"}

def sentiment(s):
    ws, sc = [norm(w) for w in re.findall(r"[^\W\d_]+", s.lower())], 0.0
    for i, w in enumerate(ws):
        v = LEX.get(w, 0)
        if v:
            win = ws[max(0, i - 3):i]
            if NEGATORS & set(win): v *= -0.8
            if BOOST & set(win): v *= 1.5
            sc += v
    return sc / math.sqrt(sc * sc + 4)  # normaliza para (-1, 1)

label = lambda x: "positivo" if x >= .2 else "negativo" if x <= -.2 else "neutro"

# ---------- Entidades nomeadas (padrões + nomes próprios) ----------
CAP = r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\w\-]*"
ENT = re.compile(rf"\b{CAP}(?:\s+(?:(?:de|da|do|dos|das|of)\s+)?{CAP})*")
PAT = [("E-mail", r"[\w.+-]+@[\w-]+\.[\w.-]+"), ("URL", r"https?://\S+|www\.\S+"),
       ("Data", r"(?i:\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\w* de \d{4})"),
       ("Valor", r"R\$\s?[\d.,]+|\b\d+(?:[.,]\d+)?\s?%")]
ORG_K = ("university", "institute", "group", "lab", "universidade", "instituto", "núcleo", "microsoft", "google", "ibm", "sas", "openai", "mit")
PLACES = {"brasil", "eua", "europa", "são paulo", "usp", "stanford", "cambridge"}

def etype(e):
    l = e.lower()
    if l in PLACES - {"usp", "stanford"}: return "Local"
    if e.isupper() or any(k in l for k in ORG_K): return "Organização"
    return "Nome próprio"

def entities(sentences):
    c = Counter()
    for s in sentences:
        for tipo, p in PAT:
            for m in re.findall(p, s): c[(m.strip(".,;"), tipo)] += 1
            s = re.sub(p, " ", s)
        for m in ENT.finditer(s):
            e = m.group().strip()
            if " " not in e and m.start() == 0 and not e.isupper(): continue  # início de frase ≠ nome próprio
            parts = e.split()
            while len(parts) > 1 and parts[0].lower() in STOP and parts[0] != "São": parts.pop(0)  # "O NILC" → "NILC"
            e = " ".join(parts)
            if e.lower() in STOP or len(e) < 2: continue
            c[(e, etype(e))] += 1
    return [{"texto": e, "tipo": t, "n": n} for (e, t), n in c.most_common(60)]

# ---------- Corpus, TF-IDF, resumo, busca ----------
def build(docs):
    units = [(d["name"], s) for d in docs for s in sents(d["text"])]
    tk = [content(s) for _, s in units]
    df = Counter(w for t in tk for w in set(t))
    N = len(units)
    STATE.update(units=units, tk=tk, idf={w: math.log((1 + N) / (1 + c)) + 1 for w, c in df.items()})

def vec(t):
    return {w: (1 + math.log(n)) * STATE["idf"].get(w, 1) for w, n in Counter(t).items()}

def cosine(a, b):
    na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
    return sum(v * b.get(w, 0) for w, v in a.items()) / (na * nb) if na and nb else 0

def analyze(docs):
    docs = [d for d in docs if d["text"].strip()]
    if not docs: return {"erro": "Nenhum texto encontrado. Envie um arquivo (PDF, DOCX, TXT) ou cole um texto."}
    build(docs)
    units, tk, idf = STATE["units"], STATE["tk"], STATE["idf"]
    if not units: return {"erro": "O texto é curto demais para ser analisado."}
    tf = Counter(w for t in tk for w in t)
    allt = [w for d in docs for w in toks(d["text"])]
    bi = Counter((a, b) for _, s in units for a, b in zip(toks(s), toks(s)[1:]) if a not in STOP and b not in STOP)
    score = lambda i: sum(tf[w] * idf[w] for w in set(tk[i])) / (len(tk[i]) + 5)
    top = sorted((i for i in range(len(units)) if len(tk[i]) >= 4), key=score, reverse=True)[:5]
    sc = [sentiment(s) for _, s in units]
    per = []
    for d in docs:
        v = [x for (n, _), x in zip(units, sc) if n == d["name"]]
        per.append({"nome": d["name"], "media": round(sum(v) / len(v), 3) if v else 0,
                    **{k: sum(label(x) == k for x in v) for k in ("positivo", "neutro", "negativo")}})
    return {
        "stats": {"docs": len(docs), "frases": len(units), "tokens": len(allt), "vocabulario": len(set(allt)),
                  "riqueza": round(len(set(allt)) / max(len(allt), 1), 3), "media_frase": round(len(allt) / len(units), 1)},
        "resumo": [units[i][1] for i in sorted(top)],
        "frequentes": tf.most_common(15),
        "tfidf": sorted(((w, round(n * idf[w], 2)) for w, n in tf.items()), key=lambda x: -x[1])[:15],
        "nuvem": tf.most_common(45),
        "bigramas": [[" ".join(k), n] for k, n in bi.most_common(10)],
        "sentimento": {"docs": per, "serie": [{"s": round(x, 2), "t": units[i][1][:140]} for i, x in enumerate(sc[:240])]},
        "entidades": entities([s for _, s in units]),
    }

def corpus_from_request():
    if request.is_json: return request.json["docs"]
    docs = [{"name": f.filename, "text": extract(f)} for f in request.files.getlist("files") if f.filename]
    if request.form.get("text", "").strip(): docs.append({"name": "Texto colado", "text": request.form["text"]})
    return docs

SAMPLE = [
    {"name": "avaliacoes_loja.txt", "text": """Adorei o produto, chegou rápido e a qualidade é excelente. Recomendo muito!
O atendimento foi péssimo, demoraram uma semana para responder e o problema continua.
Produto bom, mas a entrega atrasou. Não gostei do prazo.
Não é ruim, funciona bem pelo preço. Entrega rápida e embalagem boa.
Horrível! O produto quebrou em dois dias e o suporte não resolveu nada.
Muito satisfeito com a compra, melhor custo-benefício que já encontrei. Voltarei a comprar.
O aplicativo é lento e difícil de usar, mas o suporte da Maria Souza na Natura ajudou bastante.
Comprei na Amazon por R$ 249,90 e chegou em São Paulo em 3 dias. Perfeito!"""},
    {"name": "texto_pln.txt", "text": """A mineração de texto extrai padrões e conhecimento útil de grandes volumes de texto não estruturado. Empresas como IBM, Google e Microsoft oferecem ferramentas de análise de sentimento e extração de entidades.
Em 2017, o artigo Attention Is All You Need apresentou a arquitetura Transformer, base dos modelos de linguagem atuais. A análise de sentimento classifica a polaridade emocional de avaliações e redes sociais.
O NILC, na USP, é referência em processamento de linguagem natural para o português. Alan Turing propôs o teste de Turing em 1950, marco da inteligência artificial.
A tokenização divide o texto em palavras, e a remoção de stopwords elimina termos pouco informativos. O TF-IDF mede a importância de cada palavra em um corpus de documentos."""}]

@app.get("/")
def index(): return send_file(os.path.join(os.path.dirname(__file__), "index.html"))

@app.post("/api/analyze")
def api_analyze(): return jsonify(analyze(corpus_from_request()))

@app.get("/api/sample")
def api_sample(): return jsonify(analyze(SAMPLE))

@app.post("/api/search")
def api_search():
    q = content(request.json.get("q", ""))
    if not STATE or not q: return jsonify({"termos": q, "resultados": []})
    qv = vec(q)
    ranked = sorted(((cosine(qv, vec(t)), i) for i, t in enumerate(STATE["tk"])), reverse=True)[:5]
    return jsonify({"termos": q, "resultados": [{"doc": STATE["units"][i][0], "texto": STATE["units"][i][1], "score": round(s, 3)}
                                                  for s, i in ranked if s > 0]})

@app.post("/api/pipeline")
def api_pipeline():
    text = request.json.get("text", "")[:2000]
    lower = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()
    t = toks(text)
    kept = [w for w in t if w not in STOP]
    vocab = sorted(set(kept))
    s = sentiment(text)
    return jsonify({"original": text, "normalizado": lower, "tokens": t, "removidas": [w for w in t if w in STOP], "uteis": kept,
                    "vetor": [[w, kept.count(w)] for w in vocab], "sentimento": {"score": round(s, 2), "rotulo": label(s)},
                    "entidades": entities(sents(text + " ")) if len(text) > 20 else []})

# ===================== EXTRAS (blocos adicionais) =====================
PT_W = set("de do da dos das em no na nos nas que um uma para com não por mais como mas foi são também ao ou é os".split())
EN_W = set("the of and to in is are for on with by an be this that from at it was were has have not or".split())
sil = lambda w: max(1, len(re.findall(r"[aeiouáéíóúâêôãõàü]+", w)))  # sílabas ≈ grupos de vogais

def idioma(ws):
    p, e = sum(w in PT_W for w in ws), sum(w in EN_W for w in ws)
    return "indefinido" if p + e < 3 else ("português" if p >= e else "inglês")

@app.get("/api/extras")  # idioma, legibilidade (Flesch) e tempo de leitura por documento
def api_extras():
    by = {}
    for n, s in STATE.get("units", []): by.setdefault(n, []).append(s)
    out = []
    for n, ss in by.items():
        ws = toks(" ".join(ss))
        if not ws: continue
        lang, W, S = idioma(ws), len(ws), len(ss)
        base = 206.835 if lang == "inglês" else 248.835  # constantes do Flesch (inglês) e da adaptação ao português
        fl = max(0, min(100, base - 1.015 * W / S - 84.6 * sum(map(sil, ws)) / W))
        out.append({"nome": n, "idioma": lang, "palavras": W, "minutos": round(W / 200, 1), "flesch": round(fl),
                    "nivel": "muito fácil" if fl >= 75 else "fácil" if fl >= 50 else "difícil" if fl >= 25 else "muito difícil",
                    "tam_palavra": round(sum(map(len, ws)) / W, 1)})
    return jsonify({"docs": out})

@app.get("/api/kwic")  # palavra no contexto: frases em que o termo aparece
def api_kwic():
    w = request.args.get("w", "").lower().strip()
    hits = [{"doc": n, "texto": s} for (n, s), t in zip(STATE.get("units", []), STATE.get("tk", [])) if w in t]
    return jsonify({"total": len(hits), "resultados": hits[:15]})

@app.post("/api/analyze_url")  # texto de uma página da web
def api_analyze_url():
    url = (request.json or {}).get("url", "").strip()
    if not re.match(r"https?://", url): return jsonify({"erro": "Link inválido. Use um endereço começando com http:// ou https://."})
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return jsonify({"erro": "Faltam bibliotecas. Rode: pip install requests beautifulsoup4"})
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (mineracao-texto)"})
        r.raise_for_status()
    except Exception as e:
        return jsonify({"erro": f"Não foi possível abrir o link ({type(e).__name__})."})
    soup = BeautifulSoup(r.content[:5_000_000], "html.parser")
    nome = (soup.title.string or "").strip()[:80] if soup.title else ""
    for t in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]): t.decompose()
    root = soup.find("article") or soup.find("main") or soup
    text = "\n".join(p for p in (x.get_text(" ", strip=True) for x in root.find_all(["p", "li", "h1", "h2", "h3"])) if len(p) > 20)
    if not text: return jsonify({"erro": "Não encontrei texto nessa página (pode exigir login ou carregar por JavaScript)."})
    return jsonify(analyze([{"name": nome or url, "text": text}]))

@app.post("/api/topicos")  # modelagem de tópicos (NMF sobre TF-IDF)
def api_topicos():
    try:
        from sklearn.decomposition import NMF
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        return jsonify({"erro": "Falta a biblioteca. Rode: pip install scikit-learn"})
    k = max(2, min(6, int((request.json or {}).get("k", 3))))
    units, docs = STATE.get("units", []), [" ".join(t) for t in STATE.get("tk", [])]
    keep = [i for i, d in enumerate(docs) if len(d.split()) >= 3]
    minimo = max(10, k * 3)
    if len(keep) < minimo:
        return jsonify({"erro": f"Texto curto demais para {k} tópicos: são necessárias ao menos {minimo} frases com conteúdo (há {len(keep)})."})
    try:
        vec = TfidfVectorizer(token_pattern=r"\S+", max_df=0.9)
        X = vec.fit_transform([docs[i] for i in keep])
        model = NMF(n_components=k, init="nndsvda", random_state=0, max_iter=400)
        W = model.fit_transform(X)
    except ValueError:
        return jsonify({"erro": "Vocabulário insuficiente para separar tópicos neste texto."})
    termos, dom, out = vec.get_feature_names_out(), W.argmax(axis=1), []
    for t, comp in enumerate(model.components_):
        mine = [j for j in range(len(keep)) if dom[j] == t]
        best = max(mine, key=lambda j: W[j, t]) if mine else None
        out.append({"topico": t + 1, "pct": round(100 * len(mine) / len(keep)),
                    "palavras": [[termos[i], round(float(comp[i]), 2)] for i in comp.argsort()[::-1][:8] if comp[i] > 0],
                    "exemplo": units[keep[best]][1] if best is not None else ""})
    return jsonify({"k": k, "frases": len(keep), "topicos": out})

def sem_quickedit():
    """No Windows, clicar na janela preta pausa o servidor (modo QuickEdit). Desativa isso."""
    if os.name != "nt": return
    try:
        import ctypes
        k, m = ctypes.windll.kernel32, ctypes.c_uint32()
        h = k.GetStdHandle(-10)
        k.GetConsoleMode(h, ctypes.byref(m))
        k.SetConsoleMode(h, (m.value & ~0x40) | 0x80)
    except Exception:
        pass

if __name__ == "__main__":
    sem_quickedit()
    app.run(host="127.0.0.1", port=5000, threaded=True)  # sem debug: sem reinício duplo nem travas
