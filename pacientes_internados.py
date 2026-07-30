# ============================================================
# pacientes_internados.py - Dashboard de Pacientes Internados
# ============================================================

from datetime import date, datetime, timedelta

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from database import executar
from queries_pacientes import SQL_PACIENTES_ATUAL, SQL_PACIENTES_PERIODO

C = {
    "primaria":  "#1565C0",
    "sec":       "#0288D1",
    "fundo":     "#F0F4F8",
    "card":      "#FFFFFF",
    "borda":     "#E2E8F0",
    "texto":     "#1A237E",
    "sub":       "#546E7A",
    "verde":     "#2E7D32",
    "amarelo":   "#F57F17",
    "vermelho":  "#C62828",
    "vd_claro":  "#E8F5E9",
    "vm_claro":  "#FFEBEE",
}


def _fmt_data(val):
    if not val or str(val) in ("None", "nan", "NaT", ""):
        return "—"
    try:
        return datetime.strptime(str(val)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except:
        return str(val)[:16]


def _calcular_dias(admissao):
    if not admissao or str(admissao) in ("None", "nan", "NaT", ""):
        return "—"
    try:
        adm = datetime.strptime(str(admissao)[:19], "%Y-%m-%d %H:%M:%S")
        dias = (datetime.now() - adm).days
        return f"{dias}d"
    except:
        return "—"


def _cor_dias(admissao):
    """Cor baseada no tempo de internação."""
    try:
        adm = datetime.strptime(str(admissao)[:19], "%Y-%m-%d %H:%M:%S")
        dias = (datetime.now() - adm).days
        if dias >= 30: return C["vermelho"]
        if dias >= 15: return C["amarelo"]
        return C["texto"]
    except:
        return C["texto"]


def criar_dash_pacientes(server):
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/pacientes/",
        suppress_callback_exceptions=True,
        title="Pacientes Internados — HRRBC",
    )

    hoje = date.today()

    app.layout = html.Div([
        dcc.Store(id="pac-store-modo",   data="atual"),
        dcc.Store(id="pac-store-setor",  data=None),
        dcc.Store(id="pac-store-dados",  data={}),
        dcc.Interval(id="pac-intervalo", interval=5*60*1000, n_intervals=0),

        # ── Header ────────────────────────────────────────
        html.Div([
            html.Div([
                html.A("← Voltar ao Menu", href="/menu", className="pac-btn-voltar"),
                html.Div([
                    html.Span("🛏", style={"fontSize": "20px"}),
                    html.Span("Pacientes Internados", className="pac-header-titulo"),
                ], className="pac-header-centro"),
                html.Div("Hospital Regional Ruy de Barros Correia", className="pac-header-hospital"),
            ], className="pac-header-inner"),
        ], className="pac-header"),

        # ── Toolbar ───────────────────────────────────────
        html.Div([
            html.Div([
                # Modo: Atual ou Por Período
                html.Div([
                    html.Button("👥 Internados Agora", id="pac-btn-atual",
                                className="pac-modo-btn pac-modo-ativo", n_clicks=0),
                    html.Button("📅 Por Período", id="pac-btn-periodo",
                                className="pac-modo-btn", n_clicks=0),
                ], className="pac-modo-group"),

                # Filtros de período (oculto no modo atual)
                html.Div([
                    html.Label("De:", className="pac-label"),
                    dcc.Input(id="pac-data-ini", type="date",
                              value=(hoje - timedelta(days=1)).isoformat(),
                              className="pac-input-data"),
                    html.Label("Até:", className="pac-label"),
                    dcc.Input(id="pac-data-fim", type="date",
                              value=hoje.isoformat(),
                              className="pac-input-data"),
                    html.Button("🔍 Buscar", id="pac-btn-buscar",
                                className="pac-btn-buscar", n_clicks=0),
                ], id="pac-filtro-periodo", style={"display": "none"},
                   className="pac-filtro-periodo"),
            ], className="pac-toolbar-left"),

            html.Div([
                html.Div(id="pac-resumo-toolbar", className="pac-resumo-toolbar"),
                html.Button([html.Span("↻ "), "Atualizar"], id="pac-btn-atualizar",
                            className="pac-btn-atualizar", n_clicks=0),
            ], className="pac-toolbar-right"),
        ], className="pac-toolbar"),

        html.Div(id="pac-msg", className="pac-msg"),

        # ── Abas de setores ───────────────────────────────
        html.Div(id="pac-abas-container", className="pac-abas-container"),

        # ── Conteúdo do setor selecionado ─────────────────
        html.Div(id="pac-conteudo-setor", className="pac-conteudo"),

        # Rodapé
        html.Div([
            html.Span("Dados originados do sistema SMART Pixeon — Somente leitura"),
            html.Span(id="pac-rodape-hora"),
        ], className="pac-rodape"),

    ], className="pac-root")

    app.index_string = _shell()

    # ── Alternar modo ─────────────────────────────────────
    @app.callback(
        Output("pac-store-modo",      "data"),
        Output("pac-btn-atual",       "className"),
        Output("pac-btn-periodo",     "className"),
        Output("pac-filtro-periodo",  "style"),
        Input("pac-btn-atual",    "n_clicks"),
        Input("pac-btn-periodo",  "n_clicks"),
        State("pac-store-modo",   "data"),
        prevent_initial_call=True,
    )
    def alternar_modo(n_atual, n_periodo, modo_atual):
        ctx = dash.callback_context
        if "pac-btn-periodo" in ctx.triggered[0]["prop_id"] and n_periodo:
            return "periodo", "pac-modo-btn", "pac-modo-btn pac-modo-ativo", {"display": "flex"}
        return "atual", "pac-modo-btn pac-modo-ativo", "pac-modo-btn", {"display": "none"}

    # ── Carregar dados ────────────────────────────────────
    @app.callback(
        Output("pac-store-dados",      "data"),
        Output("pac-abas-container",   "children"),
        Output("pac-resumo-toolbar",   "children"),
        Output("pac-msg",              "children"),
        Output("pac-store-setor",      "data"),
        Output("pac-rodape-hora",      "children"),
        Input("pac-btn-atualizar",     "n_clicks"),
        Input("pac-btn-buscar",        "n_clicks"),
        Input("pac-intervalo",         "n_intervals"),
        State("pac-store-modo",        "data"),
        State("pac-data-ini",          "value"),
        State("pac-data-fim",          "value"),
        State("pac-store-setor",       "data"),
    )
    def carregar_dados(n_atu, n_bus, _, modo, data_ini, data_fim, setor_atual):
        msg = ""

        if modo == "atual":
            df = executar(SQL_PACIENTES_ATUAL())
        else:
            ini = f"{data_ini} 00:00:00" if data_ini else ""
            fim = f"{data_fim} 23:59:59" if data_fim else ""
            if not ini or not fim:
                return {}, [], "", "Selecione as datas.", setor_atual, ""
            df = executar(SQL_PACIENTES_PERIODO(ini, fim))

        if df.empty:
            return {}, [html.Div("Nenhum dado encontrado.", className="pac-vazio")], "", msg, None, ""

        # Agrupa por setor
        dados = {}
        for _, row in df.iterrows():
            cod  = str(row.get("str_cod", "")).strip()
            nome = str(row.get("setor",   "")).strip().upper()
            if not cod: continue
            dados.setdefault(cod, {"nome": nome, "pacientes": []})
            dados[cod]["pacientes"].append(dict(row))

        # Ordena setores por nome
        setores_ord = sorted(dados.items(), key=lambda x: x[1]["nome"])

        # Primeiro setor selecionado
        primeiro = setor_atual if setor_atual and setor_atual in dados else (setores_ord[0][0] if setores_ord else None)

        # Monta abas
        total_pac = sum(len(d["pacientes"]) for d in dados.values())
        abas = []
        for cod, d in setores_ord:
            qtd   = len(d["pacientes"])
            ativo = cod == primeiro
            cor_badge = C["vermelho"] if qtd >= 10 else C["amarelo"] if qtd >= 5 else C["verde"]
            abas.append(html.Button([
                html.Span(d["nome"].title(), className="pac-aba-nome"),
                html.Span(str(qtd), className="pac-aba-badge",
                          style={"background": cor_badge}),
            ],
                id={"type": "pac-aba", "cod": cod},
                className=f"pac-aba {'pac-aba-ativa' if ativo else ''}",
                n_clicks=0,
            ))

        resumo = html.Div([
            html.Span(f"🏥 {len(dados)} setores", className="pac-resumo-item"),
            html.Span(f"👥 {total_pac} pacientes", className="pac-resumo-item"),
        ])

        hora = f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        return dados, abas, resumo, msg, primeiro, hora

    # ── Selecionar aba ────────────────────────────────────
    @app.callback(
        Output("pac-conteudo-setor",  "children"),
        Output("pac-store-setor",     "data", allow_duplicate=True),
        Output({"type": "pac-aba", "cod": dash.ALL}, "className"),
        Input({"type": "pac-aba", "cod": dash.ALL}, "n_clicks"),
        State({"type": "pac-aba", "cod": dash.ALL}, "id"),
        State("pac-store-dados",  "data"),
        State("pac-store-modo",   "data"),
        prevent_initial_call=True,
    )
    def selecionar_aba(n_clicks, ids, dados, modo):
        ctx = dash.callback_context
        if not ctx.triggered or not any(n_clicks):
            return dash.no_update, dash.no_update, [dash.no_update] * len(ids)

        import json as _json
        try:
            prop = ctx.triggered[0]["prop_id"].split(".")[0]
            id_dict = _json.loads(prop)
            cod = id_dict["cod"]
        except:
            return dash.no_update, dash.no_update, [dash.no_update] * len(ids)

        classes = [f"pac-aba {'pac-aba-ativa' if i['cod'] == cod else ''}" for i in ids]
        return _render_setor(dados, cod, modo), cod, classes

    # ── Render inicial ────────────────────────────────────
    @app.callback(
        Output("pac-conteudo-setor", "children", allow_duplicate=True),
        Input("pac-store-setor",     "data"),
        State("pac-store-dados",     "data"),
        State("pac-store-modo",      "data"),
        prevent_initial_call=True,
    )
    def render_inicial(cod, dados, modo):
        if not cod or not dados:
            return html.Div("Selecione um setor.", className="pac-vazio")
        return _render_setor(dados, cod, modo)

    return app


