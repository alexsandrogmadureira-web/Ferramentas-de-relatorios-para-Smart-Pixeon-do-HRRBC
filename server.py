# ============================================================
# server.py - Flask principal com login e menu de módulos
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from config import SECRET_KEY, NOME_HOSPITAL, NOME_CIDADE
from database import executar

server = Flask(__name__)
server.secret_key = SECRET_KEY


def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@server.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logado"):
        return redirect(url_for("menu"))
    erro = ""
    if request.method == "POST":
        login_val = request.form.get("login", "").strip().upper()
        senha     = request.form.get("senha", "").strip()
        if not login_val or not senha:
            erro = "Preencha login e senha."
        else:
            df = executar(f"SELECT USR_SENHA FROM USR WHERE USR_LOGIN = '{login_val}' AND USR_STATUS = 'A'")
            if not df.empty and str(df.iloc[0]["usr_senha"]).strip() == senha:
                session["logado"]       = True
                session["login"]        = login_val
                df2 = executar(f"SELECT USR_NOME FROM USR WHERE USR_LOGIN = '{login_val}'")
                nome = str(df2.iloc[0]["usr_nome"]).strip().title() if not df2.empty else login_val
                session["nome_usuario"] = nome
                return redirect(url_for("menu"))
            else:
                erro = "Login ou senha incorretos."
    return render_template("login.html",
                           hospital=NOME_HOSPITAL,
                           cidade=NOME_CIDADE,
                           erro=erro)


@server.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@server.route("/")
@server.route("/menu")
@login_requerido
def menu():
    return render_template("menu.html",
                           hospital=NOME_HOSPITAL,
                           nome_usuario=session.get("nome_usuario", ""))


@server.before_request
def proteger():
    livres = ["/login", "/logout", "/_dash", "/static", "/taxa-ocupacao", "/pacientes", "/fluxo", "/bid", "/cirurgias"]
    if any(request.path.startswith(r) for r in livres):
        return None
    if not session.get("logado"):
        return redirect(url_for("login"))
