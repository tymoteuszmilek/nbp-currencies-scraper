from pydantic import BaseModel, Field, ValidationError
from decimal import Decimal
from typing import Literal
from datetime import date

class Rate(BaseModel):
    currency: str
    code: str = Field(pattern=r'^[A-Z]{3}$')
    mid: Decimal = Field(gt=0)

class ExchangeTable(BaseModel):
    table: Literal["A", "B", "C"]
    no: str
    effective_date: date = Field(alias="effectiveDate")
    rates: list[Rate]

if __name__ == "__main__":
    pass_data = {'table': 'A', 'no': '169/A/NBP/2026', 'effectiveDate': date(2026, 9, 1), 'rates': [{'currency': 'bat (Tajlandia)', 'code': 'THB', 'mid': 0.1124}]}
    reject_data_v1 = {'table': 'D', 'no': '169/A/NBP/2026', 'effectiveDate': '2026-09-01', 'rates': [{'currency': 'bat (Tajlandia)', 'code': 'THB', 'mid': 0.1124}]} # tabela spoza zakresu
    reject_data_v2 = {'table': 'A', 'no': '169/A/NBP/2026', 'effectiveDate': '2026:09:01', 'rates': [{'currency': 'bat (Tajlandia)', 'code': 'THB', 'mid': 0}]} # zły format daty
    reject_data_v3 = {'table': 'A', 'no': '169/A/NBP/2026', 'effectiveDate': '2026-09-01',
                 'rates': [{'currency': 'bat (Tajlandia)', 'code': 'THBA', 'mid': 0.1124}]} # 4 znakowy kod


    try:
        ex = ExchangeTable.model_validate(pass_data)
        print("Poprawna walidacja: \n", ex)
    except ValidationError as err:
        print("Błąd walidacji: \n", err)
