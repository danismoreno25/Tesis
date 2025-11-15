import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text("SELECT now()")).fetchone()
    print("Conectado a Supabase:", result[0])

    tablas = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'pricing'
        ORDER BY table_name;
    """)).fetchall()

    print("\nTablas encontradas en esquema 'pricing':")
    for (name,) in tablas:
        print(" -", name)
