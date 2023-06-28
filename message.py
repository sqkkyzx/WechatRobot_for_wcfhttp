import json
import logging
import time

import xmltodict
import sqlite3


class Record:
    def __init__(self, body: dict):
        # 删除 id 字段，从 xml 中图提取 signature 作为标识符
        # self.id: str = body.get('id')
        # 错误处理：语音电话或视频电话时，xml 为空。
        try:
            self.signature: str = xmltodict.parse(body.get('xml'), {}).get('msgsource', {}).get('signature')
        except Exception as e:
            logging.debug(e)
            self.signature: str = ''

        # 如果不存在 roomid 则将 sender 赋值给 roomid，以便于发送消息时不必再做判定。
        self.sender: str = body.get('sender')
        self.roomid: str = body.get('roomid') if body.get('roomid') else body.get('sender')

        self.thumb: str = body.get('thumb')
        self.is_at: bool = body.get('is_at')
        self.is_self: bool = body.get('is_self')
        self.is_group: bool = body.get('is_group')
        self.extra: str = body.get('extra')
        self.timestamp = time.time().__int__()

        # 调整 type 字段，细化类型:
        # 1-文本 3-图片 34-语音 42-个人或公众号名片 42-企业微信名片 43-视频 47-动画表情 48-定位 10000-系统提示 49-应用
        # 4957-引用 493-音乐 495-网页链接 496-文件 4916-卡券 4919-聊天记录 4933-小程序 492000-转账
        #
        # 调整 content 字段, 对纯文本以外其他类型的消息，提取相关的文本信息，以便能够传入 GPT 进行处理，详见函数注释。
        #
        # 调整 extra 字段，对纯文本以外其他类型的消息，提供了一些易读的信息，以便能够传入 GPT 进行处理，详见函数注释。
        #
        # 新增 parsexml 字段，对纯文本以外其他类型的消息，提供了 xml 的字典解析
        self.type, self.content, self.parsexml = self.parse(
            body.get('type'),
            body.get('content')
        )

        with MessageDB() as db:
            db.insert(self.__dict__)

    # XML 解析
    def parse(self, msgtype, content):

        match msgtype:
            # 未知类型
            case 0:
                return 0, content, {}

            # 文本
            case 1:
                return 1, content, {}

            # 图片
            case 3:
                # 引用消息循环解析的错误处理步骤
                parsexml = xmltodict.parse(content).get('msg') if content and '<img' in content else None

                return 3, f"[图片]", parsexml

            # 语音
            case 34:
                # 引用消息循环解析的错误处理步骤
                parsexml = xmltodict.parse(content).get('msg') if content and '<voicemsg' in content else None
                # 计算语音长度输出到 content
                voicelength = f"{int(parsexml['voicemsg']['@voicelength']) / 1000} 秒" if parsexml else ''

                return 34, f"[语音] {voicelength}", parsexml

            # 好友确认
            case 37:
                parsexml = xmltodict.parse(content).get('msg') if content else None
                self.extra = {
                    "v3": parsexml['@encryptusername'],
                    "v4": parsexml['@ticket'],
                    "scene": parsexml['@scene']
                }
                return 37, "[好友确认]", parsexml

            # POSSIBLEFRIEND_MSG
            case 40:
                return 40, "[POSSIBLEFRIEND_MSG]", {}

            # 名片
            case 42:
                parsexml = xmltodict.parse(content).get('msg')
                # 判断是个人名片还剩公众号名片，带名字输出到 content
                cardtype = '公众号名片' if parsexml['@certflag'] == '24' else '个人名片'
                name = parsexml['@nickname']

                return 42, f"[{cardtype}] {name}", parsexml

            # 视频
            case 43:
                # 引用消息循环解析的错误处理步骤
                parsexml = xmltodict.parse(content).get('msg') if content and '<videomsg' in content else None

                return 43, f"[视频]", parsexml

            # 动画表情
            case 47:

                # 引用消息循环解析的错误处理步骤
                parsexml = xmltodict.parse(content).get('msg') if content and '<emoji' in content else None
                # 如果 cdnurl 域名为 wxapp.tc.qq.com，就可以直接访问到表情，因此赋值给 extra
                if parsexml:
                    cdnurl: str = parsexml['emoji']['@cdnurl']
                    self.extra = cdnurl.replace('&amp;', '&') if 'wxapp.tc.qq.com' in cdnurl else self.extra

                return 47, "[动画表情]", parsexml

            # 定位
            case 48:
                parsexml = xmltodict.parse(content).get('msg')
                # 提取定位的地名和标签赋值到 content
                poiname = parsexml.get('location').get('@poiname')
                label = parsexml.get('location').get('@label')
                # 提取兴趣点 poiid 拼接一个 url 赋值到 extra
                poiid: str = parsexml.get('location').get('@poiid')
                self.extra = 'https://map.qq.com/poi/?sm=' + poiid.split('_')[1] if poiid else self.extra

                return 48, f"[定位] {poiname} {label}", parsexml

            # VOIPMSG
            case 50:
                return 50, "[VOIPMSG]", {}

            # 微信初始化
            case 51:
                return 51, "[微信初始化]", {}

            # VOIPNOTIFY
            case 52:
                return 52, "[VOIPNOTIFY]", {}

            # VOIPINVITE
            case 53:
                return 53, "[VOIPINVITE]", {}

            # 微信初始化
            case 62:
                return 62, "[小视频]", {}

            # 企业微信名片
            case 66:
                parsexml = xmltodict.parse(content).get('msg')
                # 将名字输出到 content
                name = parsexml['@nickname']
                return 66, f"[企业微信名片] {name}", parsexml

            # SYSNOTICE
            case 9999:
                return 9999, "[SYSNOTICE]", {}

            # 系统提示
            case 10000:
                return 10000, content, {}

            # 撤回消息
            case 10002:
                return 10002, "[撤回消息]", {}

            # 应用
            case 49:

                parsexml = xmltodict.parse(content).get('msg')
                appmsg = parsexml['appmsg']
                msgtype = int(appmsg['type'])

                match msgtype:

                    # 音乐
                    case 3:
                        # 提取歌曲标题、歌曲描述、歌曲链接输出到 content
                        title = appmsg['title']
                        des = appmsg['des']
                        url = appmsg['url']
                        # 提取歌曲音频数据 url 到 extra
                        self.extra = appmsg['dataurl']
                        # 提取歌曲封面到 thumb
                        self.thumb = appmsg['songalbumurl']

                        return 493, f"[音乐] <{title}> {des} ({url})", parsexml

                    # 引用消息中的音乐
                    case 76:
                        # 在引用消息中，音乐的 type 字段会变成 76
                        # 再次提取歌曲标题、歌曲描述、歌曲链接输出到 content
                        title, des, url = appmsg['title'], appmsg['des'], appmsg['url']
                        # 提取歌曲音频数据 url 到 extra
                        self.extra = appmsg['dataurl']
                        # 提取歌曲封面到 thumb
                        self.thumb = appmsg['songalbumurl']

                        return 493, f"[音乐] <{title}> {des} ({url})", parsexml

                    # 网页
                    case 5:
                        # 提取标题、描述、链接
                        appmsg = appmsg
                        title, des, url = appmsg['title'], appmsg['des'], appmsg['url']
                        self.extra = url

                        return 495, f"[链接] <{title}> {des} ({url})", parsexml

                    # 文件
                    case 6:
                        # 提取标题
                        title = appmsg['title']
                        path = self.extra

                        return 496, f"[文件] <{title}> ({path})", parsexml

                    # 卡券
                    case 16:
                        # 提取标题、描述
                        title, des = appmsg['title'], appmsg['des']
                        # 提取 LOGO 到 thumb
                        self.thumb = appmsg['thumburl']

                        return 4916, f"[卡券] <{title}> {des}", parsexml

                    # 位置共享
                    case 17:
                        return 4917, f"[发起了位置共享]", parsexml

                    # 合并转发
                    case 19:
                        # 提取标题、描述
                        title, des = appmsg['title'], appmsg['des']
                        # 重构聊天消息列表，清除不易阅读的信息
                        if appmsg['recorditem']:
                            recorditem = xmltodict.parse(appmsg['recorditem'])['recordinfo']
                            datalist = recorditem['datalist']['dataitem']
                            recorditem['datalist'] = [
                                {
                                    'type': int(item.get('@datatype', 0)),
                                    'content': ' '.join([item.get('datatitle', ''), item.get('datadesc', '')]),
                                    'name': item.get('sourcename', ''),
                                    'avatar': item.get('sourceheadurl', ''),
                                    'time': item.get('sourcetime', ''),
                                    'timestamp': int(item.get('srcMsgCreateTime', 0))
                                }
                                for item in datalist
                            ]
                            self.extra = recorditem

                        return 4919, f"[合并转发] <{title}> {des}", parsexml

                    # 引用
                    case 57:
                        # 提取实际消息
                        title = appmsg['title']
                        # 提取回复的内容
                        refermsg = appmsg.get('refermsg')

                        # 错误处理：当循环解析为 引用 类型时，最终会遇到 refermsg 为 None 的情况，因此加判断语句。
                        refertype = int(refermsg.get('type')) if refermsg else 0
                        refercontent = refermsg.get('content', '') if refermsg else ''

                        # 对引用内容的 xml 进行循环解析
                        if '<msg>' in refercontent and '</msg>' in refercontent:
                            self.extra = self.parse(refertype, refercontent)[1]
                        else:
                            # 如果非 xml ，则直接返回文本。
                            self.extra = refercontent

                        return 4957, title, parsexml

                    # 转账
                    case 2000:
                        title, des = appmsg['title'], appmsg['des']
                        # 提取接收转账用的 transferid 到 extra
                        self.extra = {
                            "transferid": appmsg['wcpayinfo']['transferid'],
                            "wxid": self.sender
                        }

                        return 2000, f"[转账] {title} {des}", parsexml

                # 当 49 类型消息有其他子类型未匹配到时，返回其他。
                return 49, "[其他]", parsexml

        # 当有其他类型的消息未匹配到时，返回空，忽略该消息。
        return msgtype, content, {}


