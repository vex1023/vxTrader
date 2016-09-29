import unittest
from vxTrader import TraderFactory, logger
import os


class yjbTraderTestCase(unittest.TestCase):
    def setUp(self):
        brokerid = os.getenv('brokerid', '')
        account = os.getenv('account', '')
        password = os.getenv('password', '')
        kwargs = os.getenv('kwargs', '')

        if brokerid == '' or account == '' or password == '':
            raise EnvironmentError('enviroment value account(%s) or password(%s) is not set' % (account, password))

        self.trader = TraderFactory.create(brokerid, account, password)

    def test_yjbLoginSession(self):
        print(self.trader.portfolio)
        print(self.trader.orderlist)
        print(self.trader.exchange_stock_account)


if __name__ == '__main__':
    unittest.main()
