from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE results ADD COLUMN IF NOT EXISTS result_metadata JSONB'))
    conn.commit()
    print('result_metadata column added successfully')