def _render_setor(dados, cod, modo):
    """Renderiza a tabela de pacientes do setor selecionado."""
    if not dados or cod not in dados:
        return html.Div("Setor não encontrado.", className="pac-vazio")

    d    = dados[cod]
    nome = d["nome"].title()
    pacs = d["pacientes"]

    if not pacs:
        return html.Div([
            html.H2(nome, className="pac-setor-titulo"),
            html.Div("Nenhum paciente neste setor.", className="pac-vazio"),
        ])

    # Cabeçalho da tabela
    if modo == "atual":
        colunas = ["Leito", "Paciente", "Prontuário", "Registro", "Admissão", "Dias", "Convênio", "Médico", "Tipo"]
    else:
        colunas = ["Leito", "Paciente", "Prontuário", "Registro", "Entrada", "Saída", "Convênio"]

    linhas = []
    for p in sorted(pacs, key=lambda x: str(x.get("leito") or x.get("loc_cod", ""))):
        adm  = p.get("admissao", "")
        dias = _calcular_dias(adm)
        cor  = _cor_dias(adm)

        if modo == "atual":
            leito_status = str(p.get("leito_status","")).strip()
            leito_nome   = str(p.get("leito","")).strip() or str(p.get("loc_cod",""))
            pac_nome     = str(p.get("paciente","")).strip().title()
            vago         = not pac_nome or pac_nome == ""
            linhas.append(html.Tr([
                html.Td(leito_nome,                    className="pac-td-leito"),
                html.Td(pac_nome if not vago else html.Span("— VAGO —", style={"color":"#90CAF9","fontStyle":"italic"}),
                        className="pac-td-pac"),
                html.Td(str(p.get("prontuario","") or "—"), className="pac-td-num"),
                html.Td(str(p.get("registro","")   or "—"), className="pac-td-num"),
                html.Td(_fmt_data(adm),                className="pac-td-data"),
                html.Td(dias, className="pac-td-dias", style={"color": cor, "fontWeight":"600"}),
                html.Td(str(p.get("convenio","")   or "—"), className="pac-td-conv"),
                html.Td(str(p.get("medico","")     or "—").title(), className="pac-td-med"),
                html.Td(str(p.get("tipo_internacao","") or "—"), className="pac-td-tipo"),
            ], className="pac-tr-vago" if vago else ""))
        else:
            linhas.append(html.Tr([
                html.Td(str(p.get("loc_cod","") or "—"), className="pac-td-leito"),
                html.Td(str(p.get("paciente","") or "—").title(), className="pac-td-pac"),
                html.Td(str(p.get("prontuario","") or "—"), className="pac-td-num"),
                html.Td(str(p.get("registro","")   or "—"), className="pac-td-num"),
                html.Td(_fmt_data(p.get("admissao","")),   className="pac-td-data"),
                html.Td(_fmt_data(p.get("alta","")),       className="pac-td-data"),
                html.Td(str(p.get("convenio","")   or "—"), className="pac-td-conv"),
            ]))

    thead = html.Thead(html.Tr([html.Th(c) for c in colunas]))
    tbody = html.Tbody(linhas)

    # Legenda de dias (apenas modo atual)
    legenda = html.Div([
        html.Span([html.Span(className="pac-leg-dot", style={"background":C["verde"]}),   " < 15 dias"]),
        html.Span([html.Span(className="pac-leg-dot", style={"background":C["amarelo"]}), " 15–29 dias"]),
        html.Span([html.Span(className="pac-leg-dot", style={"background":C["vermelho"]}), " ≥ 30 dias"]),
    ], className="pac-legenda") if modo == "atual" else None

    return html.Div([
        html.Div([
            html.Div([
                html.H2(nome, className="pac-setor-titulo"),
                html.Span(f"{len(pacs)} paciente(s)", className="pac-setor-count"),
            ], className="pac-setor-header-left"),
            legenda,
        ], className="pac-setor-header"),
        html.Div(
            html.Table([thead, tbody], className="pac-tabela"),
            className="pac-tabela-wrap",
        ),
    ])


