# encoding = utf-8

ERROR_TEMPLATE = '''{"error_code": "%s", "error_msg": "%s", "reason": "%s"}'''


class APIException(Exception):
    ERROR_CODE = '0'
    ERROR_MSG = 'Success'

    def __init__(self, reason):
        super(APIException, self).__init__(ERROR_TEMPLATE % (self.ERROR_CODE, self.ERROR_MSG, reason))


class TraderError(APIException):
    pass


class VerifyCodeError(TraderError):
    ERROR_CODE = '10001'
    ERROR_MSG = 'Trader: Wrong Verify Code Error'


class LoginFailedError(TraderError):
    ERROR_CODE = '10002'
    ERROR_MSG = 'Trader: Login Failed'


class BrokerTimeOutError(TraderError):
    ERROR_CODE = '10003'
    ERROR_MSG = 'Trader: Broker Time Out'


class TraderNetworkError(TraderError):
    ERROR_CODE = '10004'
    ERROR_MSG = 'Trader: Network Error'


class TraderAPIError(TraderError):
    ERROR_CODE = '10005'
    ERROR_MSG = 'Trader: Trade API Error'


class NotSupportAPIError(TraderError):
    ERROR_CODE = '10006'
    ERROR_MSG = 'Trader: Broker not support API'


class BrokerAttributeError(TraderError):
    ERROR_CODE = '10007'
    ERROR_MSG = 'Trader: Broker not support API'


class AuthError(TraderError):
    ERROR_CODE = '10008'
    ERROR_MSG = 'Signature or Token Wrong.'


class APIAttributeError(TraderError):
    ERROR_CODE = '10009'
    ERROR_MSG = 'API Attribute Error.'


class TokenTimeOutError(TraderError):
    ERROR_CODE = '10010'
    ERROR_MSG = 'Token Time Out.'


class NoTokenError(TraderError):
    ERROR_CODE = '10011'
    ERROR_MSG = 'No Token Params.'


class TraderUnkownError(TraderError):
    ERROR_CODE = '-1'
    ERROR_MSG = 'Unkown APIException Error.'
