# encoding = utf-8


__name__ = 'vxQuant.vxTrader'
__version__ = '0.1.8'
__author__ = 'vex1023'
__email__ = 'vex1023@qq.com'

import logging

from vxUtils.PrettyLogger import add_console_logger

logger = logging.getLogger(__name__)
add_console_logger(logger)

from .trader import Trader, load_traders

__all__ = ['logger', 'Trader', 'load_traders']