def _shell():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{%title%}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  {%favicon%}{%css%}
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{--pri:#1565C0;--fundo:#F0F4F8;--card:#fff;--borda:#E2E8F0;--texto:#1A237E;--sub:#546E7A;--verde:#2E7D32;--amarelo:#F57F17;--vermelho:#C62828}
    html,body{background:var(--fundo);color:var(--texto);font-family:'Inter',sans-serif;min-height:100vh}
    .pac-root{min-height:100vh;display:flex;flex-direction:column}

    /* Header */
    .pac-header{background:var(--pri);padding:0 24px;height:52px;display:flex;align-items:center;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,.15)}
    .pac-header-inner{display:flex;align-items:center;justify-content:space-between;width:100%}
    .pac-btn-voltar{color:#BBDEFB;font-size:13px;text-decoration:none;padding:5px 12px;border:1px solid rgba(255,255,255,.25);border-radius:7px;transition:background .15s}
    .pac-btn-voltar:hover{background:rgba(255,255,255,.15);color:#fff}
    .pac-header-centro{display:flex;align-items:center;gap:8px;color:#fff;font-size:15px;font-weight:600}
    .pac-header-hospital{color:#90CAF9;font-size:12px}

    /* Toolbar */
    .pac-toolbar{background:var(--card);border-bottom:1px solid var(--borda);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
    .pac-toolbar-left{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    .pac-toolbar-right{display:flex;align-items:center;gap:12px}
    .pac-modo-group{display:flex;gap:4px;background:#F1F5F9;border-radius:8px;padding:3px}
    .pac-modo-btn{background:transparent;border:none;border-radius:6px;padding:7px 14px;font-family:'Inter',sans-serif;font-size:13px;font-weight:500;color:var(--sub);cursor:pointer;transition:background .15s,color .15s}
    .pac-modo-ativo{background:var(--card);color:var(--pri);box-shadow:0 1px 3px rgba(0,0,0,.1)}
    .pac-filtro-periodo{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    .pac-label{font-size:12px;color:var(--sub);font-weight:500}
    .pac-input-data{border:1.5px solid var(--borda);border-radius:7px;padding:6px 10px;font-family:'Inter',sans-serif;font-size:13px;color:var(--texto);outline:none}
    .pac-input-data:focus{border-color:var(--pri)}
    .pac-btn-buscar{background:var(--pri);color:#fff;border:none;border-radius:7px;padding:7px 14px;font-family:'Inter',sans-serif;font-size:13px;font-weight:500;cursor:pointer}
    .pac-btn-atualizar{background:transparent;color:var(--pri);border:1.5px solid var(--pri);border-radius:7px;padding:7px 14px;font-family:'Inter',sans-serif;font-size:13px;cursor:pointer}
    .pac-resumo-toolbar{display:flex;gap:16px}
    .pac-resumo-item{font-size:13px;color:var(--sub);font-weight:500}
    .pac-msg{font-size:13px;min-height:20px;color:var(--verde);padding:4px 24px;font-weight:500}

    /* Abas */
    .pac-abas-container{display:flex;flex-wrap:wrap;gap:6px;padding:12px 24px;background:var(--fundo);border-bottom:1px solid var(--borda);overflow-x:auto}
    .pac-aba{display:flex;align-items:center;gap:6px;background:var(--card);border:1.5px solid var(--borda);border-radius:20px;padding:6px 14px;font-family:'Inter',sans-serif;font-size:12px;font-weight:500;color:var(--sub);cursor:pointer;transition:all .15s;white-space:nowrap}
    .pac-aba:hover{border-color:var(--pri);color:var(--pri)}
    .pac-aba-ativa{background:var(--pri);border-color:var(--pri);color:#fff!important}
    .pac-aba-nome{font-size:12px}
    .pac-aba-badge{display:inline-flex;align-items:center;justify-content:center;min-width:20px;height:20px;border-radius:10px;font-size:11px;font-weight:700;color:#fff;padding:0 5px}
    .pac-aba-ativa .pac-aba-badge{background:rgba(255,255,255,.3)!important}

    /* Conteúdo */
    .pac-conteudo{flex:1;padding:16px 24px}
    .pac-vazio{text-align:center;padding:40px;color:var(--sub);font-size:14px}
    .pac-setor-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:10px}
    .pac-setor-header-left{display:flex;align-items:center;gap:12px}
    .pac-setor-titulo{font-size:18px;font-weight:700;color:var(--texto)}
    .pac-setor-count{background:#EEF2FF;color:var(--pri);border-radius:12px;padding:3px 12px;font-size:12px;font-weight:600}
    .pac-legenda{display:flex;gap:16px;font-size:11px;color:var(--sub);align-items:center}
    .pac-leg-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:middle}

    /* Tabela */
    .pac-tabela-wrap{overflow-x:auto;background:var(--card);border:1px solid var(--borda);border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
    .pac-tabela{width:100%;border-collapse:collapse;font-size:13px}
    .pac-tabela thead{position:sticky;top:0;z-index:5}
    .pac-tabela th{background:#F8FAFC;padding:10px 12px;border-bottom:2px solid var(--borda);font-size:11px;font-weight:600;color:var(--sub);text-align:left;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}
    .pac-tabela td{padding:10px 12px;border-bottom:1px solid #F1F5F9;vertical-align:middle}
    .pac-tabela tr:last-child td{border-bottom:none}
    .pac-tabela tr:hover td{background:#F8FAFC}
    .pac-tr-vago td{opacity:.5}
    .pac-td-leito{font-weight:600;color:var(--pri);white-space:nowrap;min-width:80px}
    .pac-td-pac{font-weight:500;color:var(--texto);min-width:200px}
    .pac-td-num{color:var(--sub);font-size:12px;text-align:center}
    .pac-td-data{color:var(--sub);font-size:12px;white-space:nowrap}
    .pac-td-dias{text-align:center;font-size:13px}
    .pac-td-conv{color:var(--sub);font-size:12px}
    .pac-td-med{color:var(--texto);font-size:12px}
    .pac-td-tipo{color:var(--sub);font-size:11px}

    /* Rodapé */
    .pac-rodape{display:flex;justify-content:space-between;font-size:11px;color:#94A3B8;padding:8px 24px 12px}
  </style>
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""
