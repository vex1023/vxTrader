# encoding=utf-8
'''
各种各样的LOGGER 函数
'''

import logging
import sys
from datetime import datetime

import six

'''
彩色的LOGGER
'''

try:
    import curses

    assert curses
except ImportError:
    curses = None

_DEFAULT_LOG_FORMAT = '%(asctime)s %(levelname)s %(filename)s [line:%(lineno)d] === %(message)s'


class _LogFormatter(logging.Formatter):
    def __init__(self, color, log_format=None, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)

        if log_format:
            self._log_format = log_format
        else:
            self._log_format = _DEFAULT_LOG_FORMAT

        self._color = color
        if color:
            fg_color = (curses.tigetstr("setaf") or
                        curses.tigetstr("setf") or "")
            if (3, 0) < sys.version_info < (3, 2, 3):
                fg_color = six.text_type(fg_color, "ascii")
            self._colors = {
                logging.DEBUG: six.text_type(curses.tparm(fg_color, 4),
                                             "ascii"),  # Blue
                logging.INFO: six.text_type(curses.tparm(fg_color, 2),
                                            "ascii"),  # Green
                logging.WARNING: six.text_type(curses.tparm(fg_color, 3),
                                               "ascii"),  # Yellow
                logging.ERROR: six.text_type(curses.tparm(fg_color, 5),
                                             "ascii"),  # MAGENTA
                logging.CRITICAL: six.text_type(curses.tparm(fg_color, 1),
                                                "ascii"),  # Red

            }
            self._normal = six.text_type(curses.tigetstr("sgr0"), "ascii")

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)

        record.asctime = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")

        formatted = self._log_format % record.__dict__

        if self._color:
            formatted = (self._colors.get(record.levelno, self._normal) +
                         formatted + self._normal)

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + record.exc_text
        return formatted.replace("\n", "\n    ")


'''
企业微信号，LOG HANDLER
'''


class qyWeChatLoggerHandler(logging.Handler):
    def __init__(self, corpid, appsecret, target={}, agentid=0):
        from wechatpy.enterprise.client import WeChatClient as qyWechatClient
        self._client = qyWechatClient(corp_id=corpid, secret=appsecret)
        self._agent_id = agentid
        self._user_ids = target.get('user_ids', '@all')
        self._tag_ids = target.get('tag_ids', '')
        self._party_ids = target.get('party_ids', '')
        super(qyWeChatLoggerHandler, self).__init__()
        return

    def emit(self, record):
        msg = self.format(record)

        try:
            self._client.message.send_articles(agent_id=self._agent_id,
                                               user_ids=self._user_ids,
                                               articles=msg,
                                               party_ids=self._party_ids,
                                               tag_ids=self._tag_ids)
            pass
        except Exception as err:
            print(err)
        return

    def format(self, record):
        record.asctime = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")

        return [{
            'title': '[%(levelname)s]' % record.__dict__,
            'description': '%(asctime)s %(filename)s %(lineno)d:\n%(msg)s' % record.__dict__,
            'url': '',
            'image': ''
        }]


def add_console_logger(logger, level='info'):
    """
    增加console作为日志输入.
    """
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        # Set up color if we are in a tty and curses is installed
        color = False
        if curses and sys.stderr.isatty():
            try:
                curses.setupterm()
                if curses.tigetnum("colors") > 0:
                    color = True
            except:
                pass
        console = logging.StreamHandler()
        console.setFormatter(_LogFormatter(color=color))
        logger.addHandler(console)


def add_qyWechat_logger(logger, level, corpid, appsecret, agentid, target={}):
    qyhandler = qyWeChatLoggerHandler(corpid, appsecret, target, agentid)
    qyhandler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(qyhandler)
    return logger
