from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS progress_details JSONB'))
    conn.commit()
    print('progress_details column added successfully')
