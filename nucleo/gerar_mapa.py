"""
Gera o mapa_rag.md a partir das trajetórias salvas.
Uso: python gerar_mapa.py
Ou é chamado pelo agente.py no boot.
"""
import os
import json

TRAJ_DIR = r"C:\Nero\trajetorias"
MAPA_FILE = r"C:\Nero\mapa_rag.md"


def gerar_mapa():
    if not os.path.exists(TRAJ_DIR):
        print(f"❌ Pasta não existe: {TRAJ_DIR}")
        return

    trajs = []
    for arq in os.listdir(TRAJ_DIR):
        if not arq.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(TRAJ_DIR, arq), encoding="utf-8"))
            trajs.append(d)
        except Exception as e:
            print(f"⚠️ Erro lendo {arq}: {e}")

    if not trajs:
        print("📭 Nenhuma trajetória.")
        return

    micros = sorted([t for t in trajs if t.get("nome", "").startswith("micro_")], key=lambda x: x["nome"])
    compostas = sorted([t for t in trajs if not t.get("nome", "").startswith("micro_")], key=lambda x: x["nome"])

    linhas = ["# MAPA DE TRAJETÓRIAS\n"]
    linhas.append(f"**Total:** {len(trajs)} trajetórias ({len(micros)} micros, {len(compostas)} compostas)\n")

    if micros:
        linhas.append("\n## 🔧 MICRO-TRAJETÓRIAS\n")
        for t in micros:
            linhas.append(_bloco(t))
    if compostas:
        linhas.append("\n## 📦 TRAJETÓRIAS COMPOSTAS\n")
        for t in compostas:
            linhas.append(_bloco(t, composta=True))

    with open(MAPA_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"🗺️ Mapa: {MAPA_FILE}")
    print(f"   {len(trajs)} trajetórias ({len(micros)} micros, {len(compostas)} compostas)")


def _bloco(t, composta=False):
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


if __name__ == "__main__":
    gerar_mapa()