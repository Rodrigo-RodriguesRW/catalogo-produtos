
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

@app.route("/listar_categorias")
@administrador_logado
def listarCategoria():
    conn = conexao()

    categorias = conn.execute(
        "SELECT * FROM categoria ORDER BY id"
    ).fetchall()

    conn.close()

    return render_template(
        "admin/listar_categoria.html",
        categorias=categorias
    )


@app.route("/cadastrar_categorias", methods=["GET", "POST"])
@administrador_logado
def cadastrarCategoria():
    if request.method == "POST":
        nome_categoria = request.form.get("nome_categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        ativo = valor_ativo(request.form.get("ativo"))

        imagem = request.files.get("imagem")
        imagem_base64 = None

        if imagem and imagem.filename:
            imagem_base64 = base64.b64encode(
                imagem.read()
            ).decode("utf-8")

        if nome_categoria:
            conn = conexao()
            conn.execute(
                """
                INSERT INTO categoria
                    (nome, descricao, ativo, imagem)
                VALUES (?, ?, ?, ?)
                """,
                (nome_categoria, descricao, ativo, imagem_base64)
            )
            conn.commit()
            conn.close()

            flash("Categoria cadastrada com sucesso!", "success")
            return redirect(url_for("listarCategoria"))

        flash("Informe o nome da categoria.", "warning")

    return render_template("admin/cadastrar_categoria.html")


@app.route("/editarcategoria/<int:id>", methods=["GET", "POST"])
@administrador_logado
def editarCategoria(id):
    conn = conexao()

    categoria = conn.execute(
        "SELECT * FROM categoria WHERE id = ?",
        (id,)
    ).fetchone()

    if categoria is None:
        conn.close()
        flash("Categoria não encontrada.", "warning")
        return redirect(url_for("listarCategoria"))

    if request.method == "POST":
        nome_categoria = request.form.get("nome_categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        ativo = valor_ativo(request.form.get("ativo"))

        imagem = request.files.get("imagem")

        if nome_categoria:
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
                    (nome_categoria, descricao, ativo, imagem_base64, id)
                )
            else:
                conn.execute(
                    """
                    UPDATE categoria
                    SET nome = ?, descricao = ?, ativo = ?
                    WHERE id = ?
                    """,
                    (nome_categoria, descricao, ativo, id)
                )

            conn.commit()
            conn.close()

            flash("Categoria atualizada com sucesso!", "success")
            return redirect(url_for("listarCategoria"))

        flash("Informe o nome da categoria.", "warning")

    conn.close()

    return render_template(
        "admin/editar_categoria.html",
        categoria=categoria
    )


@app.route("/excluir_categoria/<int:id>", methods=["GET", "POST"])
@administrador_logado
def excluirCategoria(id):
    conn = conexao()

    categoria = conn.execute(
        "SELECT * FROM categoria WHERE id = ?",
        (id,)
    ).fetchone()

    if categoria is None:
        conn.close()
        flash("Categoria não encontrada.", "warning")
        return redirect(url_for("listarCategoria"))

    if request.method == "POST":
        conn.execute(
            "DELETE FROM categoria WHERE id = ?",
            (id,)
        )
        conn.commit()
        conn.close()

        flash("Categoria excluída.", "success")
        return redirect(url_for("listarCategoria"))

    conn.close()

    return render_template(
        "admin/excluir_categoria.html",
        categoria=categoria
    )


# =========================================================
# LISTAGEM ADMINISTRATIVA DE PRODUTOS
# =========================================================

@app.route("/listar_produtos")
@administrador_logado
def listarProdutos():
    conn = conexao()

    produtos = conn.execute(
        """
        SELECT
            produto.*,
            categoria.nome AS nome_categoria
        FROM produto
        LEFT JOIN categoria
            ON produto.id_categoria = categoria.id
        ORDER BY produto.nome
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin/listar_produtos.html",
        produtos=produtos
    )


# =========================================================
# CATÁLOGO PÚBLICO
# =========================================================

@app.route("/catalogo")
def catalogoPublico():
    conn = conexao()

    busca = request.args.get("busca", "").strip()
    categoria_id = request.args.get("categoria", "").strip()

    sql = """
        SELECT
            produto.*,
            categoria.nome AS nome_categoria
        FROM produto
        LEFT JOIN categoria
            ON produto.id_categoria = categoria.id
        WHERE (
            produto.ativo = 1
            OR LOWER(CAST(produto.ativo AS TEXT)) = 'true'
            OR LOWER(CAST(produto.ativo AS TEXT)) = 'on'
        )
    """

    parametros = []

    if busca:
        sql += " AND produto.nome LIKE ?"
        parametros.append(f"%{busca}%")

    if categoria_id.isdigit():
        sql += " AND produto.id_categoria = ?"
        parametros.append(int(categoria_id))

    sql += " ORDER BY produto.nome"

    produtos = conn.execute(sql, parametros).fetchall()

    print("BANCO UTILIZADO:", os.path.abspath("database.db"))
    print("PRODUTOS ENCONTRADOS:", len(produtos), [p["nome"] for p in produtos])
    categorias = conn.execute(
        """
        SELECT id, nome
        FROM categoria
        WHERE (
            ativo = 1
            OR LOWER(CAST(ativo AS TEXT)) = 'true'
            OR LOWER(CAST(ativo AS TEXT)) = 'on'
        )
        ORDER BY nome
        """
    ).fetchall()

    conn.close()

    return render_template(
        "catalogo.html",
        produtos=produtos,
        categorias=categorias,
        busca=busca,
        categoria_selecionada=categoria_id
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
