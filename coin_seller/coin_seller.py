from pybit.exceptions import InvalidRequestError
from datetime import datetime
from loguru import logger
from pybit.unified_trading import HTTP
from math import floor
from json import dumps
from time import (
    time,
    sleep,
)

import uuid

from config import (
    COIN,
    list_time,
    COEFFICIENT,
)

from asyncio import (
    AbstractEventLoop,
    coroutine,
    run,
)

class CoinSeller:
    def __init__(self, name: str, api_key: str, api_secret: str, proxy: str) -> None:
        self.account_name = name
        self.session_auth = HTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret)
        self.session_auth.client.proxies.update({'https//': proxy, 'http//': proxy})
        self.balance_before_selling = None
        self.balance_after_selling = None

    async def start(self) -> None:
        logger.info('Waiting for listing...')
        last_time = 0
        while True:
            now = floor(time())
            if list_time > now and last_time != now:
                logger.info(f'Time before sending requests: {round(list_time - now)} seconds')
            last_time = now
            if list_time < now:
                await self.check_balance()
                break

    async def check_price_and_qty(self, balance: str, price_usdt=False, price_usdc=False) -> None:
        no_orders = True
        while no_orders:
            try:
                logger.info('Looking for the best price...')
                check_usdt = self.session_auth.get_tickers(category="spot",symbol=f"{COIN}USDT")
                price_usdt = (round(float(check_usdt['result']['list'][0]['bid1Price']) * COEFFICIENT, 1))
                check_usdc = self.session_auth.get_tickers(category="spot",symbol=f"{COIN}USDC")
                check_usdc = (round(float(check_usdc['result']['list'][0]['bid1Price']) * COEFFICIENT, 1))
                if price_usdt >= check_usdc:
                    logger.info(f'Лучшая цена из двух: {price_usdt} USDT')
                    no_orders = False
                    await self.sell_tokens(price_usdt, balance, 'USDT')
                else: 
                    logger.info(f'Лучшая цена из двух: {price_usdc} USDC')
                    no_orders = False
                    await self.sell_tokens(price_usdt, balance, 'USDC')
            except:
                try:
                    if price_usdt == False:
                        check_usdc = self.session_auth.get_tickers(category="spot",symbol=f"{COIN}USDC")
                        check_usdc = (round(float(check_usdc['result']['list'][0]['bid1Price']) * COEFFICIENT, 1))
                        logger.info(f'Лучшая цена: {check_usdc} USDC')
                        no_orders = False
                        await self.sell_tokens(check_usdc, balance, 'USDC')
                    else:
                        logger.info(f'Лучшая цена: {price_usdt} USDT')
                        no_orders = False
                        await self.sell_tokens(price_usdt, balance, 'USDT')
                except:  
                    logger.info(f'Нет пар или токенов, кайфуй браточек :)')
                    sleep(0.2)
                    continue

    async def check_balance(self) -> None:
        logger.info(f'Checking balance... | {self.account_name}')
        while True:
            try:
                balance_request = self.session_auth.get_wallet_balance(accountType="SPOT", coin=COIN)
                name = balance_request['result']['list'][0]['coin'][0]['coin']
                balance = float(balance_request['result']['list'][0]['coin'][0]['free'])
                if name == COIN:
                    self.balance_before_selling = balance
                    logger.info(f'{balance, COIN} | {self.account_name}')
                    await self.check_price_and_qty(balance)
                    break
            except:
                logger.info(f'{COIN} пока не перенесли на спот, пытаюсь его отыскать :)')
                sleep(0.2)
                continue

    async def cancel_order(self, order_id: str, balance: str, price: float, pair) -> None:
        try:
            self.session_auth.cancel_order(category="spot", symbol=f"{COIN}{pair}", orderId=order_id)
            logger.info(f'Order deleted | {self.account_name}')
            await self.check_price_and_qty(balance)
        except InvalidRequestError:
            logger.success(f'Completed. | {self.account_name}')

    async def check_balance_after_selling(self, order_id: str, price: float, pair) -> None:
        balance_request = self.session_auth.get_wallet_balance(accountType="SPOT", coin=COIN)
        name = balance_request['result']['list'][0]['coin'][0]['coin']
        balance = float(balance_request['result']['list'][0]['coin'][0]['free'])
        if name == COIN and float(balance) > 0:
            logger.info(f'{balance}, {COIN} | {self.account_name}')
            await self.cancel_order(order_id, balance, price, pair)
        elif name == COIN and float(balance) == 0:
            logger.info(f'Completed. | {self.account_name}')

    async def sell_tokens(self, price: float, balance: str, pair) -> None:
        n_digits = 4
        factor = 10 ** n_digits
        qty = floor(float(balance) * factor) / factor
        if price > 1:
            req = self.session_auth.place_order(
                category="spot",
                symbol=f"{COIN}{pair}",
                side="Sell",
                orderType="Limit",
                qty=qty,
                price=price,
                timeInForce="GTC"
            )
            order_id = req['result']['orderId']
            logger.info(f'An order for {qty} coins at price of {price} placed')
            await self.check_balance_after_selling(order_id, price, pair)
        else:
            await self.check_price_and_qty(balance)

    def run(self) -> None:
        start_event_loop(self.start())

def start_event_loop(coroutine: coroutine) -> AbstractEventLoop:
    try:
        return run(coroutine)
    except RuntimeError as ex:
        logger.info(f'Something went wrong | {ex}')
