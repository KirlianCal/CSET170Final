from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import logging
import random
import string
import bcrypt
app = Flask(__name__)
app.secret_key = 'your_secret_key'

conn_str ='mysql://root:cset155@localhost/bankdb'
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

@app.route('/')
def index():
        user_id = session.get('user_id')
        return render_template('index.html', user_id = user_id)

@app.route('/base')
def base():
        return render_template('base.html')

@app.route('/admin_view', methods=['GET', 'POST'])
def admin_view():
    accounts = conn.execute(text('select * from accounts')).fetchall()
    return render_template('adminView.html', accounts=accounts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        result = conn.execute(text("select * from accounts where username = :username"), 
            {'username': username, 'password': password}).fetchone()
        hashed_password = result[5]
        print(f'***{hashed_password}***')
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            user_id = result[0]
            print(user_id)
            session['user_id'] = user_id
            return redirect(url_for("index"))
    return render_template('login.html')

@app.route('/my_account', methods=['GET', 'POST'])
def my_account():
    user_id = session.get('user_id')
    if user_id:
        account = conn.execute(text('select * from accounts where user_id = :user_id'), {'user_id': user_id}).fetchone()
        return render_template('myAccount.html', account=account)
    return render_template('index.html')

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if request.method == 'POST':
        deposit = int(request.form['deposit'])
        user_id = session.get('user_id')
        result = conn.execute(text('SELECT * FROM accounts WHERE user_id = :user_id'), {'user_id': user_id}).fetchone()
        print(f'***{result}***')
        old = int(result[7])
        print(f'***{old}***')
        new = old + deposit
        conn.execute(text('UPDATE accounts SET balance = :balance WHERE user_id = :user_id'),
            {'balance': new, 'user_id': user_id})
        conn.commit()
        return render_template('index.html')   
    return render_template('deposit.html')

@app.route('/signout', methods=['POST'])
def process():
    if request.method == 'POST':
        session['user_id'] = None
        return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        ssn = request.form['ssn']
        ssn = f"{ssn[:3]}-{ssn[3:5]}-{ssn[5:]}"
        address = request.form['address']
        phone_num = request.form['phone_num']
        phone_num = f"{phone_num[:3]}-{phone_num[3:6]}-{phone_num[6:]}"
        password = request.form['password']

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

        try:
            conn.execute(text("""
                INSERT INTO accounts 
                (first_name, last_name, phone_num, username, password, ssn, balance, address, type) 
                VALUES (:first_name, :last_name, :phone_num, :username, :password, :ssn, 0, :address, 'A')
            """), {
                'first_name': first_name, 'last_name': last_name, 
                'phone_num': phone_num, 'username': username, 
                'password': hashed_password.decode('utf-8'),
                'ssn': ssn, 'address': address
            })
            conn.commit()

            result = conn.execute(text("SELECT * FROM accounts WHERE username = :username"), 
                {'username': username}).fetchone()
            
            if result:
                user_id = result[0]
                session['user_id'] = user_id 
                return redirect(url_for("index"))

        except Exception as e:
            return render_template('signup.html', error=str(e))
    
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True)