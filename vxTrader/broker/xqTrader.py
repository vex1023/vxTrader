# encoding=utf-8
'''
雪球web交易接口
'''

import time

import demjson as json
import pandas as pd
import requests
import six

from vxTrader import logger, TraderFactory
from vxTrader.TraderException import TraderAPIError
from vxTrader.broker.WebTrader import WebTrader, LoginSession

_BASE_MULTIPE = 1000000.00

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Host': 'xueqiu.com',
    'Pragma': 'no-cache',
    'Connection': 'keep-alive',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Cache-Conrol': 'no-cache',
    'Referer': 'http://xueqiu.com/P/ZH003694',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept-Language': 'zh-CN,zh;q=0.8'
}

_RENAME_DICT = {
    'stock_symbol': 'symbol',
    'stock_name': 'symbol_name',
    'volume': 'current_amount'
}


def to_text(value, encoding="utf-8"):
    if isinstance(value, six.text_type):
        return value
    if isinstance(value, six.binary_type):
        return value.decode(encoding)
    return six.text_type(value)


class xqLoginSession(LoginSession):
    '''
    雪球登录session管理
    '''
    LoginType = 'xq'

    def pre_login(self):
        self._session = requests.session()
        self._session.headers.update(_HEADERS)
        r = self._session.get('http://www.xueqiu.com/')
        r.raise_for_status()

        return

    def login(self):
        self.pre_login()

        login_params = {
            'username': '',
            'areacode': '86',
            'telephone': self._account,
            'remember_me': '0',
            'password': self._password
        }

        # 提交登录信息
        r = self._session.post(url='https://xueqiu.com/user/login',
                               data=login_params)
        r.raise_for_status()
        login_info = r.json()

        # 错误检查，并处理
        if 'error_description' in login_info.keys():
            self._expire_at = 0
            logger.warning('Login Error: %s' % login_info['error_description'])
            raise TraderAPIError('Login Error: %s' % login_info['error_description'])

        # 登录成功
        logger.info('Login Success. uid: %s, expire_at: %s' % (login_info['uid'], login_info['expires_in']))
        return


