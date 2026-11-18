from flask import Flask, render_template, request, redirect, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import time

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-so-pra-testar-no-meu-pc")

CATEGORIAS = ["Roupas", "Calçados", "Acessórios"]

# Pasta onde o app.py está (evita erro de caminho no PythonAnywhere)
PASTA = os.path.dirname(os.path.abspath(__file__))

ARQUIVO = os.path.join(PASTA, "pecas.json")
PASTA_FOTOS = os.path.join(PASTA, "static", "fotos")

ARQUIVO_BANNERS = os.path.join(PASTA, "banners.json")
PASTA_BANNERS = os.path.join(PASTA, "static", "banners")

ARQUIVO_CONFIG = os.path.join(PASTA, "config.json")

# cria as pastas de imagens se ainda não existirem
os.makedirs(PASTA_FOTOS, exist_ok=True)
os.makedirs(PASTA_BANNERS, exist_ok=True)


# ---------- PEÇAS (ler e salvar) ----------

def carregar_pecas():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            pecas = json.load(f)
    else:
        pecas = []

    # peças antigas tinham só "foto"; transforma numa lista "fotos"
    for peca in pecas:
        if "fotos" not in peca:
            peca["fotos"] = [peca["foto"]]

    return pecas


def salvar_pecas(pecas):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(pecas, f, ensure_ascii=False, indent=4)


def salvar_fotos(arquivos):
    # salva várias fotos na pasta e devolve a lista com os nomes
    nomes = []
    numero = 0
    agora = str(int(time.time()))

    for arquivo in arquivos:
        if arquivo.filename != "":
            # coloca números na frente pra duas fotos com o mesmo nome não se substituírem
            nome = agora + "_" + str(numero) + "_" + secure_filename(arquivo.filename)
            arquivo.save(os.path.join(PASTA_FOTOS, nome))
            nomes.append(nome)
            numero = numero + 1

    return nomes


# ---------- BANNERS (ler e salvar) ----------

