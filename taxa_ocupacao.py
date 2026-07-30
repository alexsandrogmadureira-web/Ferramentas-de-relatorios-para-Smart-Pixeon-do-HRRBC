# ============================================================
# taxa_ocupacao.py - Dashboard de Taxa de Ocupação
# ============================================================

import calendar
from datetime import date, datetime, timedelta

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from ocupacao_v2 import (
    carregar_ocupacao_dia, salvar_ocupacao_dia,
    get_leitos_ativos
)

C = {
    "primaria":  "#1565C0",
    "fundo":     "#F0F4F8",
    "card":      "#FFFFFF",
    "borda":     "#E2E8F0",
    "texto":     "#1A237E",
    "sub":       "#546E7A",
    "verde":     "#2E7D32",
    "amarelo":   "#F57F17",
    "vermelho":  "#C62828",
    "vd_claro":  "#E8F5E9",
    "am_claro":  "#FFF8E1",
    "vm_claro":  "#FFEBEE",
    "vm_forte":  "#FFCDD2",
    "neutro":    "#F8FAFC",
}


def criar_dash_taxa(server):
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/taxa-ocupacao/",
        suppress_callback_exceptions=True,
        title="Taxa de Ocupação — HRRBC",
    )

    hoje = date.today()

    app.layout = html.Div([
        dcc.Store(id="tx-store-mes", data={"ano": hoje.year, "mes": hoje.month}),
        dcc.Interval(id="tx-intervalo", interval=10*60*1000, n_intervals=0),

        # ── Header ────────────────────────────────────────
        html.Div([
            html.Div([
                html.A("← Voltar ao Menu", href="/menu", className="tx-btn-voltar"),
                html.Div([
                    html.Span("📊", style={"fontSize":"20px"}),
                    html.Span("Taxa de Ocupação de Leitos", className="tx-header-titulo"),
                ], className="tx-header-centro"),
                html.Div("Hospital Regional Ruy de Barros Correia", className="tx-header-hospital"),
            ], className="tx-header-inner"),
        ], className="tx-header"),

        # ── Conteúdo ──────────────────────────────────────
        html.Div([

            # Cards de resumo do dia
            html.Div(id="tx-cards", className="tx-cards-row"),

            # Painel do mapa de calor
            html.Div([
                html.Div([
                    html.Div([
                        html.H2("Mapa de Calor — Ocupação Mensal", className="tx-section-title"),
                        html.Div(id="tx-legenda", className="tx-legenda"),
                    ]),
                    html.Div([
                        html.Button("‹", id="tx-mes-ant",  className="tx-btn-nav", n_clicks=0),
                        html.Span(id="tx-label-mes", className="tx-mes-label"),
                        html.Button("›", id="tx-mes-prox", className="tx-btn-nav", n_clicks=0),
                        html.Button(
                            [html.Span("↻ "), "Coletar Mês"],
                            id="tx-btn-coletar", className="tx-btn-coletar", n_clicks=0
                        ),
                    ], className="tx-nav-mes"),
                ], className="tx-mapa-header"),
                html.Div(id="tx-msg", className="tx-msg"),
                html.Div(id="tx-mapa-calor", className="tx-mapa-wrap"),
            ], className="tx-card"),

            # Gráfico de evolução
            html.Div([
                html.H2("Evolução da Taxa de Ocupação", className="tx-section-title"),
                html.Div(id="tx-grafico-wrap"),
            ], className="tx-card"),

            # Rodapé
            html.Div([
                html.Span("Dados originados do sistema SMART Pixeon — Somente leitura e análise interna"),
                html.Span(id="tx-rodape-hora"),
            ], className="tx-rodape"),

        ], className="tx-conteudo"),
    ], className="tx-root")

    app.index_string = _shell()

    # ── Navegação de mês ──────────────────────────────────
    @app.callback(
        Output("tx-store-mes", "data"),
        Input("tx-mes-ant",  "n_clicks"),
        Input("tx-mes-prox", "n_clicks"),
        State("tx-store-mes", "data"),
        prevent_initial_call=True,
    )
    def navegar_mes(ant, prox, store):
        ctx = dash.callback_context
        ano, mes = store["ano"], store["mes"]
        if "tx-mes-ant" in ctx.triggered[0]["prop_id"]:
            mes -= 1
            if mes == 0: mes, ano = 12, ano - 1
        else:
            mes += 1
            if mes == 13: mes, ano = 1, ano + 1
        return {"ano": ano, "mes": mes}

    # ── Callback principal ────────────────────────────────
    @app.callback(
        Output("tx-cards",      "children"),
        Output("tx-label-mes",  "children"),
        Output("tx-mapa-calor", "children"),
        Output("tx-grafico-wrap","children"),
        Output("tx-legenda",    "children"),
        Output("tx-msg",        "children"),
        Output("tx-rodape-hora","children"),
        Input("tx-store-mes",   "data"),
        Input("tx-btn-coletar", "n_clicks"),
        Input("tx-intervalo",   "n_intervals"),
    )
    def atualizar(store, n_coletar, _):
        ctx  = dash.callback_context
        hoje = date.today()
        ano, mes = store["ano"], store["mes"]
        msg  = ""

        MESES = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                 "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        label = f"{MESES[mes]} {ano}"

        # Coletar mês
        if ctx.triggered and "tx-btn-coletar" in ctx.triggered[0]["prop_id"] and n_coletar:
            cnt = 0
            for d in range(1, calendar.monthrange(ano, mes)[1] + 1):
                dia = date(ano, mes, d)
                if dia > hoje: break
                salvar_ocupacao_dia(dia); cnt += 1
            msg = f"✓ {cnt} dias coletados para {label}!"

        # Carrega leitos ativos
        leitos = get_leitos_ativos()

        # Dados do dia atual para cards
        dados_hoje = carregar_ocupacao_dia(hoje)
        if not dados_hoje:
            try: dados_hoje = salvar_ocupacao_dia(hoje)
            except: dados_hoje = {}

        total_cap  = sum(d["capacidade"] for d in leitos.values())
        total_ocup = sum(dados_hoje.get(cod, {}).get("ocupados", 0) for cod in leitos)
        taxa_hoje  = round(total_ocup / total_cap * 100, 1) if total_cap else 0
        livres     = total_cap - total_ocup
        uti_cap    = sum(d["capacidade"] for d in leitos.values() if "UTI" in d.get("setor",""))
        uti_ocup   = sum(dados_hoje.get(cod, {}).get("ocupados", 0) for cod, d in leitos.items() if "UTI" in d.get("setor",""))
        uti_taxa   = round(uti_ocup / uti_cap * 100, 1) if uti_cap else 0

        def cor_card(taxa):
            if taxa >= 90: return C["vermelho"]
            if taxa >= 75: return C["amarelo"]
            return C["verde"]

        cards = [
            _card_resumo("🛏", str(total_ocup), "Leitos Ocupados",  f"de {total_cap} disponíveis", C["primaria"]),
            _card_resumo("📊", f"{taxa_hoje}%",  "Taxa de Ocupação", f"hoje {hoje.strftime('%d/%m')}", cor_card(taxa_hoje)),
            _card_resumo("✅", str(livres),       "Leitos Livres",    "disponíveis agora",            C["verde"]),
            _card_resumo("🚨", f"{uti_taxa}%",    "UTI",              f"{uti_ocup}/{uti_cap} leitos", cor_card(uti_taxa)),
        ]

        # ── Mapa de calor ─────────────────────────────────
        dias_no_mes = calendar.monthrange(ano, mes)[1]
        dias = [date(ano, mes, d) for d in range(1, dias_no_mes + 1)]
        DIAS_SEM = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]

        # Coleta dados do mês
        dados_mes = {}
        for d in dias:
            if d <= hoje:
                dd = carregar_ocupacao_dia(d)
                if not dd:
                    try: dd = salvar_ocupacao_dia(d)
                    except: dd = {}
                dados_mes[d.day] = dd
            else:
                dados_mes[d.day] = {}

        setores_ord = list(leitos.keys())

        # Cabeçalho do mapa
        cab_cells = [
            html.Th("Setor", className="tx-th-setor"),
            html.Th("Cap.", className="tx-th-cap"),
        ]
        for d in dias:
            fim_sem = d.weekday() >= 5
            cab_cells.append(html.Th(
                [html.Div(str(d.day), className="tx-th-dia-num"),
                 html.Div(DIAS_SEM[d.weekday()], className="tx-th-dia-sem")],
                className=f"tx-th-dia {'tx-fds' if fim_sem else ''}",
            ))
        cab_cells.append(html.Th("Média", className="tx-th-media"))

        linhas = []
        for cod in setores_ord:
            nome = leitos[cod]["setor"].title()
            cap  = leitos[cod]["capacidade"]

            cels = [
                html.Td(nome, className="tx-td-setor"),
                html.Td(str(cap), className="tx-td-cap"),
            ]

            vals_mes = []
            for d in dias:
                if d > hoje:
                    cels.append(html.Td("", className="tx-td-futuro"))
                    continue
                dd   = dados_mes[d.day]
                ocup = dd.get(cod, {}).get("ocupados", 0) if dd else 0
                pct  = round(ocup / cap * 100) if cap else 0
                vals_mes.append(pct)

                # Cor de fundo da célula baseada na taxa
                if pct >= 100:
                    bg, fg = "#B71C1C", "#FFFFFF"
                elif pct >= 90:
                    bg, fg = C["vm_forte"], C["vermelho"]
                elif pct >= 75:
                    bg, fg = C["am_claro"], "#7B3F00"
                elif pct > 0:
                    bg, fg = C["vd_claro"], C["verde"]
                else:
                    bg, fg = C["neutro"], "#90A4AE"

                cels.append(html.Td(
                    [html.Div(str(ocup), className="tx-cell-num"),
                     html.Div(f"{pct}%",  className="tx-cell-pct")],
                    className="tx-td-dia",
                    style={"background": bg, "color": fg},
                ))

            media = round(sum(vals_mes)/len(vals_mes), 1) if vals_mes else 0
            cor_m = cor_card(media)
            cels.append(html.Td(f"{media}%", className="tx-td-media", style={"color": cor_m, "fontWeight":"700"}))
            linhas.append(html.Tr(cels))

        # Linha de total
        cels_tot = [
            html.Td("TOTAL GERAL", className="tx-td-total-label"),
            html.Td(str(total_cap), className="tx-td-cap"),
        ]
        taxas_total = []
        for d in dias:
            if d > hoje:
                cels_tot.append(html.Td("", className="tx-td-futuro"))
                continue
            dd   = dados_mes[d.day]
            ocup = sum(dd.get(cod, {}).get("ocupados", 0) for cod in setores_ord) if dd else 0
            pct  = round(ocup / total_cap * 100) if total_cap else 0
            taxas_total.append(pct)
            if pct >= 90: bg, fg = C["vm_claro"], C["vermelho"]
            elif pct >= 75: bg, fg = C["am_claro"], "#7B3F00"
            else: bg, fg = C["vd_claro"], C["verde"]
            cels_tot.append(html.Td(
                [html.Div(str(ocup), className="tx-cell-num"),
                 html.Div(f"{pct}%",  className="tx-cell-pct")],
                className="tx-td-dia tx-td-total-dia",
                style={"background": bg, "color": fg},
            ))
        media_tot = round(sum(taxas_total)/len(taxas_total), 1) if taxas_total else 0
        cels_tot.append(html.Td(f"{media_tot}%", className="tx-td-media", style={"color": cor_card(media_tot), "fontWeight":"700"}))
        linhas.append(html.Tr(cels_tot, className="tx-tr-total"))

        mapa = html.Div(
            html.Table([
                html.Thead(html.Tr(cab_cells)),
                html.Tbody(linhas),
            ], className="tx-tabela"),
            className="tx-scroll",
        )

        # ── Gráfico de evolução ───────────────────────────
        dias_passados = [d for d in dias if d <= hoje]
        taxas_graf = []
        for d in dias_passados:
            dd   = dados_mes[d.day]
            ocup = sum(dd.get(cod, {}).get("ocupados", 0) for cod in setores_ord) if dd else 0
            taxas_graf.append(round(ocup / total_cap * 100, 1) if total_cap else 0)

        cores_graf = [
            "#C62828" if t >= 90 else "#F57F17" if t >= 75 else "#1565C0"
            for t in taxas_graf
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[d.strftime("%d/%m") for d in dias_passados],
            y=taxas_graf,
            mode="lines+markers",
            line=dict(color=C["primaria"], width=2.5),
            marker=dict(color=cores_graf, size=8, line=dict(color="#fff", width=1.5)),
            fill="tozeroy",
            fillcolor="rgba(21,101,192,0.08)",
            hovertemplate="Dia %{x}<br>Taxa: %{y}%<extra></extra>",
        ))
        fig.add_hline(y=90, line_dash="dash", line_color=C["vermelho"],
                      annotation_text="90% — Crítico", annotation_position="right",
                      annotation_font_color=C["vermelho"])
        fig.add_hline(y=75, line_dash="dot", line_color=C["amarelo"],
                      annotation_text="75% — Alerta", annotation_position="right",
                      annotation_font_color=C["amarelo"])
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=80, t=10, b=10), height=220,
            font=dict(family="Inter", color=C["sub"], size=12),
            xaxis=dict(showgrid=False, tickfont=dict(size=11)),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9", ticksuffix="%",
                       range=[0, 110], tickfont=dict(size=11)),
            showlegend=False,
        )

        grafico = dcc.Graph(figure=fig, config={"displayModeBar": False})

        # Legenda
        legenda = html.Div([
            html.Span([html.Span(className="leg-box leg-critico"), " ≥ 100%"]),
            html.Span([html.Span(className="leg-box leg-alerta-forte"), " 90–99%"]),
            html.Span([html.Span(className="leg-box leg-alerta"), " 75–89%"]),
            html.Span([html.Span(className="leg-box leg-ok"), " < 75%"]),
            html.Span([html.Span(className="leg-box leg-vazio"), " 0%"]),
        ], className="tx-legenda-inner")

        hora = f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        return cards, label, mapa, grafico, legenda, msg, hora

    return app