@TraderFactory('xq', '雪球', '雪球组合')
class xqTrader(WebTrader):
    def __init__(self, account, password, portfolio_code):

        super(xqTrader, self).__init__(account=account, password=password, pool_size=2)
        self.portfolio_code = portfolio_code
        self.client = xqLoginSession(account=account, password=password)

    @property
    def portfolio(self):

        url = 'https://xueqiu.com/p/' + self.portfolio_code
        r = self.client.get(url)
        r.raise_for_status()

        # 查找持仓的字符串段
        html = r.text
        pos_start = html.find('SNB.cubeInfo = ') + len('SNB.cubeInfo = ')
        pos_end = html.find('SNB.cubePieData')
        json_data = to_text(html[pos_start:pos_end - 2])
        logger.debug(json_data)
        p_info = json.decode(json_data, encoding='utf-8')

        positions = p_info['view_rebalancing']['holdings']
        logger.debug(p_info)

        df = pd.DataFrame(positions)
        df.rename(columns=_RENAME_DICT, inplace=True)
        df['symbol'] = df['symbol'].str.lower()
        df = df.set_index('symbol')
        hq = self.hq(df.index)
        df['lasttrade'] = hq['lasttrade']

        df.loc['cash', 'symbol_name'] = '人民币'
        df.loc['cash', 'current_amount'] = p_info['view_rebalancing']['cash_value']
        df.loc['cash', 'lasttrade'] = 1.0

        df['current_amount'] = df['current_amount'] * _BASE_MULTIPE
        df['enable_amount'] = df['current_amount']
        df['market_value'] = df['current_amount'] * df['lasttrade']
        net_value = df['market_value'].sum()
        df['weight'] = (df['market_value'] / net_value).round(4)

        return df[['symbol_name', 'current_amount', 'enable_amount', 'lasttrade', 'market_value', 'weight']]

    def _get_stock_info(self, symbol):
        '''
        获取雪球的股票信息
        '''

        symbol = symbol.lower()

        url = 'https://xueqiu.com/stock/p/search.json?size=300&key=47bce5c74f&market=cn&code=%s' % symbol
        r = self.client.get(url=url)
        r.raise_for_status()

        data = r.json()['stocks']

        for d in data:
            code = d.get('code', '').lower()
            if symbol == code:
                return d
        return {}

    @property
    def orderlist(self):

        order_col = ['order_no', 'symbol', 'symbol_name', 'trade_side', 'order_price', 'order_amount', 'business_price',
                     'business_amount',
                     'order_status', 'order_time']

        p = {
            "cube_symbol": self.portfolio_code,
            'count': 5,
            'page': 1
        }

        resq = self.client.get(url='https://xueqiu.com/cubes/rebalancing/history.json', params=p, headers={})
        logger.debug(resq.text)
        resq.raise_for_status()
        data = resq.json()['list']
        logger.debug('get_entrust raw data: %s' % data)

        order_list = []
        for xq_orders in data:
            status = xq_orders['status']  # 调仓状态
            if status == 'pending':
                status = "已报"
            elif status == 'canceled':
                status = "已撤"
            elif status == 'failed':
                status = "废单"
            elif status == 'success':
                status = "已成"
            else:
                raise TraderAPIError('Unkown order status. %s' % status)

            for order in xq_orders['rebalancing_histories']:
                prev_target_volume = order['prev_target_volume'] if order['prev_target_volume'] is not None else 0.0
                target_volume = order['target_volume'] if order['target_volume'] else 0.0
                # 实际上应该是这里通常说得amount
                volume = abs(target_volume - prev_target_volume) * _BASE_MULTIPE
                price = order['price'] if order['price'] else 0.0
                if volume > 0:
                    order_list.append({
                        'order_no': order['id'],
                        'symbol': order['stock_symbol'].lower(),
                        'symbol_name': order['stock_name'],
                        'trade_side': "买入" if target_volume > prev_target_volume else "卖出",
                        'order_status': status,
                        'order_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(order['updated_at'] / 1000)),
                        'business_amount': volume * price if status == '已成' else 0,
                        'business_price': price if status == '已成' else 0,
                        'order_amount': volume * price,
                        'order_price': price,
                    })
        df = pd.DataFrame(order_list, columns=order_col)
        df = df.set_index('order_no')
        df[['order_price', 'order_amount', 'business_amount', 'business_price']] = \
            df[['order_price', 'order_amount', 'business_amount', 'business_price']].round(3)

        return df

    def cancel(self, order_no=0):

        portfolio = self.portfolio

        comment = '撤单\n 来自vxTrader'

        stock_infos = self._worker.imap(
            self._get_stock_info,
            portfolio.loc[portfolio.index != 'cash'].index
        )

        holdings = []
        for stock in stock_infos:
            holding = {
                "code": stock['code'],
                "flag": stock['flag'],
                "type": stock['type'],
                "stock_id": stock['stock_id'],
                "ind_id": stock['ind_id'],
                "ind_name": stock['ind_name'],
                "ind_color": stock['ind_color'],
                "textname": stock['name'],
                "segment_name": stock['ind_name'],
                # 注意此处雪球接受的是持仓百分比，例如：30.33
                "weight": round(portfolio.loc[stock['code'].lower(), 'weight'] * 100, 2),
                "proactive": True,
                "price": str(stock['current'])
            }

            holdings.append(holding)

        params = {
            # 注意此处雪球接受的是持仓百分比，例如：30.33
            'cash': round(portfolio.loc['cash', 'weight'] * 100, 2),
            'holdings': str(json.encode(holdings)),
            'cube_symbol': self.portfolio_code,
            'segment': 1,
            'comment': comment
        }

        self.client.headers.update(
            referer='https://xueqiu.com/p/update?action=holdings&symbol=%s' % self.portfolio_code)
        logger.debug(self.client.session.headers)

        try:
            r = self.client.post(url='https://xueqiu.com/cubes/rebalancing/create.json', params=params)
            r.raise_for_status()
        except Exception as err:
            logger.warning('order failed: %s' % err)
            raise TraderAPIError(str(err))

        logger.debug('order success:%s %s' % (holdings, r.json()))
        return r.json()['id']

    def _trade_api(self, symbol, target_percent, portfolio=None, comment=None):

        # 目标的持仓比例应该大于0
        if target_percent < 0:
            raise TraderAPIError('wrong target_percent: %s' % target_percent)

        # symbol 转换成小写
        symbol = symbol.lower()

        if comment is None:
            comment = '将股票( %s )的仓位调整至 %.2f%% . \n 来自vxTrader' % (symbol, target_percent * 100)

        # 如果没有穿portfolio，就更新一下
        if portfolio is None:
            portfolio = self.portfolio

        portfolio.loc[symbol, 'weight'] = target_percent
        market_weight = portfolio.loc[portfolio.index != 'cash', 'weight'].sum()
        if market_weight > 1.0:
            raise TraderAPIError('wrong target_percent: %s, market_weight is: %s' % (target_percent, market_weight))

        portfolio.loc['cash', 'weight'] = 1.0 - market_weight

        stock_infos = self._worker.imap(
            self._get_stock_info,
            portfolio.loc[portfolio.index != 'cash'].index
        )

        holdings = []
        for stock in stock_infos:
            proactive = (stock['code'].lower() == symbol)
            holding = {
                "code": stock['code'],
                "flag": stock['flag'],
                "type": stock['type'],
                "stock_id": stock['stock_id'],
                "ind_id": stock['ind_id'],
                "ind_name": stock['ind_name'],
                "ind_color": stock['ind_color'],
                "textname": stock['name'],
                "segment_name": stock['ind_name'],
                # 注意此处雪球接受的是持仓百分比，例如：30.33
                "weight": round(portfolio.loc[stock['code'].lower(), 'weight'] * 100, 2),
                "proactive": proactive,
                "price": str(stock['current'])
            }

            holdings.append(holding)

        params = {
            # 注意此处雪球接受的是持仓百分比，例如：30.33
            'cash': round(portfolio.loc['cash', 'weight'] * 100, 2),
            'holdings': str(json.encode(holdings)),
            'cube_symbol': self.portfolio_code,
            'segment': 1,
            'comment': comment
        }

        self.client.headers.update(
            referer='https://xueqiu.com/p/update?action=holdings&symbol=%s' % self.portfolio_code)
        logger.debug(self.client.session.headers)

        try:
            r = self.client.post(url='https://xueqiu.com/cubes/rebalancing/create.json', params=params)
            r.raise_for_status()
        except Exception as err:
            logger.warning('order failed: %s' % err)
            raise TraderAPIError(str(err))

        logger.debug('order success:%s %s' % (holdings, r.json()))
        return r.json()['id']

    def buy(self, symbol, price=0, amount=0, volume=0):

        symbol = symbol.lower()

        if amount == 0 and volume == 0:
            raise TraderAPIError('do you want to buy amount/volume 0 ?')

        if volume == 0:
            hq = self.hq(symbol)
            price = hq.loc[symbol, 'lasttrade']
            volume = price * amount

        portfolio = self.portfolio
        net_asset = portfolio['market_value'].sum()

        # 计算交易股票的持仓目标比例
        if symbol in portfolio.index:
            target_percent = (portfolio.loc[symbol, 'market_value'] + volume) / net_asset
        else:
            target_percent = volume / net_asset

        return self._trade_api(symbol=symbol, target_percent=target_percent, portfolio=portfolio)

    def sell(self, symbol, price=0, amount=0, volume=0):

        symbol = symbol.lower()

        if amount == 0 and volume == 0:
            raise TraderAPIError('do you want to sell amount/volume 0 ?')

        if volume == 0:
            hq = self.hq(symbol)
            price = hq.loc[symbol, 'lasttrade']
            volume = price * amount

        portfolio = self.portfolio
        # 计算一下当前持有该证券的市值
        current_market_value = 0
        if symbol in portfolio.index:
            current_market_value = portfolio.loc[symbol, 'market_value']

        target_volume = current_market_value - volume
        if target_volume < 0:
            raise TraderAPIError('Not enough %s for sell' % symbol)

        target_percent = target_volume / portfolio['market_value'].sum()
        return self._trade_api(symbol=symbol, target_percent=target_percent, portfolio=portfolio)

    def order_target_percent(self, symbol, target_percent, wait=10):

        return self._trade_api(symbol=symbol, target_percent=target_percent), 0

    def order_target_amount(self, symbol, target_amount, wait=10):

        symbol = symbol.lower()
        hq = self.hq(symbol)
        price = hq.loc[symbol, 'lasttrade']
        target_volume = price * target_amount

        portfolio = self.portfolio
        target_percent = target_volume / portfolio['market_value'].sum()

        return self._trade_api(symbol=symbol, target_percent=target_percent, portfolio=portfolio), 0

    def order_target_volume(self, symbol, target_volume, wait=10):

        portfolio = self.portfolio
        target_percent = target_volume / portfolio['market_value'].sum()

        return self._trade_api(symbol=symbol, target_percent=target_percent, portfolio=portfolio), 0

    def order(self, symbol, amount=0, volume=0, wait=10):

        if amount < 0 or volume < 0:
            return self.sell(symbol, 0, -amount, -volume), 0
        else:
            return self.buy(symbol, 0, amount, volume), 0
