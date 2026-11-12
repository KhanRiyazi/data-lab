# uvicorn app.main:app --reload --no-use-colors

# Test the connection 
python -c "from dotenv import load_dotenv; import os, sqlalchemy; load_dotenv(); e=sqlalchemy.create_engine(os.getenv('DATABASE_URL')); print(e.connect().exec_driver_sql('select version()').scalar())"