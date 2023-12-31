import json
import logging
import sqlite3
import time
import requests

with open('config.json', 'r', encoding='utf-8') as conf:
    config = json.load(conf)
    wcf = config['wcfhttpUrl']

try:
    selfwxid = requests.get("http://127.0.0.1:9999/wxid").json()['data']['wxid']
except Exception as e:
    selfwxid = None
    raise Exception("请检查 wcfhttp 是否启动。")


class QueueDB:
    def __enter__(self, db='database/queue.db'):
        self.__conn__ = sqlite3.connect(db)
        self.__cursor__ = self.__conn__.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__conn__.close()

    def __creat_table__(self):
        self.__cursor__.execute('''
            CREATE TABLE queue
            (is_consumed BOOLEAN,
             producer TEXT,
             p_time TEXT,
             consumer TEXT,
             c_time TEXT,
             data TEXT,
             timestamp INTEGER)
        ''')
        self.__conn__.commit()

    def __produce__(self, data: dict, consumer: str, producer: str):
        """
        推送消息到队列。
        :param producer: 推送者，可传入任意自定义的字符串标记
        :param data: post 数据
        :param consumer: api的完整地址 例如 http://127.0.0.1:9999/text
        :return:
        """
        data_string = json.dumps(data, ensure_ascii=False)

        record = {
            'is_consumed': False,
            'producer': producer,
            'p_time': '',
            'consumer': consumer,
            'c_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            'data': data_string,
            'timestamp': time.time().__int__()
        }

        try:
            self.__cursor__.execute('''
                INSERT INTO queue 
                (is_consumed, producer, p_time, consumer, c_time, data, timestamp) 
                VALUES 
                (:is_consumed, :producer, :p_time, :consumer, :c_time, :data, :timestamp)
            ''', record)
            self.__conn__.commit()
        except Exception as e:
            logging.debug(e)
            logging.warning('消息未推送成功。')

    def __consume__(self):
        self.__cursor__.execute('SELECT * FROM queue WHERE is_consumed = 0 ORDER BY timestamp ASC LIMIT 1')
        row = self.__cursor__.fetchone()
        if row:
            requests.post(
                url=row[3],
                json=json.loads(row[5])
            )

            p_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            # 对发送失败的消息不进行重试，直接忽略
            self.__cursor__.execute('''
            UPDATE queue 
            SET is_consumed = TRUE, p_time = ? 
            WHERE timestamp = ?
            ''', (p_time, row[6]))
            self.__conn__.commit()
        return row

    def send_text(self, msg: str, receiver: str, aters: str = "", producer: str = "main"):
        data = {
            "msg": msg,
            "receiver": receiver,
            "aters": aters
        }
        self.__produce__(data, wcf + 'text', producer)

    def send_image(self, path: str, receiver: str, producer: str = "main"):
        data = {
            "path": path,
            "receiver": receiver,
        }
        self.__produce__(data, wcf + 'image', producer)

    def send_file(self, path: str, receiver: str, producer: str = "main"):
        data = {
            "path": path,
            "receiver": receiver,
        }
        self.__produce__(data, wcf + 'file', producer)

    def send_xml(self, xml: str, receiver: str, xmltype: int = 33, path: str = "", producer: str = "main"):
        data = {
            "xml": xml,
            "type": xmltype,
            "path": path,
            "receiver": receiver,
        }
        self.__produce__(data, wcf + 'file', producer)

    def send_emotion(self, path: str, receiver: str, producer: str = "main"):
        data = {
            "path": path,
            "receiver": receiver,
        }
        self.__produce__(data, wcf + 'emotion', producer)

    def send_webview(self, title: str, des: str, url: str, thumburl: str, receiver: str, producer: str = "main"):
        """
        :param title: 卡片标题
        :param des: 卡片简介
        :param url: 卡片URL
        :param thumburl: 卡片缩略图URL
        :param receiver: 接收者
        :param producer: 发送者标识符，可随意填写
        :return:
        """
        data = {
            "receiver": receiver,
            "xml": f'<msg><appmsg><title>{title}</title><des>{des}</des><type>5</type><url>{url}</url>'
                   f'<thumburl>{thumburl}</thumburl></appmsg><fromusername>{selfwxid}</fromusername></msg>'
        }
        self.__produce__(data, wcf + 'xml', producer)

    def send_refer(
            self, msg: str, refer_content: str, refer_wxid: str, refer_nick: str, receiver: str, producer: str = "main"
    ):
        """
        :param msg: 文本消息
        :param refer_content: 被引用的文本内容
        :param refer_wxid: 被引用者的wxid
        :param refer_nick: 被引用者的昵称，可随意填写
        :param receiver: 接收者
        :param producer: 发送者标识符，可随意填写
        :return:
        """
        data = {
            "receiver": receiver,
            "xml": f"<msg><appmsg><title>{msg}</title><type>57</type><refermsg><type>1</type>"
                   f"<fromusr>{refer_wxid}</fromusr><chatusr>{selfwxid}</chatusr>"
                   f"<displayname>{refer_nick}</displayname>"
                   f"<content>{refer_content}</content>"
                   f"</refermsg></appmsg><fromusername>{selfwxid}</fromusername></msg>"
        }
        self.__produce__(data, wcf + 'xml', producer)