def carregar_banners():
    if os.path.exists(ARQUIVO_BANNERS):
        with open(ARQUIVO_BANNERS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def salvar_banners(banners):
    with open(ARQUIVO_BANNERS, "w", encoding="utf-8") as f:
        json.dump(banners, f, ensure_ascii=False, indent=4)


# ---------- CONFIGURAÇÕES (ler e salvar) ----------

def carregar_config():
    # valores padrão (usados enquanto ela não mudar nada)
    config = {
        "nome_loja": "Brechó Da Zabe",
        "subtitulo": "",
        "endereco": "",
        "instagram": "",
        "whatsapp": "",
        "usuario": "admin",
        "senha": generate_password_hash("brecho123"),
    }

    # se já existe o arquivo, os valores salvos substituem os padrão
    if os.path.exists(ARQUIVO_CONFIG):
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            salvo = json.load(f)
        for chave in salvo:
            config[chave] = salvo[chave]

    return config


def salvar_config(config):
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


# ---------- SITE ----------

@app.route("/")
def inicio():
    pecas = carregar_pecas()
    banners = carregar_banners()
    config = carregar_config()

    # tira as peças vendidas do site
    pecas_a_venda = []
    for peca in pecas:
        if not peca.get("vendida"):
            pecas_a_venda.append(peca)
    pecas = pecas_a_venda

    # pega a categoria do link, ex: /?categoria=Roupas
    categoria = request.args.get("categoria")

    if categoria:
        pecas_filtradas = []
        for peca in pecas:
            if peca.get("categoria") == categoria:
                pecas_filtradas.append(peca)
        pecas = pecas_filtradas

    return render_template("index.html", pecas=pecas, banners=banners, categorias=CATEGORIAS, categoria_atual=categoria, config=config)


# ---------- LOGIN ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    config = carregar_config()
    erro = ""

    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        # check_password_hash compara a senha digitada com a embaralhada
        if usuario == config["usuario"] and check_password_hash(config["senha"], senha):
            session["admin"] = True
            return redirect("/admin")

        erro = "Usuário ou senha incorretos"

    return render_template("login.html", erro=erro, config=config)


@app.route("/sair")
def sair():
    session.pop("admin", None)
    return redirect("/")


# ---------- ADMIN ----------

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")
    pecas = carregar_pecas()
    banners = carregar_banners()
    return render_template("admin.html", pecas=pecas, banners=banners, categorias=CATEGORIAS)


@app.route("/admin/adicionar", methods=["POST"])
def adicionar():
    if not session.get("admin"):
        return redirect("/login")

    pecas = carregar_pecas()

    # getlist pega TODAS as fotos escolhidas, não só uma
    fotos = salvar_fotos(request.files.getlist("fotos"))

    # troca vírgula por ponto, pra aceitar "45,00"
    preco = float(request.form["preco"].replace(",", "."))

    peca = {
        "nome": request.form["nome"],
        "tamanho": request.form["tamanho"],
        "preco": preco,
        "promocao": 0,
        "categoria": request.form["categoria"],
        "fotos": fotos,
        "vendida": False,
    }
    pecas.append(peca)
    salvar_pecas(pecas)
    return redirect("/admin")


@app.route("/admin/promocao/<int:numero>", methods=["POST"])
def promocao(numero):
    if not session.get("admin"):
        return redirect("/login")

    pecas = carregar_pecas()
    valor = request.form["promocao"].replace(",", ".")

    if valor == "":
        pecas[numero]["promocao"] = 0   # campo vazio = tira a promoção
    else:
        pecas[numero]["promocao"] = float(valor)

    salvar_pecas(pecas)
    return redirect("/admin")


@app.route("/admin/remover/<int:numero>", methods=["POST"])
def remover(numero):
    if not session.get("admin"):
        return redirect("/login")

    pecas = carregar_pecas()
    pecas.pop(numero)
    salvar_pecas(pecas)
    return redirect("/admin")


@app.route("/admin/editar/<int:numero>", methods=["GET", "POST"])
def editar(numero):
    if not session.get("admin"):
        return redirect("/login")

    pecas = carregar_pecas()
    peca = pecas[numero]

    # quando ela clica em "Salvar"
    if request.method == "POST":
        peca["nome"] = request.form["nome"]
        peca["tamanho"] = request.form["tamanho"]
        peca["preco"] = float(request.form["preco"].replace(",", "."))
        peca["categoria"] = request.form["categoria"]

        # fotos que ela marcou pra remover
        remover = request.form.getlist("remover_fotos")

        # guarda só as fotos que NÃO foram marcadas
        fotos_que_ficam = []
        for foto in peca["fotos"]:
            if foto not in remover:
                fotos_que_ficam.append(foto)

        # adiciona as fotos novas no final
        fotos_novas = salvar_fotos(request.files.getlist("fotos"))
        for foto in fotos_novas:
            fotos_que_ficam.append(foto)

        # a peça precisa ter pelo menos 1 foto; se ficaria sem nenhuma, mantém as antigas
        if len(fotos_que_ficam) > 0:
            peca["fotos"] = fotos_que_ficam

        salvar_pecas(pecas)
        return redirect("/admin")

    # quando ela só abre a página
    return render_template("editar.html", peca=peca, numero=numero, categorias=CATEGORIAS)


@app.route("/admin/vendida/<int:numero>", methods=["POST"])
def vendida(numero):
    if not session.get("admin"):
        return redirect("/login")

    pecas = carregar_pecas()

    # se estava vendida, volta pra vitrine; se não estava, marca como vendida
    if pecas[numero].get("vendida"):
        pecas[numero]["vendida"] = False
    else:
        pecas[numero]["vendida"] = True

    salvar_pecas(pecas)
    return redirect("/admin")


# ---------- ADMIN: BANNERS ----------

@app.route("/admin/banner/adicionar", methods=["POST"])
def adicionar_banner():
    if not session.get("admin"):
        return redirect("/login")

    banners = carregar_banners()

    imagem = request.files["imagem"]
    nome_imagem = secure_filename(imagem.filename)
    imagem.save(os.path.join(PASTA_BANNERS, nome_imagem))

    banners.append(nome_imagem)
    salvar_banners(banners)
    return redirect("/admin")


@app.route("/admin/banner/remover/<int:numero>", methods=["POST"])
def remover_banner(numero):
    if not session.get("admin"):
        return redirect("/login")

    banners = carregar_banners()
    nome_imagem = banners.pop(numero)
    salvar_banners(banners)

    # apaga o arquivo da pasta também, se ele existir
    caminho = os.path.join(PASTA_BANNERS, nome_imagem)
    if os.path.exists(caminho):
        os.remove(caminho)

    return redirect("/admin")


# ---------- ADMIN: CONFIGURAÇÕES ----------

@app.route("/admin/configuracoes", methods=["GET", "POST"])
def configuracoes():
    if not session.get("admin"):
        return redirect("/login")

    config = carregar_config()
    mensagem = ""

    if request.method == "POST":
        # nome da loja: se ela apagar tudo, mantém o que já tinha
        nome_loja = request.form["nome_loja"].strip()
        if nome_loja != "":
            config["nome_loja"] = nome_loja

        config["subtitulo"] = request.form["subtitulo"].strip()
        config["endereco"] = request.form["endereco"].strip()

        # tira o @ se ela digitar, e os espaços
        config["instagram"] = request.form["instagram"].replace("@", "").strip()

        # deixa só os números do WhatsApp, ex: "(31) 99999-8888" vira "31999998888"
        numero = ""
        for letra in request.form["whatsapp"]:
            if letra.isdigit():
                numero = numero + letra

        # se ela digitou só DDD + número, coloca o 55 do Brasil na frente
        if len(numero) == 10 or len(numero) == 11:
            numero = "55" + numero

        config["whatsapp"] = numero

        salvar_config(config)
        mensagem = "Informações salvas!"

    return render_template("configuracoes.html", config=config, mensagem=mensagem, erro="")


@app.route("/admin/conta", methods=["POST"])
def conta():
    if not session.get("admin"):
        return redirect("/login")

    config = carregar_config()
    mensagem = ""
    erro = ""

    usuario = request.form["usuario"].strip()
    senha_atual = request.form["senha_atual"]
    nova_senha = request.form["nova_senha"]
    confirmar = request.form["confirmar_senha"]

    if not check_password_hash(config["senha"], senha_atual):
        erro = "A senha atual está errada"
    elif usuario == "":
        erro = "O usuário não pode ficar vazio"
    elif nova_senha != confirmar:
        erro = "A nova senha e a confirmação não estão iguais"
    else:
        config["usuario"] = usuario

        # só troca a senha se ela digitou uma nova
        if nova_senha != "":
            config["senha"] = generate_password_hash(nova_senha)

        salvar_config(config)
        mensagem = "Conta atualizada!"

    return render_template("configuracoes.html", config=config, mensagem=mensagem, erro=erro)


if __name__ == "__main__":
    app.run(debug=True)