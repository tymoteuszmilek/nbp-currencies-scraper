import psycopg
import os
from dotenv import load_dotenv
from models import ExchangeTable
from datetime import date
from client import NBPClient as NBPClient

load_dotenv()
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")


def get_connection():
    try:
        return psycopg.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host="localhost",
            port=5433,
        )
    except psycopg.Error as e:
        print(f"Database connection error: {e}")
        raise

def init_db(conn):
    with conn.cursor() as curr:
        curr.execute("""
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                currency      VARCHAR(100) NOT NULL,
                code          VARCHAR(3) NOT NULL,
                mid           NUMERIC NOT NULL,
                table_no      VARCHAR(20) NOT NULL,
                effective_date DATE NOT NULL,
            
                CONSTRAINT uq_exchange_rates_code_date
                    UNIQUE (code, effective_date)
            );
        """)
        conn.commit()

def upsert_rates(conn, tables:list[ExchangeTable]):
    values = []
    for table in tables:
        for rate in table.rates:
            values.append((
                rate.currency,
                rate.code,
                rate.mid,
                table.no,
                table.effective_date
            ))

    with conn.cursor() as curr:
        curr.executemany("""
            INSERT INTO exchange_rates (currency, code, mid, table_no, effective_date)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (code, effective_date) 
            DO UPDATE SET 
                mid = EXCLUDED.mid,
                table_no = EXCLUDED.table_no,
                currency = EXCLUDED.currency;
        """,values)
    conn.commit()


if __name__ == "__main__":
    conn = get_connection()
    try:
        init_db(conn)
        with NBPClient() as client:
            res = client.get_rates(start_date=date(2025, 1, 5), end_date=date(2025, 1, 8))
            upsert_rates(conn, res)
            with conn.cursor() as curr:
                curr.execute("SELECT count(*) FROM exchange_rates;")
                print("Liczba wierszy w bazie:", curr.fetchone()[0])

    finally:
        conn.close()



