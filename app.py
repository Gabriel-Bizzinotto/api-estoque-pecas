import os
import cloudinary
import cloudinary.uploader
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv

# Carrega variáveis de ambiente (se houver arquivo .env)
load_dotenv()

app = Flask(__name__)
# Configuração do CORS para evitar erros de acesso entre PC e Celular
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

# --- MODELO DO BANCO DE DADOS ---
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

# --- ROTAS DE VISUALIZAÇÃO (PARA ABRIR O SITE) ---

@app.route('/')
def home():
    # Abre o cadastro (deve estar em /templates/index.html)
    return render_template('index.html')

@app.route('/catalogo')
def abrir_catalogo():
    # Abre o estoque (deve estar em /templates/catalogo.html)
    return render_template('catalogo.html')

# --- ROTAS DA API ---

# 1. LISTAR PEÇAS
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

# 2. CADASTRAR PEÇA (Com Otimização de Imagem)
@app.route('/api/pecas', methods=['POST'])
def cadastrar_peca():
    try:
        nome = request.form.get('nome')
        codigo = request.form.get('codigo_part_number')
        marca = request.form.get('marca')
        veiculo = request.form.get('veiculo')
        ano = request.form.get('ano')
        valor = request.form.get('valor')
        estoque = request.form.get('estoque', 0)
        categoria = request.form.get('categoria', 'Geral')
        
        foto_url = None
        if 'foto' in request.files:
            foto_arquivo = request.files['foto']
            if foto_arquivo.filename != '':
                # Upload com Redimensionamento para economizar espaço no plano Free
                upload_result = cloudinary.uploader.upload(
                    foto_arquivo, 
                    folder="mais-caminhonete",
                    transformation=[
                        {'width': 1000, 'crop': "limit"}, # Limita largura a 1000px
                        {'quality': "auto"}               # Qualidade automática (leve)
                    ]
                )
                foto_url = upload_result['secure_url']

        nova_peca = Peca(nome=nome, codigo_part_number=codigo, marca=marca, 
                         veiculo=veiculo, ano=ano, valor=valor, estoque=estoque, 
                         categoria=categoria, foto_url=foto_url)
        db.session.add(nova_peca)
        db.session.commit()
        return jsonify({"mensagem": "Sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"mensagem": "Erro", "erro": str(e)}), 400

# 3. EDITAR PEÇA (Incluindo campo código)
@app.route('/api/pecas/<int:id>', methods=['PUT'])
def editar_peca(id):
    try:
        peca = Peca.query.get(id)
        if not peca:
            return jsonify({"mensagem": "Não encontrada"}), 404
        
        dados = request.get_json()
        
        if 'nome' in dados: peca.nome = dados['nome']
        if 'codigo_part_number' in dados: peca.codigo_part_number = dados['codigo_part_number']
        if 'marca' in dados: peca.marca = dados['marca']
        if 'veiculo' in dados: peca.veiculo = dados['veiculo']
        if 'ano' in dados: peca.ano = dados['ano']
        if 'valor' in dados: peca.valor = dados['valor']
        if 'estoque' in dados: peca.estoque = int(dados['estoque'])
        if 'categoria' in dados: peca.categoria = dados['categoria']

        db.session.commit()
        return jsonify({"mensagem": "OK"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"mensagem": "Erro", "erro": str(e)}), 400

# 4. EXCLUIR PEÇA
@app.route('/api/pecas/<int:id>', methods=['DELETE'])
def excluir_peca(id):
    try:
        peca = Peca.query.get(id)
        if peca:
            db.session.delete(peca)
            db.session.commit()
            return jsonify({"mensagem": "Excluído"}), 200
        return jsonify({"mensagem": "Erro"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"mensagem": "Erro", "erro": str(e)}), 500

if __name__ == '__main__':
    # Roda em 0.0.0.0 para permitir acesso via IP do Wi-Fi
    app.run(host='0.0.0.0', port=5000, debug=True)