import os
import unittest

from vxTrader import create_trader


class gfTraderTestCase(unittest.TestCase):
    def setUp(self):
        brokerid = os.getenv('brokerid', '')
        account = os.getenv('account', '')
        password = os.getenv('password', '')
        kwargs = os.getenv('kwargs', '')

        if brokerid == '' or account == '' or password == '':
            raise EnvironmentError('enviroment value account(%s) or password(%s) is not set' % (account, password))

        self.trader = create_trader(brokerid, account, password)

    def test_gfLoginSession(self):
        print(self.trader.portfolio)
        print(self.trader.orderlist)
        print(self.trader.exchange_stock_account)
        print(self.trader.order('sz150023', 100))


if __name__ == '__main__':
    unittest.main()
