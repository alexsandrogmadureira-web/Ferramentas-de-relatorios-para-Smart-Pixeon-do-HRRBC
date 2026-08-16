# ============================================================
# cirurgias_hospital.py - Produção Cirúrgica (tela)
# ============================================================

from datetime import date, timedelta
from dash import Dash, html, dcc, Input, Output, State
from config import NOME_HOSPITAL
from cirurgias import get_producao_completa

def _card(valor, rotulo, cor="#1565C0"):
    """Monta um card simples de indicador (número + descrição)."""
    return html.Div([
        html.Div(str(valor), className="ci-card-numero", style={"color": cor}),
        html.Div(rotulo, className="ci-card-rotulo"),
    ], className="ci-card")

def criar_dash_cirurgias(server):
    app = Dash(
        __name__,
        server=server,
        url_base_pathname="/cirurgias/",
        title=f"Cirurgias — {NOME_HOSPITAL}",
    )

    hoje = date.today()
    inicio_padrao = hoje - timedelta(days=30)

    app.layout = html.Div([

        html.Div([
            html.Div([
                html.A("← Menu", href="/menu", className="ci-btn-voltar"),
                html.Div([
                    html.Span("🔪", style={"fontSize": "20px"}),
                    html.Span("Produção Cirúrgica", className="ci-header-titulo"),
                ], className="ci-header-centro"),
                html.Div(NOME_HOSPITAL, className="ci-header-hospital"),
            ], className="ci-header-inner"),
        ], className="ci-header"),

        html.Div([

            html.Div([
                html.Label("Período:", className="ci-label"),
                dcc.DatePickerRange(
                    id="ci-periodo",
                    start_date=inicio_padrao,
                    end_date=hoje,
                    display_format="DD/MM/YYYY",
                ),
                dcc.Input(id="ci-filtro-sus", type="text",
                          placeholder="Código(s) SUS, separados por vírgula",
                          style={"width": "260px"}),
                dcc.Dropdown(id="ci-filtro-especialidade", placeholder="Especialidade",
                             style={"width": "220px"}),
                dcc.Dropdown(id="ci-filtro-cirurgiao", placeholder="Cirurgião",
                             style={"width": "260px"}),
                html.Button("Buscar", id="ci-btn-buscar", className="ci-btn-buscar", n_clicks=0),
            ], className="ci-filtros"),

            dcc.Store(id="ci-store-dados"),

            dcc.Loading(
                html.Div(id="ci-cards", className="ci-cards-row"),
            ),

            dcc.Loading(
                html.Div(id="ci-tabela"),
            ),

        ], className="ci-conteudo"),

    ], className="ci-root")

    @app.callback(
        Output("ci-store-dados", "data"),
        Output("ci-filtro-especialidade", "options"),
        Output("ci-filtro-cirurgiao", "options"),
        Input("ci-btn-buscar", "n_clicks"),
        State("ci-periodo", "start_date"),
        State("ci-periodo", "end_date"),
        State("ci-filtro-sus", "value"),
    )
    def buscar(n_clicks, data_ini, data_fim, texto_sus):
        if not data_ini or not data_fim:
            return [], [], []

        ini = f"{data_ini} 00:00:00"
        fim_dt = date.fromisoformat(data_fim) + timedelta(days=1)
        fim = fim_dt.strftime("%Y-%m-%d 00:00:00")

        cods_sus = None
        if texto_sus:
            cods_sus = [c.strip() for c in texto_sus.split(",") if c.strip()]

        cirurgias = get_producao_completa(ini, fim, cods_sus)

     
        especialidades = sorted({c["cirurgiao_especialidade_cbo"] for c in cirurgias if c["cirurgiao_especialidade_cbo"]})
        cirurgioes     = sorted({c["cirurgiao_nome"] for c in cirurgias if c["cirurgiao_nome"]})

        opcoes_especialidade = [{"label": e, "value": e} for e in especialidades]
        opcoes_cirurgiao     = [{"label": c, "value": c} for c in cirurgioes]

        return cirurgias, opcoes_especialidade, opcoes_cirurgiao

    @app.callback(
        Output("ci-cards",  "children"),
        Output("ci-tabela", "children"),
        Input("ci-store-dados", "data"),
        Input("ci-filtro-especialidade", "value"),
        Input("ci-filtro-cirurgiao", "value"),
    )
    def filtrar(cirurgias, especialidade, cirurgiao):
        if not cirurgias:
            return [], html.Div("Nenhum dado. Clique em Buscar.", className="ci-msg")

        filtradas = cirurgias
        if especialidade:
            filtradas = [c for c in filtradas if c["cirurgiao_especialidade_cbo"] == especialidade]
        if cirurgiao:
            filtradas = [c for c in filtradas if c["cirurgiao_nome"] == cirurgiao]

        total    = len(filtradas)
        urgencia = sum(1 for c in filtradas if c["cirurgia_urgencia_sn"] == "U")
        eletiva  = total - urgencia

        cards = [
            _card(total, "Total de Cirurgias"),
            _card(urgencia, "Urgência", cor="#C62828"),
            _card(eletiva, "Eletiva", cor="#2E7D32"),
        ]

        linhas = [
            html.Tr([
                html.Td(c["cirurgia_dt_hr_inicio"]),
                html.Td(c["paciente_nome"]),
                html.Td(c["procedimento_nome"]),
                html.Td(c["cirurgiao_nome"]),
                html.Td(c["cirurgia_urgencia_sn"]),
            ])
            for c in filtradas
        ]
        tabela = html.Table([
            html.Thead(html.Tr([
                html.Th("Data/Hora"), html.Th("Paciente"), html.Th("Procedimento"),
                html.Th("Cirurgião"), html.Th("Urg."),
            ])),
            html.Tbody(linhas),
        ], className="ci-tabela-dados")

        return cards, tabela

    app.index_string = _shell()

    return app

