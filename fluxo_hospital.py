# ============================================================
# fluxo_hospital.py - Tela de Fluxo de Leitos (leitura atual)
# Substitui o dashboard antigo de Fluxo de Leitos
# ============================================================

import calendar
from datetime import date, datetime, timedelta

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from config import NOME_HOSPITAL, NOME_CIDADE
from ocupacao_v2 import (
    salvar_ocupacao_dia, carregar_ocupacao_dia,
    get_ocupacao_dia, get_leitos_ativos
)
#from fluxo_v2 import get_fluxo_dia, salvar_fluxo_dia, carregar_fluxo_dia
from fluxo_v2 import get_fluxo_periodo
from db import testar_conexao, PSYCOPG2_OK

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
}

LABELS_MOV = [
    ("ocupacao_inicial",     "Ocup. Inicial",   C["primaria"]),
    ("admissao",             "Admissões",        C["verde"]),
    ("transferencia_entrada","Transf. Entrada",  "#6A1B9A"),
    ("transferencia_saida",  "Transf. Saída",    C["amarelo"]),
    ("alta_medica",          "Altas Médicas",    "#00838F"),
    ("transferencia_externa","Transf. Externas", "#F9A825"),
    ("evasao",               "Evasões",          "#757575"),
    ("obito",                "Óbitos",           C["vermelho"]),
    ("ocupacao_final",       "Ocup. Final",      C["sec"]),
]


