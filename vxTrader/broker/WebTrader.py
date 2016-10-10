# encoding=utf-8
'''
  webtrader 的基础类
'''
import hashlib
import multiprocessing
import time
from multiprocessing.pool import ThreadPool as Pool

import numpy as np
import pandas as pd
import requests

from vxTrader import logger
from vxTrader.TraderException import TraderAPIError, TraderError

_MAX_LIST = 800

_SINA_STOCK_KEYS = [
    "name", "open", "yclose", "lasttrade", "high", "low", "bid", "ask",
    "volume", "amount", "bid1_m", "bid1_p", "bid2_m", "bid2_p", "bid3_m",
    "bid3_p", "bid4_m", "bid4_p", "bid5_m", "bid5_p", "ask1_m", "ask1_p",
    "ask2_m", "ask2_p", "ask3_m", "ask3_p", "ask4_m", "ask4_p", "ask5_m",
    "ask5_p", "date", "time", "status"]

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Pragma': 'no-cache',
    'Connection': 'keep-alive',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Cache-Conrol': 'no-cache',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept-Language': 'zh-CN,zh;q=0.8'
}

_TIMEOUT = 600


class SessionPool():
    '''
    登录session 的池子。
    同一用户在统一渠道内登录过了，就不在重复登录
    '''
    # _instance 存储初始化对象；
    _instance = {}
    # _object 存储已经初始化过的对象
    _object = {}
    # _lock多线程的线程锁
    _lock = multiprocessing.Lock()

    @classmethod
    def register(cls, session_type):
        '''
        用于注册的修饰器
        '''

        def wrapped(wrapped_cls):
            cls._instance[session_type] = wrapped_cls
            return wrapped_cls

        return wrapped

    @classmethod
    def get(cls, session_type, account, password):
        '''
        获取登录session的方法
        '''
        m = hashlib.md5()
        m.update(session_type.encode('utf-8'))
        m.update(account.encode('utf-8'))
        m.update(password.encode('utf-8'))
        # session_type, account, password 是用MD5进行创建关键字
        keyword = m.hexdigest()
        logger.debug('keyword is : %s' % keyword)

        with cls._lock:
            # 先查看一下是否已经创建了一个obj，如果有就直接返回该obj
            obj = cls._object.get(keyword, None)
            # 如果没有创建过，那么就创建
            if obj is None:
                # 看一下类是否已经初始化
                session_class = cls._instance.get(session_type, LoginSession)
                # 创建一个obj，并且保存到cls._object里面
                obj = session_class(account, password)
                cls._object[keyword] = obj
            return obj


class LoginSession():
    _objects = {}

    def __new__(cls, account, password):
        '''
        创建loginSession类时，如果同一券商的账号密码都一样时，只创建一次
        '''

        logger.debug('LoginType: %s, account: %s, password: %s' % (type(cls), account, password))

        # cls, account, password 是用MD5进行创建关键字
        m = hashlib.md5()
        m.update(str(type(cls)).encode('utf-8'))
        m.update(account.encode('utf-8'))
        m.update(password.encode('utf-8'))
        keyword = m.hexdigest()

        obj = cls._objects.get(keyword, None)
        logger.debug('keyword: %s, obj: %s' % (keyword, obj))
        if obj is None:
            # 如果没有缓存过此对象，就创建，并进行缓存
            logger.debug('缓存内没有对象，重新创建一个对象')
            obj = super(LoginSession, cls).__new__(cls)
            cls._objects[keyword] = obj

        return obj

    def __init__(self, account, password):

        self._account = account
        self._password = password

        # 内部的session 初始化，expire_at 初始化
        self._session = None
        self._expire_at = 0

        # 初始化线程锁
        self.lock = multiprocessing.Lock()

    def __enter__(self):
        with self.lock:
            now = time.time()
            if now > self._expire_at:
                # 如果登录超时了，重新登录
                # 登录前准备工作
                self.pre_login()
                # 登录
                self.login()
                # 更新超时时间
                self._expire_at = now + _TIMEOUT

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __getattr__(self, name):
        if self._session:
            return self._session.__getattribute__(name)

    def pre_login(self):
        '''
        登录前准备动作，如：创建self._session
        :return:
        '''
        # 默认创建一个requests.session对象
        self._session = requests.session()

    @property
    def session(self):
        '''
        自动登录，并返回session
        '''
        with self.lock:
            now = time.time()
            if now > self._expire_at:
                # 如果登录超时了，重新登录
                # 登录前准备工作
                self.pre_login()
                # 登录
                self.login()
                # 更新超时时间
                self._expire_at = now + _TIMEOUT
        return self._session

    def login(self):
        '''
        登录接口
        '''
        raise NotImplementedError('Login method is not implemented.')

    def request(self, method, url, **kwargs):
        '''
        调用session的各类http方法
        '''
        logger.debug('Call params: %s' % kwargs)
        with self:
            resq = self.session.request(method=method, url=url, **kwargs)
            resq.raise_for_status()
            logger.debug('return: %s' % resq.text)
            self._expire_at = time.time() + _TIMEOUT
        return resq

    def get(self, url, **kwargs):
        return self.request(method='GET', url=url, **kwargs)

    def post(self, url, **kwargs):
        return self.request(method='POST', url=url, **kwargs)


