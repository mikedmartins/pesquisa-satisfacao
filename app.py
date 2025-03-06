from flask import Flask, request, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feedback.db'  # Usando SQLite para simplicidade
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))          # Opcional
    whatsapp = db.Column(db.String(15))       # Opcional
    pergunta1 = db.Column(db.Integer, nullable=False)
    pergunta2 = db.Column(db.Integer, nullable=False)
    pergunta3 = db.Column(db.Integer, nullable=False)
    pergunta4 = db.Column(db.Text)            # Resposta aberta para "produto não encontrado"
    pergunta5 = db.Column(db.Integer, nullable=False)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/pesquisa_satisfacao', methods=['GET', 'POST'])
def pesquisa_satisfacao():
    if request.method == 'POST':
        # Perguntas obrigatórias
        p1 = request.form.get('pergunta1')
        p2 = request.form.get('pergunta2')
        p3 = request.form.get('pergunta3')
        p5 = request.form.get('pergunta5')

        # Pergunta 4 (sim/não)
        p4_radio = request.form.get('pergunta4_radio')
        if p4_radio == 'sim':
            p4 = request.form.get('pergunta4_text')
        else:
            p4 = ''

        # Identificação opcional
        nome = request.form.get('nome')
        whatsapp = request.form.get('whatsapp')

        # Validação das obrigatórias
        if not all([p1, p2, p3, p5]):
            flash('Por favor, responda as perguntas obrigatórias.', 'danger')
            return redirect(url_for('pesquisa_satisfacao'))

        try:
            # Salvar no banco
            novo_feedback = Feedback(
                nome=nome,
                whatsapp=whatsapp,
                pergunta1=int(p1),
                pergunta2=int(p2),
                pergunta3=int(p3),
                pergunta4=p4,
                pergunta5=int(p5)
            )
            db.session.add(novo_feedback)
            db.session.commit()

            # Redireciona com thankyou=1 para mostrar o modal
            return redirect(url_for('pesquisa_satisfacao', thankyou=1))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Erro ao registrar feedback: {e}')
            flash('Erro ao enviar o feedback. Tente novamente.', 'danger')
            return redirect(url_for('pesquisa_satisfacao'))

    # GET
    thankyou = request.args.get('thankyou')
    return render_template('pesquisa_satisfacao.html', thankyou=thankyou)

@app.route('/relatorio_pesquisa')
def relatorio_pesquisa():
    # Verifica se o usuário está logado (opcional, dependendo da sua aplicação)
    if 'user' not in session:
        flash('Acesso negado. Por favor, faça login.', 'danger')
        return redirect(url_for('login'))

    # Obter filtros de data (formato 'YYYY-MM-DD')
    data_inicial_str = request.args.get('data_inicial')
    data_final_str = request.args.get('data_final')

    # Se os filtros estiverem presentes, converte para datetime e filtra
    if data_inicial_str and data_final_str:
        try:
            # Início do dia da data_inicial
            data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d')
            # Final do dia da data_final: 23:59:59
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            feedbacks = Feedback.query.filter(Feedback.data_registro.between(data_inicial, data_final)).all()
        except Exception as e:
            flash("Erro no formato de data. Por favor, tente novamente.", "danger")
            feedbacks = Feedback.query.all()
    else:
        feedbacks = Feedback.query.all()

    # Contadores para perguntas 1, 2, 3 e 5 (valores de 1 a 5)
    p1_counts = [0, 0, 0, 0, 0]
    p2_counts = [0, 0, 0, 0, 0]
    p3_counts = [0, 0, 0, 0, 0]
    p5_counts = [0, 0, 0, 0, 0]

    identificados = []          # Apenas nome/whatsapp
    produtos_faltantes = []     # Respostas da pergunta 4
    identificados_detalhes = [] # Lista completa de feedbacks de quem se identificou

    for f in feedbacks:
        # Atualiza contagens para as respostas (1 a 5)
        if 1 <= f.pergunta1 <= 5:
            p1_counts[f.pergunta1 - 1] += 1
        if 1 <= f.pergunta2 <= 5:
            p2_counts[f.pergunta2 - 1] += 1
        if 1 <= f.pergunta3 <= 5:
            p3_counts[f.pergunta3 - 1] += 1
        if 1 <= f.pergunta5 <= 5:
            p5_counts[f.pergunta5 - 1] += 1

        # Se houver texto em pergunta4, adiciona na lista de produtos faltantes
        if f.pergunta4 and f.pergunta4.strip():
            produtos_faltantes.append(f.pergunta4.strip())

        # Verifica se o feedback contém identificação
        tem_nome = (f.nome and f.nome.strip())
        tem_whatsapp = (f.whatsapp and f.whatsapp.strip())
        if tem_nome or tem_whatsapp:
            # Lista simples
            identificados.append({
                'nome': f.nome or '',
                'whatsapp': f.whatsapp or ''
            })
            # Converter data_registro para GMT-3 (assumindo que f.data_registro está em GMT)
            data_local = f.data_registro - timedelta(hours=3)
            identificados_detalhes.append({
                'nome': f.nome or '',
                'whatsapp': f.whatsapp or '',
                'p1': f.pergunta1,
                'p2': f.pergunta2,
                'p3': f.pergunta3,
                'p4': f.pergunta4 or '',
                'p5': f.pergunta5,
                'data_registro': data_local  # datetime ajustado para GMT-3
            })

    return render_template(
        'relatorio_pesquisa.html',
        p1_counts=p1_counts,
        p2_counts=p2_counts,
        p3_counts=p3_counts,
        p5_counts=p5_counts,
        identificados=identificados,
        produtos_faltantes=produtos_faltantes,
        identificados_detalhes=identificados_detalhes
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)