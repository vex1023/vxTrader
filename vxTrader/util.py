# encoding = utf-8
'''
各类工具箱函数
'''
import time
from functools import wraps
from vxTrader import logger


def retry(tries, CatchExceptions=(Exception,), delay=0.01, backoff=2):
    '''
    错误重试的修饰器
    :param tries: 重试次数
    :param CatchExceptions: 需要重试的exception列表
    :param delay: 重试前等待
    :param backoff: 重试n次后，需要等待delay * n * backoff
    :return:
    '''
    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")

    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mdelay = delay
            retException = None
            for mtries in range(tries):
                try:
                    return f(*args, **kwargs)
                except CatchExceptions as ex:
                    logger.warning(
                        "function %s(%s, %s) try %d times error: %s\n" % (f.__name__, args, kwargs, mtries, str(ex)))
                    logger.warning("Retrying in %.4f seconds..." % (mdelay))

                    retException = ex
                    time.sleep(mdelay)
                    mdelay *= backoff
            raise retException

        return f_retry

    return deco_retry


def code_to_symbols(code):
    """判断股票ID对应的证券市场
     匹配规则
     ['50', '51', '60', '90', '110'] 为 sh
     ['00', '13', '18', '15', '16', '18', '20', '30', '39', '115'] 为 sz
     ['5', '6', '9'] 开头的为 sh， 其余为 sz
     :param stock_code:股票ID, 若以 'sz', 'sh' 开头直接返回对应类型，否则使用内置规则判断
     :return 'sh' or 'sz'"""
    code = str(code)
    if code is '':
        return

    if code.startswith(('sh', 'sz')):
        return code
    if code.startswith(('50', '51', '60', '73', '90', '110', '113', '132', '204')):
        return 'sh' + code
    if code.startswith(('00', '13', '18', '15', '16', '18', '20', '30', '39', '115', '1318')):
        return 'sz' + code
    if code.startswith(('5', '6', '9')):
        return 'sh' + code
    return 'sz' + code
