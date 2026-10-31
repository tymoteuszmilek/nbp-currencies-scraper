# Currencies Scraper (NBP)

Aplikacja pobiera średnie kursy walut (tabela A) z publicznego API Narodowego Banku Polskiego i zapisuje je w bazie PostgreSQL. Klient HTTP oparty o `httpx` dzieli zadany zakres dat na fragmenty (chunking, maks. 93 dni na zapytanie – limit API NBP) i automatycznie ponawia żądania przy błędach sieciowych oraz odpowiedziach `429` / `5xx` (retry z wykładniczym backoffem, `tenacity`). Odpowiedzi są walidowane modelami Pydantic v2 (m.in. format kodu waluty, dodatnia wartość kursu, typ tabeli). Zapis do bazy jest idempotentny dzięki `INSERT ... ON CONFLICT DO UPDATE` (UPSERT) na kluczu `(code, effective_date)`, więc wielokrotne uruchomienie dla tego samego zakresu dat nie tworzy duplikatów.

## Architektura

```
main.py      – punkt wejścia (CLI: --start-date, --end-date)
client.py    – NBPClient: HTTP, retry, chunking zakresu dat
models.py    – modele Pydantic v2 (Rate, ExchangeTable)
db.py        – połączenie z PostgreSQL, tworzenie tabeli, UPSERT
test_client.py – testy klienta (respx, bez dostępu do sieci)
```

## Środowisko bazodanowe (Docker)

Projekt wykorzystuje oficjalny obraz **PostgreSQL 16 (Alpine)** uruchamiany za pomocą Docker Compose:

1. **Konfiguracja środowiska:** Plik `docker-compose.yml` wczytuje zmienne uwierzytelniające (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) bezpośrednio ze zdefiniowanego lokalnie pliku `.env`.
2. **Mapowanie portów:** Port wewnętrzny bazy `5432` jest mapowany na port hosta `5433` (aby uniknąć kolizji z lokalnymi instancjami PostgreSQL).
3. **Persystencja danych:** Dane bazy są utrwalane na wolumenie `postgres_data`, co zapobiega utracie danych po zatrzymaniu kontenera.

Przepływ danych: `main.py` → `NBPClient.get_rates()` → walidacja (`models.py`) → `upsert_rates()` → tabela `exchange_rates`.

## Stos technologiczny

- Python 3.11+
- PostgreSQL 16
- Docker Compose
- httpx – klient HTTP
- pydantic v2 – walidacja danych
- tenacity – retry z exponential backoff
- psycopg 3 – sterownik PostgreSQL
- pytest – testy
- respx – mockowanie żądań httpx w testach

## Quickstart

### Krok 1: Środowisko i zależności

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env
```

Następnie uzupełnij w pliku `.env` dane dostępowe do bazy:

```env
POSTGRES_DB=currencies
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

> Plik `.env` zawiera hasła – nie commituj go do repozytorium (dodaj do `.gitignore`).

### Krok 2: Uruchomienie bazy danych

```bash
docker compose up -d
```

Baza jest dostępna na `localhost:5433`. Tabela `exchange_rates` jest tworzona automatycznie przy pierwszym uruchomieniu aplikacji (`CREATE TABLE IF NOT EXISTS`).

### Krok 3: Pobranie kursów i testy

```bash
python main.py && pytest
```

Domyślnie pobierane są kursy z ostatnich 7 dni. Własny zakres dat (format `YYYY-MM-DD`):

```bash
python main.py --start-date 2025-01-01 --end-date 2025-03-31
```

Testy nie wymagają działającej bazy ani dostępu do internetu (żądania HTTP są mockowane przez `respx`).

## Schemat bazy danych

Tabela `exchange_rates`:

| Kolumna          | Typ            | Opis                          |
|------------------|----------------|-------------------------------|
| `id`             | INTEGER (IDENTITY, PK) | Klucz główny          |
| `currency`       | VARCHAR(100)   | Nazwa waluty                  |
| `code`           | VARCHAR(3)     | Kod ISO (np. `USD`)           |
| `mid`            | NUMERIC        | Średni kurs                   |
| `table_no`       | VARCHAR(20)    | Numer tabeli NBP              |
| `effective_date` | DATE           | Data obowiązywania kursu      |

Ograniczenie unikalności: `UNIQUE (code, effective_date)` – podstawa idempotentnego UPSERT.

## Obsługa błędów

- `404` z API NBP (brak notowań, np. weekend/święto) – traktowane jako brak danych, zwracana jest pusta lista.
- `429` i `5xx` oraz błędy sieciowe – do 3 prób z wykładniczym opóźnieniem; po wyczerpaniu prób zgłaszany jest wyjątek.
- Niepoprawna odpowiedź API (błąd walidacji Pydantic) – zapisywany log błędu i zgłoszenie `ValidationError` (bez ponawiania).
