# vxTrader

## vxTrader

一个标准化，统一封装的A股券商web 交易接口。

### 安装方法

1、安装tesseract-ocr，进行校验码的自动识别；
```
sudo apt-get install tesseract-ocr
sudo apt-get install python3-image
```
2、安装依赖库
```
pip3 install -r requirement.txt
```
3、安装vxTrader
```
pip3 install vxTrader
```

### 使用方法

```python
from vxTrader import TraderFactory
trader = TraderFactory.create(
    brokerID='yjb',
    account='你的佣金宝账号',
    password='加密后的密码'
)

print(trader.portfolio)
print(trader.orderlist)

```

### 支持券商

* Broker ID : __'gf'   广发证券__  
* Broker ID : __'yjb'  国金证券（佣金宝）__
* Broker ID : __'xq'   雪球组合管理__