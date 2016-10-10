# encoding = utf-8


__name__ = 'vxTrader'
__version__ = '0.1.3'
__author__ = 'vex1023'
__email__ = 'vex1023@qq.com'

__all__ = ['logger', 'TraderFactory']

import logging

from vxTrader.PrettyLogger import add_console_logger

logger = logging.getLogger(__name__)
add_console_logger(logger)


class TraderFactory():
    '''
    创建一个修饰器，注册vxTrader
    @TraderFactory('yjb', '佣金宝', '国金证券')
    class yjbTrader(WebTrader):
        pass

    '''

    instance = {}

    def __init__(self, *brokerIDs):
        # 使用小写作为关键字
        self._brokerIDs = brokerIDs

    def __call__(self, cls):
        for brokerID in self._brokerIDs:
            TraderFactory.instance[brokerID.lower()] = cls
        return cls


def create_trader(brokerID, account, password, **kwargs):
    brokerID = brokerID.lower()
    instance = TraderFactory.instance.get(brokerID, None)

    if instance is None:
        err_msg = 'broker ID: %s is not registered by trader factory(%s).' % (brokerID, TraderFactory.instance)
        logger.error(err_msg)
        raise NotImplementedError(err_msg)

    return instance(account, password, **kwargs)
# 自动加载相应的broker
from vxTrader.broker import *
