from datetime import date, timedelta
import httpx
from models import ExchangeTable
from pydantic import ValidationError
import logging
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

def should_retry(retry_state) -> bool:
    exc = retry_state.outcome.exception()
    if isinstance(exc, httpx.RequestError):
        return True
    elif isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429 or ( code >= 500 and code < 600):
            return True
    return False

class NBPClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.client = httpx.Client(timeout=self.timeout, headers={"Accept": "application/json"})
    def close(self):
        self.client.close()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # tutaj retry_if_exception to patryzmy na wynik jaki bedzie z return self.client.get itp...
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=2), retry=should_retry, reraise=True)
    def _fetch_chunk(self, chunk_start: date, chunk_end: date) -> list[ExchangeTable]:
        final_table: list[ExchangeTable] = []
        response = self.client.get(
            f"https://api.nbp.pl/api/exchangerates/tables/A/{chunk_start}/{chunk_end}/"
        )

        if response.status_code == 200:
            for each_row in response.json():
                try:
                    table = ExchangeTable.model_validate(each_row)
                    final_table.append(table)
                except ValidationError:
                    logger.error("Błąd walidacji dla przedziału %s - %s", chunk_start, chunk_end)
                    raise
            return final_table

        elif response.status_code == 404:
            logger.info("Brak danych dla przedziału %s - %s", chunk_start, chunk_end)
            return []
        else:
            response.raise_for_status()


    def get_rates(self, start_date: date, end_date: date) -> list[ExchangeTable]:
        all_tables = []
        for chunk_start, chunk_end in split_date_range(start_date, end_date):
            table = self._fetch_chunk(chunk_start, chunk_end)
            all_tables.extend(table)
        return all_tables


def split_date_range(
    start_date: date,
    end_date: date,
    max_days: int = 93,
) -> list[tuple[date, date]]:

    if max_days < 1:
        raise ValueError("max_days musi być większe od 0")

    if start_date > end_date:
        raise ValueError("start_date nie może być późniejsze niż end_date")

    segmented_dates = []
    current_start = start_date

    while current_start <= end_date:
        current_end = min(
            current_start + timedelta(days=max_days - 1),
            end_date,
        )
        segmented_dates.append((current_start, current_end))

        current_start = current_end + timedelta(days=1)

    return segmented_dates


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with NBPClient() as client:
        res = client.get_rates(start_date=date(2025, 1, 8), end_date=date(2025, 1, 8))
        for each_row in res:
            print(each_row)