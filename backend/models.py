from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.String(50), nullable=False) # e.g. MR-2024-0891
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer)
    sex = db.Column(db.String(20))
    condition = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Stable")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fusions = db.relationship('Fusion', backref='patient_rel', lazy=True)

class Fusion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True) # Optional link to a patient
    mri_path = db.Column(db.String(300), nullable=False)
    pet_path = db.Column(db.String(300), nullable=False)
    result_path = db.Column(db.String(300), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
