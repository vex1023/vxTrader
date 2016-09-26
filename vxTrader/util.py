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
            mtries, mdelay = 0, delay
            retException = None
            # while mtries < tries:
            for mtries in range(tries):
                try:
                    return f(*args, **kwargs)
                except CatchExceptions as ex:
                    msg = "function %s(%s, %s) try %d times error: %s\n" % (f.__name__, args, kwargs, mtries, str(ex))
                    msg = msg + "Retrying in %.4f seconds..." % (mdelay)
                    retException = ex
                    logger.warning(msg)
                    time.sleep(mdelay)
                    mdelay *= backoff
            raise retException

        return f_retry

    return deco_retry
