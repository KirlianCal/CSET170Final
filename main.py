from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import logging
import random
import string
import bcrypt
from datetime import date
app = Flask(__name__)
app.secret_key = 'your_secret_key'

conn_str ='mysql://root:cset155@localhost/bankdb'
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

@app.route('/')
def index():
    session.pop('user_id', None)
    return render_template('index.html')

@app.route('/base')
def base():
    return render_template('base.html')

@app.route('/admin_view', methods=['GET', 'POST'])
def admin_view():
    accounts = conn.execute(text('select * from accounts')).fetchall()
    account_nums =  conn.execute(text('select * from approved_users')).all()
    if request.method == 'POST':
        type = request.form['type']
        if type:
            accounts = conn.execute(text("select * from accounts where type = :type"), 
                {'type': type}).all()
            return render_template('adminView.html', accounts=accounts, account_nums=account_nums)
        return render_template('adminView.html', accounts=accounts, account_nums=account_nums)
    return render_template('adminView.html', accounts=accounts, account_nums=account_nums)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            result = conn.execute(text("select * from accounts where username = :username"), 
                {'username': username, 'password': password}).fetchone()
            hashed_password = result[5]
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                user_id = result[0]
                print(user_id)
                session['user_id'] = user_id
                if user_id == 1:
                    return redirect(url_for("admin_view"))
                return redirect(url_for("my_account"))
        except:
            return render_template('login.html', e="Username or password does not match")
    return render_template('login.html')

@app.route('/my_account', methods=['GET', 'POST'])
def my_account():
    user_id = session.get('user_id')
    if user_id:
        account = conn.execute(text('select * from accounts where user_id = :user_id'), {'user_id': user_id}).fetchone()
        account_num =  conn.execute(text('select * from approved_users where user_id = :user_id'), {'user_id': user_id}).fetchone()
        if account[9] == 'A':
            return render_template('wait.html', error='Please wait for verification')
        return render_template('myAccount.html', account=account, account_num=account_num)
    return render_template('index.html')

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if request.method == 'POST':
        deposit = int(request.form['deposit'])
        user_id = session.get('user_id')
        result = conn.execute(text('SELECT * FROM accounts WHERE user_id = :user_id'), {'user_id': user_id}).fetchone()
        old = int(result[7])
        new = old + deposit
        conn.execute(text('UPDATE accounts SET balance = :balance WHERE user_id = :user_id'),
            {'balance': new, 'user_id': user_id})
        conn.commit()
        return render_template('index.html')   
    return render_template('deposit.html')

@app.route('/signout', methods=['POST'])
def signout():
    if request.method == 'POST':
        session['user_id'] = None
        return render_template('index.html')
    
@app.route('/verify', methods=['POST'])
def verify():
    if request.method == 'POST':
        user_id = request.form['user_id']
        conn.execute(text('UPDATE accounts SET type = :type WHERE user_id = :user_id'),
            {'type': 'B', 'user_id': user_id})
        account_num = random.randint(10000000, 99999999)
        while True:
            numcheck = conn.execute(text('select account_num from approved_users where account_num = :account_num'),
                    {'account_num': account_num}).fetchall()
            # print(f'***{numcheck}***')
            if len(numcheck) > 0:
                account_num = random.randint(10000000, 99999999)
            break
        conn.execute(text("INSERT INTO approved_users (account_num, user_id) VALUES (:account_num, :user_id)"), {
                'account_num': account_num, 
                'user_id': user_id, 
            })
        conn.commit()
        accounts = conn.execute(text('select * from accounts')).fetchall()
        return render_template('adminView.html', accounts = accounts)

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
                return redirect(url_for("my_account"))

        except Exception as e:
            return render_template('signup.html', error=str(e))
    
    return render_template('signup.html')


@app.route('/transactions', methods=['GET', 'POST'])
def transactions():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    account = conn.execute(text('''
        SELECT au.account_num, a.user_id, a.username, a.balance 
        FROM approved_users au
        JOIN accounts a ON au.user_id = a.user_id
        WHERE a.user_id = :user_id
    '''), {'user_id': user_id}).fetchone()

    if request.method == 'POST':
        recipient_account_num = int(request.form['recipient_account_num'])
        amount = int(request.form['amount'])

        recipient = conn.execute(text('''
            SELECT au.account_num, a.user_id, a.username, a.balance 
            FROM approved_users au
            JOIN accounts a ON au.user_id = a.user_id
            WHERE au.account_num = :account_num
        '''), {'account_num': recipient_account_num}).fetchone()

        if recipient is None:
            return render_template('transactions.html', account=account, error="Recipient not found.")
        if recipient.user_id == account.user_id:
            return render_template('transactions.html', account=account, error="You cannot send money to yourself.")
        if amount > account.balance:
            return render_template('transactions.html', account=account, error="Insufficient balance.")

        new_sender_balance = account.balance - amount
        new_recipient_balance = recipient.balance + amount
        conn.execute(text('UPDATE accounts SET balance = :balance WHERE user_id = :user_id'),
                    {'balance': new_sender_balance, 'user_id': account.user_id})
        conn.execute(text('UPDATE accounts SET balance = :balance WHERE user_id = :user_id'),
                    {'balance': new_recipient_balance, 'user_id': recipient.user_id})
        conn.commit()
        return render_template('transactions.html', account=account, success="Transaction successful!")

    return render_template('transactions.html', account=account)



if __name__ == '__main__':
    app.run(debug=True)

    