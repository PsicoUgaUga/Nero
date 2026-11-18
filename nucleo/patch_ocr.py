"""Patch: faz ler_tela focar na JANELA ATIVA em vez da tela toda.
Roda 1x: python patch_ocr.py
"""
import re

PATH = r"C:\Nero\ferramentas.py"

with open(PATH, encoding="utf-8") as f:
    src = f.read()

# --- 1. Adiciona helper _filtrar_ocr logo antes de def ler_tela ---
helper = '''
def _filtrar_ocr(texto):
    """Remove linhas que são claramente do PRÓPRIO agente/terminal."""
    if not texto:
        return texto
    ruins = (
        "Nero - Agente", "Nero- Agente", "Buscando trajetórias",
        "RAG híbrido", "Zona BAIXA", "Zona CINZENTA", "Zona ALTA",
        "Digite 'ajuda'", "Consultando treinador", "Plano com ",
        "executar_ferramenta", "usar_trajetoria", "Abrindo calc",
        "Pedido treinador", "planner.py", "rag.py", "agente.py",
        "20itens", "Q Pesquisar", "Arquivo Fonte",
    )
    linhas = []
    for l in texto.split("\\n"):
        s = l.strip()
        if not s:
            continue
        if any(r in s for r in ruins):
            continue
        if re.match(r"^-+\\s*Passo\\s+\\d+", s):
            continue
        if re.match(r"^>\\s", s):
            continue
        linhas.append(s)
    return "\\n".join(linhas) if linhas else "(nada legível na janela ativa)"


'''

# --- 2. Substitui as 3 funções de OCR ---

nova_ler_tela = '''def ler_tela(**kwargs):
    """🖥️ DESKTOP: OCR da JANELA ATIVA (não do desktop inteiro)."""
    try:
        import uiautomation as auto
        janela = auto.GetForegroundControl()
        if janela:
            rect = janela.BoundingRectangle
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 200 and h > 200:
                img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
                texto = pytesseract.image_to_string(img, lang="por")
                return _filtrar_ocr(texto)[:2000]
        img = ImageGrab.grab()
        return _filtrar_ocr(pytesseract.image_to_string(img, lang="por"))[:2000]
    except Exception as e:
        return f"Erro OCR: {e}"


def ler_tela_estruturada(**kwargs):
    """🖥️ DESKTOP: OCR com posições, focado na JANELA ATIVA."""
    try:
        import uiautomation as auto
        img = None
        janela = auto.GetForegroundControl()
        if janela:
            rect = janela.BoundingRectangle
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 200 and h > 200:
                img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
        if img is None:
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
        return "\\n".join(linhas[:80]) if linhas else "Tela sem texto legível."
    except Exception as e:
        return f"Erro OCR: {e}"


def clicar_em_texto(texto: str = None, **kwargs):
    """🖥️ DESKTOP: clica por OCR, focado na JANELA ATIVA."""
    if not texto:
        return "Erro: texto não informado"
    try:
        from fuzzywuzzy import fuzz
        import uiautomation as auto
        img = None
        offset_x = offset_y = 0
        janela = auto.GetForegroundControl()
        if janela:
            rect = janela.BoundingRectangle
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 200 and h > 200:
                img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
                offset_x, offset_y = rect.left, rect.top
        if img is None:
            img = ImageGrab.grab()
        dados = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="por")
        for i, t in enumerate(dados["text"]):
            if not t.strip():
                continue
            if int(dados["conf"][i]) < 60:
                continue
            if fuzz.ratio(texto.lower(), t.lower()) > 80:
                x = dados["left"][i] + dados["width"][i] // 2 + offset_x
                y = dados["top"][i] + dados["height"][i] // 2 + offset_y
                pyautogui.click(x, y)
                return f"Clicou em '{t}' em ({x},{y})"
        return f"Não achei: {texto}"
    except Exception as e:
        return f"Erro OCR: {e}"


'''

# Substitui cada função (do "def" até a próxima "def " ou "# ===")
def substituir_funcao(src, nome, nova):
    pattern = rf"(def {nome}\(.*?\n)(?=\n\ndef |\n\n# =|$)"
    novo, n = re.subn(pattern, nova, src, count=1, flags=re.DOTALL)
    if n == 0:
        print(f"⚠️ Não achei '{nome}' pra substituir")
    else:
        print(f"✅ '{nome}' substituída")
    return novo

src = substituir_funcao(src, "ler_tela", nova_ler_tela)

# ler_tela_estruturada e clicar_em_texto vêm juntas na "nova_ler_tela"
# (a string contém as 3). Precisamos substituir as antigas primeiro.
# Estratégia: apaga as 3 antigas e injeta o bloco novo.

# Remove as 3 funções antigas
for fn in ("ler_tela", "ler_tela_estruturada", "clicar_em_texto"):
    pattern = rf"def {fn}\(.*?\n(?=\n\ndef |\n\n# =|$)"
    src = re.sub(pattern, "", src, count=1, flags=re.DOTALL)

# Injeta o bloco novo + helper antes do próximo "# ==="
marcador = "# ============================================================\n# CLIPBOARD"
if marcador in src:
    src = src.replace(marcador, helper + nova_ler_tela + marcador, 1)
    print("✅ Bloco novo injetado")
else:
    print("⚠️ Não achei marcador CLIPBOARD. Salvando mesmo assim...")

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("\n🎉 Patch aplicado. Roda o agente de novo.")