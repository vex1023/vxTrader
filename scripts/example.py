# encoding=utf-8

import configparser
import os

import demjson as json

from vxTrader import create_trader, logger, load_traders


def get_trader():
    brokerid = os.getenv('brokerid', '')
    account = os.getenv('account', '')
    password = os.getenv('password', '')
    kwargs = os.getenv('kwargs', '')
    kwargs = json.decode(kwargs)

    if brokerid == '' or account == '' or password == '':
        raise EnvironmentError('enviroment value account(%s) or password(%s) is not set' % (account, password))

    return create_trader(brokerid, account, password, **kwargs)


def get_traders(configile):
    config = configparser.ConfigParser()
    config.read(configile)

    traders = dict()

    sections = config.sections()
    print(sections)
    for section in sections:
        kwarg = dict(config.items(section))
        print(kwarg)
        brokerid = kwarg.pop('brokerid', '')
        account = kwarg.pop('account', '')
        password = kwarg.pop('password', '')
        traders[section] = create_trader(brokerid, account, password, **kwarg)

    return traders



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
    logger.setLevel('INFO')
    # main(trader)

    traders = load_traders('/etc/vxQuant/vxTrader.conf')

    for key in traders.keys():
        print('=' * 30 + key + '=' * 30)
        trader = traders[key]
        print(trader.portfolio)
    print('==' * 30)
    print(traders['xqcash'].portfolio['market_value'].sum())
