# encoding = utf-8


__name__ = 'vxTrader'
__version__ = '0.0.1'
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
    @TraderFactory('yjb')
    class yjbTrader(WebTrader):
        pass

    '''

    _instance = {}

    def __init__(self, brokerid):
        # 使用小写作为关键字
        self._brokerid = brokerid.lower()

    def __call__(self, cls):
        TraderFactory._instance[self._brokerid] = cls
        return cls

    @classmethod
    def create(cls, brokerid, account, password, **kwargs):
        brokerid = brokerid.lower()
        instance = cls._instance.get(brokerid, None)
        if instance:
            return instance(account, password, **kwargs)


# 自动加载相应的broker
from vxTrader.broker import *
