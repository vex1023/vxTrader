# encoding=utf-8

import os

import demjson as json

from vxTrader import create_trader, logger


def get_trader():
    brokerid = os.getenv('brokerid', '')
    account = os.getenv('account', '')
    password = os.getenv('password', '')
    kwargs = os.getenv('kwargs', '')
    kwargs = json.decode(kwargs)

    if brokerid == '' or account == '' or password == '':
        raise EnvironmentError('enviroment value account(%s) or password(%s) is not set' % (account, password))

    return create_trader(brokerid, account, password, **kwargs)


def main(trader):
    print(trader.portfolio)
    print('=' * 30)
    print(trader.order_target_percent('sh510500', 0.2))
    print(trader.order('sh510500', -300))
    print(trader.order('sh510500', 300))
    print(trader.cancel())
    print(trader.orderlist)


if __name__ == '__main__':
    trader = get_trader()
    logger.setLevel('DEBUG')
    main(trader)
