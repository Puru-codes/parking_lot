from app import app
from flask import  render_template, redirect, url_for, request, flash, session
from models import db, User, ParkingLot, ParkingSpot, Reservation
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from sqlalchemy import or_



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
        return redirect(url_for('user_dashboard'))

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


@app.route('/')
@auth_required
def index():
    if session.get('is_admin'):
        return redirect(url_for('admin'))
    return render_template('user_dashboard.html')

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


@app.route('/admin/users')
@admin_required
def admin_users():
    
    users = User.query.filter_by(is_admin=False).order_by(User.name).all()
    return render_template('admin_users.html', title='Registered Users', users=users)

@app.route('/admin/search', methods=['GET', 'POST'])
@admin_required
def admin_search():
    search_results = None
    search_type = ''
    if request.method == 'POST':
        search_by = request.form.get('search_by')
        search_string = request.form.get('search_string')
        search_type = search_by

        if search_string:
            if search_by == 'user_username':
                search_results = User.query.filter(User.username.ilike(f'%{search_string}%')).all()
            elif search_by == 'location':
                search_results = ParkingLot.query.filter(ParkingLot.prime_location_name.ilike(f'%{search_string}%')).all()
        else:
            flash('Please enter a search term.', 'warning')
            
    return render_template('admin_search.html', title='Search', results=search_results, search_type=search_type)

@app.route('/admin/summary')
@admin_required
def admin_summary():
    all_lots = ParkingLot.query.all()
    

    occupancy_labels = [lot.prime_location_name for lot in all_lots]
    occupied_counts = [ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count() for lot in all_lots]
    available_counts = [ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count() for lot in all_lots]
    occupancy_data = {
        "labels": occupancy_labels,
        "occupied": occupied_counts,
        "available": available_counts
    }
    
    revenue_values = []
    for lot in all_lots:
        total_revenue = db.session.query(db.func.sum(Reservation.parking_cost))\
                                  .join(ParkingSpot)\
                                  .filter(ParkingSpot.lot_id == lot.id)\
                                  .scalar() or 0
        revenue_values.append(total_revenue)
        
    revenue_data = {
        "labels": occupancy_labels,
        "values": revenue_values
    }

    return render_template(
        'admin_summary.html',
        title='Summary',
        revenue_data=revenue_data,
        occupancy_data=occupancy_data
    )

@app.route('/admin/parking_spot/delete/<int:spot_id>', methods=['POST'])
@admin_required
def delete_parking_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    if spot.status == 'O':
        flash(f'Cannot delete Spot {spot.spot_number} as it is currently occupied.', 'danger')
        return redirect(url_for('admin'))
        

    lot_name = spot.parking_lot.prime_location_name
    spot_num = spot.spot_number

    db.session.delete(spot)
    db.session.commit()
    
    flash(f'Spot {spot_num} in lot "{lot_name}" has been deleted.', 'success')
    return redirect(url_for('admin'))



@app.route('/dashboard')
@auth_required
def user_dashboard():
    user_id = session['user_id']
    
    
    reservations = Reservation.query.filter_by(user_id=user_id)\
                                    .order_by(Reservation.parking_timestamp.desc()).limit(5).all()
    
    
    search_query = request.args.get('q')
    parking_lots = []
    if search_query:
        
        parking_lots = ParkingLot.query.filter(
            or_(
                ParkingLot.prime_location_name.ilike(f'%{search_query}%'),
                ParkingLot.pin_code.ilike(f'%{search_query}%')
            )
        ).all()
    
    return render_template('user_dashboard.html', reservations=reservations, parking_lots=parking_lots)

@app.route('/book/<int:spot_id>', methods=['GET', 'POST'])
@auth_required
def book_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    
    if spot.status != 'A':
        flash('This spot is already occupied or unavailable.', 'warning')
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number')
        if not vehicle_number:
            flash('Vehicle number is required.', 'danger')
            return redirect(url_for('book_spot', spot_id=spot_id))

        
        new_reservation = Reservation(
            user_id=session['user_id'],
            spot_id=spot.id,
            vechile_number=vehicle_number
        )
        
        
        spot.status = 'O'
        
        db.session.add(new_reservation)
        db.session.commit()
        
        flash(f'Spot {spot.spot_number} at {spot.parking_lot.prime_location_name} booked successfully!', 'success')
        return redirect(url_for('user_dashboard'))
        
    return render_template('book_spot.html', spot=spot, title="Book Spot")

@app.route('/release/<int:reservation_id>', methods=['GET', 'POST'])
@auth_required
def release_spot(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    
    if reservation.user_id != session['user_id'] or reservation.leaving_timestamp is not None:
        flash('Invalid reservation or already released.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    
    parking_duration = datetime.utcnow() - reservation.parking_timestamp
    duration_hours = parking_duration.total_seconds() / 3600
    price_per_hour = reservation.parking_spot.parking_lot.price
    cost = duration_hours * price_per_hour
    
    
    total_minutes = int(parking_duration.total_seconds() / 60)
    hours, minutes = divmod(total_minutes, 60)
    duration_str = f"{hours} hours, {minutes} minutes"

    if request.method == 'POST':
        
        reservation.leaving_timestamp = datetime.utcnow()
        reservation.parking_cost = cost
        
        
        reservation.parking_spot.status = 'A'
        
        db.session.commit()
        
        flash('Spot released successfully. Thank you!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template(
        'release_spot.html', 
        reservation=reservation, 
        duration=duration_str, 
        cost=cost, 
        title="Release Spot"
    )

@app.route('/summary')
@auth_required
def user_summary():
    user_id = session['user_id']
    
    monthly_data = db.session.query(
        db.func.strftime('%Y-%m', Reservation.parking_timestamp),
        db.func.count(Reservation.id)
    ).filter_by(user_id=user_id).group_by(db.func.strftime('%Y-%m', Reservation.parking_timestamp)).all()
    
    chart_data = {
        "labels": [row[0] for row in monthly_data],
        "values": [row[1] for row in monthly_data]
    }
    
    return render_template('user_summary.html', chart_data=chart_data, title="Your Summary")
