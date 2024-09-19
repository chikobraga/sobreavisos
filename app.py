from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
from io import BytesIO
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'seu_seguro_key_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos e Banco de Dados (models.py)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class OverTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    work_entries = db.relationship('WorkEntry', backref='overtime', lazy=True)

class WorkEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    overtime_id = db.Column(db.Integer, db.ForeignKey('over_time.id'), nullable=False)
    entry_time = db.Column(db.String(50), nullable=False)
    exit_time = db.Column(db.String(50), nullable=False)

# Formulários (forms.py) - Usando Flask-WTF ou criar manualmente
# A lógica de registro, login e logout
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = request.form.get('is_admin', False)
        new_user = User(username=username, password=password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login inválido. Tente novamente.')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    overtimes = OverTime.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html', overtimes=overtimes)

@app.route('/admin')
@login_required
def admin():
    if current_user.is_admin:
        users = User.query.all()
        return render_template('admin.html', users=users)
    return redirect(url_for('dashboard'))

# Rota para adicionar sobreaviso
@app.route('/add_overtime', methods=['POST'])
@login_required
def add_overtime():
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    new_overtime = OverTime(user_id=current_user.id, date=date, start_time=start_time, end_time=end_time)
    db.session.add(new_overtime)
    db.session.commit()
    return redirect(url_for('dashboard'))

# Rota para adicionar entradas de trabalho
@app.route('/add_work_entry/<int:overtime_id>', methods=['POST'])
@login_required
def add_work_entry(overtime_id):
    entry_time = request.form['entry_time']
    exit_time = request.form['exit_time']
    new_work_entry = WorkEntry(overtime_id=overtime_id, entry_time=entry_time, exit_time=exit_time)
    db.session.add(new_work_entry)
    db.session.commit()
    return redirect(url_for('dashboard'))

# Exportar para Excel
@app.route('/export', methods=['GET'])
@login_required
def export():
    overtimes = OverTime.query.filter_by(user_id=current_user.id).all()
    data = []
    for overtime in overtimes:
        for work_entry in overtime.work_entries:
            data.append({
                'Date': overtime.date,
                'Start Time': overtime.start_time,
                'End Time': overtime.end_time,
                'Entry Time': work_entry.entry_time,
                'Exit Time': work_entry.exit_time
            })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    output.seek(0)
    return send_file(output, attachment_filename='overtime_report.xlsx', as_attachment=True)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
