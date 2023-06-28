import asyncio
import json
import logging
import random
import re
import os
import shutil

import uvicorn
from fastapi import FastAPI, Request

import function
from message import Record
from sendqueue import QueueDB


def check_config():
    current_dir = os.getcwd()
    config_file = "config.json"
    example_file = "config.example"

    # 检查是否存在 config.json 文件
    if not os.path.isfile(os.path.join(current_dir, config_file)):
        shutil.copy(os.path.join(current_dir, example_file), os.path.join(current_dir, config_file))

    with open('config.json', 'r', encoding='utf-8') as f:
        conf = json.load(f)

    return conf


# 调用函数检测并复制配置文件
config = check_config()
wcf, timer, random_timer = config['wcfhttpUrl'], config['queueTimer'], tuple(config['queueTimerRandom'])

app = FastAPI()


if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=9998, reload=True)


# 消费队列中的消息。
async def consume_queue_timer():
    while True:
        with QueueDB() as q:
            q.__consume__()
        await asyncio.sleep(timer + random.randint(*random_timer))


# 每 3秒 + 随机 1-3 秒消费一次队列中的消息。
async def clean_histroy():
    while True:
        with QueueDB() as q:
            q.__consume__()
        await asyncio.sleep(timer + random.randint(*random_timer))


# 启动时开始消费队列
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_queue_timer())


@app.post("/")
async def root(request: Request):
    body = await request.json()
    record = Record(body)
    print(record.__dict__)

    # 消息类型：
    # 1-文本 3-图片 34-语音 42-个人或公众号名片 42-企业微信名片 43-视频 47-动画表情 48-定位 10000-系统提示
    # 49-应用 4957-引用 493-音乐 495-网页链接 496-文件 4916-卡券 4919-聊天记录 4933-小程序 492000-转账

    # 自动回复匹配
    reply, funcname = tigger(record.roomid, record.content, record.is_at)

    # 如果匹配到 reply 则自动回复
    if reply:
        with QueueDB() as mq:
            aters = record.sender if record.is_group else ''
            mq.send_text(reply, record.roomid, aters)

    # 如果匹配到 function 则执行函数
    if funcname:
        func = getattr(function, funcname, None)

        if func:
            print(f"DO FUNC: {funcname}")
            asyncio.create_task(func(record))
        else:
            logging.error('无法执行未配置的函数。')


# 匹配消息
def tigger(roomid, content, is_at):
    with open('tigger.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 对每一条记录，检查它是否符合条件
    for record in data:
        # 如果需要at自己，但是没有at，则跳过
        if record['need_at'] and not is_at:
            continue
        # 如果命中黑名单，则跳过
        if roomid in record['blacklist']:
            continue
        # 如果白名单不为空，并且没有命中白名单，则跳过
        if record['whitelist'] and roomid not in record['whitelist']:
            continue
        # 如果不符合正则匹配，则跳过
        if not re.search(record['pattern'], content, re.DOTALL):
            continue

        # 如果所有的条件都满足，返回记录
        return record['reply'], record['func_name']

    # 如果没有找到符合条件的记录，返回None
    return None, None
