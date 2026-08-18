"""
Creates default users. Run from backend/ directory:
    python seed_users.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User

init_db()
db = SessionLocal()

USERS = [
    dict(username="admin",  email="admin@pharmstock.local",  full_name="System Administrator", password="Admin1234!", role="admin"),
    dict(username="staff",  email="staff@pharmstock.local",  full_name="Demo Staff User",       password="Staff1234!", role="staff"),
    dict(username="viewer", email="viewer@pharmstock.local", full_name="Demo Viewer",           password="Viewer1234!", role="viewer"),
]

for u in USERS:
    existing = db.query(User).filter(User.username == u["username"]).first()
    if existing:
        db.delete(existing)
        db.commit()
    user = User(
        username=u["username"],
        email=u["email"],
        full_name=u["full_name"],
        hashed_password=hash_password(u["password"]),
        role=u["role"],
        is_active=True,
    )
    db.add(user)

db.commit()
db.close()

print("Users seeded:")
for u in USERS:
    print(f"  {u['username']:8s} / {u['password']:14s}  (role: {u['role']})")
