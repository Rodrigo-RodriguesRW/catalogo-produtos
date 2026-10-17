
import os
import sqlite3
import base64
from functools import wraps

from flask import (
    Flask,
    render_template,
    redirect,
    request,
    url_for,
    session,
    flash,
)

from werkzeug.security import check_password_hash

app = Flask(__name__)

# Chave de segurança da sessão
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "Defina a variável de ambiente FLASK_SECRET_KEY antes de iniciar o app."
    )


# =========================================================
# BANCO DE DADOS
# =========================================================

def conexao():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def valor_ativo(valor):
    """Converte o valor recebido do formulário para 1 ou 0."""
    return 1 if valor in ("on", "1", "True", "true", "sim") else 0


def administrador_logado(funcao):
    @wraps(funcao)
    def verificar_acesso(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Faça login para acessar a área administrativa.", "warning")
            return redirect(url_for("login"))

        return funcao(*args, **kwargs)

    return verificar_acesso


# =========================================================
# LOGIN E LOGOUT
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "")

        conn = conexao()
        usuario = conn.execute(
            "SELECT id, nome, senha, ativo FROM usuario WHERE nome = ?",
            (nome,)
        ).fetchone()
        conn.close()

        if (
            usuario
            and str(usuario["ativo"]).lower() in ("1", "true", "on")
            and check_password_hash(usuario["senha"], senha)
        ):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]

            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("dashboard"))

        flash("Nome ou senha inválidos, ou usuário inativo.", "danger")

    return render_template("admin/login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))


# =========================================================
# INÍCIO PÚBLICO
# =========================================================

@app.route("/")
def index():
    return render_template("inicio.html")


# =========================================================
# CATEGORIAS
# =========================================================

# =========================================================
# CADASTRAR CATEGORIAS
# =========================================================


@app.route("/cadastrar_categorias", methods=["GET", "POST"])
@administrador_logado
def cadastrarCategoria():
    if request.method == "POST":
        nome = request.form.get("nome_categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        ativo = valor_ativo(request.form.get("ativo"))

        imagem = request.files.get("imagem")
        imagem_base64 = None

        if imagem and imagem.filename:
            imagem_base64 = base64.b64encode(
                imagem.read()
            ).decode("utf-8")

        if not nome or not descricao:
            flash(
                "Preencha o nome e a descrição da categoria.",
                "warning"
            )
        else:
            conn = conexao()

            try:
                conn.execute(
                    """
                    INSERT INTO categoria
                        (nome, descricao, ativo, imagem)
                    VALUES (?, ?, ?, ?)
                    """,
                    (nome, descricao, ativo, imagem_base64)
                )

                conn.commit()

                flash(
                    "Categoria cadastrada com sucesso!",
                    "success"
                )

                return redirect(url_for("listarCategoria"))

            finally:
                conn.close()

    return render_template("admin/cadastrar_categoria.html")


# =========================================================
# LISTAGEM ADMINISTRATIVA DE CATEGORIAS
# =========================================================

@app.route("/listar_categorias")
@administrador_logado
def listarCategoria():
    por_pagina = 10

    try:
        pagina = int(request.args.get("pagina", 1))
    except (TypeError, ValueError):
        pagina = 1

    if pagina < 1:
        pagina = 1

    conn = conexao()

    try:
        total_categorias = conn.execute(
            "SELECT COUNT(*) FROM categoria"
        ).fetchone()[0]

        total_paginas = max(
            1,
            (total_categorias + por_pagina - 1) // por_pagina
        )

        pagina = min(pagina, total_paginas)
        offset = (pagina - 1) * por_pagina

        categorias = conn.execute(
            """
            SELECT *
            FROM categoria
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (por_pagina, offset)
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "admin/listar_categoria.html",
        categorias=categorias,
        pagina=pagina,
        total_paginas=total_paginas,
        total_categorias=total_categorias
    )
    

# =========================================================
# EDITAR CATEGORIA
# =========================================================

@app.route("/editar_categoria/<int:id>", methods=["GET", "POST"])
@administrador_logado
def editarCategoria(id):
    conn = conexao()

    try:
        categoria = conn.execute(
            "SELECT * FROM categoria WHERE id = ?",
            (id,)
        ).fetchone()

        if categoria is None:
            flash("Categoria não encontrada.", "warning")
            return redirect(url_for("listarCategoria"))

        if request.method == "POST":
            nome = request.form.get("nome_categoria", "").strip()
            descricao = request.form.get("descricao", "").strip()
            ativo = valor_ativo(request.form.get("ativo"))
            imagem = request.files.get("imagem")

            if not nome or not descricao:
                flash(
                    "Preencha o nome e a descrição da categoria.",
                    "warning"
                )
                return render_template(
                    "admin/editar_categoria.html",
                    categoria=categoria
                )

            # Mantém a imagem atual se nenhuma nova for enviada.
            imagem_base64 = categoria["imagem"]

            if imagem and imagem.filename:
                imagem_base64 = base64.b64encode(
                    imagem.read()
                ).decode("utf-8")

            conn.execute(
                """
                UPDATE categoria
                SET nome = ?, descricao = ?, ativo = ?, imagem = ?
                WHERE id = ?
                """,
                (nome, descricao, ativo, imagem_base64, id)
            )

            conn.commit()

            flash("Categoria atualizada com sucesso!", "success")
            return redirect(url_for("listarCategoria"))

        return render_template(
            "admin/editar_categoria.html",
            categoria=categoria
        )

    finally:
        conn.close()


# =========================================================
# EXCLUIR CATEGORIA
# =========================================================

@app.route("/excluir_categoria/<int:id>", methods=["POST"])
@administrador_logado
def excluirCategoria(id):
    conn = conexao()

    try:
        categoria = conn.execute(
            "SELECT id FROM categoria WHERE id = ?",
            (id,)
        ).fetchone()

        if categoria is None:
            flash("Categoria não encontrada.", "warning")
            return redirect(url_for("listarCategoria"))

        # Verifica se existem produtos vinculados à categoria.
        produtos = conn.execute(
            "SELECT COUNT(*) FROM produto WHERE id_categoria = ?",
            (id,)
        ).fetchone()[0]

        if produtos > 0:
            flash(
                "Não é possível excluir esta categoria, pois existem "
                "produtos vinculados a ela. Exclua os produtos ou "
                "altere a categoria deles antes de continuar.",
                "warning"
            )
            return redirect(url_for("listarCategoria"))

        conn.execute(
            "DELETE FROM categoria WHERE id = ?",
            (id,)
        )
        conn.commit()

        flash("Categoria excluída com sucesso!", "success")

    finally:
        conn.close()

    return redirect(url_for("listarCategoria"))



# =========================================================
# LISTAGEM ADMINISTRATIVA DE PRODUTOS
# =========================================================



@app.route("/listar_produtos")
@administrador_logado
def listarProdutos():
    por_pagina = 10

    # Parâmetros de pesquisa e filtros
    busca = request.args.get("busca", "").strip()
    categoria_selecionada = request.args.get("categoria", "").strip()
    status_selecionado = request.args.get("status", "").strip()

    # Identifica a página solicitada
    try:
        pagina = int(request.args.get("pagina", 1))
    except (TypeError, ValueError):
        pagina = 1

    if pagina < 1:
        pagina = 1

    conn = conexao()

    try:
        # Lista categorias para o filtro
        categorias = conn.execute(
            """
            SELECT id, nome
            FROM categoria
            ORDER BY nome
            """
        ).fetchall()

        # Monta os filtros da consulta
        condicoes = []
        parametros = []

        if busca:
            condicoes.append("produto.nome LIKE ?")
            parametros.append(f"%{busca}%")

        if categoria_selecionada:
            try:
                categoria_id = int(categoria_selecionada)
                condicoes.append("produto.id_categoria = ?")
                parametros.append(categoria_id)
            except ValueError:
                categoria_selecionada = ""

        if status_selecionado == "ativo":
            condicoes.append("produto.ativo = 1")

        elif status_selecionado == "inativo":
            condicoes.append(
                "(produto.ativo = 0 OR produto.ativo IS NULL)"
            )

        # Aplica os filtros à consulta
        where_sql = ""
        if condicoes:
            where_sql = "WHERE " + " AND ".join(condicoes)

        # Conta somente os produtos que correspondem aos filtros
        total_produtos = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM produto
            {where_sql}
            """,
            parametros
        ).fetchone()[0]

        # Calcula a quantidade de páginas
        total_paginas = max(
            1,
            (total_produtos + por_pagina - 1) // por_pagina
        )

        # Impede solicitar uma página além da última
        pagina = min(pagina, total_paginas)

        offset = (pagina - 1) * por_pagina

        # Busca os produtos da página atual
        produtos = conn.execute(
            f"""
            SELECT
                produto.*,
                categoria.nome AS nome_categoria
            FROM produto
            LEFT JOIN categoria
                ON produto.id_categoria = categoria.id
            {where_sql}
            ORDER BY produto.nome
            LIMIT ? OFFSET ?
            """,
            parametros + [por_pagina, offset]
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "admin/listar_produtos.html",
        produtos=produtos,
        pagina=pagina,
        total_paginas=total_paginas,
        total_produtos=total_produtos,
        categorias=categorias,
        busca=busca,
        categoria_selecionada=categoria_selecionada,
        status_selecionado=status_selecionado
    )




# =========================================================
# CATÁLOGO PÚBLICO - CATEGORIAS
# =========================================================

@app.route("/catalogo")
def catalogoPublico():
    conn = conexao()

    categorias = conn.execute(
        """
        SELECT id, nome, descricao, imagem
        FROM categoria
        WHERE (
            ativo = 1
            OR LOWER(CAST(ativo AS TEXT)) IN ('true', 'on')
        )
        ORDER BY nome
        """
    ).fetchall()

    conn.close()

    return render_template(
        "categorias_publicas.html",
        categorias=categorias
    )


# =========================================================
# CATÁLOGO PÚBLICO - PRODUTOS DA CATEGORIA
# =========================================================

@app.route("/catalogo/categoria/<int:categoria_id>")
def produtosDaCategoria(categoria_id):
    conn = conexao()

    categoria = conn.execute(
        """
        SELECT id, nome, descricao, imagem
        FROM categoria
        WHERE id = ?
          AND (
              ativo = 1
              OR LOWER(CAST(ativo AS TEXT)) IN ('true', 'on')
          )
        """,
        (categoria_id,)
    ).fetchone()

    if categoria is None:
        conn.close()
        flash("Categoria não encontrada ou inativa.", "warning")
        return redirect(url_for("catalogoPublico"))

    produtos = conn.execute(
        """
        SELECT id, nome, preco, imagem
        FROM produto
        WHERE id_categoria = ?
          AND (
              ativo = 1
              OR LOWER(CAST(ativo AS TEXT)) IN ('true', 'on')
          )
        ORDER BY nome
        """,
        (categoria_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "catalogo.html",
        produtos=produtos,
        categoria=categoria
    )



# =========================================================
# CADASTRAR PRODUTOS
# =========================================================

@app.route("/cadastrar_produtos", methods=["GET", "POST"])
@administrador_logado
def cadastrarProduto():
    conn = conexao()

    categorias = conn.execute(
        "SELECT * FROM categoria ORDER BY nome"
    ).fetchall()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        preco = request.form.get("preco", "").strip()
        ativo = valor_ativo(request.form.get("ativo"))
        id_categoria = request.form.get("id_categoria") or None

        imagem = request.files.get("imagem")
        imagem_base64 = None

        if imagem and imagem.filename:
            imagem_base64 = base64.b64encode(
                imagem.read()
            ).decode("utf-8")

        if nome and preco:
            try:
                preco_numero = float(preco.replace(",", "."))

                conn.execute(
                    """
                    INSERT INTO produto
                        (nome, preco, ativo, imagem, id_categoria)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        nome,
                        preco_numero,
                        ativo,
                        imagem_base64,
                        id_categoria
                    )
                )

                conn.commit()
                conn.close()

                flash("Produto cadastrado com sucesso!", "success")
                return redirect(url_for("listarProdutos"))

            except ValueError:
                flash("Informe um preço válido.", "danger")
        else:
            flash("Preencha o nome e o preço do produto.", "warning")

    conn.close()

    return render_template(
        "admin/cadastrar_produto.html",
        categorias=categorias
    )


# =========================================================
# EDITAR PRODUTOS
# =========================================================

@app.route("/editarproduto/<int:id>", methods=["GET", "POST"])
@administrador_logado
def editarProduto(id):
    conn = conexao()

    produto = conn.execute(
        "SELECT * FROM produto WHERE id = ?",
        (id,)
    ).fetchone()

    if produto is None:
        conn.close()
        flash("Produto não encontrado.", "warning")
        return redirect(url_for("listarProdutos"))

    categorias = conn.execute(
        "SELECT * FROM categoria ORDER BY nome"
    ).fetchall()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        preco = request.form.get("preco", "").strip()
        ativo = valor_ativo(request.form.get("ativo"))
        id_categoria = request.form.get("id_categoria") or None

        imagem = request.files.get("imagem")

        if nome and preco:
            try:
                preco_numero = float(preco.replace(",", "."))

                if imagem and imagem.filename:
                    imagem_base64 = base64.b64encode(
                        imagem.read()
                    ).decode("utf-8")

                    conn.execute(
                        """
                        UPDATE produto
                        SET nome = ?, preco = ?, ativo = ?,
                            imagem = ?, id_categoria = ?
                        WHERE id = ?
                        """,
                        (
                            nome,
                            preco_numero,
                            ativo,
                            imagem_base64,
                            id_categoria,
                            id
                        )
                    )
                else:
                    conn.execute(
                        """
                        UPDATE produto
                        SET nome = ?, preco = ?, ativo = ?,
                            id_categoria = ?
                        WHERE id = ?
                        """,
                        (
                            nome,
                            preco_numero,
                            ativo,
                            id_categoria,
                            id
                        )
                    )

                conn.commit()
                conn.close()

                flash("Produto atualizado com sucesso!", "success")
                return redirect(url_for("listarProdutos"))

            except ValueError:
                flash("Informe um preço válido.", "danger")
        else:
            flash("Preencha o nome e o preço do produto.", "warning")

    conn.close()

    return render_template(
        "admin/editar_produto.html",
        produto=produto,
        categorias=categorias
    )


# =========================================================
# EXCLUIR PRODUTOS
# =========================================================

@app.route("/excluirproduto/<int:id>", methods=["POST"])
@administrador_logado
def excluirProduto(id):
    conn = conexao()

    conn.execute(
        "DELETE FROM produto WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Produto excluído.", "success")
    return redirect(url_for("listarProdutos"))


# =========================================================
# DASHBOARD ADMINISTRATIVO
# =========================================================

@app.route("/dashboard")
@administrador_logado
def dashboard():
    return render_template("admin/dashboard.html")


# =========================================================
# EXECUTAR A APLICAÇÃO
# =========================================================

if __name__ == "__main__":
    app.run(debug=True, port=5005)
