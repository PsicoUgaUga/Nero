import os
import json
import time
import re

CONFIG_FILE = r"C:\Nero\config.json"
PADROES_FILE = r"C:\Nero\padroes.json"
PROMPT_TREINADOR_FILE = r"C:\Nero\prompt_treinador.txt"
PEDIDO_TREINADOR_FILE = r"C:\Nero\pedido_treinador.md"
MODEL_LLM = "qwen2.5:7b"

GROQ_MODELS_FALLBACK = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]

# max_tokens padrão — reasoning model precisa de folga
MAX_TOKENS_DEFAULT = 5000

_TREINADOR_BROKEN = False


def _config():
    if os.path.exists(CONFIG_FILE):
        try:
            return json.load(open(CONFIG_FILE, encoding="utf-8"))
        except:
            return {}
    return {}


# ============================================================
# SÍNTESE FINAL
# ============================================================

def sintetizar_resposta(pergunta, dump, max_chars=4500):
    import ollama
    if not dump or not pergunta:
        return None

    dump = dump[:max_chars]
    dump_low = dump.lower()
    dica_contexto = ""
    if "youtube" in dump_low and ("inscritos" in dump_low or "visualizações" in dump_low or "se inscrever" in dump_low):
        dica_contexto = """
CONTEXTO: página de VÍDEO do YouTube.
Procure: título do vídeo, nome do canal (linha após o título com "inscritos"), descrição.
Ignore: "Pular navegação", "Fazer login", "Patrocinado", "1 de 2", "AO VIVO", "Comentários".
"""
    elif "duckduckgo" in dump_low or "[link]" in dump_low:
        dica_contexto = "CONTEXTO: resultados de busca. Liste títulos e links."

    prompt = f"""Você é um assistente que EXTRAI a resposta exata de um texto.

PERGUNTA DO USUÁRIO:
{pergunta}

{dica_contexto}

CONTEÚDO DA PÁGINA:
{dump}

REGRAS ABSOLUTAS:
1. Responda em PORTUGUÊS BRASILEIRO.
2. Seja direto. 1 a 3 frases curtas.
3. Ignore menus, banners, cookies, "patrocinado", "fazer login".
4. Se a resposta NÃO estiver clara, responda EXATAMENTE: "não encontrei no conteúdo".
5. NUNCA invente.
6. Se for VÍDEO, responda: Título + canal.
7. Se for cotação, valor + moeda.

Responda APENAS JSON: {{"resposta": "..."}}"""

    try:
        resp = ollama.chat(
            model=MODEL_LLM,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        d = json.loads(resp["message"]["content"])
        r = d.get("resposta", "").strip()
        if not r:
            return None
        for ch in r:
            if "\u4e00" <= ch <= "\u9fff":
                return None
            if "\u3040" <= ch <= "\u30ff":
                return None
        return r
    except Exception as e:
        print(f"   ⚠️ Síntese falhou: {e}")
        return None


# ============================================================
# AVALIAÇÃO DE FIT
# ============================================================

SYSTEM_AVALIADOR = """Você AVALIA se trajetórias existentes RESOLVEM EXATAMENTE
o pedido do usuário. Seja RIGOROSO.

Responda SEMPRE JSON:
{
  "fit": "sim" | "parcial" | "nenhum",
  "aprovadas": ["nome1"],
  "motivo": "explicação curta"
}

REGRAS:
- "sim" = trajetória que faz o pedido COMPLETO
- "parcial" = faz ALGO parecido mas NÃO é exato
- "nenhum" = nenhuma resolve

⚠️ NUANCES que parecem iguais mas NÃO são:
- "último vídeo" ≠ "primeiro resultado de busca"
- "lista de X" ≠ "abrir X e ler"
- "canal do YouTube" ≠ "vídeo do YouTube"
- "apagar arquivo" ≠ "criar arquivo"

🚫 OPERAÇÕES PROIBIDAS (nunca aprove):
Inscrever, curtir, comentar, compartilhar, comprar, pagar, fazer login,
baixar vídeo/áudio de YouTube (mp3, mp4)."""


def avaliar_fit(tarefa, resultados_rag):
    if not resultados_rag:
        return None

    linhas = []
    for r in resultados_rag:
        t = r["trajetoria"]
        tipo = t.get("tipo") or ("micro" if t["nome"].startswith("micro_") else "composta")
        icone = "📦" if tipo == "composta" else "🔧"
        desc = t.get("descricao_rag") or t.get("template", "")
        linhas.append(f"- {icone} {t['nome']} (sim {r['similaridade']:.2f}) [{tipo}]: {desc}")

    candidatas = "\n".join(linhas)

    prompt = f"""PEDIDO DO USUÁRIO:
{tarefa}

TRAJETÓRIAS CANDIDATAS:
{candidatas}

Avalie rigorosamente. Responda APENAS JSON."""

    return _chamar_groq(SYSTEM_AVALIADOR, prompt, max_tokens=2500)


# ============================================================
# PADRÕES
# ============================================================

def carregar_padroes():
    if os.path.exists(PADROES_FILE):
        try:
            return json.load(open(PADROES_FILE, encoding="utf-8"))
        except:
            return {}
    return {}


def salvar_padroes(p):
    json.dump(p, open(PADROES_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def salvar_padrao(chave, etapas):
    if not etapas:
        return 0
    if len(etapas) == 1 and etapas[0].get("acao") == "usar_trajetoria":
        return 0
    p = carregar_padroes()
    p[chave.lower()] = etapas
    salvar_padroes(p)
    return len(p)


def listar_padroes():
    p = carregar_padroes()
    if not p:
        return "Nenhum padrão salvo."
    return "\n".join(f"- '{k}' → {len(v)} etapas" for k, v in p.items())


def limpar_padroes():
    if os.path.exists(PADROES_FILE):
        os.remove(PADROES_FILE)
    return "Padrões apagados."


def decompor_por_padrao(frase):
    p = carregar_padroes()
    fl = frase.lower()
    melhor = None
    melhor_score = 0
    for chave, etapas in p.items():
        if chave in fl:
            score = len(chave) / max(len(fl), 1)
            if score > melhor_score:
                melhor_score = score
                melhor = etapas
    return melhor


# ============================================================
# GROQ
# ============================================================

def _extrair_json_de_texto(texto):
    """Extrai o primeiro {...} balanceado do texto. Útil pra reasoning models."""
    if not texto:
        return None
    texto = texto.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(texto)
    except:
        pass
    ini = texto.find("{")
    if ini == -1:
        return None
    nivel = 0
    dentro_string = False
    escape = False
    for i in range(ini, len(texto)):
        ch = texto[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            dentro_string = not dentro_string
            continue
        if dentro_string:
            continue
        if ch == "{":
            nivel += 1
        elif ch == "}":
            nivel -= 1
            if nivel == 0:
                try:
                    return json.loads(texto[ini:i+1])
                except Exception as e:
                    print(f"   ⚠️ JSON extraído não parseia: {e}")
                    return None
    return None


def _chamar_groq(system, user, max_tokens=MAX_TOKENS_DEFAULT):
    cfg = _config()
    api_key = cfg.get("groq_api_key", "").strip()
    if not api_key or api_key == "COLE_SUA_CHAVE_AQUI":
        print("   ⚠️ Groq sem chave configurada.")
        return None

    modelo_cfg = cfg.get("groq_model", "").strip()
    modelos = []
    if modelo_cfg:
        modelos.append(modelo_cfg)
    for m in GROQ_MODELS_FALLBACK:
        if m not in modelos:
            modelos.append(m)

    from groq import Groq
    client = Groq(api_key=api_key)

    for modelo in modelos:
        conteudo = ""
        try:
            kwargs = {
                "model": modelo,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
            try:
                chat = client.chat.completions.create(reasoning_effort="low", **kwargs)
            except TypeError:
                chat = client.chat.completions.create(**kwargs)

            conteudo = chat.choices[0].message.content or ""
            finish = chat.choices[0].finish_reason

            if not conteudo.strip():
                print(f"   ⚠️ Groq '{modelo}' devolveu VAZIO (finish={finish}, max_tokens={max_tokens}).")
                continue

            dados = _extrair_json_de_texto(conteudo)
            if dados is None:
                print(f"   ⚠️ Groq '{modelo}' devolveu texto sem JSON válido.")
                print(f"      Cru: {conteudo[:300]}")
                continue
            return dados

        except json.JSONDecodeError as e:
            print(f"   ⚠️ Groq '{modelo}' JSON inválido: {str(e)[:120]}")
            print(f"      Cru: {conteudo[:300]}")
            continue
        except Exception as e:
            msg = str(e)[:200]
            print(f"   ⚠️ Groq '{modelo}' falhou: {type(e).__name__}: {msg}")
            continue
    return None


# ============================================================
# TREINADOR
# ============================================================

SYSTEM_TREINADOR = """Você é o TREINADOR. Responda SEMPRE JSON.

SCHEMA:
{"plano": [{"acao": "usar_trajetoria", "nome": "...", "params": {...}},
           {"acao": "executar_ferramenta", "ferramenta": "...", "parametros": {...}},
           {"acao": "aprender_nova", "descricao": "..."}]}

REGRAS:
1. usar_trajetoria só aceita nomes de trajetórias existentes.
2. Ferramentas vão em executar_ferramenta.
3. NUNCA invente caminhos nem URLs.
4. Use EXATAMENTE os nomes dos parâmetros.

🚫 PROIBIDO: inscrever, curtir, comentar, comprar, login, baixar do YouTube."""


def _montar_dossie(solicitacao, ferramentas_disponiveis, trajetorias_disponiveis, passos_tentados, motivo):
    if os.path.exists(PROMPT_TREINADOR_FILE):
        template = open(PROMPT_TREINADOR_FILE, encoding="utf-8").read()
    else:
        template = "SOLICITAÇÃO: {solicitacao}\n\nTENTATIVAS: {passos_tentados}\n\nMOTIVO: {motivo}"

    lista_ferr = "\n".join(
        f"- {n}({', '.join(info['parametros'].keys()) or 'sem params'}): {info['descricao']}"
        for n, info in ferramentas_disponiveis.items()
    )
    lista_traj = "\n".join(f"- {t}" for t in trajetorias_disponiveis) or "(nenhuma)"
    passos_str = json.dumps(passos_tentados, ensure_ascii=False, indent=2)

    prompt = template
    prompt = prompt.replace("{ferramentas}", lista_ferr)
    prompt = prompt.replace("{trajetorias}", lista_traj)
    prompt = prompt.replace("{solicitacao}", solicitacao)
    prompt = prompt.replace("{passos_tentados}", passos_str)
    prompt = prompt.replace("{motivo}", motivo)
    return prompt


def consultar_treinador(solicitacao, ferramentas_disponiveis, trajetorias_disponiveis, passos_tentados, motivo):
    global _TREINADOR_BROKEN
    if _TREINADOR_BROKEN:
        print("⚠️ Treinador quebrado. Pulando.")
        return None

    prompt = _montar_dossie(solicitacao, ferramentas_disponiveis, trajetorias_disponiveis, passos_tentados, motivo)

    try:
        with open(PEDIDO_TREINADOR_FILE, "w", encoding="utf-8") as f:
            f.write(prompt)
    except:
        pass

    print(f"🧠 Consultando treinador...")
    resultado = _chamar_groq(SYSTEM_TREINADOR, prompt, max_tokens=5000)
    if resultado:
        print(f"✅ Treinador respondeu.")
        return resultado
    print("❌ Treinador falhou.")
    _TREINADOR_BROKEN = True
    return None


# ============================================================
# DECOMPOSITOR
# ============================================================

SYSTEM_DECOMPOSITOR = """Responda SEMPRE JSON: {"micros": [{"nome": "...", "template": "...", "parametros": [...], "passos": [...]}]}
- Cada micro faz UMA coisa clara. Máx 3 passos."""


def decompor_trajetoria(traj, micros_existentes):
    lista_existentes = "\n".join(f"- {m}" for m in micros_existentes) or "(nenhuma)"
    prompt = f"""Decomponha:
OBJETIVO: {traj.get('exemplo_original', '?')}
PASSOS: {json.dumps(traj.get('passos', []), ensure_ascii=False, indent=2)}
MICROS EXISTENTES: {lista_existentes}
Responda JSON com "micros": [...]"""
    return _chamar_groq(SYSTEM_DECOMPOSITOR, prompt, max_tokens=5000)


# ============================================================
# COMPOSITOR
# ============================================================

SYSTEM_COMPOSITOR = """Você é o COMPOSITOR.
Recebe TAREFA + CATÁLOGO de trajetórias + LISTA de ferramentas.
Monte um PLANO.

Responda SEMPRE JSON:
{
  "plano": [
    {"acao": "usar_trajetoria", "nome": "micro_xxx", "params": {...}},
    {"acao": "executar_ferramenta", "ferramenta": "nome_ferramenta", "parametros": {...}},
    {"acao": "aprender_nova", "descricao": "..."}
  ]
}

═══════════════════════════════════════════════════════════════
🚨 REGRA CRÍTICA: TIPOS DIFERENTES DE COISA
═══════════════════════════════════════════════════════════════
- "usar_trajetoria" só aceita NOMES DO CATÁLOGO (ex: micro_abrir_youtube)
- Ferramentas (navegar, ler_texto_pagina, preencher_campo, clicar_selector,
  pressionar, esperar, abrir_programa, criar_arquivo, etc) SEMPRE vão em
  "executar_ferramenta" — NUNCA em usar_trajetoria.

Se você quer usar ler_texto_pagina, é:
  {"acao": "executar_ferramenta", "ferramenta": "ler_texto_pagina", "parametros": {}}

NUNCA: {"acao": "usar_trajetoria", "nome": "ler_texto_pagina"} ← ERRADO

═══════════════════════════════════════════════════════════════
📋 OUTRAS REGRAS
═══════════════════════════════════════════════════════════════
1. Se uma COMPOSTA 📦 faz EXATAMENTE o pedido, use ela DIRETO (1 etapa).
2. Senão, monte com MICROS 🔧 + ferramentas.
3. O ÚLTIMO passo DEVE ser uma LEITURA:
   - ler_texto_pagina (conteúdo real do site/vídeo)
   - ou ler_pagina_estruturada (resultados/listas)
4. NUNCA invente trajetórias nem URLs nem caminhos.
5. Use EXATAMENTE os nomes dos parâmetros das ferramentas.

🚫 NUNCA monte plano que inscreva, curta, comente, compre, faça login
ou baixe vídeo do YouTube. Se pedido for isso, retorne:
{"plano": [{"acao": "aprender_nova", "descricao": "recusar_educadamente"}]}"""


def planejar_composicao(tarefa, trajs_info, ferramentas_info, max_trajs=8):
    if not trajs_info and not ferramentas_info:
        return None

    trajs_info = trajs_info[:max_trajs]

    linhas_trajs = []
    for t in trajs_info:
        tipo = t.get("tipo", "micro")
        icone = "📦" if tipo == "composta" else "🔧"
        params = ", ".join(t.get("parametros", [])) or "sem params"
        template = t.get("template", "")
        desc = t.get("descricao_rag", "")
        linhas_trajs.append(f"{icone} {t['nome']}({params}) [{tipo}]: {template} | {desc}")
    catalogo_trajs = "\n".join(linhas_trajs) or "(nenhuma)"

    catalogo_ferr = "\n".join(
        f"- {n}({', '.join(info['parametros'].keys()) or 'sem params'}): {info['descricao']}"
        for n, info in ferramentas_info.items()
    )

    prompt = f"""TAREFA: {tarefa}

TRAJETÓRIAS DISPONÍVEIS (usar_trajetoria):
{catalogo_trajs}

FERRAMENTAS DISPONÍVEIS (executar_ferramenta):
{catalogo_ferr}

Monte o plano. Responda APENAS JSON."""

    return _chamar_groq(SYSTEM_COMPOSITOR, prompt, max_tokens=5000)


# ============================================================
# AUDITOR
# ============================================================

SYSTEM_AUDITOR = """Responda SEMPRE JSON:
{"acao": "manter" | "remover" | "corrigir", "motivo": "...", "passos_corrigidos": [...]}"""


def auditar_trajetoria(traj):
    prompt = f"""Audite:
OBJETIVO: {traj.get('exemplo_original', '?')}
NOME: {traj.get('nome', '?')}
PASSOS: {json.dumps(traj.get('passos', []), ensure_ascii=False, indent=2)}
Responda APENAS JSON."""
    return _chamar_groq(SYSTEM_AUDITOR, prompt, max_tokens=3000)


# ============================================================
# TEMPLATE GENÉRICO
# ============================================================

def criar_template_generico(objetivo, passos):
    import ollama
    passos_limpos = [{"ferramenta": p["ferramenta"], "params": p["params"]} for p in passos]
    prompt = f"""Gere TEMPLATE GENÉRICO.
OBJETIVO: "{objetivo}"
PASSOS: {json.dumps(passos_limpos, ensure_ascii=False)}
Responda APENAS JSON:
{{"nome": "verbo_objeto", "template": "frase REAL com {{var}}", "parametros": ["var1"], "passos": [...]}}"""
    try:
        resp = ollama.chat(model=MODEL_LLM, messages=[{"role": "user", "content": prompt}], format="json")
        return json.loads(resp["message"]["content"])
    except Exception as e:
        return {"erro": str(e)}


# ============================================================
# EXECUTAR PLANO
# ============================================================

def _eh_ferramenta_valida(nome, executar_ferramenta):
    try:
        res = executar_ferramenta(nome, {})
        if res.startswith("Ferramenta desconhecida"):
            return False, None
        return True, res
    except:
        return False, None


def _executar_etapa(etapa, executar_ferramenta, processar_nova, extrair_params, aplicar_params, objetivo_original, passos_ok):
    if not isinstance(etapa, dict):
        return

    acao = etapa.get("acao", "")

    if acao == "usar_trajetoria":
        nome = etapa.get("nome", "")
        if not nome:
            print(f"   ⚠️ usar_trajetoria sem nome.")
            return

        traj_caminho = os.path.join(r"C:\Nero\trajetorias", f"{nome}.json")
        alt = os.path.join(r"C:\Nero\trajetorias", f"micro_{nome}.json")

        if not os.path.exists(traj_caminho) and not os.path.exists(alt):
            print(f"   ⚠️ '{nome}' não é trajetória. Verificando se é ferramenta...")
            params_etapa = etapa.get("params", {})
            res = executar_ferramenta(nome, params_etapa)
            if not res.startswith("Ferramenta desconhecida"):
                print(f"   🔧 {nome}({params_etapa}) [redirecionado pra ferramenta]")
                tem_erro = "Erro" in res or "não existe" in res.lower() or "não achei" in res.lower()
                passo_info = {"ferramenta": nome, "params": params_etapa, "erro": tem_erro}
                if nome.startswith("ler_") and not tem_erro:
                    passo_info["resultado"] = res
                    print(f"   📤 {res[:600]}")
                elif tem_erro:
                    print(f"   ⚠️ {res[:200]}")
                else:
                    print(f"   📤 {res[:300]}")
                passos_ok.append(passo_info)
                return
            print(f"   ⚠️ Trajetória '{nome}' não existe. Aprendendo do zero.")
            if processar_nova:
                processar_nova(nome)
            return

        if not os.path.exists(traj_caminho):
            traj_caminho = alt
            nome = f"micro_{nome}"

        params = etapa.get("params", {})
        traj = json.load(open(traj_caminho, encoding="utf-8"))
        passos = traj["passos"]
        if traj.get("parametros") and not params:
            params = extrair_params(traj.get("template", ""), traj["parametros"], objetivo_original)
        passos = aplicar_params(passos, params)
        print(f"   📦 {nome} ({len(passos)} passos)")
        for j, p in enumerate(passos, 1):
            print(f"      [{j}/{len(passos)}] {p['ferramenta']}({p['params']})")
            res = executar_ferramenta(p["ferramenta"], p["params"])
            tem_erro = "Erro" in res or "não existe" in res.lower() or "não achei" in res.lower()
            passo_info = {"ferramenta": p["ferramenta"], "params": p["params"], "erro": tem_erro}
            if p["ferramenta"].startswith("ler_") and not tem_erro:
                passo_info["resultado"] = res
                print(f"      📤 {res[:600]}")
                if len(res) > 600:
                    print(f"      ... (+{len(res)-600} chars)")
            elif tem_erro:
                print(f"      ⚠️ {res[:200]}")
            elif p["ferramenta"] in ("preencher_campo", "clicar_selector", "clicar_no_elemento", "pressionar", "navegar", "pressionar_tecla", "digitar_teclado"):
                print(f"      ✓ {res[:150]}")
            passos_ok.append(passo_info)
        return

    if acao == "executar_ferramenta":
        ferr = etapa.get("ferramenta", "")
        par = etapa.get("parametros", {})
        if not ferr:
            print(f"   ⚠️ executar_ferramenta sem ferramenta.")
            return
        print(f"   🔧 {ferr}({par})")
        res = executar_ferramenta(ferr, par)
        tem_erro = "Erro" in res or "não existe" in res.lower() or "não achei" in res.lower()
        passo_info = {"ferramenta": ferr, "params": par, "erro": tem_erro}
        if ferr.startswith("ler_") and not tem_erro:
            passo_info["resultado"] = res
            print(f"   📤 {res[:800]}")
            if len(res) > 800:
                print(f"   ... (+{len(res)-800} chars)")
        else:
            print(f"   📤 {res[:300]}")
        passos_ok.append(passo_info)
        return

    if acao == "aprender_nova":
        descricao = etapa.get("descricao", "")
        if not descricao:
            return
        print(f"   🧠 Aprender: {descricao}")
        if processar_nova:
            try:
                processar_nova(descricao)
                passos_ok.append({"ferramenta": "aprender_nova", "params": {"descricao": descricao}, "erro": False})
            except Exception as e:
                print(f"   ❌ {e}")
                passos_ok.append({"ferramenta": "aprender_nova", "params": {"descricao": descricao}, "erro": True})
        return

    FERRAMENTAS_CONHECIDAS = {
        "navegar", "ler_pagina_estruturada", "preencher_campo", "clicar_no_elemento",
        "clicar_selector", "pressionar", "digitar", "url_atual", "recarregar", "voltar",
        "fechar_browser", "esperar", "tirar_print", "ler_tela", "ler_tela_estruturada",
        "clicar_em_texto", "ler_clipboard", "escrever_clipboard", "limpar_clipboard",
        "abrir_programa", "executar_cmd", "bloquear_pc", "copiar", "colar", "salvar",
        "criar_pasta", "criar_arquivo", "escrever_arquivo", "anexar_arquivo",
        "ler_arquivo", "apagar_caminho", "mover", "renomear", "salvar_como",
        "listar_pasta", "procurar_pasta", "lembrar", "esquecer_fato", "listar_contexto",
        "ler_uia", "clicar_controle", "ler_texto_pagina",
        "pressionar_tecla", "digitar_teclado",
    }
    if acao in FERRAMENTAS_CONHECIDAS:
        params = {k: v for k, v in etapa.items() if k != "acao"}
        print(f"   🔧 {acao}({params})")
        res = executar_ferramenta(acao, params)
        tem_erro = "Erro" in res or "não existe" in res.lower() or "não achei" in res.lower()
        passo_info = {"ferramenta": acao, "params": params, "erro": tem_erro}
        if acao.startswith("ler_") and not tem_erro:
            passo_info["resultado"] = res
            print(f"   📤 {res[:800]}")
        else:
            print(f"   📤 {res[:300]}")
        passos_ok.append(passo_info)
        return

    if etapa.get("ferramenta"):
        ferr = etapa["ferramenta"]
        par = etapa.get("parametros", {})
        print(f"   🔧 {ferr}({par})")
        res = executar_ferramenta(ferr, par)
        tem_erro = "Erro" in res or "não existe" in res.lower() or "não achei" in res.lower()
        passo_info = {"ferramenta": ferr, "params": par, "erro": tem_erro}
        if ferr.startswith("ler_") and not tem_erro:
            passo_info["resultado"] = res
        passos_ok.append(passo_info)
        print(f"   📤 {res[:300]}")
        return

    print(f"   ⚠️ Etapa desconhecida: {etapa}")


def _extrair_ultimo_dump(passos_ok):
    for p in reversed(passos_ok):
        if p.get("resultado") and p["ferramenta"].startswith("ler_"):
            return p["resultado"]
    return None


def _houve_navegacao(passos_ok):
    ferrs_nav = ("navegar", "clicar_selector", "clicar_no_elemento")
    return any(p.get("ferramenta") in ferrs_nav and not p.get("erro") for p in passos_ok)


def executar_plano(plano, ferramentas, executar_ferramenta, processar_nova, salvar_traj_template, criar_template, extrair_params, aplicar_params, objetivo_original):
    if not plano:
        print("⚠️ Plano vazio.")
        return False

    if "final" in plano:
        print(f"\n✅ Treinador: {plano['final']}")
        return True

    if "plano" not in plano:
        print(f"⚠️ Plano sem 'plano': {plano}")
        return False

    etapas = plano["plano"]
    print(f"\n📋 Plano com {len(etapas)} etapa(s):")

    passos_ok = []
    for i, etapa in enumerate(etapas, 1):
        acao_label = etapa.get("acao") or etapa.get("ferramenta") or "?"
        print(f"\n▶️ [{i}/{len(etapas)}] {acao_label}")
        _executar_etapa(etapa, executar_ferramenta, processar_nova, extrair_params, aplicar_params, objetivo_original, passos_ok)

    tem_erro_total = any(p.get("erro") for p in passos_ok)

    if passos_ok and not tem_erro_total:
        chave = " ".join(objetivo_original.lower().split()[:5])
        salvo = salvar_padrao(chave, [
            {"acao": e.get("acao"), "nome": e.get("nome") or e.get("descricao") or e.get("ferramenta")}
            for e in etapas
        ])
        if salvo:
            print(f"\n💾 Padrão salvo: '{chave}'")

    if passos_ok and not tem_erro_total:
        dump = _extrair_ultimo_dump(passos_ok)

        url_final = None
        if _houve_navegacao(passos_ok):
            try:
                url_final = executar_ferramenta("url_atual", {})
                if url_final and not url_final.startswith("Erro"):
                    print(f"\n🔗 URL final: {url_final}")
            except:
                pass

        if dump:
            print(f"\n{'='*55}")
            print("🧠 Sintetizando resposta...")
            print(f"{'='*55}")
            resposta = sintetizar_resposta(objetivo_original, dump)
            if resposta:
                print(f"\n💬 RESPOSTA: {resposta}")
            else:
                print(f"\n💬 (não consegui sintetizar)")
            if url_final and not url_final.startswith("Erro"):
                print(f"🔗 Link: {url_final}")
            print("")

    return not tem_erro_total