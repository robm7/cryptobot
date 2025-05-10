from app import app
from database.models import User, Trade
from database.db import db

with app.app_context():
    # Check if user exists
    existing = User.query.filter_by(email='test@example.com').first()
    if existing:
        # Delete associated trades
        Trade.query.filter_by(user_id=existing.id).delete()
        db.session.delete(existing)
        db.session.commit()
    
    # Create new test user
    user = User(email='test@example.com')
    user.set_password('Test123!')
    db.session.add(user)
    db.session.commit()
    print("Test user created successfully")