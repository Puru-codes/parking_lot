from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from app import app

db = SQLAlchemy(app)

class User(db.Model):
   
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    
    reservations = db.relationship('Reservation', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'
    

class ParkingLot(db.Model):
    
    __tablename__ = 'parking_lots'

    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False) 
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)

    
    spots = db.relationship('ParkingSpot', backref='parking_lot', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ParkingLot {self.prime_location_name}>'
    

class ParkingSpot(db.Model):
    """
    Represents a single parking spot within a lot.
    """
    __tablename__ = 'parking_spots'

    id = db.Column(db.Integer, primary_key=True)
    
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    
    status = db.Column(db.String(1), default='A', nullable=False)

   
    reservations = db.relationship('Reservation', backref='parking_spot', lazy=True)

    def __repr__(self):
        return f'<ParkingSpot {self.id} in Lot {self.lot_id}>'
    

class Reservation(db.Model):
    
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=True) 
    parking_cost = db.Column(db.Float, nullable=True) 

    def __repr__(self):
        return f'<Reservation {self.id} for User {self.user_id}>'