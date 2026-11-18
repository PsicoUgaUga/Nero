import subprocess
import os
import json
import time
import ctypes
import requests
import pyautogui
import pyperclip
from PIL import ImageGrab
import pytesseract
import urllib.parse

pytesseract.pytesseract.tesseract_cmd = r"C:\Nero\trenheira\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\Nero\trenheira\tessdata"

CONFIG_FILE = r"C:\Nero\config.json"
CONTEXTO_FILE = r"C:\Nero\contexto.json"

PASTA_CONTEUDO = r"C:\Nero\conteudo\txt"
PASTA_PRINTS = r"C:\Nero\conteudo\prints"
PASTA_DOWNLOADS = r"C:\Nero\conteudo\downloads"
os.makedirs(PASTA_CONTEUDO, exist_ok=True)
os.makedirs(PASTA_PRINTS, exist_ok=True)
os.makedirs(PASTA_DOWNLOADS, exist_ok=True)

PLACEHOLDER_PATHS = [
    "caminho/do", "caminho\\do", "caminho/da", "caminho\\da",
    "path/to", "path\\to", "seu/caminho", "seu\\caminho",
    "example/", "example\\", "/path/", "\\path\\",
    "diretorio/", "diretorio\\", "pasta/destino", "pasta\\destino",
    "c:/caminho", "c:\\caminho",
]

PREFIXOS_PROIBIDOS = [
    "c:\\temp", "c:\\tmp", "c:\\users", "c:\\windows", "c:\\program",
    "c:\\arquivos", "c:\\documents", "c:\\desktop", "c:\\downloads",
]


def _config():
    if os.path.exists(CONFIG_FILE):
        try:
            return json.load(open(CONFIG_FILE, encoding="utf-8"))
        except:
            return {}
    return {}


def _sanitizar_caminho(caminho: str):
    if not caminho or not isinstance(caminho, str):
        return None
    c = caminho.lower().strip()
    for p in PLACEHOLDER_PATHS:
        if p in c:
            return None
    if c in ("caminho", "path", "arquivo", "file"):
        return None
    return caminho.strip()


def _resolver_caminho(caminho: str):
    caminho = _sanitizar_caminho(caminho)
    if caminho is None:
        return None
    c = caminho.replace("/", "\\").strip()
    c_low = c.lower()

    if ":" in c[:3]:
        if c_low.startswith("c:\\nero"):
            return c
        for prefixo in PREFIXOS_PROIBIDOS:
            if c_low.startswith(prefixo):
                nome = os.path.basename(c) or "arquivo.txt"
                print(f"   ⚠️ Path '{c}' fora de C:\\Nero → redirecionando pra {PASTA_CONTEUDO}")
                return os.path.join(PASTA_CONTEUDO, nome)
        nome = os.path.basename(c) or "arquivo.txt"
        print(f"   ⚠️ Path '{c}' fora de C:\\Nero → redirecionando pra {PASTA_CONTEUDO}")
        return os.path.join(PASTA_CONTEUDO, nome)

    if "\\" in c or c.startswith("."):
        return os.path.join(PASTA_CONTEUDO, c.lstrip(".\\/"))
    return os.path.join(PASTA_CONTEUDO, c)


# ============================================================
# CONTEXTO
# ============================================================

def carregar_contexto():
    if os.path.exists(CONTEXTO_FILE):
        try:
            return json.load(open(CONTEXTO_FILE, encoding="utf-8"))
        except:
            return {}
    return {}


