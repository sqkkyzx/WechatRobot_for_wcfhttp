# Wechat Robot For wcfhttp


基于 wcfhttp 的机器人示例。该项目仅作为示例，项目中，未对大量可能发生的错误做处理。
集成了以下功能：
- 消息推送队列：设置固定或随机的消息发送间隔时间
- 相对完善的触发规则：黑名单、白名单、正则、是否被@
- 三种触发结果：发送固定文本、执行函数、通过GPT智能选择执行函数

> **⚠** 项目正在开发中，部分模块未经测试，可能有重大 BUG

###
## 参考
- [WeChatFerry](https://github.com/lich0821/WeChatFerry)
- [WeChatRobot](https://github.com/lich0821/WeChatRobot)


###
## 启动
该程序与 `wcfhttp` 通信，用于处理 `wcfhttp` 的 callback ，不能独立运行。旨在可以将本项目部署在任意 linux 服务器、docker 上，与运行 Wechat 的 PC 分离。

1、先在 PC 启动 `wcfhttp` ，参数中携带本项目运行的 ip 和端口, 默认端口是 9998

```commandline
下载 wcfhttp
python -m pip install wcfhttp

运行 wcfhttp
wcfhttp -cb http://127.0.0.1:9998/
```

2、拉取本项目，安装依赖，在 `config.json` 中配置 `wcfhttpURL` 为 `wcfhttp` 运行的 ip 和端口地址。


```commandline
安装必要依赖
python -m pip install -r requirements.txt

启动
python main.py
```
###
## 配置文件

```python
{
  # wcfhttp 的地址，用于发送消息。结尾必须以 / 结束
  "wcfhttpUrl": "http://127.0.0.1:9999/", 
  
  # 参考后文: 使用队列
  "queueTimer": 5,
  "queueTimerRandom": [1,5],
  
  # GPT 的上下文超时时间，单位秒。超过此时间后，将会删除数据库中存储的上下文。
  "histroyTimeout": 360000,
  
  # GPT 的 apikey
  "openaiKey": "",
}
```

###
## 实现自己的回复逻辑


### 1. 编辑触发逻辑


在 `tigger.json` 中，可以编写自己的触发逻辑。

```python
# 一个触发逻辑的列表， 黑名单、白名单、消息正则、是否被@ 四个条件均满足时，才会触发执行。
# 将从上到下依次遍历列表的每一项进行匹配。
# 匹配成功后，如果 reply 不为空，将立即推送一条文本消息回复
# 如果 func_name 不为空，将执行名为 func_name 的函数，并传入消息作为参数。

[
  {
    # 黑名单：
    # 将 roomid 写入后，任何命中黑名单的 roomid 都不会触发自动回复。roomid 可以以任意分隔符写入    
    "blacklist": "xx1xx@chatrooom/xx2xx@chatrooom|xx3xx@chatrooom",
    
    # 白名单：
    # 留空时，将会所有人都可以触发
    # 不为空时，只有在白名单内的 roomid 才会触发。roomid 可以以任意分隔符写入    
    "whitelist": "xx0xx@chatrooom",
    
    # 正则表达式:
    # 填写正则表达式，消息文本 content 匹配正则时，才会触发。可以匹配多行
    # 可以使用 .* 匹配包括空值的任意字符串    
    "pattern": ".+",
    
    # 是否需要被@:
    # 留空时视为 False, 填写任意值均被视为 True。当为 True 时，只有被@以后才能触发    
    "need_at": "",    
    
    # 需要回复的文本消息    
    "reply": "",
    
    # 需要执行的函数名，仅函数名称，无需参数和括弧    
    "func_name": ""
  }
]
```


### 2. 添加函数

- 示例：添加一个函数，回复自己发送的内容。


在 `function` 模块文件夹中，添加 `repeater.py` 文件
```python
# 引入内置的队列模块
from sendqueue import QueueDB

# 函数参数必须为 record ，用于接受消息对象实例，需要以 async 模式定义函数
async def repeater(record):
    
    # 函数不处理返回，可以使用 http 请求 或 内置的队列 来发送回复。
    with QueueDB() as mq:
        mq.send_text(record.content, record.roomid)
        
    return 
```
然后需要在 `function/__init__.py` 中引入函数。
```python
# 在开头引入函数
from repeater.py import repeater
```

现在，你在 `tigger.json` 中，`func_name` 字段填写的 `repeater` 函数就可以被正确执行了。


###
## 使用内置队列
队列读取 `config.json` 中的 `queueTimer` 字段作为固定间隔秒数，`queueTimerRandom` 字段作为随机增加的时间间隔。可以将 `queueTimerRandom` 设置为 `[0, 0]` 以使用固定的时间。

```python
from sendqueue import QueueDB

# 内置队列使用上下文进行数据库连接的管理，提供以下方法供调用
with QueueDB() as mq:
    mq.send_text()  # 发送文本
    mq.send_xml()  # 发送XML
    mq.send_image()  # 发送图片
    mq.send_file()  # 发送文件
    mq.send_emotion()  # 发送动态表情
    mq.send_webview()   # 发送网页链接
    mq.send_refer()     # 发送引用消息
```


###
## gpt-3.5-turbo-0613 自动选择函数

> **⚠** 使用 AUTO 模式需要能够请求 gpt-3.5-turbo-0613 的 apikey

### 1. 如何启用

- 设置 `tigger.json` 的 `func_name` 设置为 `auto`

- 在 `config.json` 中设置你的 `openaiKey`

- 已内置一个 `nowtime` 和一个 `weather` 函数，可自行查看其实现。


### 2. 编写自己的函数逻辑

以 `weather` 为例。添加一个新的文件 `function/weather.py`

```python
import requests
import time

# 需要根据你传入其他需要通过 gpt 解析得到的参数，如 city。
# record 参数是必须的，无论是否使用。
async def auto_weather(city: str, record):
    try:
        # 进行一个 API 请求
        res = requests.get(
            url=f"https://api.seniverse.com/v3/weather/daily.json?key=SCYrvkytJze9qyzOh&location={city}"
        ).json().get("results")[0].get("daily")
        
        # 对请求结果做出修改。
        res[0]["date"] = "今天 " + time.strftime('%Y-%m-%d', time.localtime())
        res[1]["date"] = "明天 " + time.strftime('%Y-%m-%d', time.localtime(time.time()+86400))
        res[2]["date"] = "后天 " + time.strftime('%Y-%m-%d', time.localtime(time.time()+172800))
        
        # 需要一个返回值，以便于 gpt 根据返回值进行处理，最终生成自然语言的回复。
        # 返回值必须是 dict 类型（包含字典的 list 也可以）或 str 类型，其他类
        # 型的返回未进行处理，如若需要，请自行修改 __init__.py 的 70-71行
        return res
    
    except Exception as e:
        # 或者返回错误的结尾 80 个字符，让 gpt 识别有哪些错误，并回复用户。
        # 常见用例是识别参数缺失。gpt 可以识别有哪些缺少的参数，并在回复内容中要求用户提供。
        return '...' + e.__str__()[-80:]
    
    # 注意：
    # 可以使用 retrun None 或者 return 0 返回空值，则 gpt 不会对结果进行再次对话。
```

### 3. 引入自己的函数
在 `function/auto_factory.py` 引入函数。 

```python
# 在引入函数时，建议使用 `as` 重命名函数名称，说明函数具体的功能，并符合良好的蛇形或驼峰命名规则。
# 一个精准、明确的函数名，有利于 gpt 更准确的识别函数功能。

from function.weather import auto_weather as query_weacher
```

### 4. 给GPT备选函数列表新增可用项

编辑 `function/auto_factory.py` 的 `functions` 变量。该变量是提供给 gpt 的可用函数列表。

```python
# 应该是一个列表
functions = [    
  {
    "name": "query_weather",    # 定义函数名，需要与引入的函数名相同
    "description": "Query weather.",    # 描述函数功能
    "parameters": {
      "type": "object",
      "properties": {
        "city": {   # 定义参数名，参数名与函数同样要求以蛇形或驼峰命名，gpt 才能更精准识别。
          "type": "string",     # 设置参数的类型，可以是类型的列表，常用有 string, null, boolean, array, number
          "description": "Witch city wants to search."      # 描述参数。
          # "enum": ["北京", "上海" ...]    # 枚举值，gpt 会尽可能匹配。但若输入文本识别不到枚举的内容，也可能输入其他值。
        }
      },
      "required": []   # 可以留空，看起来填写的内容对结果并无影响。
    }
  }
]
```
