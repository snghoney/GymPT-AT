from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta
import os

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    phone = db.Column(db.String(20), unique=True)

    def __repr__(self):
        return f'<User {self.name}>'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        session.permanent = True
        name = request.form['name']
        phone = request.form['phone']
        user = User.query.filter_by(name=name).first()
        
        if user is None:
            user = User(name=name, phone=phone)
            db.session.add(user)
            db.session.commit()
        else:
            if user.phone != phone:
                flash('전화번호가 일치하지 않습니다.')
                return redirect(url_for('home'))

        session['name'] = user.name
        session['phone'] = user.phone
        flash('로그인 성공!')
        return redirect(url_for('select'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('name', None)
    session.pop('phone', None)
    flash('로그아웃 되었습니다.')
    return redirect(url_for('home'))

@app.route('/select')
def select():
    if 'name' in session and 'phone' in session:
        name = session['name']
        return render_template('select.html', name=name)
    else:
        flash('로그인이 필요합니다.')
        return redirect(url_for('home'))

@app.route('/rank')
def rank():
    return render_template('rank.html')

@app.route('/anal')
def anal():
    return render_template('anal.html')

@app.route('/exercise3')
def exercise3():
    return render_template('exercise3.html')

if __name__ == '__main__':
    app.run(debug=True)
