# encoding=utf-8
'''
佣金宝交易接口
'''

import random
import re
import ssl
import urllib
import uuid

import demjson
import pandas as pd
import pytesseract
import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

from vxTrader import TraderFactory, logger
from vxTrader.TraderException import VerifyCodeError, TraderAPIError, LoginFailedError
from vxTrader.broker.WebTrader import LoginSession, WebTrader, SessionPool
from vxTrader.util import code_to_symbols, retry, to_time

TIMEOUT = 600

FLOAT_COLUMNS = [
    'order_amount', 'order_price', 'lasttrade', 'current_amount', 'enable_amount', 'market_value',
    'enable_balance', 'asset_balance', 'business_price', 'business_amount', 'order_time', 'order_amount',
    'order_price'
]

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


class Ssl3HttpAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)



@SessionPool.register('yjb')
class yjbLoginSession(LoginSession):
    def __init__(self, account, password):

        # 初始化父类
        super(yjbLoginSession, self).__init__(account=account, password=password)

        # 初始化登录参数
        self.mac_address = ("".join(c + "-" if i % 2 else c for i, c in \
                                    enumerate(hex(uuid.getnode())[2:].zfill(12)))[:-1]).upper()

        # TODO disk_serial_id and cpuid machinecode 修改为实时获取
        self.disk_serial_id = "ST3250890AS"
        self.cpuid = "-41315-FA76111D"
        self.machinecode = "-41315-FA76111D"

        self.expire_at = 0
        self._exchange_stock_account = None

        # 校验码规则
        self.code_rule = re.compile("^[0-9]{4}$")

    def pre_login(self):

        session = requests.session()
        session.mount('https://', Ssl3HttpAdapter())
        r = session.get('https://jy.yongjinbao.com.cn/winner_gj/gjzq/')
        r.raise_for_status()
        self._session = session
        return

    @property
    @retry(10, VerifyCodeError)
    def vcode(self):

        r = self._session.get(
            'https://jy.yongjinbao.com.cn/winner_gj/gjzq/user/extraCode.jsp',
            params={'randomStamp': random.random()}
        )
        r.raise_for_status()

        with open('.yjb_%s_vcode.png' % self._account, 'wb') as pic:
            pic.write(r.content)

        img = Image.open('.yjb_%s_vcode.png' % self._account)
        code = pytesseract.image_to_string(img)
        img.close()

        if self.code_rule.findall(code) == []:
            raise VerifyCodeError('Wrong verify code: %s' % code)
        else:
            logger.debug('Verify Code is: %s' % code)
            return code

    def login(self):

        self.pre_login()

        login_params = {
            "function_id": 200,
            "login_type": "stock",
            "version": 200,
            "identity_type": "",
            "remember_me": "",
            "input_content": 1,
            "content_type": 0,
            "loginPasswordType": "B64",
            "disk_serial_id": self.disk_serial_id,
            "cpuid": self.cpuid,
            "machinecode": self.machinecode,
            "mac_addr": self.mac_address,
            "account_content": self._account,
            "password": urllib.parse.unquote(self._password),
            "validateCode": self.vcode
        }
        logger.debug('login_params is: %s' % login_params)

        r = self._session.post(
            'https://jy.yongjinbao.com.cn/winner_gj/gjzq/exchange.action',
            params=login_params)
        r.raise_for_status()

        logger.debug('Login respone: %s' % r.text)

        returnJson = r.json()['returnJson']
        data = demjson.decode(returnJson)
        error_msg = dict()
        if data['msg_no'] != '0':
            if 'msg_info' in data.keys() and data['msg_info'] != '':
                error_msg['error_info'] = data['msg_info']
            else:
                error_msg = data[data['error_grids']][1]

            if error_msg['error_info'].find('验证码') != -1:
                logger.warning('vcode error : %s' % error_msg['error_info'])
                raise VerifyCodeError(error_msg['error_info'])
            else:
                logger.error('login Failed :%s' % error_msg['error_info'])
                raise LoginFailedError(error_msg['error_info'])

        return

    def request(self, method, url, **kwargs):

        # 加入token
        params = {
            'CSRF_Token': 'undefined',
            'timestamp': random.random()
        }
        params.update(
            # 弹出kwargs中的params
            kwargs.pop('params', {})
        )

        r = self.session.request(
            method=method,
            url=url,
            params=params,
            **kwargs
        )
        r.raise_for_status()

        return r