def criar_dash_fluxo_hospital(server):
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/fluxo/",
        suppress_callback_exceptions=True,
        title="Fluxo de Leitos — HRRBC",
    )

    hoje = date.today()

    app.layout = html.Div([
        dcc.Store(id="fh-store-edit", data={}),
        dcc.Interval(id="fh-intervalo", interval=5*60*1000, n_intervals=0),
        dcc.Download(id="fh-download-excel"),

        # ── Header ────────────────────────────────────────
        html.Div([
            html.Div([
                html.A("← Menu", href="/menu", className="fh-btn-voltar"),
                html.Div([
                    html.Span("📋", style={"fontSize":"20px"}),
                    html.Span("Fluxo de Leitos", className="fh-header-titulo"),
                ], className="fh-header-centro"),
                html.Div(NOME_HOSPITAL, className="fh-header-hospital"),
            ], className="fh-header-inner"),
        ], className="fh-header"),

        # ── Conteúdo ──────────────────────────────────────
        html.Div([

            # Cards + Gráfico
            html.Div([

                # Cards de resumo
                html.Div(id="fh-cards", className="fh-cards-row"),

                # Gráfico
                #html.Div([
                #    html.H2("Ocupação Atual por Clínica", className="fh-section-title"),
                #    dcc.Graph(id="fh-grafico", config={"displayModeBar": False}),
                #], className="fh-card"),

            ], id="fh-secao-ocupacao"),

            # ── Fluxo atual ───────────────────────────────
            html.Div([
                html.Div([
                    html.Div([
                        html.H2("Fluxo e Movimentação de Leitos", className="fh-section-title"),
                        html.Div(id="fh-fluxo-label", className="fh-sub"),
                    ]),
                    html.Div([
                        dcc.Dropdown(
                            id="fh-periodo",
                            options=[
                                {"label": "Última 1 hora",   "value": 1},
                                {"label": "Últimas 2 horas", "value": 2},
                                {"label": "Últimas 4 horas", "value": 4},
                            ],
                            value=1,
                            clearable=False,
                            style={"width": "170px"},
                        ),
                        html.Div(id="fh-db-status"),
                        html.Button([html.Span("↻ "), "Atualizar"], id="fh-btn-atualizar",
                                    className="fh-btn-outline", n_clicks=0),
                    ], className="fh-toolbar-right"),
                ], className="fh-fluxo-header"),
                html.Div(id="fh-fluxo-msg", className="fh-msg"),
                html.Div(id="fh-fluxo-tabela"),
            ], className="fh-card fh-card-fluxo"),

            # Rodapé
            html.Div([
                html.Span("Dados: SMART Pixeon — Somente leitura"),
                html.Span(id="fh-rodape-hora"),
            ], className="fh-rodape"),

        ], className="fh-conteudo"),
    ], className="fh-root")

    app.index_string = _shell()

    # ── Callback status banco ─────────────────────────────
    @app.callback(Output("fh-db-status","children"), Input("fh-intervalo","n_intervals"))
    def db_status(_):
        if not PSYCOPG2_OK:
            return html.Span("⚠ Banco offline", style={"fontSize":"11px","color":C["amarelo"]})
        ok = testar_conexao()
        return html.Span("🟢 Banco" if ok else "🔴 Banco offline",
                         style={"fontSize":"11px","color":C["verde"] if ok else C["vermelho"]})

    # ── Callback principal ────────────────────────────────
    @app.callback(
        Output("fh-cards",        "children"),
        Output("fh-fluxo-label",  "children"),
        Output("fh-fluxo-tabela", "children"),
        Output("fh-fluxo-msg",    "children"),
        Output("fh-rodape-hora",  "children"),
        Input("fh-btn-atualizar", "n_clicks"),
        Input("fh-intervalo",     "n_intervals"),
        Input("fh-periodo",       "value"),
    )
    def atualizar(n_atu, _, horas):
        ctx  = dash.callback_context
        hoje = date.today()
        ontem = hoje - timedelta(days=1)
        msg  = ""

        if ctx.triggered and "fh-btn-atualizar" in ctx.triggered[0]["prop_id"] and n_atu:
            try:
                salvar_ocupacao_dia(hoje)
                msg = "✓ Dados atualizados!"
            except Exception as e:
                msg = f"✗ {e}"

        # ── Ocupação atual ────────────────────────────────
        leitos = get_leitos_ativos()
        dados_hoje = carregar_ocupacao_dia(hoje)
        if not dados_hoje:
            try: dados_hoje = get_ocupacao_dia(hoje)
            except: dados_hoje = {}

        total_cap  = sum(d["capacidade"] for d in leitos.values())
        total_ocup = sum(dados_hoje.get(cod,{}).get("ocupados",0) for cod in leitos)
        taxa       = round(total_ocup/total_cap*100,1) if total_cap else 0
        livres     = total_cap - total_ocup
        uti_cap    = sum(d["capacidade"] for d in leitos.values() if "UTI" in d.get("setor",""))
        uti_ocup   = sum(dados_hoje.get(cod,{}).get("ocupados",0) for cod,d in leitos.items() if "UTI" in d.get("setor",""))
        uti_taxa   = round(uti_ocup/uti_cap*100,1) if uti_cap else 0

        def cor(t): return C["vermelho"] if t>=90 else C["amarelo"] if t>=75 else C["verde"]

        cards = [
            _card("🛏", str(total_ocup), "Leitos Ocupados",  f"de {total_cap} disponíveis", C["primaria"]),
            _card("📊", f"{taxa}%",       "Taxa de Ocupação", hoje.strftime("%d/%m %H:%M"),   cor(taxa)),
            _card("✅", str(livres),       "Leitos Livres",    "disponíveis agora",            C["verde"]),
            _card("🚨", f"{uti_taxa}%",    "UTI",              f"{uti_ocup}/{uti_cap} leitos", cor(uti_taxa)),
        ]

        #setores_ord = list(leitos.keys())
        #nomes    = [leitos[s]["setor"].title() for s in setores_ord]
        #caps     = [leitos[s]["capacidade"]    for s in setores_ord]
        #ocupados = [dados_hoje.get(s,{}).get("ocupados",0) for s in setores_ord]
        #pcts     = [round(o/c*100) if c else 0 for o,c in zip(ocupados,caps)]
        #cores    = [C["vermelho"] if p>=90 else C["amarelo"] if p>=75 else C["primaria"] for p in pcts]

        #fig = go.Figure()
        #fig.add_trace(go.Bar(y=nomes, x=ocupados, orientation="h", marker_color=cores,
        #                     text=[f"{p}%" for p in pcts], textposition="outside",
        #                     hovertemplate="%{y}<br>Ocupados: %{x}<extra></extra>"))
        #fig.add_trace(go.Bar(y=nomes, x=[c-o for c,o in zip(caps,ocupados)], orientation="h",
        #                     marker_color="rgba(0,0,0,0.05)", showlegend=False))
        #fig.update_layout(barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        #                  margin=dict(l=0,r=70,t=10,b=10), height=500, showlegend=False,
        #                  font=dict(family="Inter",color=C["sub"],size=12),
        #                  xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
        #                  yaxis=dict(showgrid=False,tickfont=dict(size=11,color=C["texto"])))

        # ── Fluxo em tempo real (últimas N horas) ─────────
        try:
            dados_fluxo = get_fluxo_periodo(horas)
        except Exception as e:
            dados_fluxo = {}
            msg = msg or f"✗ Erro ao buscar fluxo: {e}"

        agora = datetime.now()
        label = f"Movimentação das últimas {horas}h — gerado em {agora.strftime('%d/%m/%Y %H:%M')}"

        if not dados_fluxo:
            tabela = html.Div("Nenhum dado de fluxo. Clique em Atualizar.", className="fh-vazio")
        else:
            nomes_cfg = [d["setor"] for d in leitos.values()]
            setores_f = []
            for cod_l, dl in leitos.items():
                for cod, d in dados_fluxo.items():
                    if d["setor"] == dl["setor"]:
                        setores_f.append((cod,d)); break
            for cod, d in dados_fluxo.items():
                if d["setor"] not in nomes_cfg:
                    setores_f.append((cod,d))

            totais = {k:0 for k,_,_ in LABELS_MOV}

            cab = [
                html.Th("Cap.", className="fh-th-cap"),
                html.Th("Setor", className="fh-th-setor"),
            ] + [html.Th(lbl, className="fh-th-mov", style={"borderTop":f"3px solid {cor_col}"})
                 for _,lbl,cor_col in LABELS_MOV]

            linhas = []
            for idx,(cod,d) in enumerate(setores_f):
                cap_info = next((dl for dl in leitos.values() if dl["setor"]==d["setor"]),None)
                cap = cap_info["capacidade"] if cap_info else None
                bg  = "#FFFFFF" if idx%2==0 else "#F8FAFC"

                cels = [
                    html.Td(str(cap) if cap else "—", className="fh-td-cap"),
                    html.Td(d["setor"].title(), className="fh-td-setor"),
                ]
                for chave,_,cor_col in LABELS_MOV:
                    val = d.get(chave,0) or 0
                    totais[chave] += val
                    cell_bg = bg
                    if chave=="obito" and val>0: cell_bg="#FFEBEE"
                    elif chave=="evasao" and val>0: cell_bg="#FFF8E1"
                    elif chave in ("ocupacao_inicial","ocupacao_final") and cap:
                        pct=round(val/cap*100) if cap else 0
                        if pct>=100: cell_bg="#FFEBEE"
                        elif pct>=90: cell_bg="#FFF3E0"
                    cels.append(html.Td(
                        dcc.Input(id={"type":"fhi","cod":cod,"campo":chave},
                                  type="number",value=val,min=0,debounce=True,
                                  className="fh-input",
                                  style={"borderColor":cor_col,"backgroundColor":cell_bg,"color":cor_col}),
                        className="fh-td-input",
                    ))
                linhas.append(html.Tr(cels,style={"backgroundColor":bg}))

            cels_tot = [html.Td("",className="fh-td-cap"),
                        html.Td("TOTAL GERAL",className="fh-td-total")]
            for chave,_,cor_col in LABELS_MOV:
                cels_tot.append(html.Td(str(totais[chave]),className="fh-td-tot-val",
                                        style={"color":cor_col}))
            linhas.append(html.Tr(cels_tot,className="fh-tr-total"))

            tabela = html.Div(
                html.Table([html.Thead(html.Tr(cab)),html.Tbody(linhas)],className="fh-tabela"),
                className="fh-tabela-wrap",
            )

        hora = f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        #return cards, fig, label, tabela, msg, hora
        return cards, label, tabela, msg, hora

    return app