def _shell():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{%title%}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  {%favicon%}{%css%}
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{--pri:#1565C0;--fundo:#F0F4F8;--card:#fff;--borda:#E2E8F0;--texto:#1A237E;--sub:#546E7A;--verde:#2E7D32;--vermelho:#C62828}
    html,body{background:var(--fundo);color:var(--texto);font-family:'Inter',sans-serif;min-height:100vh}
    .ci-root{min-height:100vh;display:flex;flex-direction:column}
    .ci-header{background:var(--pri);padding:0 28px;height:52px;display:flex;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.15);flex-shrink:0}
    .ci-header-inner{display:flex;align-items:center;justify-content:space-between;width:100%}
    .ci-btn-voltar{color:#BBDEFB;font-size:13px;text-decoration:none;padding:5px 12px;border:1px solid rgba(255,255,255,.25);border-radius:7px}
    .ci-btn-voltar:hover{background:rgba(255,255,255,.15);color:#fff}
    .ci-header-centro{display:flex;align-items:center;gap:8px;color:#fff;font-size:15px;font-weight:600}
    .ci-header-hospital{color:#90CAF9;font-size:12px}
    .ci-conteudo{flex:1;padding:20px 28px;display:flex;flex-direction:column;gap:16px}
    .ci-filtros{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .ci-label{font-size:13px;color:var(--sub);font-weight:500}
    .ci-btn-buscar{background:var(--pri);color:#fff;border:none;border-radius:8px;padding:8px 18px;font-family:'Inter',sans-serif;font-size:13px;font-weight:600;cursor:pointer}
    .ci-btn-buscar:hover{background:#0D47A1}
    .ci-cards-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
    .ci-card{background:var(--card);border:1px solid var(--borda);border-radius:12px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
    .ci-card-numero{font-size:28px;font-weight:700;line-height:1}
    .ci-card-rotulo{font-size:12px;color:var(--sub);margin-top:4px}
    .ci-msg{font-size:13px;color:var(--sub);padding:20px;text-align:center}
    .ci-tabela-dados{border-collapse:collapse;width:100%;font-size:12px;background:var(--card);border-radius:12px;overflow:hidden}
    .ci-tabela-dados th{background:#F8FAFC;padding:10px 8px;border-bottom:2px solid var(--borda);font-weight:600;color:var(--sub);font-size:11px;text-transform:uppercase;text-align:left}
    .ci-tabela-dados td{padding:8px;border-bottom:1px solid #F1F5F9}
  </style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""