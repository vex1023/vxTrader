# encoding = utf-8
'''
各类工具箱函数
'''


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


def to_time(exchange_time):
    '''
    格式化交易所返回的交易时间
    :param yjb_time:
    :return:
    '''
    exchange_time = '{:0>6}'.format(exchange_time)
    return '%s:%s:%s' % (exchange_time[:2], exchange_time[2:4], exchange_time[4:6])
