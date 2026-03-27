import os
import cloudinary
import cloudinary.uploader
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Permite que o celular acesse o PC e o banco sem bloqueios de segurança
CORS(app)

# --- CONFIGURAÇÃO CLOUDINARY ---
cloudinary.config( 
  cloud_name = "dhm3xue11", 
  api_key = "689934283739685", 
  api_secret = "3AuHv8AXwDk1iXH-5gT-JEbIu1c", 
  secure = True
)

# --- CONEXÃO SUPABASE / POSTGRES ---
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

# --- ROTAS DE PÁGINAS ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/catalogo')
def abrir_catalogo():
    return render_template('catalogo.html')

# --- API (CONTROLE DE DADOS) ---

@app.route('/api/pecas', methods=['GET'])
def listar_pecas():
    pecas = Peca.query.order_by(Peca.nome.asc()).all()
    resultado = []
    for peca in pecas:
        resultado.append({
            "id": peca.id, 
            "nome": peca.nome, 
            "codigo_part_number": peca.codigo_part_number,
            "marca": peca.marca, 
            "veiculo": peca.veiculo, 
            "ano": peca.ano,
            "valor": float(peca.valor), 
            "estoque": peca.estoque, 
            "categoria": peca.categoria, 
            "foto_url": peca.foto_url
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
        return jsonify({"erro": f"O código '{codigo}' já está cadastrado."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 400

@app.route('/api/pecas/<int:id>', methods=['PUT', 'DELETE'])
def gerenciar_peca(id):
    peca = Peca.query.get(id)
    if not peca: 
        return jsonify({"erro": "Peça não encontrada"}), 404
    
    # --- LÓGICA DE EXCLUSÃO (BANCO + CLOUDINARY) ---
    if request.method == 'DELETE':
        try:
            if peca.foto_url:
                # Extrai o public_id: pega o nome do arquivo da URL e adiciona a pasta
                # Ex URL: .../mais-caminhonete/abc123.jpg -> Public ID: mais-caminhonete/abc123
                filename = peca.foto_url.split('/')[-1].split('.')
                public_id = f"mais-caminhonete/{filename}"
                cloudinary.uploader.destroy(public_id)
            
            db.session.delete(peca)
            db.session.commit()
            return jsonify({"mensagem": "Peça e Foto removidas com sucesso!"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"erro": f"Erro ao excluir: {str(e)}"}), 400
    
    # --- LÓGICA DE EDIÇÃO ---
    try:
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
        return jsonify({"mensagem": "Atualizado com sucesso!"}), 200
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({"erro": "Este código já pertence a outra peça."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)