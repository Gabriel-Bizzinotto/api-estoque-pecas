import os
import cloudinary
import cloudinary.uploader
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError  # ESSENCIAL PARA O ERRO AMIGÁVEL
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Permite que o celular acesse o PC sem bloqueios
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- CONFIGURAÇÃO CLOUDINARY ---
cloudinary.config( 
  cloud_name = "dhm3xue11", 
  api_key = "689934283739685", 
  api_secret = "3AuHv8AXwDk1iXH-5gT-JEbIu1c", 
  secure = True
)

# --- CONEXÃO SUPABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres.tqjswejrrozegaaplsyl:glZydFHlkynW4UAd@aws-1-sa-east-1.pooler.supabase.com:5432/postgres"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Peca(db.Model):
    __tablename__ = 'pecas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    codigo_part_number = db.Column(db.String(50), unique=True, nullable=False)
    marca = db.Column(db.String(100), nullable=True) 
    veiculo = db.Column(db.String(100), nullable=True)
    ano = db.Column(db.String(50), nullable=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    estoque = db.Column(db.Integer, default=0)
    categoria = db.Column(db.String(50), nullable=True, default="Geral")
    foto_url = db.Column(db.String(255), nullable=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/catalogo')
def abrir_catalogo():
    return render_template('catalogo.html')

# --- API ---

@app.route('/api/pecas', methods=['GET'])
def listar_pecas():
    pecas = Peca.query.order_by(Peca.nome.asc()).all()
    resultado = []
    for peca in pecas:
        resultado.append({
            "id": peca.id, "nome": peca.nome, "codigo_part_number": peca.codigo_part_number,
            "marca": peca.marca, "veiculo": peca.veiculo, "ano": peca.ano,
            "valor": float(peca.valor), "estoque": peca.estoque, 
            "categoria": peca.categoria, "foto_url": peca.foto_url
        })
    return jsonify(resultado), 200

@app.route('/api/pecas', methods=['POST'])
def cadastrar_peca():
    nome = request.form.get('nome')
    codigo = request.form.get('codigo_part_number')
    try:
        valor = request.form.get('valor')
        estoque = int(request.form.get('estoque', 0))
        
        foto_url = None
        if 'foto' in request.files:
            foto_arquivo = request.files['foto']
            if foto_arquivo.filename != '':
                upload_result = cloudinary.uploader.upload(
                    foto_arquivo, 
                    folder="mais-caminhonete",
                    format="jpg", 
                    transformation=[{'width': 1000, 'crop': "limit"}, {'quality': "auto"}]
                )
                foto_url = upload_result['secure_url']

        nova_peca = Peca(
            nome=nome, 
            codigo_part_number=codigo, 
            marca=request.form.get('marca'), 
            veiculo=request.form.get('veiculo'), 
            ano=request.form.get('ano'), 
            valor=valor, 
            estoque=estoque, 
            categoria=request.form.get('categoria', 'Geral'), 
            foto_url=foto_url
        )
        
        db.session.add(nova_peca)
        db.session.commit()
        return jsonify({"mensagem": "Sucesso!"}), 201

    except IntegrityError:
        db.session.rollback()
        # ESSA RESPOSTA É O QUE O CELULAR PRECISA LER
        return jsonify({"erro": f"O código '{codigo}' já está cadastrado em outra peça."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 400

@app.route('/api/pecas/<int:id>', methods=['PUT', 'DELETE'])
def gerenciar_peca(id):
    peca = Peca.query.get(id)
    if not peca: return jsonify({"erro": "Não encontrada"}), 404
    if request.method == 'DELETE':
        db.session.delete(peca)
        db.session.commit()
        return jsonify({"mensagem": "Excluído"}), 200
    try:
        dados = request.get_json()
        if 'estoque' in dados: peca.estoque = int(dados['estoque'])
        db.session.commit()
        return jsonify({"mensagem": "OK"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)