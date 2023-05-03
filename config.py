from datetime import datetime
from pathlib import Path

""" https://www.bybit.com/app/user/api-management - link to create API-key and API-secret """

""" Монета, которую будем продавать """
COIN = ''

""" Время листининга, настраиваем по тому, которое показывает ваша система """
list_time = datetime(year=2023, month=5, day=3, hour=14, minute=59, second=59)

""" Коффициент для продажи """
COEFFICIENT = 0.96


correction = 0
list_time = list_time.timestamp() + correction
project_root = Path(__file__).parent
