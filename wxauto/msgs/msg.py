from .mattr import *
from .type import OtherMessage
from . import self as selfmsg
from . import friend as friendmsg
from wxauto.languages import *
from wxauto.param import WxParam
from wxauto import uia
from typing import Literal, List
import re


class MESSAGE_ATTRS:
    SYS_TEXT_HEIGHT = 33
    TIME_TEXT_HEIGHT = 34
    CHAT_TEXT_HEIGHT = 52
    FILE_MSG_HEIGHT = 115
    VOICE_MSG_HEIGHT = 55
    LOCATION_MSG_HEIGHT = 80
    LINK_CARD_MSG_HEIGHT = 100
    MERGE_MSG_HEIGHT = 100
    PERSONAL_CARD_MSG_HEIGHT = 121

    TEXT_MSG_CONTROL_NUM = (8, 9, 10, 11)
    TIME_MSG_CONTROL_NUM = (1,)
    SYS_MSG_CONTROL_NUM = (4,5,6)
    IMG_MSG_CONTROL_NUM = (9, 10, 11, 12)
    FILE_MSG_CONTROL_NUM = tuple(i for i in range(15, 30))
    VOICE_MSG_CONTROL_NUM = tuple(i for i in range(10, 30))
    VIDEO_MSG_CONTROL_NUM = (13, 14, 15, 16)
    LOCATION_MSG_CONTROL_NUM = (12, 13, 14, 15, 16, 17)
    LINK_CARD_MSG_CONTROL_NUM = tuple(i for i in range(10, 20))
    EMOTION_MSG_CONTROL_NUM = (8, 9, 10, 11)
    MERGE_MSG_CONTROL_NUM = tuple(i for i in range(15, 20))
    QUOTE_MSG_CONTROL_NUM = tuple(i for i in range(16, 30))
    PERSONAL_CARD_MSG_CONTROL_NUM = (16, 17)
    TIKCLE_MSG_CONTROL_NUM = tuple(i for i in range(10, 100))
    NOTE_MSG_CONTROL_NUM = tuple(i for i in range(15, 20))

def _lang(text: str) -> str:
    return MESSAGES.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

SEPICIAL_MSGS = [
    _lang(i)
    for i in [
        '[图片]',     # ImageMessage
        '[视频]',     # VideoMessage
        '[语音]',     # VoiceMessage
        # '[音乐]',
        '[位置]',     # LocationMessage
        '[链接]',     # LinkMessage
        '[文件]',     # FileMessage
        '[名片]',     # PersonalCardMessage
        '[笔记]',     # NoteMessage
        # '[视频号]',
        '[动画表情]',  # EmotionMessage
        '[聊天记录]',  # MergeMessage
    ]
]

def parse_msg(
        control: uia.Control, 
        parent,
    ):
    msg_rect = control.BoundingRectangle
    height = msg_rect.height()
    mid = (msg_rect.left + msg_rect.right) / 2

    # sub_controls = control.FindAll()[1:]
    sub_control_pointer = control.FindAll(return_pointer=True)
    length = sub_control_pointer.Length - 1

    # TimeMessage
    if (
        length in MESSAGE_ATTRS.TIME_MSG_CONTROL_NUM
    ):
        return TimeMessage(control, parent, sub_control_pointer)
    
    # FriendMessage or SelfMessage
    if (head_control := control.ButtonControl(searchDepth=2)).Exists(0):
        head_rect = head_control.BoundingRectangle
        if head_rect.left < mid:
            return parse_msg_type(control, parent, 'Friend', sub_control_pointer)
        else:
            return parse_msg_type(control, parent, 'Self', sub_control_pointer)
    
    # SystemMessage or TickleMessage
    else:
        if length in MESSAGE_ATTRS.SYS_MSG_CONTROL_NUM:
            return SystemMessage(control, parent)
        elif control.ListItemControl(RegexName=_lang('re_拍一拍')).Exists(0):
            return TickleMessage(control, parent)
        else:
            # print(height, length)
            # control.tree
            return OtherMessage(control, parent)

