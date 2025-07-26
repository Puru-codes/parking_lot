from app import app
from flask import  render_template, redirect, url_for, request, flash, session
from models import db, User, ParkingLot, ParkingSpot, Reservation
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime



def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login'))
    return inner

def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session and session.get('is_admin') == True:
            return func(*args, **kwargs)
        else:
            flash('Admin access required. Please log in as an administrator.', 'danger')
            return redirect(url_for('login'))
    return inner

# --- All routes now use @main_routes_blueprint.route ---

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        flash('Invalid username or password.', 'danger')
        return redirect(url_for('login'))

    session['user_id'] = user.id
    session['is_admin'] = user.is_admin
    session['username'] = user.username

    flash('Login successful!', 'success')

    if user.is_admin:
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('profile'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    name = request.form.get('name')
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    user_exists = User.query.filter_by(username=username).first()
    if user_exists:
        flash('Username already exists. Please choose a different one.', 'danger')
        return redirect(url_for('register'))

    if password != confirm_password:
        flash('Passwords do not match. Please try again.', 'danger')
        return redirect(url_for('register'))

    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('register'))

    if not all([username, password, email, name]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('register'))

    new_user = User(username=username, email=email, name=name, is_admin=False)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    flash('Registration successful! Please login.', 'success')
    return redirect(url_for('login'))

@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- General User Routes ---

@app.route('/')
@auth_required
def index():
    if session.get('is_admin'):
        return redirect(url_for('admin'))
    return render_template('index.html')

@app.route('/profile')
@auth_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile', methods=['POST'])
@auth_required
def profile_post():
    current_user_id = session.get('user_id')
    user = User.query.get(current_user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    username = request.form.get('username')
    cpassword = request.form.get('cpassword')
    new_password = request.form.get('password')

    if not username or not cpassword or not new_password:
        flash('All fields are required to update profile.', 'danger')
        return redirect(url_for('profile'))

    if not user.check_password(cpassword):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile'))

    if username != user.username:
        existing_user_with_new_username = User.query.filter(
            User.username == username,
            User.id != user.id
        ).first()
        if existing_user_with_new_username:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('profile'))

    user.username = username
    user.set_password(new_password)
    db.session.commit()
    session['username'] = user.username
    flash('Profile updated successfully.', 'success')
    return redirect(url_for('profile'))

# --- ADMIN ROUTES ---

@app.route('/admin')
@admin_required
def admin():
    parking_lots = ParkingLot.query.all()
    return render_template('admin.html', parking_lots=parking_lots)