def _card_resumo(icone, valor, titulo, sub, cor):
    return html.Div([
        html.Div(icone, className="tx-card-icon"),
        html.Div([
            html.Div(valor,  className="tx-card-valor", style={"color": cor}),
            html.Div(titulo, className="tx-card-titulo"),
            html.Div(sub,    className="tx-card-sub"),
        ]),
    ], className="tx-resumo-card", style={"borderTop": f"4px solid {cor}"})


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
    :root{
      --pri:#1565C0;--fundo:#F0F4F8;--card:#fff;--borda:#E2E8F0;
      --texto:#1A237E;--sub:#546E7A;
      --verde:#2E7D32;--amarelo:#F57F17;--vermelho:#C62828;
    }
    html,body{background:var(--fundo);color:var(--texto);font-family:'Inter',sans-serif;min-height:100vh}
    .tx-root{min-height:100vh;display:flex;flex-direction:column}

    /* Header */
    .tx-header{background:var(--pri);padding:0 32px;height:56px;display:flex;align-items:center;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,.15)}
    .tx-header-inner{display:flex;align-items:center;justify-content:space-between;width:100%}
    .tx-btn-voltar{color:#BBDEFB;font-size:13px;text-decoration:none;padding:6px 12px;border:1px solid rgba(255,255,255,.25);border-radius:7px;transition:background .15s;white-space:nowrap}
    .tx-btn-voltar:hover{background:rgba(255,255,255,.15);color:#fff}
    .tx-header-centro{display:flex;align-items:center;gap:10px;color:#fff;font-size:16px;font-weight:600}
    .tx-header-titulo{color:#fff}
    .tx-header-hospital{color:#90CAF9;font-size:12px;text-align:right}

    /* Conteúdo */
    .tx-conteudo{flex:1;padding:24px 32px;display:flex;flex-direction:column;gap:20px;max-width:1800px;width:100%;margin:0 auto}

    /* Cards */
    .tx-cards-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
    .tx-resumo-card{background:var(--card);border:1px solid var(--borda);border-radius:12px;padding:18px 20px;display:flex;align-items:center;gap:14px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
    .tx-card-icon{font-size:28px}
    .tx-card-valor{font-size:28px;font-weight:700;line-height:1}
    .tx-card-titulo{font-size:13px;color:var(--texto);font-weight:500;margin-top:3px}
    .tx-card-sub{font-size:11px;color:var(--sub);margin-top:2px}

    /* Card painel */
    .tx-card{background:var(--card);border:1px solid var(--borda);border-radius:12px;padding:22px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
    .tx-section-title{font-size:15px;font-weight:600;color:var(--texto);margin-bottom:0}
    .tx-mapa-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px}
    .tx-nav-mes{display:flex;align-items:center;gap:8px}
    .tx-mes-label{font-size:15px;font-weight:700;color:var(--texto);min-width:140px;text-align:center}
    .tx-btn-nav{background:var(--card);border:1.5px solid var(--borda);color:var(--sub);width:30px;height:30px;border-radius:7px;cursor:pointer;font-size:15px;transition:border-color .15s}
    .tx-btn-nav:hover{border-color:var(--pri);color:var(--pri)}
    .tx-btn-coletar{background:var(--pri);color:#fff;border:none;border-radius:8px;padding:7px 14px;font-family:'Inter',sans-serif;font-size:12px;font-weight:500;cursor:pointer;transition:background .15s}
    .tx-btn-coletar:hover{background:#0D47A1}
    .tx-msg{font-size:13px;min-height:18px;color:var(--verde);font-weight:500;margin-bottom:8px}

    /* Legenda */
    .tx-legenda{display:flex;align-items:center}
    .tx-legenda-inner{display:flex;gap:16px;font-size:11px;color:var(--sub);align-items:center;flex-wrap:wrap}
    .leg-box{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:4px;vertical-align:middle}
    .leg-critico{background:#B71C1C}
    .leg-alerta-forte{background:#FFCDD2}
    .leg-alerta{background:#FFF8E1;border:1px solid #F57F17}
    .leg-ok{background:#E8F5E9;border:1px solid #2E7D32}
    .leg-vazio{background:#F8FAFC;border:1px solid #CFD8DC}

    /* Mapa de calor */
    .tx-mapa-wrap{overflow-x:auto}
    .tx-scroll{overflow-x:auto}
    .tx-tabela{border-collapse:collapse;font-size:11.5px;width:100%}
    .tx-tabela thead{position:sticky;top:0;z-index:10}
    .tx-tabela th{background:#F8FAFC;padding:6px 4px;border-bottom:2px solid var(--borda);border-right:1px solid #EEF2F7;font-weight:600;color:var(--sub);text-align:center;white-space:nowrap}
    .tx-tabela td{padding:3px 4px;border-bottom:1px solid #F1F5F9;border-right:1px solid #F1F5F9;text-align:center}
    .tx-th-setor{text-align:left!important;min-width:180px;padding-left:10px!important}
    .tx-th-cap{min-width:40px}
    .tx-th-dia{min-width:46px}
    .tx-th-dia-num{font-size:13px;font-weight:700;color:var(--texto)}
    .tx-th-dia-sem{font-size:10px;color:var(--sub);font-weight:400}
    .tx-th-media{min-width:56px;color:var(--pri)!important}
    .tx-fds .tx-th-dia-num{color:var(--pri)}
    .tx-td-setor{text-align:left!important;color:var(--texto);font-weight:500;padding-left:10px!important;white-space:nowrap}
    .tx-td-cap{color:var(--sub);font-weight:500}
    .tx-td-futuro{background:#FAFAFA}
    .tx-td-dia{transition:background .2s;cursor:default}
    .tx-td-dia:hover{filter:brightness(.95)}
    .tx-cell-num{font-size:12px;font-weight:700;line-height:1.2}
    .tx-cell-pct{font-size:10px;opacity:.8;line-height:1}
    .tx-td-media{font-size:12px;text-align:center}
    .tx-tr-total td{border-top:2px solid var(--borda);font-weight:700;background:#F0F4F8!important}
    .tx-td-total-label{text-align:left!important;padding-left:10px!important;color:var(--sub)}
    .tx-td-total-dia{}

    /* Rodapé */
    .tx-rodape{display:flex;justify-content:space-between;font-size:11px;color:#94A3B8;padding:8px 0 4px}
  </style>
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""
