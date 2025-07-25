from app import app
from flask import render_template, redirect, url_for, request, flash, session
from models import db, User, ParkingLot, ParkingSpot, Reservation
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('index.html')
    else:
        flash('You need to log in first.')
        return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username= request.form.get('username')
    password= request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        flash('Invalid username or password.')
        return redirect(url_for('login'))
    session['user_id'] = user.id
    flash('Login successful!')
    return redirect(url_for('index'))
    


@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    name= request.form.get('name')

    user= User.query.filter_by(username=username).first()
    if user:
        flash('Username already exists. Please choose a different one.')
        return redirect(url_for('register'))
    
    if password != confirm_password:
        flash('Passwords do not match. Please try again.')
        return redirect(url_for('register'))
    
    if not username or not password :
        flash('All fields are required.')
        return redirect(url_for('register'))
    password_hash= generate_password_hash(password)
    new_user = User(username=username, password_hash=password_hash)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))