class MessageDB:
    def __enter__(self, db='database/message.db'):
        self.__conn__ = sqlite3.connect(db)
        self.__cursor__ = self.__conn__.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__conn__.close()

    def __creat_table__(self):
        self.__cursor__.execute('''
                CREATE TABLE messages
                (signature TEXT, 
                 sender TEXT, 
                 roomid TEXT, 
                 thumb TEXT, 
                 is_at BOOLEAN, 
                 is_self BOOLEAN, 
                 is_group BOOLEAN, 
                 extra TEXT, 
                 type INTEGER, 
                 content TEXT, 
                 parsexml TEXT, 
                 timestamp INTEGER)
            ''')
        self.__conn__.commit()

    def insert(self, record):
        record['extra'] = json.dumps(
            record['extra'], ensure_ascii=False
        ) if isinstance(record['extra'], dict) else record['extra']

        record['parsexml'] = json.dumps(record['parsexml'], ensure_ascii=False)

        self.__cursor__.execute('''
            INSERT INTO messages 
            (signature, sender, roomid, thumb, is_at, is_self, is_group, extra, type, content, parsexml, timestamp) 
            VALUES 
            (:signature, :sender, :roomid, :thumb, :is_at, :is_self, :is_group, :extra, :type, :content, :parsexml, :timestamp)
        ''', record)
        self.__conn__.commit()

    def select(self, signature):
        self.__cursor__.execute("SELECT * FROM messages WHERE signature=?", (signature,))
        result = self.__cursor__.fetchone()
        row = result if result else None
        return row
