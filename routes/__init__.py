"""Routes package initialization"""
from .prescription_routes import prescription_bp, init_prescription_routes
from .hospital_routes import hospital_bp, init_hospital_routes

__all__ = [
    'prescription_bp',
    'hospital_bp',
    'init_prescription_routes',
    'init_hospital_routes'
]
