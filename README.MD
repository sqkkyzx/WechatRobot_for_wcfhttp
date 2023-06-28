# Wechat Robot For wcfhttp

---

基于 wcfhttp 的机器人示例。该项目仅作为示例，项目中，未对大量可能发生的错误做处理。
> **⚠** 项目正在开发中，部分模块未经测试，可能有重大 BUG

## 参考
- [WeChatFerry](https://github.com/lich0821/WeChatFerry)
- [WeChatRobot](https://github.com/lich0821/WeChatRobot)

## 启动

```python
# 升级 pip
python -m pip install -U pip
# 安装必要依赖
python -m pip install pip install -r requirements.txt
# 启动
python main.py
```

## 配置文件

```json
{
  // wcfhttp 的地址，用于发送消息。结尾必须以 / 结束
  "wcfhttpUrl": "http://127.0.0.1:9999/", 
  
  // 参考后文: 使用队列
  "queueTimer": 5,
  "queueTimerRandom": [1,5],
  
  // GPT 的上下文超时时间，单位秒。超过此时间后，将会删除数据库中存储的上下文。
  "histroyTimeout": 360000,
  
  //GPT的 apikey
  "openaiKey": "",
}
```


## 实现自己的回复逻辑

---

### 1. 编辑触发逻辑


在 `tigger.json` 中，可以编写自己的触发逻辑。

```json
// 一个触发逻辑的列表， 黑名单、白名单、消息正则、是否被@ 四个条件均满足时，才会触发执行。
// 将从上到下依次遍历列表的每一项进行匹配。
// 匹配成功后，如果 reply 不为空，将立即推送一条文本消息回复
// 如果 func_name 不为空，将执行名为 func_name 的函数，并传入消息作为参数。

[
  {
    // 黑名单：
    // 将 roomid 写入后，任何命中黑名单的 roomid 都不会触发自动回复。roomid 可以以任意分隔符写入
    
    "blacklist": "xx1xx@chatrooom/xx2xx@chatrooom|xx3xx@chatrooom",
    
    // 白名单：
    // 留空时，将会所有人都可以触发
    // 不为空时，只有在白名单内的 roomid 才会触发。roomid 可以以任意分隔符写入
    
    "whitelist": "xx0xx@chatrooom",
    
    // 正则表达式:
    // 填写正则表达式，消息文本 content 匹配正则时，才会触发。可以匹配多行
    // 可以使用 .* 匹配包括空值的任意字符串
    
    "pattern": ".+",
    
    // 是否需要被@:
    // 留空时视为 False, 填写任意值均被视为 True。当为 True 时，只有被@以后才能触发
    
    "need_at": "",    
    
    // 需要回复的文本消息
    
    "reply": "",
    
    // 需要执行的函数名，仅函数名称，无需参数和括弧
    
    "func_name": ""
  }
]
```

---

### 2. 添加函数

示例：添加一个函数，回复自己发送的内容。

在 `function` 模块文件夹中，添加 `repeater.py` 文件
```python
# 引入内置的队列模块
from sendqueue import QueueDB

# 函数参数必须为 record ，用于接受消息对象实例。
def repeater(record):
    
    # 函数不处理返回，可以使用 http 请求 或 内置的队列 来发送回复。
    with QueueDB() as mq:
        mq.send_text(record.content, record.roomid)
        
    return 
```
然后需要在 `__init__.py` 中引入函数。
```python
# 在开头引入函数
from repeater.py import repeater
```

现在，你在 `tigger.json` 中，`func_name` 字段填写的 `repeater` 函数就可以被正确执行了。

---

## 内置队列的使用
内置队列读取 `config.json` 中的 `queueTimer` 字段作为固定间隔秒数，`queueTimerRandom` 字段作为随机增加的时间间隔。

可以将 `queueTimerRandom` 设置为 `[0, 0]` 以使用固定的时间。

内置队列使用上下文进行数据库连接的管理，提供以下方法:
```python
from sendqueue import QueueDB

with QueueDB() as mq:
    mq.send_text()
    mq.send_text()
    mq.send_image()
    mq.send_file()
    mq.send_image()
```

---

## gpt-3.5-turbo-0613 自动选择函数

> **⚠** 该模块在此项目的实现尚未经过测试



1、`tigger.json` 的 `func_name` 字段设置为 `auto`

2、编辑 `auto_factory.py` ，在顶部引入备选函数。 

```python
from function.repeater import auto_repeater
```
3、定义函数。

与直接触发的函数不同地方在于，除了 `record` 参数，还需要自定义其他需要通过 gpt 解析得到的参数。

同时，需要一个返回值，以便于 gpt 根据返回值进行处理，最终生成自然语言的回复。

请自行参考 `weather.py` 和 `auto_factory.py` 中的实现。
