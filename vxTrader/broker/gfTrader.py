# encoding=utf-8

'''
广发证券的交易接口分为：
1. gfTrader   ——普通的证券交易接口
2. gfMarginTrader  —— 融资融券证券交易接口
'''

import re
import time
import uuid
from io import BytesIO

import pandas as pd
import pytesseract
import requests
from PIL import Image, ImageFilter
from vxUtils.decorator import retry

from vxTrader import logger
from vxTrader.TraderException import VerifyCodeError, TraderAPIError
from vxTrader.broker.WebTrader import LoginSession, WebTrader, BrokerFactory
from vxTrader.util import code_to_symbols

FLOAT_COLUMNS = [
    'order_amount', 'order_price', 'lasttrade', 'current_amount', 'enable_amount', 'market_value',
    'enable_balance', 'current_balance', 'net_balance', 'asset_balance', 'business_price', 'business_amount',
    'order_amount', 'order_price', 'fund_balance']

RENAME_DICT = {
    'last_price': 'lasttrade',
    'entrust_no': 'order_no',
    'stock_name': 'symbol_name',
    'stock_code': 'symbol',
    'entrust_bs': 'trade_side',
    'entrust_price': 'order_price',
    'entrust_amount': 'order_amount',
    'entrust_status': 'order_status',
    'report_time': 'order_time'
}

TIMEOUT = 600


class gfLoginSession(LoginSession):
    '''
    广发证券登录session管理
    '''

    def __init__(self, account, password):

        # 初始化父类
        super(gfLoginSession, self).__init__(account=account, password=password)

        # TODO 从系统中读取磁盘编号
        self.disknum = "S2ZWJ9AF517295"
        self.mac_address = ("".join(c + "-" if i % 2 else c for i, c in \
                                    enumerate(hex(uuid.getnode())[2:].zfill(12)))[:-1]).upper()
        # 校验码的正则表达式
        self.code_rule = re.compile("^[A-Za-z0-9]{5}$")

        # 交易用的sessionId
        self._dse_sessionId = None

        # 融资融券标志
        self.margin = False

    def pre_login(self):
        '''
        初始化session，以及需要的headers
        :return:
        '''

        # session
        gfheader = {'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-Hans-CN, zh-Hans; q=0.5',
                    'Connection': 'Keep-Alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
                    'X-Requested-With': 'XMLHttpRequest'}

        session = requests.session()
        session.headers.update(gfheader)
        resq = session.get('https://trade.gf.com.cn/')
        resq.raise_for_status()
        logger.debug('get trade home pages sucess.')

        self._expire_at = 0
        self._session = session
        return

    @property
    @retry(10, VerifyCodeError)
    def vcode(self):

        # 获取校验码
        r = self._session.get('https://trade.gf.com.cn/yzm.jpgx')
        r.raise_for_status()

        # 通过内存保存图片，进行识别
        img_buffer = BytesIO(r.content)
        img = Image.open(img_buffer)
        if hasattr(img, "width"):
            width, height = img.width, img.height
        else:
            width, height = img.size
        for x in range(width):
            for y in range(height):
                if img.getpixel((x, y)) < (100, 100, 100):
                    img.putpixel((x, y), (256, 256, 256))

        gray = img.convert('L')
        two = gray.point(lambda x: 0 if 68 < x < 90 else 256)
        min_res = two.filter(ImageFilter.MinFilter)
        med_res = min_res.filter(ImageFilter.MedianFilter)
        for _ in range(1):
            med_res = med_res.filter(ImageFilter.MedianFilter)

        # 通过tesseract-ocr的工具进行校验码识别
        vcode = pytesseract.image_to_string(med_res)
        img.close()
        img_buffer.close()

        vcode = vcode.replace(' ', '')
        if self.code_rule.findall(vcode) != []:
            logger.debug('vcode is: %s' % vcode)
            return vcode
        else:
            raise VerifyCodeError('verify code error: %s' % vcode)

    @retry(10, VerifyCodeError)
    def login(self):

        # 无论是否登录，都重新创建一个session对象
        self.pre_login()

        login_params = {
            "authtype": 2,
            "disknum": self.disknum,
            "loginType": 2,
            "origin": "web",
            'mac': self.mac_address,
            'username': self._account,
            'password': self._password,
            'tmp_yzm': self.vcode
        }
        resq = self._session.post(
            url='https://trade.gf.com.cn/login',
            params=login_params
        )
        resq.raise_for_status()
        logger.debug('login resq: %s' % resq.json())

        data = resq.json()
        if data['success'] == True:
            v = resq.headers
            self._dse_sessionId = v['Set-Cookie'][-32:]
            # 等待服务器准备就绪
            time.sleep(0.1)
            logger.info('Login success: %s' % self._dse_sessionId)
            return
        elif data['success'] == False and 'error_info' not in data.keys():
            logger.warning('当前系统无法登陆')
            raise TraderAPIError(data)
        elif data['error_info'].find('验证码') != -1:
            self.dse_sessionId = None
            logger.warning('VerifyCode Error: %s' % data)
            raise VerifyCodeError(data['error_info'])
        else:
            self.dse_sessionId = None
            logger.warning('API Login Error: %s' % data)
            raise TraderAPIError(data['error_info'])

    def request(self, method, url, **kwargs):

        with self:
            params = kwargs.get('params', {})
            params.update({'dse_sessionId': self._dse_sessionId})
            kwargs['params'] = params

            logger.debug('Call params: %s' % kwargs)
            r = self._session.request(method=method, url=url, **kwargs)
            r.raise_for_status()
            logger.debug('return: %s' % r.text)
            self._expire_at = time.time() + TIMEOUT
        return r

    def post_login(self):

        if self.margin:
            r = self.session.post(
                url='https://trade.gf.com.cn/entry',
                classname='com.gf.etrade.control.RZRQUF2Control',
                method='ValidataLogin'
            )
            data = r.json()

            if data.get('success', False) == False:
                logger.error(data)
                error_info = data.get('error_info', data)
                raise TraderAPIError(error_info)

            logger.debug('Login Margin Success.')

        return

    def logout(self):

        url = 'https://trade.gf.com.cn/entry'
        params = {
            'classname': 'com.gf.etrade.control.AuthenticateControl',
            'method': 'logout'
        }
        if self._session:
            self._session.get(url, params=params)

        self._session = None
        self._expire_at = 0


