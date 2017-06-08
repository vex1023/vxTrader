# 版本信息

## v0.1.11

1.修复bug#4 自动申购错误

## v0.1.10

1. 修复bug#3

## v0.1.9

1. 停用了order_target_amount, order_target_volume, order_target_weight接口，用order_target替代
2. 修订了雪球组合下单的问题
3. 修订了order_auto_ipo 的返回值，返回{ order_no, symbol, trade_side, amount, price}
4. 调整了order_transfer_to的入口参数，增加transfer_amount, transfer_volume, transfer_weight参数

## v0.1.8

1. 增加order_transfer_to接口用户调仓下单；
2. 修订了说明文档的一些一楼

## v0.1.7

1. 调整了broker的结构
2. 增加Trader类
3. 增加分单下单，order_auto_ipo接口
4. 更新了文档

## v0.1.6

1. 修复广发证券现金current_amount 取值错误
2. 增加loginsession 的reset方法，用于重置一下session

## v0.1.5

1. 佣金宝11月30日开始不再提供web接口。
2. 广发证券新增ipo_limits 和ipo_lists接口。
3. 修复广发证券portfolio 的并行缺陷。

## v0.1.4

1. 广发证券——场内基金申购，场内基金赎回，分级基金合并接口，分级基金拆分接口
2. 国金证券(佣金宝)——场内基金申购，场内基金赎回
3. 增加load_traders 的函数，通过配置文件生成traders


## v0.1.3

1. 修改了LogSession的实现方式；
2. 修复了广发证券sell的下单参数缺陷；



## v0.1.2

创建第一个版本号 实现功能： 

1. 广发证券 
2. 国金证券(佣金宝) 
3. 雪球组合