class WebTrader():
    def __init__(self, account, password, **kwargs):
        self._account = account
        self._password = password

        self._exchange_stock_account = None
        # 初始化线程池
        pool_size = kwargs.pop('pool_size', 5)
        self._worker = Pool(pool_size)

    def keepalive(self, now=0):
        '''
        自动保持连接的函数
        '''
        if now == 0:
            now = time.time()

        logger.debug('keepalive checking. now: %s, expire_at: %s' % (now, self.expire_at))
        if now + 60 > self.expire_at:
            self.portfolio
            logger.info('Reflash the expire time, expire_at timestamp is: %s' % self.expire_at)

        return

    @property
    def exchange_stock_account(self):
        '''
        交易所交易账号
        '''
        raise NotImplementedError('login_info method is not implemented.')

    @property
    def portfolio(self):
        '''
        portfolio is a dataframe:
        symbol  : symbol_name, current_amount, enable_amount, lasttrade, market_value, weight
        sz150023  深成指B     1000    500      0.434  4340     0.5
        cash      现金        4340    300      1      4340     0.5
        '''

        pass

    def hq(self, symbols):
        '''
        行情接口——默认使用新浪的行情接口
        :param symbols: [ 'sz150023','sz150022','sz159915']
        :return: 行情数据
        '''
        if symbols is None:
            raise AttributeError('symbols is empty')
        elif isinstance(symbols, str) is True:
            symbols = [symbols]

        url = 'http://hq.sinajs.cn/?rn=%d&list=' % int(time.time())

        urls = [url + ','.join(symbols[i:i + _MAX_LIST]) \
                for i in range(0, len(symbols), _MAX_LIST)]

        respones = self._worker.imap(requests.get, urls)
        data = list()
        for r in respones:
            lines = r.text.splitlines()
            for line in lines:
                d = line.split('"')[1].split(',')
                # 如果格式不正确,则返回nan
                if len(d) != len(_SINA_STOCK_KEYS):
                    d = [np.nan] * len(_SINA_STOCK_KEYS)
                data.append(d)
        df = pd.DataFrame(data, index=symbols, columns=_SINA_STOCK_KEYS, dtype='float')
        df.index.name = 'symbol'
        df.sort_index()
        if 'volume' in _SINA_STOCK_KEYS and 'lasttrade' in _SINA_STOCK_KEYS and 'yclose' in _SINA_STOCK_KEYS:
            df.loc[df.volume == 0, 'lasttrade'] = df['yclose']
        return df

    def buy(self, symbol, price=0, amount=0, volume=0):
        '''
        买入股票
        :return:  order_no
        '''
        raise NotImplementedError('Buy Not Implemented.')

    def sell(self, symbol, price=0, amount=0, volume=0):
        '''
        卖出股票
        :return:  order_no
        '''
        raise NotImplementedError('Sell Not Implemented.')

    def subscribe(self, symbol, volume):
        '''
        场内基金申购接口
        :param symbol: 基金代码,以of 开头
        :param volume: 申购金额
        :return : order_no
        '''
        raise NotImplementedError('Subscription Not Implemented.')

    def redemption(self, symbol, amount):
        '''
        场内基金赎回接口
        :param symbol: 基金代码,以of 开头
        :param amount: 赎回份额
        :return: order_no
        '''
        raise NotImplementedError('Redemption Not Implemented.')

    def split(self, symbol, amount):
        '''
        分级基金分拆接口
        :param symbol: 基金代码,以of 开头
        :param amount: 母基金分拆份额
        :return: order_no
        '''
        raise NotImplementedError('Split Not Implemented.')

    def merge(self, symbol, amount):
        '''
        分级基金合并接口
        :param symbol: 基金代码,以of 开头
        :param amount: 母基金合并份额
        :return: order_no
        '''
        raise NotImplementedError('Merge Not Implemented.')

    @property
    def orderlist(self):
        '''
        获取当日委托列表
        :return: DataFrame
        index : order_no
        columns : symbol, symbol_name, trade_side, order_price, order_amount, business_price, business_amount, order_status, order_time
        '''

        raise NotImplementedError('OrderList Not Implemented.')

    def cancel(self, order_no):
        '''
        撤销下单
        :param order_no:
        :return: order_no
        '''
        raise NotImplementedError('Cancel Not Implemented.')

    def ipo_subscribe(self, symbol):
        '''
        ipo新股申购
        :param symbol: 新股名称
        :return: order_no
        '''
        raise NotImplementedError('IPO subscribe Not Implemented.')

    def trans_in(self, cash_in, bank_no=None):
        '''
        资金转入
        :param cash_in:
        :param bank_no:
        :return:
        '''
        raise NotImplementedError('trans_in Not Implemented.')

    def trans_out(self, cash_out, bank_no=None):
        '''
        资金转出
        :param cash_out:
        :param bank_no:
        :return:
        '''
        raise NotImplementedError('trans_out Not Implemented.')

    def order(self, symbol, amount=0, volume=0, wait=10):
        '''
        按数量下单
        :return: order_no, left
        '''
        logger.debug('order_amount: symbol: %s, amount: %s, volume: %s, wait: %s' % (symbol, amount, volume, wait))

        if (amount == 0 and volume == 0):
            raise AttributeError('order_amount amount and volume can not be 0')

        # 下单
        try:
            hq = self.hq(symbol)
            logger.debug('hq: %s' % hq.loc[symbol])
            price = hq.loc[symbol, 'lasttrade']
            amount = amount if amount else round(volume, 2) // price // 100 * 100
            if amount == 0:
                return 0, 0

            if amount > 0 or volume > 0:
                price = hq.loc[symbol, 'ask']
                order_no = self.buy(symbol, price, amount=amount)
                logger.info('buy order send,order_no: %s' % order_no)
            elif amount < 0 or volume < 0:
                price = hq.loc[symbol, 'bid']
                order_no = self.sell(symbol, price, amount=-amount)
                logger.info('sell order send,order_no: %s' % order_no)

        except TraderError as err:
            logger.debug('Order Error: %s' % err)
            raise err

        # 每隔2秒检查一下成交状态.
        # 如果是已成交,则返回order_no, 0
        # 如果是已报、部成, 则再等2秒钟。
        # 如果是其他状态,就报警
        time.sleep(5)
        for i in range(int((wait + 1) / 2)):
            logger.info('Check Order Status %s times.' % i)
            orderlist = self.orderlist
            status = orderlist.loc[order_no, 'order_status']

            if status in ('已成'):
                logger.info('Order Success. %s' % orderlist.loc[order_no])
                return order_no, 0

            elif status in ('已报', '部成', '正常'):
                logger.info('Order not Complete. %s' % orderlist.loc[order_no])
                time.sleep(5)

            elif status in ('未报'):
                logger.info('Not Allow to Send Order. %s' % orderlist.loc[order_no])
                self.cancel(order_no)
                return order_no, amount
            else:
                logger.error('Order Status Invaild. %s' % orderlist.loc[order_no])
                raise TraderAPIError('Order Status Invaild. %s' % orderlist.loc[order_no])

        # 等待了足够时间,仍未全部成交,则撤单
        try:
            logger.warning('Cancel order: %s' % order_no)
            self.cancel(order_no)
            time.sleep(0.3)
            orderlist = self.orderlist
            status = orderlist.loc[order_no, 'order_status']
            if status in ('已撤', '部撤'):
                orderlist['left'] = orderlist['order_amount'] - orderlist['business_amount']
                left = orderlist.loc[order_no, 'left']
                if amount < 0:
                    left = -left
                return order_no, left
            else:
                raise TraderAPIError('Order Status Invaild. %s' % orderlist.loc[order_no])

        except TraderError as err:
            logger.warning(err)
            logger.warning('Order Status Invaild. %s' % orderlist.loc[order_no])

    def order_target_amount(self, symbol, target_amount, wait=10):
        '''
        根据持仓目标下单：按最终持有数量
        :return: order_no, left
        '''
        logger.info('order target amount: symbol: %s, target_amount: %s' % (symbol, target_amount))
        if target_amount < 0:
            raise AttributeError('target_amount(%s) must be larger than 0.' % target_amount)
        portfolio = self.portfolio
        base_amount = 0
        if symbol in portfolio.index:
            base_amount = portfolio.loc[symbol, 'current_amount']
        amount = target_amount - base_amount
        if amount != 0:
            return self.order(symbol, amount=amount, wait=wait)
        else:
            return 0, 0

    def order_target_volume(self, symbol, target_volume, wait=10):
        '''
        根据持仓目标下单：按照最终持仓金额
        :return: order_no, left
        '''
        logger.info('order target volume: symbol: %s, target_volume: %s' % (symbol, target_volume))
        if target_volume < 0:
            raise AttributeError('target_volume(%s) must be larger than 0.' % target_volume)
        portfolio = self.portfolio
        base_volume = 0
        if symbol in portfolio.index:
            base_volume = portfolio.loc[symbol, 'market_value']
        volume = target_volume - base_volume
        if volume != 0:
            return self.order(symbol, volume=volume, wait=wait)
        else:
            return 0, 0

    def order_target_percent(self, symbol, target_percent, wait=10):
        '''
        根据持仓目标下单：按照最终持仓比例
        :return: order_no, left
        '''
        logger.info('order target percent: symbol: %s, target_percent: %s' % (symbol, target_percent))
        if target_percent < 0:
            raise AttributeError('target_percent(%s) must be larger than 0.' % target_percent)
        if target_percent > 1:
            raise AttributeError('target_percent(%s) must be smaller than 1.' % target_percent)

        portfolio = self.portfolio
        portfolio_value = portfolio['market_value'].sum()
        target_volume = portfolio_value * target_percent
        base_volume = 0
        if symbol in portfolio.index:
            base_volume = portfolio.loc[symbol, 'market_value']
        volume = target_volume - base_volume
        if volume != 0:
            return self.order(symbol, volume=volume, wait=wait)
        else:
            return 0, 0
