import json
import os
import re
import threading
import queue
import time
from collections import Counter
import ollama
import keyboard

from ferramentas import FERRAMENTAS as FERRAMENTAS_BASE, carregar_contexto
from rag import (
    buscar_trajetoria_rag,
    buscar_top_rag,
    formatar_contexto_rag,
    gerar_descricao_rag,
    gerar_mapa_rag,
    salvar_trajetoria_template,
    salvar_trajetoria_legacy,
    listar_trajetorias,
    ler_trajetoria,
    formatar_trajetoria,
    remover_trajetoria,
    criar_template,
    extrair_parametros,
    aplicar_parametros,
    TRAJ_DIR,
    _carregar_rag,
    _reindexar,
)
from planner import (
    decompor_por_padrao,
    consultar_treinador,
    executar_plano,
    listar_padroes,
    limpar_padroes,
    criar_template_generico,
    auditar_trajetoria,
    decompor_trajetoria,
    planejar_composicao,
    sintetizar_resposta,
    avaliar_fit,
)

MODEL = "qwen2.5:7b"
ENSINAMENTOS_FILE = r"C:\Nero\ensinamentos.json"
CONFIG_FILE = r"C:\Nero\config.json"

MAX_HISTORICO = 6
MAX_ERROS_ANTES_TREINADOR = 2
MIN_PASSOS_PARA_SALVAR = 2
MIN_FERRAMENTAS_UNICAS = 1
MAX_REPETICAO_FERRAMENTA = 4
MAX_PROPORCAO_LEITURAS = 0.6

THRESHOLD_REPLAY_DIRETO = 0.85
THRESHOLD_AVALIACAO = 0.50

AUDITORIA_ATIVA = True
AUDITORIA_FAIL_CLOSED = True
AUDITAR_MANUAIS = False
COMPOSICAO_ATIVA = True
AUTO_COMPILAR = True
BOOT_AUTOMATICO = True

CANCELAR = False

COMANDOS_CLI = {
    "ajuda", "help", "sair", "exit", "quit", "limpar", "limpar_ruins",
    "auditar", "auditar_forcar", "reindexar", "contexto", "padroes", "ensinamentos",
    "trajetorias", "compilar", "limpar_padroes", "mapa",
}


# ============================================================
# PSEUDO-FERRAMENTA: usar_trajetoria (pra ReAct)
# ============================================================

def _usar_trajetoria_react(nome: str = None, params: dict = None, **kwargs):
    """Executa uma trajetória salva de dentro do ReAct."""
    if not nome:
        return "Erro: nome da trajetória não informado"
    params = params or {}

    traj = ler_trajetoria(nome)
    if not traj:
        alt = f"micro_{nome}"
        traj = ler_trajetoria(alt)
        if traj:
            nome = alt
        else:
            return f"Trajetória '{nome}' não existe"

    passos = traj.get("passos", [])
    if not passos:
        return f"Trajetória '{nome}' não tem passos"

    if params and traj.get("parametros"):
        passos = aplicar_parametros(passos, params)

    resultados = []
    for i, p in enumerate(passos, 1):
        ferr = p["ferramenta"]
        par = p["params"]
        if ferr not in FERRAMENTAS_BASE:
            resultados.append(f"[{i}] {ferr}: ferramenta desconhecida")
            continue
        try:
            res = FERRAMENTAS_BASE[ferr]["funcao"](**par)
            res_str = str(res)
            if ferr.startswith("ler_") or ferr == "url_atual":
                resultados.append(f"[{i}] {ferr} →\n{res_str[:1500]}")
            else:
                resultados.append(f"[{i}] {ferr} → {res_str[:300]}")
        except Exception as e:
            resultados.append(f"[{i}] {ferr} Erro: {e}")

    return "\n".join(resultados)


FERRAMENTAS = dict(FERRAMENTAS_BASE)
FERRAMENTAS["usar_trajetoria"] = {
    "funcao": _usar_trajetoria_react,
    "descricao": "Executa uma trajetória JÁ SALVA (micro ou composta) de uma vez. "
                 "Use quando uma trajetória conhecida resolver o pedido sem precisar re-montar. "
                 "Parâmetro 'nome' = nome EXATO da trajetória. 'params' = dict opcional.",
    "parametros": {"nome": "nome da trajetória", "params": "dict opcional"},
}


def _panico():
    global CANCELAR
    while True:
        keyboard.wait("esc")
        CANCELAR = True
        print("\n\n⚠️ ESC! Cancelando...")


threading.Thread(target=_panico, daemon=True).start()


def carregar_ensinamentos():
    if os.path.exists(ENSINAMENTOS_FILE):
        try:
            return json.load(open(ENSINAMENTOS_FILE, encoding="utf-8"))
        except:
            return []
    return []