@app.route('/admin/parking_lot/add', methods=['GET', 'POST'])
@admin_required
def add_parking_lot():
    if request.method == 'POST':
        prime_location_name = request.form.get('prime_location_name')
        address = request.form.get('address')
        pin_code = request.form.get('pin_code')
        price_str = request.form.get('price')
        maximum_number_of_spots_str = request.form.get('maximum_number_of_spots')

        if not all([prime_location_name, address, pin_code, price_str, maximum_number_of_spots_str]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('parking_lot_form.html', parking_lot=None)

        try:
            price = float(price_str)
            maximum_number_of_spots = int(maximum_number_of_spots_str)
            if price <= 0 or maximum_number_of_spots <= 0:
                flash('Price and maximum spots must be positive numbers.', 'danger')
                return render_template('parking_lot_form.html', parking_lot=None)
        except ValueError:
            flash('Invalid numbers for price or maximum spots.', 'danger')
            return render_template('parking_lot_form.html', parking_lot=None)

        existing_lot = ParkingLot.query.filter_by(prime_location_name=prime_location_name).first()
        if existing_lot:
            flash(f'A parking lot with the name "{prime_location_name}" already exists.', 'danger')
            return render_template('parking_lot_form.html', parking_lot=None)

        new_lot = ParkingLot(
            prime_location_name=prime_location_name,
            address=address,
            pin_code=pin_code,
            price=price,
            maximum_number_of_spots=maximum_number_of_spots,
        )
        db.session.add(new_lot)
        db.session.commit()

        for i in range(1, new_lot.maximum_number_of_spots + 1):
            new_spot = ParkingSpot(lot_id=new_lot.id, spot_number=i, status='A')
            db.session.add(new_spot)
        db.session.commit()

        flash('Parking Lot added successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('parking_lot_form.html', parking_lot=None)

@app.route('/admin/parking_lot/edit/<int:lot_id>', methods=['GET', 'POST'])
@admin_required
def edit_parking_lot(lot_id):
    parking_lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        prime_location_name = request.form.get('prime_location_name')
        address = request.form.get('address')
        pin_code = request.form.get('pin_code')
        price_str = request.form.get('price')

        if not all([prime_location_name, address, pin_code, price_str]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('parking_lot_form.html', parking_lot=parking_lot)

        try:
            price = float(price_str)
            if price <= 0:
                flash('Price must be a positive number.', 'danger')
                return render_template('parking_lot_form.html', parking_lot=parking_lot)
        except ValueError:
            flash('Invalid number for price.', 'danger')
            return render_template('parking_lot_form.html', parking_lot=parking_lot)

        existing_lot = ParkingLot.query.filter(
            ParkingLot.prime_location_name == prime_location_name,
            ParkingLot.id != lot_id
        ).first()
        if existing_lot:
            flash(f'A parking lot with the name "{prime_location_name}" already exists.', 'danger')
            return render_template('parking_lot_form.html', parking_lot=parking_lot)

        parking_lot.prime_location_name = prime_location_name
        parking_lot.address = address
        parking_lot.pin_code = pin_code
        parking_lot.price = price
        db.session.commit()

        flash('Parking Lot updated successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('parking_lot_form.html', parking_lot=parking_lot)

@app.route('/admin/parking_lot/delete/<int:lot_id>', methods=['POST'])
@admin_required
def delete_parking_lot(lot_id):
    parking_lot = ParkingLot.query.get_or_404(lot_id)

    occupied_spots_count = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').count()
    if occupied_spots_count > 0:
        flash(f'Cannot delete parking lot "{parking_lot.prime_location_name}" because there are {occupied_spots_count} occupied spots.', 'danger')
        return redirect(url_for('admin'))

    try:
        db.session.delete(parking_lot)
        db.session.commit()
        flash(f'Parking Lot "{parking_lot.prime_location_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting parking lot: {e}', 'danger')

    return redirect(url_for('admin'))

@app.route('/admin/parking_lot/<int:lot_id>/spots')
@admin_required
def manage_parking_spots(lot_id):
    parking_lot = ParkingLot.query.get_or_404(lot_id)
    parking_spots = ParkingSpot.query.filter_by(lot_id=lot_id).order_by(ParkingSpot.spot_number).all()

    return render_template('manage_spots.html', parking_lot=parking_lot, parking_spots=parking_spots)
# from app import app
# from flask import render_template, redirect, url_for, request, flash, session
# from models import db, User, ParkingLot, ParkingSpot, Reservation
# from werkzeug.security import generate_password_hash, check_password_hash
# from functools import wraps


# @app.route('/login')
# def login():
#     return render_template('login.html')

# @app.route('/login', methods=['POST'])
# def login_post():
#     username= request.form.get('username')
#     password= request.form.get('password')
#     user = User.query.filter_by(username=username).first()
#     if not user or not check_password_hash(user.password_hash, password):
#         flash('Invalid username or password.')
#         return redirect(url_for('login'))
#     session['user_id'] = user.id
#     session['is_admin'] = user.is_admin
#     flash('Login successful!')
#     return redirect(url_for('profile'))
    


# @app.route('/register')
# def register():
#     return render_template('register.html')

# @app.route('/register', methods=['POST'])
# def register_post():
#     username = request.form.get('username')
#     password = request.form.get('password')
#     confirm_password = request.form.get('confirm_password')
#     name= request.form.get('name')

#     user= User.query.filter_by(username=username).first()
#     if user:
#         flash('Username already exists. Please choose a different one.')
#         return redirect(url_for('register'))
    
#     if password != confirm_password:
#         flash('Passwords do not match. Please try again.')
#         return redirect(url_for('register'))
    
#     if not username or not password :
#         flash('All fields are required.')
#         return redirect(url_for('register'))
#     password_hash= generate_password_hash(password)
#     new_user = User(username=username, password_hash=password_hash)
#     db.session.add(new_user)
#     db.session.commit()
#     return redirect(url_for('login'))

# def auth_required(func):
#     @wraps(func)
#     def inner(*args, **kwargs):
#         if 'user_id' in session:
#             return func(*args, **kwargs)
#         else:
#             flash('You need to log in first.')
#             return redirect(url_for('login'))
#     return inner




# @app.route('/')
# @auth_required
# def index():
#     return render_template('index.html')
    

# @app.route('/profile')
# @auth_required
# def profile():
#     user=User.query.get(session['user_id'])
#     return render_template('profile.html',user=user)

# @app.route('/profile', methods=['POST'])
# @auth_required
# def profile_post():
#     username= request.form.get('username')
#     cpassword=request.form.get('cpassword')
#     password=request.form.get('password')

#     if not username or not cpassword or not password:
#         flash('All fields are required.')
#         return redirect(url_for('profile'))
    
#     user=User.query.get(session['user_id'])
#     if not check_password_hash(user.password_hash, cpassword):
#         flash('Current password is incorrect.')
#         return redirect(url_for('profile'))
    
#     if username!= user.username:
#         new_user = User.query.filter_by(username=username).first()
#         if new_user:
#             flash('Username already exists. Please choose a different one.')
#             return redirect(url_for('profile'))
        
#     user.username = username
#     user.password_hash = generate_password_hash(password)
#     db.session.commit()
#     flash('Profile updated successfully.')
#     return redirect(url_for('profile'))


# @app.route('/logout')
# @auth_required
# def logout():
#     session.pop('user_id')
#     return redirect(url_for('login'))