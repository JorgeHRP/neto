from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client
from dotenv import load_dotenv
import os
from functools import wraps
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Credenciais
ADMIN_USER = os.getenv("ADMIN_USERNAME")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('home'))
        flash('Login incorreto!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    try:
        response = supabase.table('orcamentos').select('*').order('created_at', desc=True).execute()
        orcamentos = response.data or []
    except:
        orcamentos = []
    return render_template('home.html', orcamentos=orcamentos)

@app.route('/blocos')
@login_required
def blocos():
    try:
        response = supabase.table('blocos_salvos').select('*').order('nome').execute()
        blocos = response.data or []
    except:
        blocos = []
    return render_template('blocos.html', blocos=blocos)

@app.route('/blocos/novo', methods=['POST'])
@login_required
def novo_bloco():
    try:
        data = {
            'nome': request.form['nome'],
            'unidade': request.form['unidade'],
            'preco_unitario': float(request.form['preco_unitario'])
        }
        supabase.table('blocos_salvos').insert(data).execute()
        flash('Bloco salvo!', 'success')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('blocos'))

@app.route('/blocos/<int:id>/deletar', methods=['POST'])
@login_required
def deletar_bloco(id):
    try:
        supabase.table('blocos_salvos').delete().eq('id', id).execute()
        flash('Bloco deletado!', 'success')
    except:
        flash('Erro ao deletar!', 'danger')
    return redirect(url_for('blocos'))

@app.route('/criar', methods=['GET', 'POST'])
@login_required
def criar_orcamento():
    if request.method == 'POST':
        try:
            itens = json.loads(request.form['itens'])
            total = sum(float(item['valor']) for item in itens)
            iva_percent = float(request.form.get('iva', 6))
            valor_iva = total * (iva_percent / 100)
            total_com_iva = total + valor_iva
            
            # Gerar ou validar número do orçamento
            numero_base = request.form.get('numero', '').strip()
            
            if not numero_base:
                # Gerar automaticamente
                from datetime import datetime
                nome_cliente = request.form.get('nome_cliente', '')
                # Limpar nome do cliente (apenas letras e números)
                nome_limpo = ''.join(c for c in nome_cliente.upper() if c.isalnum() or c.isspace())
                nome_limpo = '-'.join(nome_limpo.split())[:20]  # Max 20 chars
                
                agora = datetime.now()
                data_hora = agora.strftime('%d%m%Y-%H%M')
                numero_base = f"{nome_limpo}-{data_hora}"
            
            # Validar se número já existe e adicionar sufixo se necessário
            numero_final = numero_base
            contador = 1
            
            while True:
                try:
                    response = supabase.table('orcamentos').select('id').eq('numero', numero_final).execute()
                    if not response.data or len(response.data) == 0:
                        break  # Número disponível
                    # Número existe, tentar próximo
                    contador += 1
                    numero_final = f"{numero_base}-{contador}"
                except:
                    break
            
            data = {
                'numero': numero_final,
                'nome_cliente': request.form['nome_cliente'],
                'telefone': request.form.get('telefone', ''),
                'local_obra': request.form.get('local_obra', ''),
                'itens': itens,
                'total': total,
                'iva': iva_percent,
                'total_com_iva': total_com_iva
            }
            
            supabase.table('orcamentos').insert(data).execute()
            flash(f'Orçamento {numero_final} criado com sucesso!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')
    
    try:
        response = supabase.table('blocos_salvos').select('*').order('nome').execute()
        blocos = response.data or []
    except:
        blocos = []
    
    return render_template('criar.html', blocos=blocos)

@app.route('/orcamento/<int:id>')
@login_required
def ver_orcamento(id):
    try:
        response = supabase.table('orcamentos').select('*').eq('id', id).execute()
        orcamento = response.data[0] if response.data else None
        if not orcamento:
            flash('Orçamento não encontrado!', 'danger')
            return redirect(url_for('home'))
    except:
        flash('Erro ao carregar!', 'danger')
        return redirect(url_for('home'))
    
    return render_template('ver.html', orcamento=orcamento)

@app.route('/orcamento/<int:id>/deletar', methods=['POST'])
@login_required
def deletar_orcamento(id):
    try:
        supabase.table('orcamentos').delete().eq('id', id).execute()
        flash('Orçamento deletado!', 'success')
    except:
        flash('Erro ao deletar!', 'danger')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')