def parse_msg_type(
        control: uia.Control,
        parent,
        attr: Literal['Self', 'Friend'],
        sub_control_pointer: List[uia.Control] = None
    ):
    if sub_control_pointer is None:
        sub_control_pointer = control.FindAll(return_pointer=True)
    length = sub_control_pointer.Length - 1
    content = control.Name
    msg_rect = control.BoundingRectangle
    height = msg_rect.height()
    wxlog.debug(f"parse message: c({content}), l({length}), h({height})")
    if attr == 'Friend':
        msgtype = friendmsg
    else:
        msgtype = selfmsg
    
    # Special Message Type
    if content in SEPICIAL_MSGS:
        # ImageMessage
        if content == _lang('[图片]') and length in MESSAGE_ATTRS.IMG_MSG_CONTROL_NUM:
            return getattr(msgtype, f'{attr}ImageMessage')(control, parent, sub_control_pointer)
        
        # VideoMessage
        elif content == _lang('[视频]') and length in MESSAGE_ATTRS.VIDEO_MSG_CONTROL_NUM:
            return getattr(msgtype, f'{attr}VideoMessage')(control, parent, sub_control_pointer)
        
        # FileMessage
        elif content == _lang('[文件]') and length in MESSAGE_ATTRS.FILE_MSG_CONTROL_NUM:
            return getattr(msgtype, f'{attr}FileMessage')(control, parent, sub_control_pointer)
        
        # LocationMessage
        elif (
            content == _lang('[位置]') 
            and length in MESSAGE_ATTRS.LOCATION_MSG_CONTROL_NUM
            and height > MESSAGE_ATTRS.LOCATION_MSG_HEIGHT
        ):
            return getattr(msgtype, f'{attr}LocationMessage')(control, parent, sub_control_pointer)
        
        # LinkMessage
        elif (
            content == _lang('[链接]')
            and length in MESSAGE_ATTRS.LINK_CARD_MSG_CONTROL_NUM
            # and height >= MESSAGE_ATTRS.LINK_CARD_MSG_HEIGHT
        ):
            return getattr(msgtype, f'{attr}LinkMessage')(control, parent, sub_control_pointer)
        
        # EmotionMessage
        elif (
            content == _lang('[动画表情]')
            and length in MESSAGE_ATTRS.EMOTION_MSG_CONTROL_NUM
        ):
            return getattr(msgtype, f'{attr}EmotionMessage')(control, parent, sub_control_pointer)
        
        # MergeMessage
        elif (
            content == _lang('[聊天记录]')
            and length in MESSAGE_ATTRS.MERGE_MSG_CONTROL_NUM
            and height >= MESSAGE_ATTRS.MERGE_MSG_HEIGHT
        ):
            return getattr(msgtype, f'{attr}MergeMessage')(control, parent, sub_control_pointer)
        
        # PersonalCardMessage
        elif (
            content == _lang('[名片]')
            and length in MESSAGE_ATTRS.PERSONAL_CARD_MSG_CONTROL_NUM
            and height >= MESSAGE_ATTRS.PERSONAL_CARD_MSG_HEIGHT
        ):
            return getattr(msgtype, f'{attr}PersonalCardMessage')(control, parent, sub_control_pointer)
        
        # NoteMessage
        elif (
            content == _lang('[笔记]')
            and length in MESSAGE_ATTRS.NOTE_MSG_CONTROL_NUM
        ):
            return getattr(msgtype, f'{attr}NoteMessage')(control, parent, sub_control_pointer)
    
    # TextMessage
    if length in MESSAGE_ATTRS.TEXT_MSG_CONTROL_NUM:
        return getattr(msgtype, f'{attr}TextMessage')(control, parent, sub_control_pointer)
    
    # QuoteMessage
    elif (
        rematch := re.compile(_lang('re_引用消息'), re.DOTALL).match(content)
        and length in MESSAGE_ATTRS.QUOTE_MSG_CONTROL_NUM
    ):
        return getattr(msgtype, f'{attr}QuoteMessage')(control, parent, sub_control_pointer)
    
    # VoiceMessage    
    elif (
        rematch := re.compile(_lang('re_语音')).match(content)
        and length in MESSAGE_ATTRS.VOICE_MSG_CONTROL_NUM
    ):
        return getattr(msgtype, f'{attr}VoiceMessage')(control, parent, sub_control_pointer)
    
    # print(length, content)
    return getattr(msgtype, f'{attr}OtherMessage')(control, parent, sub_control_pointer)
