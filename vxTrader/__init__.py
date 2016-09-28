# encoding = utf-8

from vxTrader.PrettyLogger import add_console_logger
from .broker import *

__name__ = 'vxTrader'
__version__ = '0.0.1'
__author__ = 'vex1023'
__email__ = 'vex1023@qq.com'

__all__ = [logger, TraderFactory]

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
    def create(self, brokerid, account, password, **kwargs):
        brokerid = brokerid.lower()
        instance = TraderFactory._instance.get(brokerid, None)
        if instance:
            return instance(account, password, **kwargs)
