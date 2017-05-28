# encoding = utf-8


__name__ = 'vxTrader'
__version__ = '0.1.11'
__author__ = 'vex1023'
__email__ = 'vex1023@qq.com'

import logging

from vxUtils.PrettyLogger import add_console_logger

logger = logging.getLogger('vxQuant.vxTrader')
add_console_logger(logger)

from vxTrader.trader import Trader, load_traders

__all__ = ['logger', 'Trader', 'load_traders']
