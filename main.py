import argparse
from datetime import date, timedelta

from db import get_connection, init_db, upsert_rates
from models import ExchangeTable
from client import NBPClient


def main():
    parser = argparse.ArgumentParser(description='Fetch exchange rates')
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args()

    today = date.today()
    seven_days_ago = today - timedelta(days=7)

    if args.start_date:
        start_date = date.fromisoformat(args.start_date)
    else:
        start_date = seven_days_ago

    if args.end_date:
        end_date = date.fromisoformat(args.end_date)
    else:
        end_date = today

    conn = get_connection()
    try:
        with conn:
            init_db(conn)
            with NBPClient() as client:
                res = client.get_rates(start_date, end_date)
                print(f"Pomyślnie pobrano i zapisano {len(res)} tabel kursów.")
                upsert_rates(conn, res)
    finally:
        conn.close()


if __name__ == "__main__":
    main()