def salvar_contexto(ctx):
    json.dump(ctx, open(CONTEXTO_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def lembrar(chave: str, valor: str):
    ctx = carregar_contexto()
    ctx[chave] = valor
    salvar_contexto(ctx)
    return f"Guardei: {chave} = {valor}"


def esquecer_fato(chave: str):
    ctx = carregar_contexto()
    if chave in ctx:
        del ctx[chave]
        salvar_contexto(ctx)
        return f"Esqueci: {chave}"
    return f"Não sabia: {chave}"


def listar_contexto():
    ctx = carregar_contexto()
    if not ctx:
        return "Nada guardado."
    return "\n".join(f"- {k}: {v}" for k, v in ctx.items())


# ============================================================
# SISTEMA
# ============================================================

def abrir_programa(nome: str = None, programa: str = None, app: str = None, **kwargs):
    nome = nome or programa or app
    if not nome:
        return "Erro: nome do programa não informado"
    mapa = {
        "calculadora": "calc.exe", "calc": "calc.exe",
        "bloco de notas": "notepad.exe", "notepad": "notepad.exe",
        "navegador": "chrome.exe", "chrome": "chrome.exe",
        "explorer": "explorer.exe", "paint": "mspaint.exe", "cmd": "cmd.exe",
    }
    exe = mapa.get(str(nome).lower(), str(nome))
    try:
        subprocess.Popen(exe)
        return f"Abri {exe}"
    except Exception as e:
        return f"Erro: {e}"


def executar_cmd(comando: str = None, cmd: str = None, comando_cmd: str = None, **kwargs):
    comando = comando or cmd or comando_cmd
    if not comando:
        return "Erro: comando não informado"
    try:
        r = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=30)
        return ((r.stdout or "") + (r.stderr or ""))[:2000]
    except Exception as e:
        return f"Erro: {e}"


def bloquear_pc(**kwargs):
    ctypes.windll.user32.LockWorkStation()
    return "PC bloqueado"


def copiar(**kwargs):
    pyautogui.hotkey("ctrl", "c")
    return "Copiado"


def colar(**kwargs):
    pyautogui.hotkey("ctrl", "v")
    return "Colado"


def salvar(**kwargs):
    pyautogui.hotkey("ctrl", "s")
    return "Salvo"


def salvar_como(caminho: str = None, nome: str = None, **kwargs):
    caminho = caminho or nome
    c = _resolver_caminho(caminho)
    if c is None:
        return f"Erro: caminho inválido ou placeholder: '{caminho}'"
    try:
        os.makedirs(os.path.dirname(c) or ".", exist_ok=True)
        pyautogui.hotkey("ctrl", "shift", "s")
        time.sleep(0.7)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.typewrite(c, interval=0.01)
        time.sleep(0.3)
        pyautogui.press("Enter")
        time.sleep(0.5)
        pyautogui.press("Enter")
        return f"Salvo como: {c}"
    except Exception as e:
        return f"Erro: {e}"


def esperar(segundos: float = None, tempo: float = None, **kwargs):
    segundos = segundos or tempo or 1
    time.sleep(float(segundos))
    return f"Esperou {segundos}s"


# ============================================================
# ARQUIVOS
# ============================================================

def listar_pasta(caminho: str = None, nome: str = None, **kwargs):
    caminho = caminho or nome
    c = _resolver_caminho(caminho)
    if c is None:
        return f"Caminho inválido: {caminho}"
    if not os.path.exists(c):
        return f"Não existe: {c}"
    return os.listdir(c)


def criar_pasta(caminho: str = None, nome: str = None, **kwargs):
    caminho = caminho or nome
    c = _resolver_caminho(caminho)
    if c is None:
        return f"Caminho inválido: {caminho}"
    os.makedirs(c, exist_ok=True)
    return f"Pasta criada: {c}"


def procurar_pasta(nome: str = None, raiz: str = "C:\\", **kwargs):
    if not nome:
        return "Erro: nome não informado"
    achados = []
    try:
        for dirpath, dirnames, _ in os.walk(raiz):
            for d in dirnames:
                if nome.lower() in d.lower():
                    achados.append(os.path.join(dirpath, d))
            if len(achados) > 20:
                break
    except Exception as e:
        return f"Erro: {e}"
    return achados if achados else f"Nada encontrado: {nome}"


def criar_arquivo(caminho: str = None, nome: str = None, arquivo: str = None,
                  path: str = None, conteudo: str = "", **kwargs):
    caminho = caminho or nome or arquivo or path
    c = _resolver_caminho(caminho)
    if c is None:
        return f"Erro: caminho inválido ou placeholder: '{caminho}'"
    try:
        os.makedirs(os.path.dirname(c) or ".", exist_ok=True)
        with open(c, "w", encoding="utf-8") as f:
            f.write(conteudo or "")
        return f"Arquivo criado: {c}"
    except Exception as e:
        return f"Erro: {e}"


def escrever_arquivo(caminho: str = None, nome: str = None, arquivo: str = None,
                     path: str = None, conteudo: str = "", **kwargs):
    return criar_arquivo(caminho=caminho or nome or arquivo or path, conteudo=conteudo)


def anexar_arquivo(caminho: str = None, nome: str = None, arquivo: str = None,
                   conteudo: str = "", **kwargs):
    caminho = caminho or nome or arquivo
    c = _resolver_caminho(caminho)
    if c is None:
        return f"Erro: caminho inválido: '{caminho}'"
    try:
        os.makedirs(os.path.dirname(c) or ".", exist_ok=True)
        with open(c, "a", encoding="utf-8") as f:
            f.write((conteudo or "") + "\n")
        return f"Anexado: {c}"
    except Exception as e:
        return f"Erro: {e}"


def ler_arquivo(caminho: str = None, nome: str = None, arquivo: str = None, path: str = None, **kwargs):
    caminho = caminho or nome or arquivo or path
    c = _resolver_caminho(caminho)
    if c is None or not os.path.exists(c):
        return f"Não existe: {caminho}"
    return open(c, encoding="utf-8").read()[:3000]


def apagar_caminho(caminho: str = None, nome: str = None, **kwargs):
    import shutil
    caminho = caminho or nome
    c = _resolver_caminho(caminho)
    if c is None or not os.path.exists(c):
        return f"Não existe: {caminho}"
    if os.path.isdir(c):
        shutil.rmtree(c)
        return f"Pasta apagada: {c}"
    else:
        os.remove(c)
        return f"Arquivo apagado: {c}"


def mover(origem: str = None, destino: str = None, **kwargs):
    import shutil
    if not origem or not destino:
        return "Erro: origem e destino são obrigatórios"
    try:
        shutil.move(origem, destino)
        return f"Movido: {origem} → {destino}"
    except Exception as e:
        return f"Erro: {e}"


def renomear(antigo: str = None, novo: str = None, **kwargs):
    if not antigo or not novo:
        return "Erro: antigo e novo são obrigatórios"
    try:
        os.rename(antigo, novo)
        return f"Renomeado: {antigo} → {novo}"
    except Exception as e:
        return f"Erro: {e}"


# ============================================================
# TELA / OCR
# ============================================================

def tirar_print(caminho: str = None, nome: str = None, **kwargs):
    if not caminho or not str(caminho).lower().startswith("c:\\nero"):
        caminho = os.path.join(PASTA_PRINTS, f"print_{int(time.time())}.png")
    pyautogui.screenshot(caminho)
    return f"Print salvo: {caminho}"


def ler_tela(**kwargs):
    try:
        img = ImageGrab.grab()
        return pytesseract.image_to_string(img, lang="por")[:2000]
    except Exception as e:
        return f"Erro OCR: {e}"


def ler_tela_estruturada(**kwargs):
    try:
        img = ImageGrab.grab()
        dados = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="por")
        linhas = []
        for i, t in enumerate(dados["text"]):
            t = t.strip()
            if not t:
                continue
            if int(dados["conf"][i]) < 60:
                continue
            x = dados["left"][i] + dados["width"][i] // 2
            y = dados["top"][i] + dados["height"][i] // 2
            linhas.append(f"'{t}' em ({x},{y})")
        return "\n".join(linhas[:80]) if linhas else "Tela sem texto legível."
    except Exception as e:
        return f"Erro OCR: {e}"


