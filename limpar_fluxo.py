# ============================================================
# limpar_fluxo.py - Apaga os JSONs de fluxo para recoleta
# Execute: python limpar_fluxo.py
# ============================================================

from pathlib import Path

DATA_DIR = Path(__file__).parent / "dados_fluxo"

arquivos = list(DATA_DIR.glob("*.json"))
if not arquivos:
    print("Nenhum arquivo encontrado em dados_fluxo/")
else:
    for f in arquivos:
        f.unlink()
        print(f"  Removido: {f.name}")
    print(f"\n{len(arquivos)} arquivo(s) removido(s).")
    print("Agora clique em 'Atualizar' no dashboard para recoltar.")
