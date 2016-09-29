# encoding = utf-8

ERROR_TEMPLATE = '''{"error_code": "%s", "error_msg": "%s", "reason": "%s"}'''


class TraderError(Exception):
    '''
    交易错误和代码定义
    '''
    ERROR_CODE = '0'
    ERROR_MSG = 'Success'

    def __init__(self, reason):
        super(TraderError, self).__init__(ERROR_TEMPLATE % (self.ERROR_CODE, self.ERROR_MSG, reason))


class VerifyCodeError(TraderError):
    '''
    校验码错误
    '''
    ERROR_CODE = '10001'
    ERROR_MSG = 'Trader: Wrong Verify Code Error'


class LoginFailedError(TraderError):
    '''
    登录失败
    '''
    ERROR_CODE = '10002'
    ERROR_MSG = 'Trader: Login Failed'


class TraderNetworkError(TraderError):
    '''
    网络连接失败
    '''
    ERROR_CODE = '10004'
    ERROR_MSG = 'Trader: Network Error'


class TraderAPIError(TraderError):
    '''
    接口调用失败
    '''
    ERROR_CODE = '10005'
    ERROR_MSG = 'Trader: Trade API Error'


class NotSupportAPIError(TraderError):
    '''
    接口不支持错误
    '''
    ERROR_CODE = '10006'
    ERROR_MSG = 'Trader: Broker not support API'


class BrokerAttributeError(TraderError):
    '''
    接口参数错误
    '''
    ERROR_CODE = '10007'
    ERROR_MSG = 'Trader: Broker not support API'


class TraderUnkownError(TraderError):
    '''
    未知错误
    '''
    ERROR_CODE = '-1'
    ERROR_MSG = 'Unkown APIException Error.'
