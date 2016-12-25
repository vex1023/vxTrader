# vxTrader

## vxTrader

一个标准化，统一封装的A股券商web 交易接口。

### 安装方法

1. 安装tesseract-ocr 程序，用于校验码识别
```
apt-get install tesseract-ocr
```

2. 安装依赖库
```
pip3 install -r requirements.txt
```
3. 安装vxTrader

```
pip3 install vxTrader
```

### 使用方法

```python
from vxTrader import Trader
trader = Trader(
    brokerID='gf',
    account='加密后广发账号',
    password='加密后的密码'
)

print(trader.portfolio)

print(trader.orderlist)

```

### 支持券商

* 广发证券————(__'gf'__)  
* 雪球组合管理———(__'xq'__)
   
* 国金证券（佣金宝)———(__'yjb'__)   11月30日以后，佣金宝不再提供web交易接口

### 主要接口介绍

#### hq——实时行情接口（level 1）

支持单只股票实时行情查询

```python
df = trader.hq('sz150023')
```
或者是 多只股票实时行情查询
```python
df = trader.hq(['sz150023','sz150022'])
```
返回一个pandas.DataFrame格式的数据
* index

```
symbol : 被查询的股票
```

* columns

```python
[
    "name", "open", "yclose", "lasttrade", "high", "low", "bid", "ask",
    "volume", "amount", "bid1_m", "bid1_p", "bid2_m", "bid2_p", "bid3_m",
    "bid3_p", "bid4_m", "bid4_p", "bid5_m", "bid5_p", "ask1_m", "ask1_p",
    "ask2_m", "ask2_p", "ask3_m", "ask3_p", "ask4_m", "ask4_p", "ask5_m",
    "ask5_p", "date", "time", "status"
]
```

#### portfolio——查询当前的持仓状况

```python
trader.portfolio
```

返回pandas.DataFrame格式的数据
* index 

```
symbol : 持仓股票,'cash' 标识现金持有情况
```

* columns:

```
symbol_name : 股票名称

current_amount : 当前持有股数

enable_amount : 当前可卖股数

lasttrade : 最近成交价格

market_value : 证券市值

weight : 持仓权重（精确到小数点后4为)

```

#### orderlist ——委托订单查询（当日）

```python
trader.orderlist
```
返回pandas.DataFrame格式的数据

* index 

```
order_no : 订单号
```
* columns

```
symbol : 交易证券代码

symbol_name : 交易证券名称

trade_side : 交易方向， '买入' 或 '卖出'

order_price : 下单价格

order_amount : 下单数量

business_price : 已成交平均成交价格

business_amount : 已成交的数量

order_status : 订单状态: 如'已报','未报','部成','部撤','已撤','已成'

order_time : 下单时间
```

### 基本委托下单指令

* ___buy___   —— 股票/ETF/LOF买入
* ___sell___  —— 股票/ETF/LOF卖出
* ___subscription___ —— 场内基金/分级基金申购
* ___redemption___ —— 场内基金/分级基金赎回
* ___split___ —— 分级基金拆分
* ___merge___ —— 分级基金合并
* ___cancel___ —— 撤单
* ___ipo_subscribe___ —— 新股申购交易
* ___trans_in___ —— 银证转账转入证券账户
* ___trans_out___ —— 银证转账转出证券账户
* ___ipo_list___ —— ipo申购股票情况
* ___ipo_limits___ —— ipo申购额度查询

### 组合委托下单指令

组合下单时，程序会每隔5秒对成交情况进行监控，并持续10次；

如果不成交，将进行撤单并且按照最新的价格进行下单，以确保最快速的达成交易;

下单指令返回后，这个交易指令下达的所有未成交的订单都会被 __撤销__ 。

* ___order___ —— 基本组合下单交易
```
trader.order('sh511880',amount=500)

trader.order('sh511880',volume=50000)

trader.order('sh511880',weight=0.2)

```
* ___order_target___ —— 按照目标持股数量、持股市值、持股比例下单
```
trader.order_target('sh511880', target_amount=500)

trader.order_target('sh511880', target_volume=50000)

trader.order_target('sh511880', target_weight=0.2)

```
* ___order_auto_ipo___ —— 自动IPO申购
```
trader.order_auto_ipo()
```
* ___order_transfer_to___ —— 调仓操作
```
trader.order_transfer_to(source_symbol='sh511880', target_symbol='sh511010', transfer_amount=100)
```

* ___order_cashout___ -- 套现交易
```python
trader.order_cashout(['sh511880','sh511010'], 30000)
```



## 版本信息

参见ChangeLog.md