@TraderFactory('yjb', '佣金宝', '国金证券')
class yjbTrader(WebTrader):
    def __init__(self, account, password, bank_password=None, fund_password=None):

        super(yjbTrader, self).__init__(account=account, password=password, pool_size=5)

        self.bank_password = bank_password
        self.fund_password = fund_password
        self._exchange_stock_account = None
        self.client = yjbLoginSession(account=account, password=password)

    def _trade_api(self, **kwargs):
        '''
        底层交易接口
        '''

        logger.debug('call params: %s' % kwargs)
        r = self.client.get(url='https://jy.yongjinbao.com.cn/winner_gj/gjzq/stock/exchange.action',
                            params=kwargs)
        logger.debug('return: %s' % r.text)

        # 解析返回的结果数据
        returnJson = r.json()['returnJson']
        if returnJson is None:
            return None

        data = demjson.decode(returnJson)
        if data['msg_no'] != '0':
            error_msg = data[data['error_grids']][1]
            logger.error(
                'error no: %s,error info: %s' % (error_msg.get('error_no', ''), error_msg.get('error_info', '')))
            raise TraderAPIError(error_msg.get('error_info', ''))

        data = data['Func%s' % data['function_id']]
        df = pd.DataFrame(data[1:])

        # 替换表头的命名
        df.rename(columns=RENAME_DICT, inplace=True)
        # 生成symbol
        if 'symbol' in df.columns:
            df['symbol'] = df['symbol'].apply(code_to_symbols)
        # FLOAT_COLUMNS和 df.columns取交集，以减少调用时间
        cols = list(set(FLOAT_COLUMNS).intersection(set(df.columns)))

        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='ignore')

        return df

    @property
    def exchange_stock_account(self):
        if self._exchange_stock_account is None:
            ex_account = self._trade_api(service_type='stock', function_id='407')
            self._exchange_stock_account = dict(ex_account[['exchange_type', 'stock_account']].values)
            logger.info('exchange_stock_account is: %s' % self.exchange_stock_account)

        return self._exchange_stock_account

    @property
    def portfolio(self):

        logger.debug('call mystock_403 and mystock_405')
        p = self._worker.apply_async(self._trade_api, kwds={'request_id': 'mystock_403'})
        b = self._worker.apply_async(self._trade_api, kwds={'request_id': 'mystock_405'})
        p = p.get().copy()
        p.set_index('symbol', inplace=True)
        p = p[['symbol_name', 'current_amount', 'enable_amount', 'lasttrade', 'market_value']]

        b = b.get().copy()
        money_type = b['money_type'].iloc[0]
        current_amount = b['enable_balance'].iloc[0]

        p.loc['cash', 'symbol_name'] = money_type
        p.loc['cash', 'current_amount'] = current_amount
        p.loc['cash', 'enable_amount'] = current_amount
        p.loc['cash', 'lasttrade'] = 1.0
        p.loc['cash', 'market_value'] = current_amount

        p['weight'] = p['market_value'] / b['asset_balance'].iloc[0]
        p['weight'] = p['weight'].round(4)
        p = p.dropna(axis=0)

        return p

    def buy(self, symbol, price, amount=0, volume=0):

        symbol = symbol.lower()
        # 上海：1 ； 深圳：2
        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        if amount == 0:
            amount = volume // price // 100 * 100

        params = {
            "service_type": "stock",
            'entrust_bs': 1,  # 1:买入 ; 2:卖出
            'entrust_amount': amount,
            'elig_riskmatch_flag': 1,
            'stock_code': symbol[2:],
            'stock_account': self.exchange_stock_account[exchange_type],
            'exchange_type': exchange_type,
            'entrust_prop': 0,
            'entrust_price': price,
            'request_id': 'buystock_302'
        }

        df = self._trade_api(**params)
        return df['order_no'].iloc[0]

    def sell(self, symbol, price, amount=0, volume=0):

        symbol = symbol.lower()
        # 上海：1 ； 深圳：2
        exchange_type = '1' if symbol[:2] == 'sh' else '2'

        if amount == 0:
            amount = volume // price // 100 * 100

        params = {
            "service_type": "stock",
            'entrust_bs': 2,  # 1:买入 ; 2:卖出
            'entrust_amount': amount,
            'elig_riskmatch_flag': 1,
            'stock_code': symbol[2:],
            'stock_account': self.exchange_stock_account[exchange_type],
            'exchange_type': exchange_type,
            'entrust_prop': 0,
            'entrust_price': price,
            'request_id': 'sellstock_302'
        }

        df = self._trade_api(**params)
        return df['order_no'].iloc[0]

    def ipo_subscribe(self, symbol):
        df = self._trade_api(request_id='buystock_301', stock_code=symbol[2:])
        return df['order_no'].iloc[0]

    @property
    def orderlist(self):
        orderlist = self._trade_api(
            request_id='trust_401',
            sort_direction=1,
            deliver_type='',
            service_type='stock'
        )
        orderlist.set_index('order_no', inplace=True)
        orderlist = orderlist[['symbol', 'symbol_name', 'trade_side', 'order_price', \
                               'order_amount', 'business_price', 'business_amount', 'order_status', 'order_time']]
        orderlist = orderlist.dropna(axis=0)
        # TODO order_time is wrong
        # 日期格式为： [%H%M%S] 例如：23:15:30 ——> 231530
        # 调整日期格式
        orderlist['order_time'] = orderlist['order_time'].apply(to_time)
        return orderlist

    def cancel(self, order_no):

        df = self._trade_api(
            request_id='chedan_304',
            entrust_no=order_no
        )

        return df['order_no'].iloc[0]

    def subscription(self, symbol, volume):

        symbol = symbol.lower()
        df = self._trade_api(
            function_id='7413',
            fund_code=symbol[2:],
            service_type='stock',
            fund_company='',
            sort_direction=15
        )
        fund_company = df.loc[df.fund_code == symbol[2:], 'fund_company'].values[0]

        # 检查一下客户信息是否正确
        self._trade_api(function_id='415', service_type='stock')

        df = self._trade_api(
            balance=volume,
            fund_code=symbol[2:],
            fund_company=fund_company,
            request_id='fund_perchase_7402',
            service_type='stock'
        )

        return df

    def trans_in(self, cash_in, bank_no=None):

        if self.bank_password is None:
            return 0

        # 查询第三方存管信息
        self._trade_api(function_id='452', service_type='stock')

        df = self._trade_api(
            request_id='zhuanzhang2_500',
            bank_no=bank_no,
            transfer_direction=1,  # 1 转入证券账户，2 转入银行
            money_type=0,
            bank_password=self.bank_password,
            fund_password='',
            loginPasswordType='RSA',
            occur_balance=cash_in,
            random_number=''
        )

        return df

    def trans_out(self, cash_out, bank_no=None):
        if self.fund_password is None:
            return 0

        # 查询第三方存管信息
        df = self._trade_api(
            function_id=452,
            service_type='stock',
        )

        df = self._trade_api(
            request_id='zhuanzhang2_500',
            bank_no=bank_no,
            transfer_direction=2,  # 1 转入证券账户，2 转入银行
            money_type=0,
            bank_password='',
            fund_password=self.fund_password,
            loginPasswordType='RSA',
            occur_balance=cash_out,
            random_number=''
        )

        return df