def _card(icone,valor,titulo,sub,cor):
    return html.Div([
        html.Div(icone,className="fh-card-icon"),
        html.Div([
            html.Div(valor,className="fh-card-valor",style={"color":cor}),
            html.Div(titulo,className="fh-card-titulo"),
            html.Div(sub,className="fh-card-sub"),
        ]),
    ],className="fh-resumo-card",style={"borderTop":f"4px solid {cor}"})


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
    :root{--pri:#1565C0;--fundo:#F0F4F8;--card:#fff;--borda:#E2E8F0;--texto:#1A237E;--sub:#546E7A;--verde:#2E7D32;--amarelo:#F57F17;--vermelho:#C62828}
    html,body{background:var(--fundo);color:var(--texto);font-family:'Inter',sans-serif;min-height:100vh}
    .fh-root{min-height:100vh;display:flex;flex-direction:column}
    .fh-header{background:var(--pri);padding:0 28px;height:52px;display:flex;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.15);flex-shrink:0}
    .fh-header-inner{display:flex;align-items:center;justify-content:space-between;width:100%}
    .fh-btn-voltar{color:#BBDEFB;font-size:13px;text-decoration:none;padding:5px 12px;border:1px solid rgba(255,255,255,.25);border-radius:7px}
    .fh-btn-voltar:hover{background:rgba(255,255,255,.15);color:#fff}
    .fh-header-centro{display:flex;align-items:center;gap:8px;color:#fff;font-size:15px;font-weight:600}
    .fh-header-hospital{color:#90CAF9;font-size:12px}
    .fh-conteudo{flex:1;padding:20px 28px;display:flex;flex-direction:column;gap:16px}
    .fh-cards-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:4px}
    .fh-resumo-card{background:var(--card);border:1px solid var(--borda);border-radius:12px;padding:16px 18px;display:flex;align-items:center;gap:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
    .fh-card-icon{font-size:26px}
    .fh-card-valor{font-size:26px;font-weight:700;line-height:1}
    .fh-card-titulo{font-size:12px;color:var(--texto);font-weight:500;margin-top:3px}
    .fh-card-sub{font-size:11px;color:var(--sub)}
    .fh-card{background:var(--card);border:1px solid var(--borda);border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
    .fh-card-fluxo{padding:20px}
    .fh-section-title{font-size:15px;font-weight:600;color:var(--texto);margin-bottom:14px}
    .fh-fluxo-header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px;gap:12px}
    .fh-sub{font-size:12px;color:var(--sub);margin-top:3px}
    .fh-toolbar-right{display:flex;align-items:center;gap:10px;flex-shrink:0}
    .fh-btn-outline{background:#fff;color:var(--pri);border:1.5px solid var(--pri);border-radius:8px;padding:7px 14px;font-family:'Inter',sans-serif;font-size:13px;cursor:pointer}
    .fh-btn-outline:hover{background:var(--pri);color:#fff}
    .fh-msg{font-size:13px;min-height:18px;color:var(--verde);font-weight:500;margin-bottom:8px}
    .fh-vazio{text-align:center;padding:32px;color:var(--sub);font-size:13px}
    .fh-tabela-wrap{overflow-x:auto}
    .fh-tabela{border-collapse:collapse;width:100%;font-size:12px}
    .fh-tabela thead{position:sticky;top:0;z-index:10}
    .fh-tabela th{background:#F8FAFC;padding:8px 6px;border-bottom:2px solid var(--borda);border-right:1px solid #EEF2F7;font-weight:600;color:var(--sub);font-size:11px;text-transform:uppercase;letter-spacing:.04em;text-align:center;white-space:nowrap}
    .fh-tabela td{padding:3px 4px;border-bottom:1px solid #F1F5F9;border-right:1px solid #F1F5F9;text-align:center}
    .fh-th-cap{min-width:38px;text-align:left!important}
    .fh-th-setor{text-align:left!important;min-width:200px}
    .fh-th-mov{min-width:90px;padding-top:10px!important}
    .fh-td-cap{color:var(--sub);font-size:11px;text-align:left;padding-left:8px!important}
    .fh-td-setor{text-align:left!important;color:var(--texto);font-weight:500;white-space:nowrap;padding-left:4px!important}
    .fh-td-input{padding:3px!important}
    .fh-input{border-radius:6px;border-width:1.5px;border-style:solid;width:72px;padding:5px 4px;text-align:center;font-family:'Inter',sans-serif;font-size:12px;font-weight:500;outline:none}
    .fh-input:focus{box-shadow:0 0 0 2px rgba(21,101,192,.2)}
    .fh-tr-total td{border-top:2px solid var(--borda);font-weight:700;background:#F0F4F8!important}
    .fh-td-total{text-align:left!important;padding-left:4px!important;color:var(--sub)}
    .fh-td-tot-val{font-weight:700;font-size:13px}
    .fh-rodape{display:flex;justify-content:space-between;font-size:11px;color:#94A3B8;padding:4px 0 8px}
  </style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""
