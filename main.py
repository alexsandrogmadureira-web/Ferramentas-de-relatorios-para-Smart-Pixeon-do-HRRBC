# ============================================================
# main.py - BID Hospital · Ponto de entrada
# ============================================================

from server import server
from dashboard import criar_dash
from taxa_ocupacao import criar_dash_taxa
from pacientes_internados import criar_dash_pacientes
from fluxo_hospital import criar_dash_fluxo_hospital
from cirurgias_hospital import criar_dash_cirurgias
from config import PORTA, NOME_HOSPITAL

criar_dash(server)
criar_dash_taxa(server)
criar_dash_pacientes(server)
criar_dash_fluxo_hospital(server)
criar_dash_cirurgias(server)

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  BID Hospital")
    print(f"  {NOME_HOSPITAL}")
    print(f"  Acesse: http://127.0.0.1:{PORTA}")
    print(f"{'='*50}\n")
    server.run(host="0.0.0.0", port=PORTA, debug=False)
