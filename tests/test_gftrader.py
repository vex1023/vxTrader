import unittest
from vxTrader import TraderFactory, logger
import os


class gfTraderTestCase(unittest.TestCase):
    def setUp(self):
        account = os.getenv('account', '')
        password = os.getenv('password', '')
        kwargs = os.getenv('kwargs', '')

        if account == '' or password == '':
            raise EnvironmentError('enviroment value account(%s) or password(%s) is not set' % (account, password))

        self.trader = TraderFactory.create('gf', account, password)

    def test_gfLoginSession(self):
        print(self.trader.portfolio)


if __name__ == '__main__':
    unittest.main()
