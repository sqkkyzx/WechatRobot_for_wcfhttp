# README:
# 在此文件夹内编写业务函数，并且需要在 __init__.py 内引入函数。
# 业务函数需要回复的内容 ，需要自行调用队列进行推送，示例：
#
# from sendqueue import QueueDB
# with QueueDB() as mq:
#   mq.send_text(..., ...)
#
# 或者使用 requests 模块直接请求 wcfhttp
#
import json
import logging
import sqlite3
import time

import openai

from function.nowtime import nowtime
from function import auto_factory


# 执行自动任务
# 自动函数可以执行的列表需要在 auto_factory 中编辑 functions
# 自动函数执行的 function 需要在 auto_factory 中导入
# 编写的用于自动执行的函数，变量必须携带 record，即使不使用。

def auto(record):
    with open('config.json') as f:
        conf = json.load(f)

    openai.api_key = conf["openaiKey"]
    # 1. 从数据库中读取聊天记录并限制长度
    with HistoryDB() as db:
        history = db.select(record)

    while len(str(history)) > 2000:
        history.pop(0)

    # 2. 使用聊天记录构建提示词
    messages: list = history + [{"role": "user", "content": record.content}]

    # 3. 读取可供执行的任务列表
    functions = auto_factory.functions

    # 4. 让 GPT 判断任务。
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        functions=functions,
        function_call="auto"
    )["choices"][0]["message"]

    # 5-1. 检查GPT是否要调用函数
    if response.get("function_call"):

        # 6-1.1 获取函数，构建参数。
        func_name = response["function_call"]["name"]
        func_args = json.loads(response["function_call"]["arguments"])
        func_args["record"] = record

        # 6-1.2 执行函数获取返回值。
        try:
            func_call = getattr(auto_factory, func_name)
            print(f"{func_call} + {func_args}")
            func_response = func_call(**func_args)
            func_response = json.dumps(func_response, ensure_ascii=False) \
                if isinstance(func_response, (dict, list)) else func_response
        except Exception as e:
            func_response = str(e).split("\n")[-1]
            func_response = f"错误信息：{func_response}。如果你觉得没有问题，请重新提交一次试试看吧！"

        # 6-1.3 如果有返回，则通过GPT扩展对话，然后返回自然语言的回复。
        if func_response:
            messages.append(response)
            messages.append({
                "role": "function",
                "name": func_name,
                "content": func_response
            })

            while len(str(messages)) > 3000:
                messages.pop(0)
                if len(messages) == 0:
                    messages.append({
                        "role": "function",
                        "name": func_name,
                        "content": "查到的内容太多，超出了读取长度。"
                    })
                    break

            second_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-0613",
                messages=messages
            )
            reply = second_response.choices[0].message.content

            messages.append(second_response["choices"][0]["message"])
            with HistoryDB() as db:
                db.insert(record, messages)
            return reply
        else:
            messages.append({
                "role": "function",
                "name": func_name,
                "content": "success."
            })
            with HistoryDB() as db:
                db.insert(record, messages)
            return None

    # 6-2. 如果GPT不准备调用函数，则使用聊天模式。
    else:
        try:
            chat_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            reply = chat_response.choices[0].message.content
            messages.append(chat_response["choices"][0]["message"])
            with HistoryDB() as db:
                db.insert(record, messages)
            return reply
        except Exception as e:
            logging.error(e)
            return "程序故障。"


class HistoryDB:
    def __enter__(self, db='database/history.db'):
        self.__conn__ = sqlite3.connect(db)
        self.__cursor__ = self.__conn__.cursor()

        # 先清除超时的聊天记录
        with open('config.json') as f:
            conf = json.load(f)
        self.__clean_history__(conf["histroyTimeout"])

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__conn__.close()

    def __creat_table__(self):
        self.__cursor__.execute('CREATE TABLE history (people TEXT UNIQUE, history TEXT, lasttime INTEGER)')
        self.__conn__.commit()

    def insert(self, record, history: list):
        row = {
            'people': "|".join([record.sender, record.roomid]),
            'history': json.dumps(history, ensure_ascii=False),
            'lasttime': time.time().__int__()
        }
        if self.select(record):
            self.__cursor__.execute(
                '''UPDATE history SET history=:history, lasttime=:lasttime WHERE people=:people''',
                row
            )
        else:
            self.__cursor__.execute(
                "INSERT INTO history (people, history, lasttime) VALUES (:people, :history, :lasttime)",
                row
            )
        self.__conn__.commit()

    def select(self, record):
        people = "|".join([record.sender, record.roomid])
        self.__cursor__.execute("SELECT history FROM history WHERE people=?", (people,))
        result = self.__cursor__.fetchone()
        row = result[0] if result else []
        return row

    def __clean_history__(self, timeout: int):
        t = time.time().__int__() - timeout
        self.__cursor__.execute('DELETE FROM history WHERE lasttime < ?', (t,))
        self.__conn__.commit()

