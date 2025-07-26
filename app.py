# app.py

from flask import Flask
app=Flask(__name__)
import os
import config
import models 
import routes






if __name__ == '__main__':
    app.run(debug=True,port=5000)