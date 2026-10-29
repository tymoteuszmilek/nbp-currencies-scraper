import os
import psycopg
from dotenv import load_dotenv
load_dotenv()

user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
dbname = os.getenv("POSTGRES_DB")

conn = psycopg.connect(
    user=user,
    dbname=dbname,
    password=password,
    host="localhost",
    port=5433
)

with conn:
    with conn.cursor() as curr:
        curr.execute("SELECT VERSION()")
        result = curr.fetchone()
        print(result)

