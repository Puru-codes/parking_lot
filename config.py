from dotenv import load_dotenv
import os
from app import app
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('sqlalchemy_database_uri')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('sqlalchemy_track_modifications')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG') == 'True'