import os
import json
import time
import numpy as np

TRAJ_DIR = r"C:\Nero\trajetorias"
CHROMA_DIR = r"C:\Nero\dados\chroma_traj"
MAPA_FILE = r"C:\Nero\mapa_rag.md"
MODEL_LLM = "qwen2.5:7b"

os.makedirs(TRAJ_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

_modelo_emb = None
_modelo_rerank = None
_chroma_client = None
_colecao = None
_bm25 = None
_trajetorias_cache = []


# ============================================================
# CARREGAMENTO
# ============================================================

def _carregar_rag():
    global _modelo_emb, _modelo_rerank, _chroma_client, _colecao, _bm25
    if _modelo_emb is not None:
        return
    print("🧠 Carregando MiniLM + Chroma...")
    from sentence_transformers import SentenceTransformer, CrossEncoder
    _modelo_emb = SentenceTransformer("all-MiniLM-L6-v2")
    try:
        print("🎯 Carregando Reranker (Cross-Encoder)...")
        _modelo_rerank = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception as e:
        print(f"⚠️ Reranker falhou: {e}. Seguindo sem rerank.")
        _modelo_rerank = None
    import chromadb
    _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    _reindexar()


def _texto_indexavel(t):
    """Monta o texto que vai pro RAG. Prioriza descricao_rag."""
    partes = []
    if t.get("descricao_rag"):
        partes.append(t["descricao_rag"])
    if t.get("template"):
        partes.append(t["template"])
    if t.get("exemplo_original"):
        partes.append(t["exemplo_original"])
    if not partes:
        partes.append(t.get("nome", ""))
    ferrs = set(p["ferramenta"] for p in t.get("passos", []))
    if ferrs:
        partes.append("Ferramentas: " + ", ".join(sorted(ferrs)))
    return " | ".join(partes)


def _reindexar():
    global _colecao, _bm25, _trajetorias_cache
    _trajetorias_cache = []

    if os.path.exists(TRAJ_DIR):
        for arq in os.listdir(TRAJ_DIR):
            if not arq.endswith(".json"):
                continue
            try:
                d = json.load(open(os.path.join(TRAJ_DIR, arq), encoding="utf-8"))
                _trajetorias_cache.append(d)
            except Exception as e:
                print(f"⚠️ Erro lendo {arq}: {e}")

    try:
        _chroma_client.delete_collection("trajetorias")
    except:
        pass
    _colecao = _chroma_client.create_collection(
        "trajetorias",
        metadata={"hnsw:space": "cosine"}
    )

    if not _trajetorias_cache:
        _bm25 = None
        print("📚 0 trajetórias indexadas.")
        return

    textos = []
    ids = []
    for t in _trajetorias_cache:
        textos.append(_texto_indexavel(t))
        ids.append(t["nome"])

    embs = [_modelo_emb.encode(t, normalize_embeddings=True).tolist() for t in textos]
    _colecao.add(documents=textos, embeddings=embs, ids=ids)

    from rank_bm25 import BM25Okapi
    _bm25 = BM25Okapi([t.lower().split() for t in textos])
    print(f"📚 {len(_trajetorias_cache)} trajetória(s) indexada(s).")


# ============================================================
# BUSCA
# ============================================================

def _rrf(listas, k=60):
    scores = {}
    for lista in listas:
        for rank, doc in enumerate(lista, start=1):
            scores[doc] = scores.get(doc, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def _gerar_variacoes(frase):
    """Query Expansion com o 7B."""
    import ollama
    prompt = f"""Reformule a frase abaixo em 3 versões diferentes, mantendo o sentido.
Use palavras diferentes que possam aparecer em descrições de trajetórias de um agente.

Frase: "{frase}"

Responda APENAS JSON: {{"variacoes": ["v1", "v2", "v3"]}}"""
    try:
        resp = ollama.chat(model=MODEL_LLM, messages=[{"role": "user", "content": prompt}], format="json")
        d = json.loads(resp["message"]["content"])
        vars = d.get("variacoes", [])
        return [frase] + [v for v in vars if v and v != frase][:3]
    except:
        return [frase]


def _busca_hibrida(query, top_k):
    emb = _modelo_emb.encode(query, normalize_embeddings=True).tolist()
    n = min(top_k, max(1, len(_trajetorias_cache)))
    res = _colecao.query(query_embeddings=[emb], n_results=n)
    ids_vetor = res["ids"][0]

    ids_bm25 = []
    if _bm25 is not None:
        scores_bm25 = _bm25.get_scores(query.lower().split())
        todos_ids = [t["nome"] for t in _trajetorias_cache]
        ids_bm25 = [todos_ids[i] for i in np.argsort(scores_bm25)[::-1][:n]]

    return _rrf([ids_vetor, ids_bm25])


def buscar_top_rag(frase, top_k_final=3, top_k_inicial=10):
    """Retorna lista de até top_k_final trajetórias com score e similaridade."""
    _carregar_rag()
    if not _trajetorias_cache:
        return []

    variacoes = _gerar_variacoes(frase)

    scores_finais = {}
    for v in variacoes:
        ranking = _busca_hibrida(v, top_k_inicial)
        for doc_id, score in ranking:
            scores_finais[doc_id] = scores_finais.get(doc_id, 0) + score

    if not scores_finais:
        return []

    ordenado = sorted(scores_finais.items(), key=lambda x: -x[1])[:top_k_inicial]
    ids_top = [d for d, _ in ordenado]
    trajs_top = [t for t in _trajetorias_cache if t["nome"] in ids_top]

    if _modelo_rerank is not None and len(trajs_top) > 1:
        pares = [(frase, _texto_indexavel(t)) for t in trajs_top]
        try:
            scores_rerank = _modelo_rerank.predict(pares)
            pares_ordenados = sorted(zip(trajs_top, scores_rerank), key=lambda x: -x[1])
        except:
            pares_ordenados = [(t, scores_finais.get(t["nome"], 0)) for t in trajs_top]
    else:
        pares_ordenados = [(t, scores_finais.get(t["nome"], 0)) for t in trajs_top]

    frase_emb = _modelo_emb.encode(frase, normalize_embeddings=True)
    resultados = []
    for traj, score in pares_ordenados[:top_k_final]:
        t_emb = _modelo_emb.encode(_texto_indexavel(traj), normalize_embeddings=True)
        sim = float(np.dot(frase_emb, t_emb))
        resultados.append({
            "trajetoria": traj,
            "score": float(score),
            "similaridade": sim,
            "dist_cos": 1 - sim,
            "score_rrf": float(score),
        })
    return resultados


def buscar_trajetoria_rag(frase, top_k=3, threshold=0.35):
    """Compat: retorna o melhor match ou None."""
    resultados = buscar_top_rag(frase, top_k_final=top_k, top_k_inicial=top_k)
    if not resultados:
        return None
    return resultados[0]


def formatar_contexto_rag(resultados):
    """Formata top N do RAG em texto pro LLM."""
    if not resultados:
        return ""
    linhas = ["TRAJETÓRIAS RELEVANTES QUE VOCÊ JÁ SABE FAZER:"]
    for i, r in enumerate(resultados, 1):
        t = r["trajetoria"]
        desc = t.get("descricao_rag") or t.get("template") or t.get("objetivo_original", "")
        params = ", ".join(t.get("parametros", [])) or "nenhum"
        linhas.append(f"{i}. {t['nome']} (score {r['similaridade']:.2f})")
        linhas.append(f"   O que faz: {desc}")
        linhas.append(f"   Parâmetros: {params}")
        linhas.append(f"   Passos: {len(t.get('passos', []))}")
    linhas.append("")
    linhas.append("Se uma dessas serve, use modo 'usar_trajetoria' com o nome EXATO. Se não, crie nova.")
    return "\n".join(linhas)


# ============================================================
# DESCRIÇÃO RAG (texto natural pra busca)
# ============================================================

def gerar_descricao_rag(nome, template, exemplo, passos):
    """Gera descrição em texto natural usando qwen2.5:7b."""
    import ollama
    ferrs = [p["ferramenta"] for p in passos]
    prompt = f"""Descreva essa trajetória em UMA frase natural em português, com sinônimos, para outra IA achar ela fácil numa busca.

Nome: {nome}
Template: {template}
Exemplo: "{exemplo}"
Ferramentas usadas: {", ".join(ferrs)}

Exemplos BONS:
- "Abre o YouTube e pesquisa um termo, clicando no primeiro vídeo. Útil pra assistir ou achar vídeos."
- "Cria um arquivo de texto com conteúdo numa pasta padrão."

Responda APENAS JSON: {{"descricao": "sua descrição"}}"""
    try:
        resp = ollama.chat(model=MODEL_LLM, messages=[{"role": "user", "content": prompt}], format="json")
        d = json.loads(resp["message"]["content"])
        return d.get("descricao", "").strip()
    except:
        return ""


# ============================================================
# MAPA RAG
# ============================================================

def gerar_mapa_rag():
    """Gera mapa_rag.md com todas as trajetórias descritas em texto natural."""
    if _modelo_emb is None:
        _carregar_rag()
    if not _trajetorias_cache:
        _reindexar()
    if not _trajetorias_cache:
        print("📭 Nada pra gerar mapa.")
        return

    micros = sorted([t for t in _trajetorias_cache if t.get("nome", "").startswith("micro_")], key=lambda x: x["nome"])
    compostas = sorted([t for t in _trajetorias_cache if not t.get("nome", "").startswith("micro_")], key=lambda x: x["nome"])

    linhas = ["# MAPA DE TRAJETÓRIAS\n"]
    linhas.append(f"**Total:** {len(_trajetorias_cache)} trajetórias ({len(micros)} micros, {len(compostas)} compostas)\n")

    if micros:
        linhas.append("\n## 🔧 MICRO-TRAJETÓRIAS\n")
        for t in micros:
            linhas.append(_bloco_mapa(t))
    if compostas:
        linhas.append("\n## 📦 TRAJETÓRIAS COMPOSTAS\n")
        for t in compostas:
            linhas.append(_bloco_mapa(t, composta=True))

    with open(MAPA_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"🗺️ Mapa: {MAPA_FILE} ({len(_trajetorias_cache)} trajetórias)")


def _bloco_mapa(t, composta=False):
    linhas = [f"### {t['nome']}"]
    if t.get("descricao_rag"):
        linhas.append(f"- **O que faz:** {t['descricao_rag']}")
    if t.get("template"):
        linhas.append(f"- **Template:** `{t['template']}`")
    if t.get("parametros"):
        linhas.append(f"- **Parâmetros:** {', '.join(t['parametros'])}")
    if t.get("exemplo_original"):
        linhas.append(f"- **Exemplo:** \"{t['exemplo_original']}\"")
    if composta and t.get("composta_de"):
        linhas.append(f"- **Composta de:** {', '.join(t['composta_de'])}")
    ferrs = sorted(set(p["ferramenta"] for p in t.get("passos", [])))
    if ferrs:
        linhas.append(f"- **Ferramentas:** {', '.join(ferrs)}")
    linhas.append(f"- **Passos:** {len(t.get('passos', []))}")
    linhas.append("")
    return "\n".join(linhas)


# ============================================================
# CRUD
# ============================================================

def listar_trajetorias():
    if not os.path.exists(TRAJ_DIR):
        return []
    return sorted([f.replace(".json", "") for f in os.listdir(TRAJ_DIR) if f.endswith(".json")])


def ler_trajetoria(nome):
    caminho = os.path.join(TRAJ_DIR, f"{nome}.json")
    if not os.path.exists(caminho):
        return None
    try:
        return json.load(open(caminho, encoding="utf-8"))
    except:
        return None


def formatar_trajetoria(nome):
    d = ler_trajetoria(nome)
    if not d:
        return f"❌ Não achei: {nome}"
    linhas = [f"📋 {d['nome']}"]
    if d.get("descricao_rag"):
        linhas.append(f"   Descrição: {d['descricao_rag']}")
    if "template" in d:
        linhas.append(f"   Template: {d['template']}")
        linhas.append(f"   Parâmetros: {d.get('parametros', [])}")
    else:
        linhas.append(f"   Objetivo: {d.get('objetivo_original', '?')}")
    linhas.append(f"   Criada: {d.get('criado_em', '?')}")
    linhas.append(f"   Passos ({len(d['passos'])}):")
    for i, p in enumerate(d["passos"], 1):
        linhas.append(f"     {i}. {p['ferramenta']}({p['params']})")
    return "\n".join(linhas)


def remover_trajetoria(nome):
    caminho = os.path.join(TRAJ_DIR, f"{nome}.json")
    if not os.path.exists(caminho):
        return f"Não existe: {nome}"
    os.remove(caminho)
    _reindexar()
    return f"Apagada: {nome}"


def salvar_trajetoria_template(nome, template, parametros, passos, exemplo, descricao_rag=""):
    nome_limpo = "".join(c for c in nome.lower().replace(" ", "_") if c.isalnum() or c == "_")[:60]
    caminho = os.path.join(TRAJ_DIR, f"{nome_limpo}.json")
    dados = {
        "nome": nome_limpo,
        "template": template,
        "parametros": parametros,
        "exemplo_original": exemplo,
        "descricao_rag": descricao_rag,
        "criado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "passos": passos,
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    _reindexar()
    return nome_limpo


def salvar_trajetoria_legacy(nome, objetivo, passos):
    nome_limpo = "".join(c for c in nome.lower().replace(" ", "_") if c.isalnum() or c == "_")[:60]
    caminho = os.path.join(TRAJ_DIR, f"{nome_limpo}.json")
    dados = {
        "nome": nome_limpo,
        "objetivo_original": objetivo,
        "descricao_rag": "",
        "criado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "passos": [{"ferramenta": p["ferramenta"], "params": p["params"]} for p in passos],
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    _reindexar()
    return nome_limpo


# ============================================================
# TEMPLATE / PARÂMETROS
# ============================================================

def criar_template(objetivo, passos):
    import ollama
    passos_limpos = [{"ferramenta": p["ferramenta"], "params": p["params"]} for p in passos]

    prompt = f"""Transforme uma tarefa executada num TEMPLATE reutilizável.

OBJETIVO ORIGINAL: "{objetivo}"

PASSOS EXECUTADOS:
{json.dumps(passos_limpos, ensure_ascii=False, indent=2)}

Tarefa:
1. Identifique FIXO (site, botão) vs VARIÁVEL (email, senha, URL, termo digitado).
2. Nome curto (use _).
3. Template de frase com {{var}}.
4. Liste as variáveis.
5. Reescreva os passos com {{var}}.

Responda APENAS JSON:
{{
  "nome": "nome_curto",
  "template": "frase genérica com {{var}}",
  "parametros": ["var1"],
  "passos": [{{"ferramenta": "nome", "params": {{"chave": "{{var}}"}}}}]
}}

REGRAS:
- Nomes de variáveis em português sem acento: url, email, senha, texto, nome, caminho, termo.
- Não invente ferramentas."""
    try:
        resp = ollama.chat(model=MODEL_LLM, messages=[{"role": "user", "content": prompt}], format="json")
        return json.loads(resp["message"]["content"])
    except Exception as e:
        return {"erro": str(e)}


def extrair_parametros(template, parametros, frase):
    import ollama
    if not parametros:
        return {}
    prompt = f"""Template: "{template}"
Parâmetros a extrair: {parametros}

Frase do usuário: "{frase}"

Extraia os valores. Responda APENAS JSON: {{"parametro1": "valor1"}}
Se não estiver na frase, use null."""
    try:
        resp = ollama.chat(model=MODEL_LLM, messages=[{"role": "user", "content": prompt}], format="json")
        return json.loads(resp["message"]["content"])
    except:
        return {}


def aplicar_parametros(passos, params):
    def _subst(valor):
        if isinstance(valor, str):
            for k, v in params.items():
                if v is not None and v != "":
                    valor = valor.replace("{" + k + "}", str(v))
            return valor
        elif isinstance(valor, dict):
            return {k: _subst(v) for k, v in valor.items()}
        elif isinstance(valor, list):
            return [_subst(v) for v in valor]
        return valor
    return [{"ferramenta": p["ferramenta"], "params": _subst(p["params"])} for p in passos]