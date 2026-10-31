from client import NBPClient
import respx
from datetime import date
from decimal import Decimal
from httpx import Response, HTTPStatusError
from pydantic import ValidationError

import pytest
import httpx

@respx.mock
def test_get_rates_success():
    chunk_start = date(2025, 1, 7)
    chunk_end =date(2025, 1, 7)
    my_route = respx.get(f"https://api.nbp.pl/api/exchangerates/tables/A/{chunk_start}/{chunk_end}/").mock(
        return_value=Response(
            status_code=200,
            json=[
                {
                    "table": 'A',
                    "no": '004/A/NBP/2025',
                    "effectiveDate": "2025-01-07",
                    "rates": [
                        {
                            "currency": "dolar amerykański",
                            "code": "USD",
                            "mid": 0.1194
                        }
                    ]
                }
            ]
        )
    )
    with NBPClient() as client:
        result = client.get_rates(chunk_start, chunk_end)
        assert my_route.called
        assert my_route.call_count == 1
        assert isinstance(result, list)
        assert len(result) == 1

        assert result[0].rates[0].code == 'USD'
        assert isinstance(result[0].rates[0].mid, Decimal)

@respx.mock
def test_get_rates_404():
    chunk_start = date(2025, 1, 7)
    chunk_end = date(2025, 1, 7)
    my_route = respx.get(f"https://api.nbp.pl/api/exchangerates/tables/A/{chunk_start}/{chunk_end}/").mock(
        return_value=Response(status_code=404)
    )
    with NBPClient() as client:
        result = client.get_rates(chunk_start, chunk_end)
        assert my_route.called
        assert my_route.call_count == 1
        assert result == []


@respx.mock
def test_get_rates_retries_on_500_then_succeeds():
    chunk_start = date(2025, 1, 7)
    chunk_end = date(2025, 1, 7)
    my_route = respx.get(f"https://api.nbp.pl/api/exchangerates/tables/A/{chunk_start}/{chunk_end}/").mock(
        side_effect =
            [
                Response(status_code=500),
                Response(
                    status_code=200,
                    json=[
                        {
                            "table": 'A',
                            "no": '004/A/NBP/2025',
                            "effectiveDate": "2025-01-07",
                            "rates": [
                                {
                                    "currency": "dolar amerykański",
                                    "code": "USD",
                                    "mid": 0.1194
                                }
                            ]
                        }
                    ]
                )
            ]
        )
    with NBPClient() as client:
        result = client.get_rates(chunk_start, chunk_end)
        assert my_route.called
        assert my_route.call_count == 2
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].rates[0].code == 'USD'
        assert isinstance(result[0].rates[0].mid, Decimal)

@respx.mock
def test_get_rates_invalid_schema_raises_validation_error():
    chunk_start = date(2025, 1, 7)
    chunk_end = date(2025, 1, 7)
    my_route = respx.get(f"https://api.nbp.pl/api/exchangerates/tables/A/{chunk_start}/{chunk_end}/").mock(
        return_value=
            Response(
                status_code=200,
                json=[
                    {
                        # No "table" field
                        "no": '004/A/NBP/2025',
                        "effectiveDate": "2025-01-07",
                        "rates": [
                            {
                                "currency": "dolar amerykański",
                                "code": "USD",
                                "mid": 0.1194
                            }
                        ]
                    }
                ]
            )
    )
    with NBPClient() as client:
        with pytest.raises(ValidationError) as exc_info:
            client.get_rates(chunk_start, chunk_end)

        assert my_route.called
        assert my_route.call_count == 1
        assert len(exc_info.value.errors()) == 1
        assert isinstance(exc_info.value, ValidationError)



@respx.mock
def test_get_rates_500_retries_exhausted_raises_error():
    chunk_start = date(2025, 1, 7)
    chunk_end = date(2025, 1, 7)
    my_route = respx.get(f"https://api.nbp.pl/api/exchangerates/tables/A/{chunk_start}/{chunk_end}/").mock(
        side_effect=
        [
            Response(status_code=500),
            Response(status_code=500),
            Response(status_code=500)

        ]
    )
    with NBPClient() as client:
        with pytest.raises(HTTPStatusError) as exc_info:
            client.get_rates(chunk_start, chunk_end)

        assert my_route.called
        assert my_route.call_count == 3
        assert exc_info.value.response.status_code == 500
        assert isinstance(exc_info.value, HTTPStatusError)