def clicar_em_texto(texto: str = None, **kwargs):
    if not texto:
        return "Erro: texto não informado"
    try:
        from fuzzywuzzy import fuzz
        img = ImageGrab.grab()
        dados = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="por")
        for i, t in enumerate(dados["text"]):
            if not t.strip():
                continue
            if int(dados["conf"][i]) < 60:
                continue
            if fuzz.ratio(texto.lower(), t.lower()) > 80:
                x = dados["left"][i] + dados["width"][i] // 2
                y = dados["top"][i] + dados["height"][i] // 2
                pyautogui.click(x, y)
                return f"Clicou em '{t}' em ({x},{y})"
        return f"Não achei: {texto}"
    except Exception as e:
        return f"Erro OCR: {e}"


# ============================================================
# CLIPBOARD
# ============================================================

def ler_clipboard(**kwargs):
    try:
        texto = pyperclip.paste()
        return texto if texto else "(vazio)"
    except Exception as e:
        return f"Erro: {e}"


def escrever_clipboard(texto: str = None, **kwargs):
    if not texto:
        return "Erro: texto não informado"
    try:
        pyperclip.copy(texto)
        return f"Copiado para clipboard: {texto[:100]}"
    except Exception as e:
        return f"Erro: {e}"


def limpar_clipboard(**kwargs):
    try:
        pyperclip.copy("")
        return "Clipboard limpo"
    except Exception as e:
        return f"Erro: {e}"


# ============================================================
# NAVEGADOR
# ============================================================

