from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///database/cryptobot.db')
Session = sessionmaker(bind=engine)
session = Session()

try:
    result = session.execute(text("SELECT * FROM alembic_version"))
    version = result.fetchone()
    if version:
        print("Current migration version:", version[0])
    else:
        print("No migrations have been applied yet")
except Exception as e:
    print("Error checking migration version:", e)
finally:
    session.close()