def salvar_ensinamentos(lista):
    json.dump(lista, open(ENSINAMENTOS_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def adicionar_ensinamento(texto):
    lista = carregar_ensinamentos()
    lista.append(texto)
    salvar_ensinamentos(lista)
    return len(lista)


def listar_ensinamentos():
    return carregar_ensinamentos()


HISTORICO_CHAT = []


def limpar_historico():
    global HISTORICO_CHAT
    HISTORICO_CHAT = []


def _deduplicar_passos(passos):
    if not passos:
        return []
    resultado = [passos[0]]
    for p in passos[1:]:
        ant = resultado[-1]
        if p["ferramenta"] == ant["ferramenta"] and p["params"] == ant["params"]:
            continue
        resultado.append(p)
    return resultado


def _avaliar_qualidade(passos, objetivo, eh_template=False):
    if not passos:
        return False, "sem passos"
    passos_dedup = _deduplicar_passos(passos)
    ferramentas_unicas = set(p["ferramenta"] for p in passos_dedup)
    if len(ferramentas_unicas) < MIN_FERRAMENTAS_UNICAS:
        return False, f"só {len(ferramentas_unicas)} ferramenta(s)"
    leituras = sum(1 for p in passos_dedup if p["ferramenta"].startswith("ler_"))
    if leituras / len(passos_dedup) > MAX_PROPORCAO_LEITURAS:
        return False, f"{leituras}/{len(passos_dedup)} passos são leituras"
    contagem = Counter(p["ferramenta"] for p in passos_dedup)
    mais_repetida, qtd = contagem.most_common(1)[0]
    if qtd > MAX_REPETICAO_FERRAMENTA:
        return False, f"'{mais_repetida}' apareceu {qtd}x"
    for p in passos_dedup:
        if p["ferramenta"] in ("preencher_campo", "digitar"):
            v = str(p["params"].get("valor") or p["params"].get("texto") or "").strip()
            if v == "":
                return False, f"{p['ferramenta']} com valor vazio"
            if not eh_template and v in ("{termo}", "{valor}", "{comando}", "{}", "{var}"):
                return False, f"{p['ferramenta']} com placeholder não substituído"
    return True, "ok"


def _template_eh_lixo(template_str):
    if not template_str:
        return True
    t = template_str.lower().strip()
    lixos = {
        "frase com {var}", "frase com {var1}", "frase com {var2}",
        "template com {var}", "template generico", "template genérico",
        "exemplo", "nome_curto", "nome curto", "", "frase generica", "frase genérica",
        "{var}", "{{var}}",
    }
    if t in lixos:
        return True
    if t.startswith("frase com {") and t.endswith("}"):
        return True
    if t.startswith("template com {") and t.endswith("}"):
        return True
    return False


def _eh_manual(traj):
    return str(traj.get("criado_por", "")).lower() == "manual"


def _salvar_com_qualidade(entrada, passos_ok, auditar=True):
    passos_limpos = _deduplicar_passos(passos_ok)
    ok_qual, motivo = _avaliar_qualidade(passos_limpos, entrada, eh_template=False)
    if not ok_qual:
        print(f"🚫 Não salvei (heurística): {motivo}")
        return None

    if auditar and AUDITORIA_ATIVA:
        print(f"\n{'='*50}")
        print(f"🔍 AUDITORIA (Groq)")
        print(f"{'='*50}")
        traj_temp = {"nome": "temp", "exemplo_original": entrada, "template": "", "parametros": [], "passos": passos_limpos}
        resultado = auditar_trajetoria(traj_temp)
        if resultado:
            acao = resultado.get("acao", "manter")
            motivo_a = resultado.get("motivo", "?")
            if acao == "remover":
                print(f"🚫 REJEITADA: {motivo_a}")
                return None
            elif acao == "corrigir":
                passos_novos = resultado.get("passos_corrigidos", [])
                if passos_novos:
                    print(f"✏️ CORRIGIDA: {motivo_a}")
                    passos_limpos = passos_novos
            else:
                print(f"✅ APROVADA: {motivo_a}")
        else:
            if AUDITORIA_FAIL_CLOSED:
                print(f"🚫 Auditoria falhou. Não salvo (fail-closed).")
                return None

    print(f"💡 Salvando trajetória ({len(passos_limpos)} passos)...")
    tmpl_gen = criar_template_generico(entrada, passos_limpos)
    template_str = (tmpl_gen or {}).get("template", "")
    if _template_eh_lixo(template_str):
        tmpl_gen = {"erro": "template lixo"}

    if "erro" not in tmpl_gen and "nome" in tmpl_gen:
        nome = tmpl_gen["nome"]
        template_final = tmpl_gen.get("template", entrada)
        descricao = gerar_descricao_rag(nome, template_final, entrada, passos_limpos)
        nome_final = salvar_trajetoria_template(
            nome, template_final,
            tmpl_gen.get("parametros", []),
            tmpl_gen["passos"], entrada,
            descricao_rag=descricao,
        )
        print(f"💾 Salva (GENÉRICA): {nome_final}")
        nome = nome_final
    else:
        nome = salvar_trajetoria_legacy(entrada[:40], entrada, passos_limpos)
        print(f"💾 Salva (simples): {nome}")

    if AUTO_COMPILAR and nome:
        _auto_decompor(nome)

    return nome


def _auto_decompor(nome_traj):
    traj = ler_trajetoria(nome_traj)
    if not traj:
        return
    passos = traj.get("passos", [])
    if len(passos) < 3 or traj.get("tipo") == "composta" or nome_traj.startswith("micro_"):
        return

    micros_existentes = _listar_micros()
    print(f"\n🔧 Auto-decompondo '{nome_traj}' em micros...")
    resultado = decompor_trajetoria(traj, micros_existentes)
    if not resultado or "micros" not in resultado:
        return

    nomes_micros = []
    for m in resultado.get("micros", []):
        nome_m = m.get("nome", "").strip()
        if not nome_m:
            continue
        if not nome_m.startswith("micro_"):
            nome_m = f"micro_{nome_m}"
        if nome_m in micros_existentes:
            nomes_micros.append(nome_m)
            continue
        passos_m = m.get("passos", [])
        template_m = m.get("template", "")
        if not passos_m or _template_eh_lixo(template_m):
            continue
        descricao_m = gerar_descricao_rag(nome_m, template_m, traj.get("exemplo_original", ""), passos_m)
        salvar_trajetoria_template(nome_m, template_m, m.get("parametros", []), passos_m, traj.get("exemplo_original", ""), descricao_rag=descricao_m)
        caminho_m = os.path.join(TRAJ_DIR, f"{nome_m}.json")
        if os.path.exists(caminho_m):
            dados_m = json.load(open(caminho_m, encoding="utf-8"))
            dados_m["tipo"] = "micro"
            dados_m["origem"] = nome_traj
            json.dump(dados_m, open(caminho_m, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"   ✅ {nome_m}")
        micros_existentes.append(nome_m)
        nomes_micros.append(nome_m)

    if nomes_micros:
        traj["tipo"] = "composta"
        traj["composta_de"] = nomes_micros
        json.dump(traj, open(os.path.join(TRAJ_DIR, f"{nome_traj}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _listar_micros():
    return [t for t in listar_trajetorias() if t.startswith("micro_")]


def _listar_compostas():
    return [t for t in listar_trajetorias() if not t.startswith("micro_")]


def compilar_trajetorias():
    compostas = _listar_compostas()
    if not compostas:
        print("📚 Nada pra compilar.")
        return
    print(f"🔧 Compilando {len(compostas)} trajetória(s)...\n")
    micros_existentes = _listar_micros()
    micros_criadas = 0
    trajs_decompostas = 0
    for nome in compostas:
        traj = ler_trajetoria(nome)
        if not traj or traj.get("tipo") == "composta" or _eh_manual(traj):
            continue
        passos = traj.get("passos", [])
        if len(passos) < 3:
            continue
        print(f"📋 {nome} ({len(passos)} passos)")
        resultado = decompor_trajetoria(traj, micros_existentes)
        if not resultado or "micros" not in resultado:
            continue
        nomes_micros = []
        for m in resultado.get("micros", []):
            nome_m = m.get("nome", "").strip()
            if not nome_m:
                continue
            if not nome_m.startswith("micro_"):
                nome_m = f"micro_{nome_m}"
            if nome_m in micros_existentes:
                nomes_micros.append(nome_m)
                continue
            passos_m = m.get("passos", [])
            template_m = m.get("template", "")
            if not passos_m or _template_eh_lixo(template_m):
                continue
            descricao_m = gerar_descricao_rag(nome_m, template_m, traj.get("exemplo_original", ""), passos_m)
            salvar_trajetoria_template(nome_m, template_m, m.get("parametros", []), passos_m, traj.get("exemplo_original", ""), descricao_rag=descricao_m)
            caminho_m = os.path.join(TRAJ_DIR, f"{nome_m}.json")
            if os.path.exists(caminho_m):
                dados_m = json.load(open(caminho_m, encoding="utf-8"))
                dados_m["tipo"] = "micro"
                dados_m["origem"] = nome
                json.dump(dados_m, open(caminho_m, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            micros_existentes.append(nome_m)
            nomes_micros.append(nome_m)
            micros_criadas += 1
        traj["tipo"] = "composta"
        traj["composta_de"] = nomes_micros
        json.dump(traj, open(os.path.join(TRAJ_DIR, f"{nome}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        trajs_decompostas += 1
    _reindexar()
    print(f"📊 {trajs_decompostas} decomposta(s), {micros_criadas} micro(s).\n")


def auditar_todas(forcar=False):
    trajs = listar_trajetorias()
    if not trajs:
        print("📚 Nada pra auditar.")
        return
    print(f"🔍 Auditando {len(trajs)} trajetória(s)...\n")
    m = c = r = p = 0
    for nome in trajs:
        traj = ler_trajetoria(nome)
        if not traj:
            continue
        if _eh_manual(traj) and not forcar:
            print(f"⏭️ {nome} (manual — pulando auditoria)")
            p += 1
            continue
        print(f"📋 {nome} ({len(traj.get('passos', []))} passos)")
        res = auditar_trajetoria(traj)
        if not res:
            m += 1
            continue
        acao = res.get("acao", "manter")
        motivo = res.get("motivo", "?")
        if acao == "remover":
            print(f"   🗑️ REMOVER: {motivo}")
            remover_trajetoria(nome)
            r += 1
        elif acao == "corrigir":
            pn = res.get("passos_corrigidos", [])
            if pn:
                print(f"   ✏️ CORRIGIR: {motivo}")
                traj["passos"] = pn
                json.dump(traj, open(os.path.join(TRAJ_DIR, f"{nome}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                c += 1
            else:
                m += 1
        else:
            m += 1
    _reindexar()
    print(f"📊 {m} mantida, {c} corrigida, {r} removida, {p} pulada (manual).\n")


def _limpar_trajetorias_ruins():
    ruins = []
    for nome in listar_trajetorias():
        traj = ler_trajetoria(nome)
        if not traj:
            continue
        passos = traj.get("passos", [])
        ok, motivo = _avaliar_qualidade(passos, traj.get("exemplo_original", ""), eh_template=True)
        template = traj.get("template", "")
        if not ok:
            ruins.append((nome, motivo))
        elif _template_eh_lixo(template):
            ruins.append((nome, "template lixo"))
    if not ruins:
        print("✨ Nenhuma ruim.")
        return
    print(f"🗑️ {len(ruins)} ruim(ns):")
    for nome, motivo in ruins:
        print(f"   - {nome}: {motivo}")
        c = os.path.join(TRAJ_DIR, f"{nome}.json")
        if os.path.exists(c):
            os.remove(c)
    _reindexar()
    print(f"✅ Apagadas.\n")


def _boot_automatico():
    print("\n" + "=" * 55)
    print("🔧 BOOT AUTOMÁTICO")
    print("=" * 55)
    print("\n[1/4] Limpando trajetórias ruins (heurística)...")
    _limpar_trajetorias_ruins()
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8")) if os.path.exists(CONFIG_FILE) else {}
    tem_groq = cfg.get("groq_api_key", "").startswith("gsk_")
    trajs = listar_trajetorias()
    if tem_groq and trajs:
        print(f"\n[2/4] Auditando {len(trajs)} trajetória(s) com Groq...")
        auditar_todas()
    else:
        print(f"\n[2/4] Sem trajetórias ou sem Groq — pulando auditoria.")
    print(f"\n[3/4] Compilando trajetórias em micros...")
    compilar_trajetorias()
    print(f"\n[4/4] Gerando mapa RAG...")
    try:
        gerar_mapa_rag()
    except Exception as e:
        print(f"⚠️ Mapa falhou: {e}")
    print("=" * 55)
    print("✅ BOOT COMPLETO")
    print("=" * 55 + "\n")


STOPWORDS = {
    "me", "traz", "o", "a", "os", "as", "de", "do", "da", "no", "na", "num", "numa",
    "um", "uma", "por", "favor", "que", "e", "é", "pra", "para", "pelo", "pela",
    "com", "sem", "sobre", "the", "ai", "aí", "link", "url", "endereço", "site",
    "canal", "pega", "pegar", "busca", "buscar", "pesquisa", "pesquisar", "acha",
    "achar", "encontra", "encontrar", "quero", "preciso", "vai", "vou", "ir",
    "videos", "vídeos", "faz", "lista",
}


def _extrair_palavras_chave(objetivo):
    palavras = re.findall(r"\w+", objetivo.lower())
    return [p for p in palavras if p not in STOPWORDS and len(p) > 2]


def detectar_resposta(objetivo, resultado):
    obj_low = objetivo.lower()
    if not any(w in obj_low for w in ["link", "url", "endereço", "site", "canal"]):
        return None
    chaves = _extrair_palavras_chave(objetivo)
    if not chaves:
        return None
    urls = re.findall(r"https?://[^\s'\"<>\)]+", resultado)
    candidatos = []
    for u in urls:
        if "accounts.google" in u or "/redirect" in u or "webcache" in u:
            continue
        match_kw = sum(1 for c in chaves if c in u.lower())
        if match_kw == 0:
            continue
        try:
            from urllib.parse import urlparse
            partes = urlparse(u)
            if partes.path.rstrip("/") == "" and not partes.query:
                continue
        except:
            pass
        candidatos.append((u, match_kw))
    if not candidatos:
        return None
    candidatos.sort(key=lambda x: -x[1])
    return candidatos[0][0]


def montar_lista_ferramentas():
    linhas = []
    for nome, info in FERRAMENTAS.items():
        params = ", ".join(f"{k}" for k in info["parametros"].keys()) or "nenhum"
        linhas.append(f"- {nome}({params}): {info['descricao']}")
    return "\n".join(linhas)


def _montar_bloco_trajetorias(nomes):
    if not nomes:
        return ""
    linhas = ["TRAJETÓRIAS DISPONÍVEIS (use com a ferramenta usar_trajetoria):"]
    for nome in nomes[:15]:
        t = ler_trajetoria(nome)
        if not t:
            continue
        tipo = t.get("tipo") or ("micro" if nome.startswith("micro_") else "composta")
        icone = "📦" if tipo == "composta" else "🔧"
        desc = t.get("descricao_rag") or t.get("template") or t.get("exemplo_original", "")
        linhas.append(f"  {icone} {nome}: {desc[:120]}")
    linhas.append("")
    linhas.append("Pra usar, chame a ferramenta usar_trajetoria com:")
    linhas.append('  {"modo":"acao","ferramenta":"usar_trajetoria","parametros":{"nome":"NOME_EXATO","params":{}}}')
    return "\n".join(linhas)


def montar_system(contexto_extra="", bloco_trajs=""):
    ensinos = listar_ensinamentos()
    ctx = carregar_contexto()
    bloco_ensinos = "\n\nREGRAS DO USUÁRIO:\n" + "\n".join(f"- {e}" for e in ensinos) if ensinos else ""
    bloco_ctx = "\n\nFATOS:\n" + "\n".join(f"- {k}: {v}" for k, v in ctx.items()) if ctx else ""
    bloco_rag = f"\n\n{contexto_extra}" if contexto_extra else ""

    return f"""Você é o Bebê, agente AUTÔNOMO.

🧑 SEU NOME É "Bebê". Se o usuário te chamar por "Bebê", é VOCÊ.

FERRAMENTAS:
{montar_lista_ferramentas()}

{bloco_trajs}

Responda SEMPRE JSON válido.

MODOS:
1) CHAT: {{"modo": "chat", "resposta": "curta"}}
2) ACAO: {{"modo": "acao", "pensamento": "...", "ferramenta": "nome", "parametros": {{...}}}}
3) FIM: {{"modo": "fim", "resposta": "resumo COM RESULTADO"}}
4) APRENDER: {{"modo": "aprender", "regra": "texto"}}

🚨 REGRA #0 — BROWSER vs DESKTOP (CRÍTICA)
Cada ferramenta tem marcação:
- 🌐 BROWSER = opera na PÁGINA web (Playwright). Ex: navegar, preencher_campo, clicar_no_elemento, clicar_selector, digitar, pressionar.
- 🖥️ DESKTOP = opera no APP ATIVO do Windows (pyautogui/uiautomation). Ex: abrir_programa, pressionar_tecla, digitar_teclado, ler_tela, clicar_controle.

⚠️ Se você ABRIU UM PROGRAMA (calculadora, notepad, paint):
  → Use SÓ ferramentas 🖥️ DESKTOP.
  → NUNCA use preencher_campo, clicar_selector, digitar, pressionar (essas são do browser e vão abrir o Chromium à toa).
  → Pra digitar na calculadora: pressionar_tecla(tecla='2'), pressionar_tecla(tecla='+'), pressionar_tecla(tecla='enter').
  → Pra ler o resultado: ler_tela().

⚠️ Se você está numa PÁGINA WEB:
  → Use SÓ ferramentas 🌐 BROWSER.
  → NUNCA use pressionar_tecla, digitar_teclado (essas são do desktop).

🚨 REGRA #0.5 — NOMES EXATOS DOS PARÂMETROS
- preencher_campo(descricao="...", valor="...")   ← use 'valor', NÃO 'value'
- digitar(texto="...", selector="...")             ← browser
- digitar_teclado(texto="...")                     ← desktop
- pressionar_tecla(tecla="...")                    ← desktop
- pressionar(tecla="...")                          ← browser
- abrir_programa(nome="...")                       ← desktop

🚨 REGRA CRÍTICA — TRAJETÓRIA vs FERRAMENTA
- Se existe uma trajetória que RESOLVE o pedido (aparece na lista acima),
  chame: {{"modo":"acao","ferramenta":"usar_trajetoria","parametros":{{"nome":"NOME_EXATO","params":{{...}}}}}}
- Se nenhuma serve, use as FERRAMENTAS direto.
- NUNCA chame uma trajetória como se fosse ferramenta.

🚨 AÇÃO vs APRENDER
APRENDER apenas se o usuário disser LITERALMENTE: "aprenda que", "anote que", etc.

🚨 REGRA #1 — ACHOU RESPOSTA = FIM
🚨 REGRA #2 — NUNCA INVENTE URLS
🚨 REGRA #3 — NAVEGADOR: navegar → ler_pagina_estruturada → preencher/clicar
⚠️ REGRA #4 — SELETORES com aspas duplas
🚫 REGRA #5 — SEM OCR EM NAVEGADOR
🔄 FALHOU? 3 tentativas → pare.
- Um passo por vez.
{bloco_rag}{bloco_ensinos}{bloco_ctx}

Responda APENAS o JSON."""


def extrair_json(texto):
    texto = texto.strip().replace("```json", "").replace("```", "").strip()
    i = texto.find("{")
    f = texto.rfind("}")
    if i == -1 or f == -1:
        return None
    try:
        return json.loads(texto[i:f+1])
    except Exception:
        return None


def executar_ferramenta(nome, params):
    if nome not in FERRAMENTAS:
        return f"Ferramenta desconhecida: {nome}"
    try:
        return str(FERRAMENTAS[nome]["funcao"](**params))
    except Exception as e:
        return f"Erro: {e}"


STDIN_Q = queue.Queue()


def _stdin_reader():
    while True:
        try:
            linha = input()
            STDIN_Q.put(linha)
        except (EOFError, KeyboardInterrupt):
            return
        except Exception:
            return


threading.Thread(target=_stdin_reader, daemon=True).start()


def drenar_feedbacks():
    fb = []
    while True:
        try:
            l = STDIN_Q.get_nowait().strip()
            if l:
                fb.append(l)
        except queue.Empty:
            break
    return fb


def replay(nome, passos):
    global CANCELAR
    print(f"⚡ REPLAY: {nome} ({len(passos)} passos)")
    dumps = []
    for i, passo in enumerate(passos, 1):
        if CANCELAR:
            return False
        ferr = passo["ferramenta"]
        par = passo["params"]
        print(f"   [{i}/{len(passos)}] {ferr}({par})")
        res = executar_ferramenta(ferr, par)
        if "Erro" in res or "não existe" in res.lower() or "não achei" in res.lower():
            print(f"   ⚠️ {res}")
            return False
        if ferr.startswith("ler_"):
            dumps.append(res)
    return dumps if dumps else True


def verificar_conclusao(objetivo, passos_ok, resp_fim):
    if not passos_ok:
        return True, ""
    passos_resumo = "\n".join(f"- {p['ferramenta']}({p['params']}) → {'ERRO' if p.get('erro') else 'OK'}" for p in passos_ok)
    verificacao = f"""Objetivo: "{objetivo}"
Passos: {passos_resumo}
Resposta: "{resp_fim}"
Cumprido? JSON: {{"cumprido": true}} ou {{"cumprido": false, "o_que_falta": "..."}}"""
    try:
        rv = ollama.chat(model=MODEL, messages=[{"role": "user", "content": verificacao}], format="json")
        verif = json.loads(rv["message"]["content"])
        return verif.get("cumprido", True), verif.get("o_que_falta", "")
    except:
        return True, ""


def detectar_loop(passos_ok):
    if len(passos_ok) < 3:
        return False
    ultimos = passos_ok[-3:]
    todos_erro = all(p.get("erro") for p in ultimos)
    mesma_ferramenta = all(p["ferramenta"] == ultimos[0]["ferramenta"] for p in ultimos)
    return todos_erro or mesma_ferramenta


def processar_react(entrada, _recursivo=False, contexto_extra="", nomes_trajs=None):
    global CANCELAR, HISTORICO_CHAT
    CANCELAR = False

    if not _recursivo:
        drenar_feedbacks()
        print(f"\n🎯 {entrada}\n")

    HISTORICO_CHAT.append({"role": "user", "content": entrada})
    if len(HISTORICO_CHAT) > MAX_HISTORICO:
        HISTORICO_CHAT = HISTORICO_CHAT[-MAX_HISTORICO:]

    if nomes_trajs is None:
        nomes_trajs = listar_trajetorias()
    bloco_trajs = _montar_bloco_trajetorias(nomes_trajs)

    mensagens = [{"role": "system", "content": montar_system(contexto_extra, bloco_trajs)}] + HISTORICO_CHAT
    passos_ok = []
    erros_consecutivos = 0
    erros_tool = []
    treinador_ja_chamado = False
    urls_invalidas = 0

    for passo in range(1, 30):
        if CANCELAR:
            print("🛑 Cancelado.")
            return

        feedbacks = drenar_feedbacks()
        if feedbacks:
            texto_fb = " | ".join(feedbacks)
            print(f"\n📝 [feedback]: {texto_fb}")
            mensagens.append({"role": "user", "content": f"[COMENTÁRIO]: {texto_fb}"})
            if any(p in texto_fb.lower() for p in ["para", "pare", "cancela"]):
                return

        if not treinador_ja_chamado and detectar_loop(passos_ok):
            print(f"\n🆘 Loop detectado. Consultando treinador...")
            treinador_ja_chamado = True
            plano = consultar_treinador(entrada, FERRAMENTAS_BASE, listar_trajetorias(), passos_ok, "Loop")
            if plano:
                ok = executar_plano(plano, FERRAMENTAS_BASE, executar_ferramenta,
                                    lambda d: processar_react(d, _recursivo=True),
                                    salvar_trajetoria_template, criar_template,
                                    extrair_parametros, aplicar_parametros, entrada)
                if ok:
                    return
            erros_tool = []

        print(f"\n--- Passo {passo} ---")
        try:
            resp = ollama.chat(model=MODEL, messages=mensagens, format="json")
        except Exception as e:
            print(f"❌ Erro LLM: {e}")
            return

        conteudo = resp["message"]["content"]
        dados = extrair_json(conteudo)

        if not dados:
            erros_consecutivos += 1
            print(f"⚠️ JSON inválido ({erros_consecutivos}/3)")
            if erros_consecutivos >= 3:
                return
            mensagens.append({"role": "assistant", "content": conteudo})
            mensagens.append({"role": "user", "content": 'Responda APENAS JSON válido.'})
            continue

        erros_consecutivos = 0
        modo = dados.get("modo", "").lower()
        pensamento = dados.get("pensamento", "")
        if pensamento:
            print(f"💭 {pensamento}")

        if modo == "chat":
            resp_txt = dados.get("resposta", "...")
            print(f"\n🤖 Bebê: {resp_txt}")
            HISTORICO_CHAT.append({"role": "assistant", "content": resp_txt})
            HISTORICO_CHAT = HISTORICO_CHAT[-MAX_HISTORICO:]
            return

        if modo == "aprender":
            regra = dados.get("regra", "").strip()
            gatilhos = ("aprenda", "anote", "lembre", "guarda", "toda vez")
            if not any(g in entrada.lower() for g in gatilhos):
                print(f"\n⚠️ Falso APRENDER. Tratando como ACAO.")
                mensagens.append({"role": "assistant", "content": conteudo})
                mensagens.append({"role": "user", "content": '❌ Isso é TAREFA, não aprender. Use modo ACAO.'})
                continue
            if regra:
                n = adicionar_ensinamento(regra)
                print(f"\n🧠 Aprendi: {regra} ({n} total)")
            return

        if modo == "fim":
            resp_fim = dados.get("resposta", "Pronto.")
            if passos_ok and not _recursivo:
                cumprido, falta = verificar_conclusao(entrada, passos_ok, resp_fim)
                if not cumprido:
                    print(f"❌ Não cumprido. Falta: {falta}")
                    mensagens.append({"role": "assistant", "content": conteudo})
                    mensagens.append({"role": "user", "content": f"❌ Falta: {falta}. Continue."})
                    continue
            print(f"\n✅ {resp_fim}")
            tem_erro = any(p.get("erro") for p in passos_ok) if passos_ok else True
            if passos_ok and not tem_erro and len(passos_ok) >= MIN_PASSOS_PARA_SALVAR:
                _salvar_com_qualidade(entrada, passos_ok)
            HISTORICO_CHAT.append({"role": "assistant", "content": f"[fim: {resp_fim}]"})
            HISTORICO_CHAT = HISTORICO_CHAT[-MAX_HISTORICO:]
            return

        if modo == "acao":
            ferr = dados.get("ferramenta")
            par = dados.get("parametros", {})
            if not ferr:
                mensagens.append({"role": "assistant", "content": conteudo})
                mensagens.append({"role": "user", "content": "Escolha uma ferramenta."})
                continue
            print(f"🔧 {ferr}({par})")
            resultado = executar_ferramenta(ferr, par)
            if ferr.startswith("ler_") or ferr == "usar_trajetoria":
                print(f"📤 {resultado[:1500]}")
            else:
                print(f"📤 {resultado[:300]}")
            tem_erro = ("Erro" in resultado or "não existe" in resultado.lower() or "não achei" in resultado.lower())
            passos_ok.append({"ferramenta": ferr, "params": par, "erro": tem_erro})

            if ferr in ("ler_pagina_estruturada", "ler_texto_pagina", "url_atual", "ler_tela", "ler_tela_estruturada"):
                url_achada = detectar_resposta(entrada, resultado)
                if url_achada:
                    print(f"\n🎯 LINK DETECTADO: {url_achada}")
                    print(f"\n✅ Encontrado! Link: {url_achada}")
                    tem_erro_anterior = any(p.get("erro") for p in passos_ok)
                    if not tem_erro_anterior and len(passos_ok) >= MIN_PASSOS_PARA_SALVAR:
                        _salvar_com_qualidade(entrada, passos_ok)
                    HISTORICO_CHAT.append({"role": "assistant", "content": f"[fim: {url_achada}]"})
                    HISTORICO_CHAT = HISTORICO_CHAT[-MAX_HISTORICO:]
                    return

            if tem_erro:
                erros_tool.append((ferr, resultado))

            if len(erros_tool) >= MAX_ERROS_ANTES_TREINADOR and not treinador_ja_chamado:
                print(f"\n🆘 {MAX_ERROS_ANTES_TREINADOR} erros. Consultando treinador...")
                treinador_ja_chamado = True
                plano = consultar_treinador(entrada, FERRAMENTAS_BASE, listar_trajetorias(), passos_ok, "Erros")
                if plano:
                    ok = executar_plano(plano, FERRAMENTAS_BASE, executar_ferramenta,
                                        lambda d: processar_react(d, _recursivo=True),
                                        salvar_trajetoria_template, criar_template,
                                        extrair_parametros, aplicar_parametros, entrada)
                    if ok:
                        return
                erros_tool = []

            mensagens.append({"role": "assistant", "content": conteudo})
            if tem_erro:
                mensagens.append({"role": "user", "content": f"❌ ERRO: {resultado[:300]}\nTente outra abordagem."})
            else:
                mensagens.append({"role": "user", "content": f"Resultado: {resultado[:600]}\nPróximo passo ou 'fim'."})
            continue

        mensagens.append({"role": "assistant", "content": conteudo})
        mensagens.append({"role": "user", "content": "Use modo: chat, acao, fim, aprender."})

    print("\n⚠️ Máximo de passos.")


def processar(entrada):
    print("🔍 Buscando trajetórias (RAG híbrido + rerank)...")
    try:
        resultados = buscar_top_rag(entrada, top_k_final=5)
    except Exception as e:
        print(f"⚠️ RAG falhou: {e}. Seguindo sem contexto.")
        resultados = []

    if not resultados:
        print("📭 RAG vazio. Caindo pro ReAct com conhecimento zero...\n")
        processar_react(entrada, contexto_extra="")
        return

    top1_sim = resultados[0]["similaridade"]
    top1_traj = resultados[0]["trajetoria"]
    print(f"🧠 Top1: {top1_traj['nome']} (sim {top1_sim:.2f})")

    if top1_sim >= THRESHOLD_REPLAY_DIRETO and top1_traj.get("tipo") != "composta":
        print(f"   → Zona ALTA: replay direto")
        params = {}
        passos_finais = top1_traj["passos"]
        if top1_traj.get("parametros"):
            params = extrair_parametros(top1_traj.get("template", ""), top1_traj["parametros"], entrada)
            passos_finais = aplicar_parametros(top1_traj["passos"], params)
        resultado_replay = replay(top1_traj["nome"], passos_finais)
        if resultado_replay and resultado_replay is not True:
            print(f"\n{'='*55}")
            print("🧠 Sintetizando resposta...")
            print("="*55)
            dump = resultado_replay[-1] if isinstance(resultado_replay, list) else None
            if dump:
                resposta = sintetizar_resposta(entrada, dump)
                if resposta:
                    print(f"\n💬 RESPOSTA: {resposta}\n")
            print("\n✅ REPLAY")
            return
        elif resultado_replay is True:
            print("\n✅ REPLAY")
            return
        print("⚠️ Replay falhou. Continuando...\n")

    if top1_sim < THRESHOLD_AVALIACAO:
        print(f"   → Zona BAIXA: nada relevante. Caindo pro ReAct...\n")
        nomes_trajs = [r["trajetoria"]["nome"] for r in resultados[:3]]
        contexto = formatar_contexto_rag(resultados[:2])
        processar_react(entrada, contexto_extra=contexto, nomes_trajs=nomes_trajs)
        return

    print(f"   → Zona CINZENTA: avaliando fit com Groq...")
    avaliacao = avaliar_fit(entrada, resultados[:3])

    trajs_aprovadas_nomes = []

    if avaliacao:
        fit = avaliacao.get("fit", "nenhum")
        aprovadas = avaliacao.get("aprovadas", [])
        motivo = avaliacao.get("motivo", "")
        print(f"   Fit: {fit} | aprovadas: {aprovadas}")
        if motivo:
            print(f"   Motivo: {motivo}")

        if fit == "nenhum" or not aprovadas:
            print(f"\n⚠️ Nenhuma trajetória resolve exatamente. Caindo pro ReAct...\n")
            nomes_trajs = [r["trajetoria"]["nome"] for r in resultados[:5]]
            contexto = formatar_contexto_rag(resultados[:3])
            processar_react(entrada, contexto_extra=contexto, nomes_trajs=nomes_trajs)
            return

        for nome in aprovadas:
            if ler_trajetoria(nome):
                trajs_aprovadas_nomes.append(nome)
            else:
                alt = f"micro_{nome}"
                if ler_trajetoria(alt):
                    trajs_aprovadas_nomes.append(alt)

        if not trajs_aprovadas_nomes:
            print(f"   ⚠️ Groq aprovou nomes inexistentes. Caindo pro ReAct...\n")
            nomes_trajs = [r["trajetoria"]["nome"] for r in resultados[:5]]
            contexto = formatar_contexto_rag(resultados[:3])
            processar_react(entrada, contexto_extra=contexto, nomes_trajs=nomes_trajs)
            return

        if fit == "parcial":
            print(f"   ⚠️ Fit PARCIAL — usando aproximação.")
    else:
        print(f"   ⚠️ Avaliação Groq falhou. Usando top RAG sem filtro.")
        trajs_aprovadas_nomes = [r["trajetoria"]["nome"] for r in resultados[:2]]

    if COMPOSICAO_ATIVA:
        micros_todas = _listar_micros()
        nomes_final = list(trajs_aprovadas_nomes)
        for m in micros_todas:
            if len(nomes_final) >= 8:
                break
            if m not in nomes_final:
                nomes_final.append(m)

        print(f"\n🧩 Compositor ({len(nomes_final)} trajetórias pré-aprovadas)...")

        trajs_info = []
        for nome_m in nomes_final:
            t = ler_trajetoria(nome_m)
            if t:
                tipo = t.get("tipo") or ("micro" if nome_m.startswith("micro_") else "composta")
                trajs_info.append({
                    "nome": nome_m,
                    "template": t.get("template", ""),
                    "parametros": t.get("parametros", []),
                    "descricao_rag": t.get("descricao_rag", ""),
                    "tipo": tipo,
                })

        plano = planejar_composicao(entrada, trajs_info, FERRAMENTAS_BASE)
        if plano and "plano" in plano and len(plano["plano"]) >= 1:
            print(f"\n📋 Compositor: {len(plano['plano'])} etapa(s)")
            ok = executar_plano(
                plano, FERRAMENTAS_BASE, executar_ferramenta,
                lambda d: processar_react(d, _recursivo=True),
                salvar_trajetoria_template, criar_template,
                extrair_parametros, aplicar_parametros, entrada,
            )
            if ok:
                print("\n✅ COMPOSIÇÃO")
                return
            print("⚠️ Composição falhou. ReAct...\n")

    etapas = decompor_por_padrao(entrada)
    if etapas:
        print(f"🐍 Padrão Python: {len(etapas)} etapa(s)")
        plano = {"plano": etapas}
        ok = executar_plano(
            plano, FERRAMENTAS_BASE, executar_ferramenta,
            lambda d: processar_react(d, _recursivo=True),
            salvar_trajetoria_template, criar_template,
            extrair_parametros, aplicar_parametros, entrada,
        )
        if ok:
            print("\n✅ PADRÃO")
            return

    contexto = formatar_contexto_rag(resultados[:3])
    nomes_trajs = [r["trajetoria"]["nome"] for r in resultados[:5]]
    processar_react(entrada, contexto_extra=contexto, nomes_trajs=nomes_trajs)


def mostrar_ajuda():
    print("""
📖 COMANDOS:
   <qualquer coisa>    → replay → avaliação → composição → ReAct
   compilar, auditar, auditar_forcar, mapa, limpar_ruins
   limpar_padroes, trajetorias, ver <nome>, apagar <nome>
   contexto, padroes, ensinamentos, esquecer <n>, limpar, reindexar
   ajuda / sair
""")


if __name__ == "__main__":
    print("=" * 55)
    print("🤖 BEBÊ - Agente Autônomo + Treinador Groq")
    print("=" * 55)
    print(f"📁 Trajetórias: {TRAJ_DIR}")
    print(f"📁 Conteúdo:   C:\\Nero\\conteudo\\txt")

    _carregar_rag()

    cfg = json.load(open(CONFIG_FILE, encoding="utf-8")) if os.path.exists(CONFIG_FILE) else {}
    tem_groq = cfg.get("groq_api_key", "").startswith("gsk_")

    print(f"🤖 Groq: {'ATIVO' if tem_groq else 'SEM CHAVE'}")
    print(f"🎯 Avaliação de fit: ON (zonas 0.50 - 0.85)")
    print(f"🔧 usar_trajetoria no ReAct: ON")
    print(f"🔍 Auditoria: ON")
    print(f"🧩 Composição: ON")
    print(f"💬 Síntese final: ON")

    if BOOT_AUTOMATICO and tem_groq:
        _boot_automatico()
    elif BOOT_AUTOMATICO:
        print("\n🔧 Boot parcial (sem Groq)...")
        _limpar_trajetorias_ruins()
        compilar_trajetorias()
        try:
            gerar_mapa_rag()
        except Exception as e:
            print(f"⚠️ Mapa falhou: {e}")

    trajs = listar_trajetorias()
    micros = _listar_micros()
    print(f"📚 {len(trajs)} trajetória(s) — {len(micros)} micro(s)")

    print("\n💡 Digite 'ajuda' ou só use direto\n")

    while True:
        try:
            print("\n> ", end="", flush=True)
            obj = STDIN_Q.get().strip()
            if not obj:
                continue
            low = obj.lower()

            if len(obj.split()) == 1 and low in COMANDOS_CLI:
                if low in ("ajuda", "help"):
                    mostrar_ajuda()
                    continue
                if low in ("sair", "exit", "quit"):
                    print("👋 Até mais!")
                    break
                if low == "limpar":
                    limpar_historico()
                    print("🧹 Limpo.")
                    continue
                if low == "limpar_ruins":
                    _limpar_trajetorias_ruins()
                    continue
                if low == "limpar_padroes":
                    print(limpar_padroes())
                    continue
                if low == "auditar":
                    auditar_todas(forcar=False)
                    continue
                if low == "auditar_forcar":
                    auditar_todas(forcar=True)
                    continue
                if low == "compilar":
                    compilar_trajetorias()
                    continue
                if low == "mapa":
                    gerar_mapa_rag()
                    continue
                if low == "reindexar":
                    _reindexar()
                    print("✅ Reindexado.")
                    continue
                if low == "contexto":
                    from ferramentas import listar_contexto
                    print(listar_contexto())
                    continue
                if low == "padroes":
                    print(listar_padroes())
                    continue
                if low == "ensinamentos":
                    e = listar_ensinamentos()
                    if e:
                        for i, item in enumerate(e, 1):
                            print(f"   {i}. {item}")
                    else:
                        print("🧠 Nenhum.")
                    continue
                if low == "trajetorias":
                    t = listar_trajetorias()
                    for nome in t:
                        marcador = "🧩" if nome.startswith("micro_") else "📦"
                        print(f"   {marcador} {nome}")
                    continue

            if low.startswith("esquecer "):
                try:
                    n = int(obj.split()[1]) - 1
                    lista = listar_ensinamentos()
                    if 0 <= n < len(lista):
                        removido = lista.pop(n)
                        salvar_ensinamentos(lista)
                        print(f"🗑️ Esqueci: {removido}")
                except:
                    print("Uso: esquecer <número>")
                continue

            if low.startswith("ver "):
                print(formatar_trajetoria(obj[4:].strip()))
                continue

            if low.startswith("apagar "):
                print(remover_trajetoria(obj[7:].strip()))
                continue

            processar(obj)

        except KeyboardInterrupt:
            print("\n⚠️ Ctrl+C.")
            continue
        except EOFError:
            print("\n👋 EOF.")
            break