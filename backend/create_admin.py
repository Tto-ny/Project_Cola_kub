import os
from database import SessionLocal, Officer, engine, Base
from auth import get_password_hash

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def create_admin_user():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(Officer).filter(Officer.username == "admin").first()
        if admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        # Password will be "nanlandslide2024" or from env
        password = os.getenv("ADMIN_PASSWORD", "nanlandslide2024")
        hashed_password = get_password_hash(password)
        
        new_admin = Officer(
            username="admin",
            password_hash=hashed_password,
            role="admin"
        )
        db.add(new_admin)
        db.commit()
        print(f"✅ Admin user created successfully!")
        print(f"Username: admin")
        print(f"Password: {password}")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
