# encoding=utf-8

import configparser
import os

import demjson as json

from vxTrader import logger, Trader, load_traders

if __name__ == '__main__':
    logger.setLevel('INFO')

    traders = load_traders('/etc/vxQuant/vxTrader.conf')

    trader = traders['wife']

    print(trader.portfolio)
    print('=' * 30)
    print(trader.orderlist)
    print('=' * 30)
    print(trader.order('sh511880', amount=-4000))
