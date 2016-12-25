# endcoding = utf-8
'''
author : vex1023
email :  vex1023@qq.com
组合下单方法
'''

import configparser
import logging
import time

from vxTrader.broker import *

logger = logging.getLogger('vxQuant.vxTrader')

# 最大单笔下单数量 10万股
_MAX_AMOUNT = 100000
# 最大单笔下单金额 20万元
_MAX_VOLUME = 200000


class Trader():
    def __init__(self, brokerID, account, password, **kwargs):
        brokerID = brokerID.lower()
        Broker = BrokerFactory.instance.get(brokerID, None)

        if Broker:
            self.broker = Broker(account, password, **kwargs)

            # 如果broker 提供了order, 直接使用broker的接口
            if hasattr(self.broker, 'order'):
                self.__dict__['order'] = self.broker.__getattribute__('order')
        else:
            err_msg = 'broker ID: %s is not registered by trader factory(%s).' % (brokerID, BrokerFactory.instance)
            logger.error(err_msg)
            raise NotImplementedError(err_msg)

    def __getattr__(self, item):
        return self.broker.__getattribute__(item)

    def _split_order(self, symbol, trade_side, amount):
        '''分单下单'''
        symbol = symbol.lower()

        if symbol == 'cash':
            return 0

        left = amount
        # 获取下单行情
        hq = self.broker.hq(symbol)
        price = hq.loc[symbol, 'lasttrade']
        order_nos = []
        if (_MAX_AMOUNT * price) <= _MAX_VOLUME:
            max_amount = _MAX_AMOUNT
        else:
            max_amount = (_MAX_VOLUME // price // 100 * 100)

        # 下单执行交易
        while left > 0:
            order_amount = max_amount if left > max_amount else left

            if trade_side == 'buy':
                order_price = hq.loc[symbol, 'ask']

                logger.info('buy: symbol(%s), price(%s), amount(%s)' % (symbol, order_price, order_amount))
                order_no = self.broker.buy(symbol=symbol, price=order_price, amount=order_amount)
            else:
                order_price = hq.loc[symbol, 'bid']

                logger.info('sell: symbol(%s), price(%s), amount(%s)' % (symbol, order_price, order_amount))
                order_no = self.broker.sell(symbol=symbol, price=order_price, amount=order_amount)

            left = left - order_amount
            order_nos.append(order_no)
            time.sleep(1.1)

        return order_nos

    def order(self, symbol, amount=0, volume=0, weight=0, portfolio=None):
        '''
        下单后，观察5s后，检查是否已经成交，若未成交，则撤单，再下单，最多重复10次.
        返回剩余未成交量
        '''

        symbol = symbol.lower()

        if symbol == 'cash':
            return 0

        logger.info('order: symbol(%s), amount(%.2f), volume(%.2f), weight(%.4f)' % (symbol, amount, volume, weight))
        if amount != 0:
            left = amount
        elif volume != 0:
            hq = self.broker.hq(symbol)
            price = hq.loc[symbol, 'lasttrade']
            left = volume // price // 100 * 100
        elif weight != 0:
            if weight < -1.0 or weight > 1.0:
                raise ValueError('weight(%s) must between [-1,1]' % weight)

            if portfolio is None:
                portfolio = self.broker.portfolio
            left_volume = round(portfolio['market_value'].sum(), 2)
            if symbol in portfolio.index:
                price = portfolio.loc[symbol, 'lasttrade']
            else:
                hq = self.broker.hq(symbol)
                price = hq.loc[symbol, 'lasttrade']
            left = left_volume // price // 100 * 100
        else:
            # amount , volume, weight均为0，则不作任何操作直接返回
            return 0

        trade_side = 'buy'
        if left < 0:
            trade_side = 'sell'
            left = -left

        for i in range(10):
            order_nos = self._split_order(symbol, trade_side, left)
            # 等待一段时间
            time.sleep(min((2 + 3 * i), 10))

            # 检查成交情况
            orderlist = self.broker.orderlist
            orderlist = orderlist[orderlist['order_status'] != '已成']
            need_cancel = orderlist.loc[orderlist.index.isin(order_nos)]
            if need_cancel.shape[0] > 0:

                need_cancel['left'] = need_cancel['order_amount'] - need_cancel['business_amount']
                for order_no in need_cancel.index:
                    try:
                        logger.debug('Cancel order_no(%s)' % order_no)
                        self.broker.cancel(order_no)
                    except Exception as err:
                        logger.info('Order no cancel failed: %s' % err)

                left = round(need_cancel['left'].sum(), 2)
                logger.info('第%s次下单后，剩余未成交股数: %s' % (i + 1, left))
            else:
                logger.info('Order Completed.')
                return 0

        logger.info('Order Not Completed. Left(%s)' % left)
        return left

    def order_target(self, symbol, target_amount=None, target_volume=None, target_weight=None, portfolio=None):
        '''
        按照目标持股数量，持仓市值或者持仓比例下单
        '''
        logger.info('Order target: symbol(%s), target_amount(%s), target_volume(%s), target_weight(%s)' % \
                    (symbol, target_amount, target_volume, target_weight))

        symbol = symbol.lower()

        if symbol == 'cash':
            return 0

        if portfolio is None:
            portfolio = self.broker.portfolio

        source_amount = source_volume = source_weight = 0
        amount = volume = weight = 0

        if symbol in portfolio.index:
            source_amount = portfolio.loc[symbol, 'current_amount']
            source_volume = portfolio.loc[symbol, 'market_value']
            source_weight = portfolio.loc[symbol, 'weight']

        # 修复target_amount, target_volume, target_weight为0 的情况
        if target_amount is not None:
            amount = target_amount - source_amount
        elif target_volume is not None:
            volume = target_volume - source_volume
        elif target_weight is not None:
            weight = target_weight - source_weight

        return self.order(symbol, amount, volume, weight, portfolio)

    def order_auto_ipo(self):
        '''
        新股自动申购
        '''
        logger.info('Order auto IPO')
        ipo_limit = self.broker.ipo_limit()
        ipo_list = self.broker.ipo_list()
        order_nos = []

        if ipo_list.shape[0] == 0:
            logger.info('今日没有新股')
            return order_nos
        if ipo_limit.shape[0] == 0:
            logger.info('新股申购额度不足')
            return order_nos

        for symbol in ipo_list.index:
            max_buy = ipo_list.loc[symbol, 'max_buy_amount']
            lmt_buy = ipo_limit.loc[ipo_list.loc[symbol, 'exchange_type'], 'amount_limits']
            amount = min(float(max_buy), float(lmt_buy))
            price = ipo_list.loc[symbol, 'ipo_price']
            if amount > 0:
                order_no = self.broker.buy(symbol, amount=amount, price=price)
                logger.info('新股申购: %s, 数量: %s, 价格: %s' % (symbol, amount, price))
                order_nos.append({
                    'order_no': order_no,
                    'trade_side': '新股申购',
                    'symbol': symbol,
                    'amount': amount,
                    'price': price}
                )

        return order_nos

    def order_transfer_to(self, source_symbol, target_symbol,
                          transfer_amount=0, transfer_volume=0, transfer_weight=0):
        '''移仓，将source_symbol的股票卖掉，买入target_symbol'''

        source_symbol = source_symbol.lower()
        target_symbol = target_symbol.lower()

        if min(transfer_amount, transfer_volume, transfer_weight) < 0:
            raise ValueError('transfer_amount, transfer_volume, transfer_weight must be bigger than 0')

        if source_symbol == target_symbol:
            logger.info('Order transfer to: source_symbol == target_symbol.')
            return 0, 0

        portfolio = self.broker.portfolio

        if source_symbol not in portfolio.index:
            raise ValueError('source symbol not in portfolio')

        # 如果不指定转换数量，则默认全部转移
        if transfer_amount == 0 and transfer_volume == 0 and transfer_weight == 0:
            transfer_amount = portfolio.loc[source_symbol, 'enable_amount']

        logger.info('Order source_symbol(%s) (%s,%s,%s) transfer to target_symbol(%s)' % (
            source_symbol, transfer_amount, transfer_volume, transfer_weight, target_symbol))

        source_left = 0
        source_volume = portfolio.loc[source_symbol, 'market_value']
        if source_symbol != 'cash':
            source_left = self.order(source_symbol, amount=-transfer_amount, volume=-transfer_volume,
                                     weight=-transfer_weight, portfolio=portfolio)
            portfolio = self.broker.portfolio
            target_volume = source_volume - portfolio.loc[source_symbol, 'market_value']

        if target_symbol != 'cash':
            target_left = self.order_target(target_symbol, target_volume=target_volume, portfolio=portfolio)

        if source_left != 0:
            logger.info('Order transfer to: source_left(%s)' % source_left)

        if target_left != 0:
            logger.info('Order transfer to: target_left(%s)' % target_left)

        if source_left == 0 and target_left == 0:
            logger.info('Order transfer to Success.')

        return source_left, target_left

    def order_cashout(self, symbols=[], cash_value=0, portfolio=None):

        logger.info('Order CashOut: from symbols %s, cash_value: %s' % (symbols, cash_value))

        if not portfolio:
            portfolio = self.portfolio

        left = cash_value - portfolio.loc['cash', 'enable_amount'] * 1.0
        symbols_value = portfolio.loc[portfolio.index.isin(symbols), 'market_value'].sum()
        if symbols_value < left:
            logger.warning('not enought symbols_value symbols_value: %s, cashout: %s' % (symbols_value, left))
            return

        for symbol in symbols:
            if left <= 0:
                return 0
            else:
                if symbol in portfolio.index:
                    market_value = portfolio.loc[symbol, 'market_value']
                    if market_value > left:
                        # TODO 假设肯定成交完成
                        self.order(symbol, volume=-left)
                        left = 0
                    else:
                        # TODO 假设肯定成交完成
                        self.order_target(symbol, target_amount=0)
                        left = left - market_value

        return left


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

        traders[section] = Trader(brokerid, account, password, **kwargs)

    return traders