@BrokerFactory('gf', '广发证券')
class gfTrader(WebTrader):
    def __init__(self, account, password, **kwargs):
        super(gfTrader, self).__init__(account=account, password=password, **kwargs)
        self.client = gfLoginSession(account=account, password=password)

    @property
    def exchange_stock_account(self):

        if self._exchange_stock_account:
            return self._exchange_stock_account

        account_params = {
            'classname': 'com.gf.etrade.control.FrameWorkControl',
            'method': 'getMainJS'
        }

        url = 'https://trade.gf.com.cn/entry'
        resq = self.client.get(url, params=account_params)
        resq.raise_for_status()

        jslist = resq.text.split(';')
        jsholder = jslist[11]
        jsholder = re.findall(r'\[(.*)\]', jsholder)
        jsholder = eval(jsholder[0])

        self._exchange_stock_account = dict()

        for holder in jsholder:
            if isinstance(holder, dict):
                self._exchange_stock_account[holder['exchange_type']] = holder['stock_account']

        return self._exchange_stock_account

    @property
    def portfolio(self):

        # 异步提交持仓和余额
        balance = self._trade_api(
            classname='com.gf.etrade.control.StockUF2Control',
            method='queryAssert'
        )

        position = self._trade_api(
            classname='com.gf.etrade.control.StockUF2Control',
            method='queryCC'
        )

        # 处理持仓
        if position.shape[0] > 0:
            position = position[
                ['symbol', 'symbol_name', 'current_amount', 'enable_amount', 'lasttrade', 'market_value']]
        else:
            position = pd.DataFrame([], columns=['order_no', 'symbol', 'symbol_name', 'trade_side', 'order_price', \
                                                 'order_amount', 'business_price', 'business_amount', 'order_status',
                                                 'order_time'])
        position = position.set_index('symbol')

        # 处理现金
        asset_balance = balance['asset_balance'].iloc[0]
        position.loc['cash', 'symbol_name'] = balance['money_type_dict'].iloc[0]
        position.loc['cash', 'current_amount'] = balance['fund_balance'].iloc[0]
        position.loc['cash', 'enable_amount'] = balance['enable_balance'].iloc[0]
        position.loc['cash', 'lasttrade'] = 1.0
        position.loc['cash', 'market_value'] = balance['fund_balance'].iloc[0]

        # 计算仓位
        position['weight'] = position['market_value'] / asset_balance
        position['weight'] = position['weight'].round(4)
        position = position.dropna(axis=0)

        return position

    def _trade_api(self, **kwargs):
        url = 'https://trade.gf.com.cn/entry'
        resq = self.client.post(url, params=kwargs)
        if len(resq.text) == 0:
            self.client.reset()
            resq = self.client.post(url, params=kwargs)

        data = resq.json()

        if data.get('success', False) == False:
            logger.error(data)
            error_info = data.get('error_info', data)
            raise TraderAPIError(error_info)

        df = pd.DataFrame(data['data'])

        df.rename(columns=RENAME_DICT, inplace=True)
        if 'symbol' in df.columns:
            df['symbol'] = df['symbol'].apply(code_to_symbols)

        # 去字段的并集，提高效率
        cols = list(set(FLOAT_COLUMNS).intersection(set(df.columns)))

        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        return df

    @property
    def orderlist(self):

        orderlist = self._trade_api(
            classname='com.gf.etrade.control.StockUF2Control',
            method='queryDRWT',
            action_in=1,
            query_direction=0,
            limit=20,
            request_num=100
        )

        # 如果是空的orderlist，处理一下columns
        if orderlist.shape[0] == 0:
            orderlist = pd.DataFrame([], columns=['order_no', 'symbol', 'symbol_name', 'trade_side', 'order_price', \
                                                  'order_amount', 'business_price', 'business_amount', 'order_status',
                                                  'order_time'])

        else:
            orderlist['trade_side'] = orderlist['entrust_bs_dict']
            orderlist['order_status'] = orderlist['entrust_status_dict']
            orderlist = orderlist[['order_no', 'symbol', 'symbol_name', 'trade_side', 'order_price', \
                                   'order_amount', 'business_price', 'business_amount', 'order_status', 'order_time']]
            orderlist.dropna(axis=0, inplace=True)

        orderlist.set_index('order_no', inplace=True)
        return orderlist

    def cancel(self, order_no):
        df = self._trade_api(
            entrust_no=order_no,
            classname='com.gf.etrade.control.StockUF2Control',
            method='cancel',
            exchange_type=1,
            batch_flag=0
        )

        return df['order_no'].iloc[0]

    def buy(self, symbol, price=0, amount=0, volume=0):

        symbol = symbol.lower()
        if symbol[:2] not in ['sz', 'sh']:
            raise ValueError('symbol(%s) is not support' % symbol)

        if price == 0:
            hq = self.hq(symbol)
            price = hq.loc[symbol, 'ask']

        if amount == 0:
            if volume == 0:
                raise ValueError('amount and volume both is 0' % symbol)
            else:
                amount = volume // price // 100 * 100

        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        df = self._trade_api(
            entrust_amount=amount,
            entrust_prop=0,  # 委托方式
            classname='com.gf.etrade.control.StockUF2Control',
            method='entrust',
            entrust_bs=1,
            stock_account=self.exchange_stock_account[exchange_type],
            exchange_type=exchange_type,
            stock_code=symbol[2:],
            entrust_price=price
        )

        return df['order_no'].iloc[0]

    def sell(self, symbol, price=0, amount=0, volume=0):

        symbol = symbol.lower()
        if symbol[:2] not in ['sz', 'sh']:
            raise ValueError('symbol(%s) is not support' % symbol)

        if price == 0:
            hq = self.hq(symbol)
            price = hq.loc[symbol, 'bid']

        if amount == 0:
            if volume == 0:
                raise ValueError('amount and volume both is 0' % symbol)
            else:
                amount = volume // price // 100 * 100

        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        df = self._trade_api(
            entrust_amount=amount,
            entrust_prop=0,  # 委托方式
            classname='com.gf.etrade.control.StockUF2Control',
            method='entrust',
            entrust_bs=2,  # 1 买入， 2 卖出
            stock_account=self.exchange_stock_account[exchange_type],
            exchange_type=exchange_type,
            stock_code=symbol[2:],
            entrust_price=price
        )

        return df['order_no'].iloc[0]

    def subscribe(self, symbol, volume):

        # 转换成交易所sz或者sh开头的symbol
        symbol = code_to_symbols(symbol[2:])

        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        df = self._trade_api(
            entrust_amount=volume,
            classname='com.gf.etrade.control.StockUF2Control',
            method='CNJJSS',
            entrust_bs=1,  # 1 买入， 2 卖出
            stock_account=self.exchange_stock_account[exchange_type],
            exchange_type=exchange_type,
            stock_code=symbol[2:],
            entrust_price=0,
        )

        return df['order_no'].iloc[0]

    def redemption(self, symbol, amount):

        # 转换成交易所sz或者sh开头的symbol
        symbol = code_to_symbols(symbol[2:])

        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        df = self._trade_api(
            entrust_amount=amount,
            classname='com.gf.etrade.control.StockUF2Control',
            method='CNJJSS',
            entrust_bs=2,  # 1 买入， 2 卖出
            stock_account=self.exchange_stock_account[exchange_type],
            exchange_type=exchange_type,
            stock_code=symbol[2:],
            entrust_price=0,
        )

        return df['order_no'].iloc[0]

    def merge(self, symbol, amount):

        # 转换成交易所sz或者sh开头的symbol
        symbol = code_to_symbols(symbol[2:])

        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        df = self._trade_api(
            classname='com.gf.etrade.control.SHLOFFundControl',
            method='assetSecuprtTrade',
            entrust_bs='',
            entrust_amount=amount,
            stock_account=self.exchange_stock_account[exchange_type],
            exchange_type=exchange_type,
            stock_code=symbol[2:],
            entrust_prop='LFM',
            entrust_price=1
        )

        return df['order_no'].iloc[0]

    def split(self, symbol, amount):

        # 转换成交易所sz或者sh开头的symbol
        symbol = code_to_symbols(symbol[2:])

        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        df = self._trade_api(
            classname='com.gf.etrade.control.SHLOFFundControl',
            method='doDZJYEntrust',
            entrust_bs='',
            entrust_amount=amount,
            stock_account=self.exchange_stock_account[exchange_type],
            exchange_type=exchange_type,
            stock_code=symbol[2:],
            entrust_prop='LFP',
            entrust_price=1
        )

        return df['order_no'].iloc[0]

    def ipo_limit(self):
        df = self._trade_api(
            classname='com.gf.etrade.control.StockUF2Control',
            method='querySecuSubequity',
            limit=50
        )
        if df.shape[0] == 0:
            df = pd.DataFrame([], columns=['exchange_type', 'exchange_stock_account', 'amount_limits', \
                                           'accountno', 'init_date'])
        else:
            df = df[['exchange_type', 'stock_account', 'enable_amount', 'client_id', 'init_date']]
            rename = {
                'stock_account': 'exchange_stock_account',
                'enable_amount': 'amount_limits',
                'client_id': 'accountno'
            }
            df.rename(columns=rename, inplace=True)
            df.set_index('exchange_type', inplace=True)
        return df

    def ipo_list(self):
        df = self._trade_api(
            classname='com.gf.etrade.control.StockUF2Control',
            method='queryNewStkcode',
            request_num=50,
            query_direction=1
        )

        if df.shape[0] == 0:
            df = pd.DataFrame([], columns=['symbol', 'symbol_name', 'exchange_type', 'subscribe_type', \
                                           'max_buy_amount', 'buy_unit', 'money_type', 'ipo_price', \
                                           'ipo_date', 'ipo_status'])
        else:
            df = df[['symbol', 'symbol_name', 'exchange_type', 'stock_type_dict', \
                     'high_amount', 'buy_unit', 'money_type_dict', 'lasttrade', 'issue_date', 'stkcode_status_dict']]

            rename = {
                'stock_type_dict': 'subscribe_type',
                'high_amount': 'max_buy_amount',
                'money_type_dict': 'money_type',
                'lasttrade': 'ipo_price',
                'issue_date': 'ipo_date',
                'stkcode_status_dict': 'ipo_status'
            }
            df.rename(columns=rename, inplace=True)
            df.set_index('symbol', inplace=True)

        return df
