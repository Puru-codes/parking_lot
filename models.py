# models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from app import app
from werkzeug.security import generate_password_hash, check_password_hash


db=SQLAlchemy(app)



class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    name = db.Column(db.String(100), nullable=True) # Added from project statement
    email = db.Column(db.String(120), unique=True, nullable=True) # Added from project statement

    reservations = db.relationship('Reservation', backref='user', lazy=True)

    def set_password(self, password_text):
        """Hashes the given password and sets it to password_hash."""
        self.password_hash = generate_password_hash(password_text)

    def check_password(self, password_text):
        """Checks if the given password matches the hashed password."""
        return check_password_hash(self.password_hash, password_text)

    def __repr__(self):
        return f'<User {self.username}>'


class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'

    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False) # Price per unit time (e.g., per hour)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    # Add other fields like 'description' if needed in the future

    spots = db.relationship('ParkingSpot', backref='parking_lot', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ParkingLot {self.prime_location_name}>'


class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'

    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    status = db.Column(db.String(1), default='A', nullable=False) # 'A' for Available, 'O' for Occupied
    spot_number = db.Column(db.Integer, nullable=False) # To identify spots within a lot (e.g., Spot 1, Spot 2)

    # Ensure unique combination of lot_id and spot_number
    __table_args__ = (db.UniqueConstraint('lot_id', 'spot_number', name='_lot_spot_uc'),)
    reservations = db.relationship('Reservation', backref='parking_spot', lazy=True)


    def __repr__(self):
        return f'<ParkingSpot {self.spot_number} (Lot: {self.lot_id}, Status: {self.status})>'


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)

    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=True) # Null until the user leaves
    parking_cost = db.Column(db.Float, nullable=True) # Calculated when user leaves

    # Ensure a spot can only have one active reservation at a time (if needed, this can be handled in logic)
    # For now, allow multiple, but leaving_timestamp will indicate active vs past.

    def __repr__(self):
        return f'<Reservation {self.id} for User {self.user_id} on Spot {self.spot_id}>'
    

with app.app_context():
    db.create_all()
    print("Database tables created successfully.")
    admin = User.query.filter_by(is_admin=True).first()       
    if not admin:
        print("No admin user found. Creating a default admin user...")
        password_for_admin = 'admin' # !! IMPORTANT: Change this in production !!
            # You might want to get this from environment variables or a config file in a real app

            # Generate password hash
        hashed_password = generate_password_hash(password_for_admin)

            # Create the new admin user
        admin = User(
            username='admin',
            password_hash=hashed_password,
            is_admin=True
            )
        db.session.add(admin)
        db.session.commit()