# encoding = utf-8


__name__ = 'vxTrader'
__version__ = '0.1.5'
__author__ = 'vex1023'
__email__ = 'vex1023@qq.com'

__all__ = ['logger', 'TraderFactory']

import configparser
import logging

from vxUtils.PrettyLogger import add_console_logger

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


# 自动加载相应的broker
from vxTrader.broker import *



def create_trader(brokerID, account, password, **kwargs):
    '''
    创建单个trader的接口
    '''
    brokerID = brokerID.lower()
    instance = TraderFactory.instance.get(brokerID, None)

    if instance is None:
        err_msg = 'broker ID: %s is not registered by trader factory(%s).' % (brokerID, TraderFactory.instance)
        logger.error(err_msg)
        raise NotImplementedError(err_msg)

    return instance(account, password, **kwargs)


# 根据配置文件来创建
def load_traders(ConfigFile='/etc/vxQuant/vxTrader.conf'):
    '''
    通过配置文件来批量创建traders
    :param ConfigFile:
    :return: traders的dict
    '''
    config = configparser.ConfigParser()
    config.read(ConfigFile)

    traders = {}

    sections = config.sections()
    for section in sections:
        # 读取全部section下的所有items
        kwargs = dict(config.items(section))

        brokerid = kwargs.pop('brokerid', '')
        account = kwargs.pop('account', '')
        password = kwargs.pop('password', '')
        # 检查配置是否正确
        if brokerid == '' or account == '' or password == '':
            raise ValueError('brokerid: %s, account: %s, password: %s' % (brokerid, account, password))

        traders[section] = create_trader(brokerid, account, password, **kwargs)

    return traders
