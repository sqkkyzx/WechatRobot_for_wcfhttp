import time
from sendqueue import QueueDB


async def nowtime(record: any):
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    with QueueDB() as mq:
        mq.send_text(now, record.roomid)
    return now
