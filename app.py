from flask import Flask, render_template, redirect, request, url_for
import sqlite3
import base64

app = Flask(__name__)


def conexao():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# INÍCIO
# =========================================================

@app.route("/")
def index():
    return render_template("admin/index.html")


# =========================================================
# CATEGORIAS
# =========================================================

@app.route("/listar_categorias")
def listarCategoria():

    conn = conexao()

    categorias = conn.execute(
        'SELECT * FROM categoria ORDER BY id'
    ).fetchall()

    conn.close()

    return render_template(
        'admin/listar_categoria.html',
        categorias=categorias
    )


@app.route("/cadastrar_categorias", methods=['GET', 'POST'])
def cadastrarCategoria():

    if request.method == 'POST':

        # Pega exatamente o nome digitado no formulário
        nome_categoria = request.form.get('nome_categoria', '').strip()

        descricao = request.form.get('descricao', '').strip()

        ativo = request.form.get('ativo')

        imagem = request.files.get('imagem')

        imagem_base64 = None

        if imagem and imagem.filename != '':
            imagem_base64 = base64.b64encode(
                imagem.read()
            ).decode('utf-8')

        print("================================")
        print("NOME RECEBIDO:", nome_categoria)
        print("DESCRIÇÃO:", descricao)
        print("STATUS:", ativo)
        print("================================")

        if nome_categoria:

            conn = conexao()

            conn.execute(
                '''
                INSERT INTO categoria
                (nome, descricao, ativo, imagem)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    nome_categoria,
                    descricao,
                    ativo,
                    imagem_base64
                )
            )

            conn.commit()
            conn.close()

            return redirect(
                url_for('listarCategoria')
            )

    return render_template(
        'admin/cadastrar_categoria.html'
    )


@app.route("/editarcategoria/<int:id>", methods=['GET', 'POST'])
def editarCategoria(id):

    conn = conexao()

    categoria = conn.execute(
        'SELECT * FROM categoria WHERE id = ?',
        (id,)
    ).fetchone()

    if request.method == 'POST':

        nome_categoria = request.form.get(
            'nome_categoria',
            ''
        ).strip()

        descricao = request.form.get(
            'descricao',
            ''
        ).strip()

        ativo = request.form.get('ativo')

        imagem = request.files.get('imagem')

        if nome_categoria:

            if imagem and imagem.filename != '':

                imagem_base64 = base64.b64encode(
                    imagem.read()
                ).decode('utf-8')

                conn.execute(
                    '''
                    UPDATE categoria
                    SET
                        nome = ?,
                        descricao = ?,
                        ativo = ?,
                        imagem = ?
                    WHERE id = ?
                    ''',
                    (
                        nome_categoria,
                        descricao,
                        ativo,
                        imagem_base64,
                        id
                    )
                )

            else:

                conn.execute(
                    '''
                    UPDATE categoria
                    SET
                        nome = ?,
                        descricao = ?,
                        ativo = ?
                    WHERE id = ?
                    ''',
                    (
                        nome_categoria,
                        descricao,
                        ativo,
                        id
                    )
                )

            conn.commit()
            conn.close()

            return redirect(
                url_for('listarCategoria')
            )

    conn.close()

    return render_template(
        'admin/editar_categoria.html',
        categoria=categoria
    )


@app.route("/excluir_categoria/<int:id>", methods=['GET', 'POST'])
def excluirCategoria(id):

    conn = conexao()

    categoria = conn.execute(
        'SELECT * FROM categoria WHERE id = ?',
        (id,)
    ).fetchone()

    if request.method == 'POST':

        conn.execute(
            'DELETE FROM categoria WHERE id = ?',
            (id,)
        )

        conn.commit()
        conn.close()

        return redirect(
            url_for('listarCategoria')
        )

    conn.close()

    return render_template(
        'admin/excluir_categoria.html',
        categoria=categoria
    )


# =========================================================
# PRODUTOS
# =========================================================

@app.route("/listar_produtos")
def listarProdutos():

    conn = conexao()

    produtos = conn.execute(
        '''
        SELECT
            produto.*,
            categoria.nome AS nome_categoria
        FROM produto
        LEFT JOIN categoria
            ON produto.id_categoria = categoria.id
        '''
    ).fetchall()

    conn.close()

    return render_template(
        'admin/listar_produtos.html',
        produtos=produtos
    )


@app.route("/cadastrar_produtos", methods=['GET', 'POST'])
def cadastrarProduto():

    conn = conexao()

    categorias = conn.execute(
        'SELECT * FROM categoria ORDER BY nome'
    ).fetchall()

    if request.method == 'POST':

        nome = request.form.get('nome')

        preco = request.form.get('preco')

        ativo = request.form.get('ativo')

        id_categoria = request.form.get('id_categoria')

        imagem = request.files.get('imagem')

        imagem_base64 = None

        if imagem and imagem.filename != '':
            imagem_base64 = base64.b64encode(
                imagem.read()
            ).decode('utf-8')

        if nome and preco:

            conn.execute(
                '''
                INSERT INTO produto
                (nome, preco, ativo, imagem, id_categoria)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    nome,
                    preco,
                    ativo,
                    imagem_base64,
                    id_categoria
                )
            )

            conn.commit()
            conn.close()

            return redirect(
                url_for('listarProdutos')
            )

    conn.close()

    return render_template(
        'admin/cadastrar_produto.html',
        categorias=categorias
    )


@app.route("/editarproduto/<int:id>", methods=['GET', 'POST'])
def editarProduto(id):

    conn = conexao()

    produto = conn.execute(
        'SELECT * FROM produto WHERE id = ?',
        (id,)
    ).fetchone()

    categorias = conn.execute(
        'SELECT * FROM categoria ORDER BY nome'
    ).fetchall()

    if request.method == 'POST':

        nome = request.form.get('nome')

        preco = request.form.get('preco')

        ativo = request.form.get('ativo')

        id_categoria = request.form.get('id_categoria')

        imagem = request.files.get('imagem')

        if nome and preco:

            if imagem and imagem.filename != '':

                imagem_base64 = base64.b64encode(
                    imagem.read()
                ).decode('utf-8')

                conn.execute(
                    '''
                    UPDATE produto
                    SET
                        nome = ?,
                        preco = ?,
                        ativo = ?,
                        imagem = ?,
                        id_categoria = ?
                    WHERE id = ?
                    ''',
                    (
                        nome,
                        preco,
                        ativo,
                        imagem_base64,
                        id_categoria,
                        id
                    )
                )

            else:

                conn.execute(
                    '''
                    UPDATE produto
                    SET
                        nome = ?,
                        preco = ?,
                        ativo = ?,
                        id_categoria = ?
                    WHERE id = ?
                    ''',
                    (
                        nome,
                        preco,
                        ativo,
                        id_categoria,
                        id
                    )
                )

            conn.commit()
            conn.close()

            return redirect(
                url_for('listarProdutos')
            )

    conn.close()

    return render_template(
        'admin/editar_produto.html',
        produto=produto,
        categorias=categorias
    )


@app.route("/excluirproduto/<int:id>", methods=['GET'])
def excluirProduto(id):

    conn = conexao()

    conn.execute(
        'DELETE FROM produto WHERE id = ?',
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for('listarProdutos')
    )


# =========================================================
# EXECUTAR
# =========================================================

app.run(
    debug=True,
    port=5005
)