_pw = None
_browser = None
_page = None
_context = None

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en']});
window.chrome = {runtime: {}};
"""


def _garantir_browser():
    global _pw, _browser, _page, _context

    if _browser is not None:
        try:
            _ = _page.url
        except Exception:
            print("⚠️ Navegador morreu. Reabrindo...")
            try:
                _browser.close()
            except:
                pass
            _browser = None
            _page = None
            _context = None

    if _browser is None:
        from playwright.sync_api import sync_playwright

        headless = True
        slow_mo = 0
        try:
            cfg = _config()
            if "browser_headless" in cfg:
                headless = bool(cfg.get("browser_headless"))
            if "browser_slow_mo" in cfg:
                slow_mo = int(cfg.get("browser_slow_mo"))
        except:
            pass

        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--lang=pt-BR",
                "--window-size=1366,768",
            ],
        )
        _context = _browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            accept_downloads=True,
            extra_http_headers={
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
        )
        _context.add_init_script(STEALTH_SCRIPT)
        _page = _context.new_page()

        # Tenta o pw-stealth-enhanced (mais moderno) e cai no antigo como fallback
        try:
            from pw_stealth_enhanced import stealth_sync
            stealth_sync(_page)
        except ImportError:
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(_page)
            except ImportError:
                pass
            except Exception as e:
                print(f"   ⚠️ Stealth antigo falhou: {e}.")
        except Exception as e:
            print(f"   ⚠️ pw-stealth-enhanced falhou: {e}. Tentando o antigo...")
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(_page)
            except Exception:
                pass

    return _page


def fechar_browser(**kwargs):
    global _pw, _browser, _page, _context
    try:
        if _browser:
            _browser.close()
        if _pw:
            _pw.stop()
    except:
        pass
    _browser = None
    _page = None
    _context = None
    return "Navegador fechado"


def navegar(url: str = None, **kwargs):
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return f"Erro: URL inválida: '{url}'"
    try:
        pg = _garantir_browser()
        pg.goto(url, timeout=30000, wait_until="domcontentloaded")
        return f"Navegou: {url}"
    except Exception as e:
        return f"Erro: {e}"


def url_atual(**kwargs):
    try:
        pg = _garantir_browser()
        return pg.url
    except Exception as e:
        return f"Erro: {e}"


def ler_pagina_estruturada(**kwargs):
    try:
        pg = _garantir_browser()
        url = pg.url
        titulo = pg.title()

        if url in ("about:blank", "") or url.startswith("data:"):
            return f"⚠️ Ainda não navegou. URL atual: {url}"

        query = ""
        if "search_query=" in url or "q=" in url:
            import urllib.parse
            qs = urllib.parse.urlparse(url).query
            params = urllib.parse.parse_qs(qs)
            query = params.get("search_query", params.get("q", [""]))[0]

        dados = pg.evaluate("""(query) => {
            const out = {campos: [], botoes: [], links: []};
            document.querySelectorAll('input, textarea, select').forEach(el => {
                const tipo = el.tagName.toLowerCase() === 'input' ? (el.type || 'text') : el.tagName.toLowerCase();
                if (tipo === 'hidden') return;
                let sel = el.id ? '#' + el.id : el.name ? `${el.tagName.toLowerCase()}[name="${el.name}"]` : el.tagName.toLowerCase();
                let lbl = '';
                if (el.id) {
                    const l = document.querySelector(`label[for="${el.id}"]`);
                    if (l) lbl = (l.innerText || '').trim();
                }
                if (!lbl && el.closest('label')) lbl = (el.closest('label').innerText || '').trim();
                out.campos.push({tipo, placeholder: el.placeholder || '', label: lbl, seletor: sel});
            });
            document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]').forEach(el => {
                const txt = (el.innerText || el.value || '').trim().slice(0, 50);
                if (!txt) return;
                out.botoes.push({texto: txt});
            });
            const q = (query || '').toLowerCase();
            document.querySelectorAll('a').forEach(el => {
                const txt = (el.innerText || '').trim().slice(0, 100);
                const href = el.href || '';
                if (!txt || !href) return;
                if (href.startsWith('https://accounts.google.com')) return;
                let rel = 0;
                if (q) {
                    if (txt.toLowerCase().includes(q) || href.toLowerCase().includes(q)) rel = 100;
                    else if (href.includes('/watch') || href.includes('/shorts')) rel = 60;
                    else rel = 20;
                } else {
                    if (href.includes('/watch') || href.includes('/shorts')) rel = 60;
                    else if (href.includes('/@') || href.includes('/channel/')) rel = 50;
                    else rel = 20;
                }
                out.links.push({texto: txt, href: href, rel: rel});
            });
            return out;
        }""", query)

        dados["links"].sort(key=lambda x: -x.get("rel", 0))

        linhas = [f"📍 URL: {url}", f"📄 Título: {titulo}"]
        if query:
            linhas.append(f"🔍 Busca: {query}")
        linhas.append("")

        for c in dados["campos"][:15]:
            linhas.append(f"[CAMPO] tipo={c['tipo']} placeholder='{c['placeholder']}' label='{c['label']}' seletor='{c['seletor']}'")
        for b in dados["botoes"][:15]:
            linhas.append(f"[BOTAO] '{b['texto']}'")
        for l in dados["links"][:25]:
            linhas.append(f"[LINK] '{l['texto'][:70]}' href='{l['href'][:130]}'")

        return "\n".join(linhas)
    except Exception as e:
        return f"Erro ao ler página: {e}"


def ler_texto_pagina(**kwargs):
    try:
        pg = _garantir_browser()
        return pg.inner_text("body")[:2000]
    except Exception as e:
        return f"Erro: {e}"


def preencher_campo(descricao: str = None, valor: str = None, **kwargs):
    try:
        if descricao is None:
            descricao = kwargs.get("campo") or kwargs.get("seletor") or ""
        pg = _garantir_browser()
        d = str(descricao).strip()

        if not valor or str(valor).strip() == "":
            return f"⚠️ Valor vazio. Não vou preencher '{d}'."

        if "{comando}" in str(valor) or "{termo}" in str(valor) or "{var}" in str(valor):
            return f"⚠️ Valor tem placeholder não substituído: '{valor}'"

        parece_css = (
            d.startswith("input[") or d.startswith("textarea") or
            d.startswith("select") or d.startswith("#") or
            d.startswith("[name=") or d.startswith(".") or
            ("[" in d and "]" in d)
        )
        if parece_css:
            for variacao in [d, d.replace("'", '"'), d.replace('"', "'")]:
                try:
                    pg.locator(variacao).first.fill(valor, timeout=3000)
                    return f"Preencheu via seletor '{variacao}' com {valor[:30]}"
                except:
                    pass

        for tentativa in [
            lambda: pg.get_by_label(d, exact=False).first.fill(valor, timeout=1500),
            lambda: pg.get_by_placeholder(d, exact=False).first.fill(valor, timeout=1500),
            lambda: pg.locator(f'[name="{d}"]').first.fill(valor, timeout=1500),
            lambda: pg.locator(f'#{d}').first.fill(valor, timeout=1500),
            lambda: pg.locator(f'input[type="{d}"]').first.fill(valor, timeout=1500),
        ]:
            try:
                tentativa()
                return f"Preencheu '{d}' com {valor[:30]}"
            except:
                pass

        for sel_fallback in [
            'textarea[name="q"]',
            'input[name="q"]',
            'input[name="search_query"]',
            'input[type="search"]',
            'input[type="text"]',
            'textarea',
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
        ]:
            try:
                pg.locator(sel_fallback).first.fill(valor, timeout=1500)
                return f"Preencheu (fallback '{sel_fallback}') com {valor[:30]}"
            except:
                pass

        from fuzzywuzzy import fuzz
        candidatos = pg.evaluate("""() => {
            const out = [];
            document.querySelectorAll('input, textarea, select').forEach((el) => {
                const tipo = el.type || el.tagName.toLowerCase();
                if (tipo === 'hidden' || tipo === 'submit' || tipo === 'button' || tipo === 'checkbox' || tipo === 'radio' || tipo === 'file') return;
                let label = '';
                if (el.labels && el.labels[0]) label = el.labels[0].innerText || '';
                out.push({
                    placeholder: el.placeholder || '',
                    label: label,
                    name: el.name || '',
                    id: el.id || '',
                    type: tipo,
                    visivel: el.offsetParent !== null
                });
            });
            return out;
        }""")

        melhor = None
        melhor_score = 0
        for c in candidatos:
            if not c["visivel"]:
                continue
            for campo in [c["placeholder"], c["label"], c["name"], c["id"]]:
                if not campo:
                    continue
                score = fuzz.ratio(d.lower(), campo.lower())
                if score > melhor_score:
                    melhor_score = score
                    melhor = c

        if melhor and melhor_score > 50:
            sel = f'#{melhor["id"]}' if melhor["id"] else f'[name="{melhor["name"]}"]' if melhor["name"] else f'input[type="{melhor["type"]}"]'
            pg.locator(sel).first.fill(valor, timeout=3000)
            return f"Preencheu (fuzzy {melhor_score}%) '{melhor['placeholder'] or melhor['label'] or sel}' com {valor[:30]}"

        return f"Não achei campo: {descricao}"
    except Exception as e:
        return f"Erro: {e}"


def clicar_no_elemento(descricao: str = None, **kwargs):
    try:
        if descricao is None:
            descricao = kwargs.get("elemento") or kwargs.get("texto") or ""
        pg = _garantir_browser()
        d = str(descricao).strip()

        if ("[" in d and "]" in d) or d.startswith("#") or d.startswith("."):
            for variacao in [d, d.replace("'", '"')]:
                try:
                    pg.locator(variacao).first.click(timeout=3000)
                    return f"Clicou via seletor: {variacao}"
                except:
                    pass

        for tentativa in [
            lambda: pg.get_by_text(d, exact=False).first.click(timeout=2000),
            lambda: pg.get_by_role("button", name=d, exact=False).first.click(timeout=2000),
            lambda: pg.get_by_role("link", name=d, exact=False).first.click(timeout=2000),
            lambda: pg.get_by_placeholder(d, exact=False).first.click(timeout=2000),
            lambda: pg.get_by_label(d, exact=False).first.click(timeout=2000),
        ]:
            try:
                tentativa()
                return f"Clicou em: {d}"
            except:
                pass

        from fuzzywuzzy import fuzz
        candidatos = pg.evaluate("""() => {
            const out = [];
            document.querySelectorAll('button, a, [role="button"], input[type="submit"]').forEach((el) => {
                const txt = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim();
                if (!txt) return;
                out.push({texto: txt.slice(0,80), visivel: el.offsetParent !== null});
            });
            return out;
        }""")

        melhor = None
        melhor_score = 0
        for c in candidatos:
            if not c["visivel"]:
                continue
            score = fuzz.ratio(d.lower(), c["texto"].lower())
            if score > melhor_score:
                melhor_score = score
                melhor = c

        if melhor and melhor_score > 60:
            try:
                pg.get_by_text(melhor["texto"], exact=False).first.click(timeout=3000)
                return f"Clicou (fuzzy {melhor_score}%) em '{melhor['texto']}'"
            except:
                pass

        return f"Não achei elemento: {d}"
    except Exception as e:
        return f"Erro: {e}"


def clicar_selector(selector: str = None, **kwargs):
    if not selector:
        selector = kwargs.get("seletor")
    if not selector:
        return "Erro: selector não informado"
    try:
        pg = _garantir_browser()
        pg.wait_for_selector(selector, timeout=20000)
        pg.click(selector, timeout=10000)
        return f"Clicou: {selector}"
    except Exception as e:
        return f"Erro: {e}"


def digitar(texto: str = None, selector: str = None, **kwargs):
    if not texto:
        texto = kwargs.get("valor") or kwargs.get("value")
    if not texto:
        return "⚠️ Texto vazio."
    try:
        pg = _garantir_browser()
        if selector:
            pg.wait_for_selector(selector, timeout=15000)
            pg.fill(selector, texto, timeout=10000)
        else:
            pg.keyboard.type(texto)
        return f"Digitou: {texto}"
    except Exception as e:
        return f"Erro: {e}"


def _norm_tecla(s):
    if not s:
        return s
    mapa = {
        "enter": "Enter", "return": "Enter",
        "tab": "Tab", "espaco": " ", "space": " ",
        "esc": "Escape", "escape": "Escape",
        "backspace": "Backspace", "delete": "Delete",
        "up": "ArrowUp", "cima": "ArrowUp",
        "down": "ArrowDown", "baixo": "ArrowDown",
        "left": "ArrowLeft", "esquerda": "ArrowLeft",
        "right": "ArrowRight", "direita": "ArrowRight",
        "ctrl": "Control", "control": "Control",
        "alt": "Alt", "shift": "Shift",
    }
    return mapa.get(str(s).lower().strip(), s)


def pressionar(tecla: str = None, **kwargs):
    """🌐 BROWSER ONLY: pressiona tecla na PÁGINA web. Pra app desktop use pressionar_tecla."""
    if not tecla:
        tecla = kwargs.get("key") or kwargs.get("tecla_press")
    if not tecla:
        return "Erro: tecla não informada"
    try:
        pg = _garantir_browser()
        t = _norm_tecla(tecla)
        pg.keyboard.press(t)
        return f"Pressionou (browser): {t}"
    except Exception as e:
        return f"Erro: {e}"


def recarregar(**kwargs):
    try:
        pg = _garantir_browser()
        pg.reload()
        return "Página recarregada"
    except Exception as e:
        return f"Erro: {e}"


def voltar(**kwargs):
    try:
        pg = _garantir_browser()
        pg.go_back()
        return "Voltou"
    except Exception as e:
        return f"Erro: {e}"


# ============================================================
# DOWNLOAD (BROWSER E HTTP DIRETO)
# ============================================================

def baixar_arquivo(descricao: str = None, **kwargs):
    r"""
    🌐 BROWSER: Clica em um elemento (texto/seletor) e espera o download.
    Salva o arquivo em C:\Nero\conteudo\downloads com o nome sugerido.
    """
    if not descricao:
        return "Erro: descrição do elemento que dispara o download não informada."
    try:
        pg = _garantir_browser()
        d = str(descricao).strip()

        with pg.expect_download(timeout=30000) as download_info:
            try:
                if ("[" in d and "]" in d) or d.startswith("#") or d.startswith("."):
                    pg.locator(d).first.click(timeout=5000)
                else:
                    pg.get_by_text(d, exact=False).first.click(timeout=5000)
            except Exception:
                pg.get_by_role("button", name=d, exact=False).first.click(timeout=5000)
        
        download = download_info.value
        caminho_final = os.path.join(PASTA_DOWNLOADS, download.suggested_filename)
        download.save_as(caminho_final)
        
        return f"Download concluído: {caminho_final}"

    except Exception as e:
        return f"Erro ao tentar baixar: {e}"


def baixar_imagem_url(url_imagem: str = None, nome_arquivo: str = None, **kwargs):
    """🌐 BROWSER: Baixa uma imagem direto pela URL (sem depender do navegador)"""
    if not url_imagem:
        return "Erro: URL da imagem não informada."
    try:
        # Define o nome do arquivo (se não passou, tenta pegar da URL ou gera um timestamp)
        if not nome_arquivo:
            parsed = urllib.parse.urlparse(url_imagem)
            nome_arquivo = os.path.basename(parsed.path) or f"imagem_{int(time.time())}.jpg"
            if not nome_arquivo.lower().endswith(('.jpg', '.png', '.jpeg', '.webp', '.gif')):
                nome_arquivo += ".jpg"

        caminho_final = os.path.join(PASTA_DOWNLOADS, nome_arquivo)
        
        # Faz o download
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url_imagem, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(caminho_final, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return f"Imagem salva em: {caminho_final}"
    except Exception as e:
        return f"Erro ao baixar imagem: {e}"


# ============================================================
# TECLADO DESKTOP (pyautogui — atua no app ATIVO do Windows)
# ============================================================

def _norm_tecla_desktop(s):
    if not s:
        return s
    mapa = {
        "enter": "enter", "return": "enter", "entrar": "enter",
        "tab": "tab",
        "espaco": "space", "space": "space",
        "esc": "esc", "escape": "esc",
        "backspace": "backspace",
        "delete": "delete", "del": "delete",
        "up": "up", "cima": "up",
        "down": "down", "baixo": "down",
        "left": "left", "esquerda": "left",
        "right": "right", "direita": "right",
        "ctrl": "ctrl", "control": "ctrl",
        "alt": "alt", "shift": "shift",
        "soma": "+", "mais": "+",
        "subtracao": "-", "menos": "-",
        "multiplicacao": "*", "vezes": "*",
        "divisao": "/", "dividir": "/",
        "igual": "=",
    }
    s_low = str(s).lower().strip()
    return mapa.get(s_low, s)


def pressionar_tecla(tecla: str = None, **kwargs):
    """🖥️ DESKTOP ONLY: pressiona tecla no app ATIVO do Windows."""
    if not tecla:
        tecla = kwargs.get("key") or kwargs.get("tecla_press")
    if not tecla:
        return "Erro: tecla não informada"
    try:
        t = _norm_tecla_desktop(tecla)
        pyautogui.press(t)
        return f"Pressionou (desktop): {tecla}"
    except Exception as e:
        return f"Erro: {e}"


def digitar_teclado(texto: str = None, **kwargs):
    """🖥️ DESKTOP ONLY: digita texto no app ATIVO do Windows."""
    if not texto:
        texto = kwargs.get("valor") or kwargs.get("value")
    if not texto:
        return "Erro: texto não informado"
    try:
        pyautogui.typewrite(str(texto), interval=0.05)
        return f"Digitou (desktop): {texto}"
    except Exception as e:
        return f"Erro: {e}"


# ============================================================
# UIA
# ============================================================

def ler_uia(**kwargs):
    try:
        import uiautomation as auto
        janela = auto.GetForegroundControl()
        if not janela:
            return "Nenhuma janela ativa."
        linhas = []

        def walk(ctrl, depth=0):
            if depth > 4 or len(linhas) > 80:
                return
            try:
                nome = ctrl.Name or ""
                tipo = ctrl.ControlTypeName or ""
                if nome and tipo in ("ButtonControl", "EditControl", "MenuItemControl",
                                     "TextControl", "HyperlinkControl", "ComboBoxControl",
                                     "CheckBoxControl", "RadioButtonControl"):
                    linhas.append("  " * depth + f"[{tipo.replace('Control','')}] '{nome[:60]}'")
                for child in ctrl.GetChildren():
                    walk(child, depth + 1)
            except:
                pass

        walk(janela)
        return "\n".join(linhas) if linhas else "Janela sem elementos interativos."
    except Exception as e:
        return f"Erro UIA: {e}"


def clicar_controle(descricao: str = None, **kwargs):
    if not descricao:
        descricao = kwargs.get("nome") or kwargs.get("texto")
    if not descricao:
        return "Erro: descrição não informada"
    try:
        import uiautomation as auto
        janela = auto.GetForegroundControl()
        if not janela:
            return "Nenhuma janela ativa."
        ctrl = janela.Control(Name=descricao)
        if ctrl.Exists(2):
            ctrl.Click()
            return f"Clicou em: {descricao}"
        for c in janela.GetChildren():
            try:
                if descricao.lower() in (c.Name or "").lower():
                    c.Click()
                    return f"Clicou em: {c.Name}"
            except:
                pass
        return f"Não achei: {descricao}"
    except Exception as e:
        return f"Erro: {e}"


# ============================================================
# REGISTRO
# ============================================================

FERRAMENTAS = {
    "lembrar":              {"funcao": lembrar,              "descricao": "Salva um fato permanente", "parametros": {"chave": "chave", "valor": "valor"}},
    "esquecer_fato":        {"funcao": esquecer_fato,        "descricao": "Esquece um fato", "parametros": {"chave": "chave"}},
    "listar_contexto":      {"funcao": listar_contexto,      "descricao": "Lista fatos guardados", "parametros": {}},

    # ===== DESKTOP =====
    "abrir_programa":       {"funcao": abrir_programa,       "descricao": "🖥️ DESKTOP: abre programa. Parâmetro 'nome' (ex: 'calculadora', 'notepad', 'chrome')", "parametros": {"nome": "nome"}},
    "executar_cmd":         {"funcao": executar_cmd,         "descricao": "🖥️ DESKTOP: executa comando no CMD", "parametros": {"comando": "comando"}},
    "bloquear_pc":          {"funcao": bloquear_pc,          "descricao": "🖥️ DESKTOP: bloqueia o PC", "parametros": {}},
    "copiar":               {"funcao": copiar,               "descricao": "🖥️ DESKTOP: Ctrl+C", "parametros": {}},
    "colar":                {"funcao": colar,                "descricao": "🖥️ DESKTOP: Ctrl+V", "parametros": {}},
    "salvar":               {"funcao": salvar,               "descricao": "🖥️ DESKTOP: Ctrl+S", "parametros": {}},
    "salvar_como":          {"funcao": salvar_como,          "descricao": "🖥️ DESKTOP: Salvar como (Ctrl+Shift+S + caminho).", "parametros": {"caminho": "caminho completo"}},
    "pressionar_tecla":     {"funcao": pressionar_tecla,     "descricao": "🖥️ DESKTOP ONLY: pressiona tecla no APP ATIVO do Windows (calculadora, notepad). NÃO use pra browser.", "parametros": {"tecla": "tecla"}},
    "digitar_teclado":      {"funcao": digitar_teclado,      "descricao": "🖥️ DESKTOP ONLY: digita texto no APP ATIVO do Windows. NÃO use pra browser.", "parametros": {"texto": "texto"}},
    "esperar":              {"funcao": esperar,              "descricao": "Espera N segundos", "parametros": {"segundos": "número"}},

    # ===== ARQUIVOS =====
    "listar_pasta":         {"funcao": listar_pasta,         "descricao": "Lista arquivos", "parametros": {"caminho": "caminho"}},
    "criar_pasta":          {"funcao": criar_pasta,          "descricao": "Cria pasta", "parametros": {"caminho": "caminho"}},
    "procurar_pasta":       {"funcao": procurar_pasta,       "descricao": "Procura pasta", "parametros": {"nome": "nome", "raiz": "opcional"}},
    "criar_arquivo":        {"funcao": criar_arquivo,        "descricao": "Cria arquivo texto. Se só passar nome, salva em C:\\Nero\\conteudo\\txt", "parametros": {"caminho": "nome ou caminho", "conteudo": "texto"}},
    "escrever_arquivo":     {"funcao": escrever_arquivo,     "descricao": "Escreve/sobrescreve arquivo", "parametros": {"caminho": "caminho", "conteudo": "texto"}},
    "anexar_arquivo":       {"funcao": anexar_arquivo,       "descricao": "Anexa linha no fim", "parametros": {"caminho": "caminho", "conteudo": "texto"}},
    "ler_arquivo":          {"funcao": ler_arquivo,          "descricao": "Lê arquivo", "parametros": {"caminho": "caminho"}},
    "apagar_caminho":       {"funcao": apagar_caminho,       "descricao": "Apaga arquivo ou pasta", "parametros": {"caminho": "caminho"}},
    "mover":                {"funcao": mover,                "descricao": "Move arquivo ou pasta", "parametros": {"origem": "origem", "destino": "destino"}},
    "renomear":             {"funcao": renomear,             "descricao": "Renomeia", "parametros": {"antigo": "antigo", "novo": "novo"}},

    # ===== TELA / OCR (desktop) =====
    "tirar_print":          {"funcao": tirar_print,          "descricao": "🖥️ DESKTOP: print da tela (vai pra C:\\Nero\\conteudo\\prints)", "parametros": {"caminho": "opcional"}},
    "ler_tela":             {"funcao": ler_tela,             "descricao": "🖥️ DESKTOP: OCR da tela inteira (só apps desktop)", "parametros": {}},
    "ler_tela_estruturada": {"funcao": ler_tela_estruturada, "descricao": "🖥️ DESKTOP: OCR com posições (só apps desktop)", "parametros": {}},
    "clicar_em_texto":      {"funcao": clicar_em_texto,      "descricao": "🖥️ DESKTOP: clique por OCR (só apps desktop)", "parametros": {"texto": "texto"}},

    # ===== CLIPBOARD =====
    "ler_clipboard":        {"funcao": ler_clipboard,        "descricao": "Lê clipboard", "parametros": {}},
    "escrever_clipboard":   {"funcao": escrever_clipboard,   "descricao": "Escreve no clipboard", "parametros": {"texto": "texto"}},
    "limpar_clipboard":     {"funcao": limpar_clipboard,     "descricao": "Limpa clipboard", "parametros": {}},

    # ===== BROWSER =====
    "navegar":              {"funcao": navegar,              "descricao": "🌐 BROWSER: abre URL", "parametros": {"url": "URL"}},
    "url_atual":            {"funcao": url_atual,            "descricao": "🌐 BROWSER: retorna URL atual", "parametros": {}},
    "ler_pagina_estruturada": {"funcao": ler_pagina_estruturada, "descricao": "🌐 BROWSER: OLHO que lê a página (campos, botões, links)", "parametros": {}},
    "ler_texto_pagina":     {"funcao": ler_texto_pagina,     "descricao": "🌐 BROWSER: lê texto visível da página", "parametros": {}},
    "clicar_no_elemento":   {"funcao": clicar_no_elemento,   "descricao": "🌐 BROWSER: clica em elemento (texto/role). NÃO use pra desktop.", "parametros": {"descricao": "descrição"}},
    "preencher_campo":      {"funcao": preencher_campo,      "descricao": "🌐 BROWSER: preenche campo. Parâmetro 'descricao' = label/seletor CSS. Parâmetro 'valor' = texto (NÃO use 'value'). NÃO use pra desktop.", "parametros": {"descricao": "label ou seletor CSS", "valor": "texto a digitar"}},
    "clicar_selector":      {"funcao": clicar_selector,      "descricao": "🌐 BROWSER: clica em seletor CSS. NÃO use pra desktop.", "parametros": {"selector": "seletor"}},
    "digitar":              {"funcao": digitar,              "descricao": "🌐 BROWSER: digita em campo da PÁGINA web. NÃO use pra desktop.", "parametros": {"texto": "texto", "selector": "opcional"}},
    "pressionar":           {"funcao": pressionar,           "descricao": "🌐 BROWSER: pressiona tecla na PÁGINA web. Pra app desktop use pressionar_tecla.", "parametros": {"tecla": "tecla"}},
    "recarregar":           {"funcao": recarregar,           "descricao": "🌐 BROWSER: recarrega", "parametros": {}},
    "voltar":               {"funcao": voltar,               "descricao": "🌐 BROWSER: volta", "parametros": {}},
    "fechar_browser":       {"funcao": fechar_browser,       "descricao": "🌐 BROWSER: fecha navegador", "parametros": {}},
    
    # ===== DOWNLOAD (BROWSER E HTTP DIRETO) =====
    "baixar_arquivo":       {"funcao": baixar_arquivo,       "descricao": "🌐 BROWSER: clica em um elemento e baixa o arquivo para C:\\Nero\\conteudo\\downloads.", "parametros": {"descricao": "texto ou seletor do botão de download"}},
    "baixar_imagem_url":    {"funcao": baixar_imagem_url,    "descricao": "🌐 BROWSER: baixa uma imagem a partir da URL direta (src) e salva em C:\\Nero\\conteudo\\downloads.", "parametros": {"url_imagem": "URL direta da imagem", "nome_arquivo": "opcional"}},

    # ===== UIA (Windows accessibility) =====
    "ler_uia":              {"funcao": ler_uia,              "descricao": "🖥️ DESKTOP: OLHO que lê árvore do Windows (janela ativa)", "parametros": {}},
    "clicar_controle":      {"funcao": clicar_controle,      "descricao": "🖥️ DESKTOP: clica em controle do Windows pelo nome", "parametros": {"descricao": "descrição"}},
}