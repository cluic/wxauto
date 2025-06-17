from .attr import *
from .type import OtherMessage
from . import self as selfmsg
from . import friend as friendmsg
from wxauto.languages import *
from wxauto.param import WxParam
from wxauto import uiautomation as uia
from typing import Literal
import re

class MESSAGE_ATTRS:
    SYS_TEXT_HEIGHT = 33
    TIME_TEXT_HEIGHT = 34
    CHAT_TEXT_HEIGHT = 52
    FILE_MSG_HEIGHT = 115
    VOICE_MSG_HEIGHT = 55

    TEXT_MSG_CONTROL_NUM = (8, 9, 10, 11)
    TIME_MSG_CONTROL_NUM = (1,)
    SYS_MSG_CONTROL_NUM = (4,5,6)
    IMG_MSG_CONTROL_NUM = (9, 10, 11, 12)
    FILE_MSG_CONTROL_NUM = (21, 22, 23, 24)
    VOICE_MSG_CONTROL_NUM = tuple(i for i in range(10, 30))
    VIDEO_MSG_CONTROL_NUM = (13, 14, 15, 16)

def _lang(text: str) -> str:
    return MESSAGES.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

SEPICIAL_MSGS = [
    _lang(i)
    for i in [
        '[图片]',     # ImageMessage
        '[视频]',     # VideoMessage
        '[语音]',     # VoiceMessage
    ]
]

def parse_msg_attr(
        control: uia.Control, 
        parent,
    ):
    msg_rect = control.BoundingRectangle
    height = msg_rect.height()
    mid = (msg_rect.left + msg_rect.right) / 2
    for length, _ in enumerate(uia.WalkControl(control)):length += 1

    # TimeMessage
    if (
        height == MESSAGE_ATTRS.TIME_TEXT_HEIGHT
        and length in MESSAGE_ATTRS.TIME_MSG_CONTROL_NUM
    ):
        return TimeMessage(control, parent)
    
    # FriendMessage or SelfMessage
    if (head_control := control.ButtonControl(searchDepth=2)).Exists(0):
        head_rect = head_control.BoundingRectangle
        if head_rect.left < mid:
            return parse_msg_type(control, parent, 'Friend')
        else:
            return parse_msg_type(control, parent, 'Self')
    
    # SystemMessage or TickleMessage
    else:
        if length in MESSAGE_ATTRS.SYS_MSG_CONTROL_NUM:
            return SystemMessage(control, parent)
        elif control.ListItemControl(RegexName=_lang('re_拍一拍')).Exists(0):
            return TickleMessage(control, parent)
        else:
            return OtherMessage(control, parent)

def parse_msg_type(
        control: uia.Control,
        parent,
        attr: Literal['Self', 'Friend']
    ):
    for length, _ in enumerate(uia.WalkControl(control)):length += 1
    content = control.Name
    msg_rect = control.BoundingRectangle
    height = msg_rect.height()

    if attr == 'Friend':
        msgtype = friendmsg
    else:
        msgtype = selfmsg
    
    # Special Message Type
    if content in SEPICIAL_MSGS:
        # ImageMessage
        if content == _lang('[图片]') and length in MESSAGE_ATTRS.IMG_MSG_CONTROL_NUM:
            return getattr(msgtype, f'{attr}ImageMessage')(control, parent)
        
        # VideoMessage
        elif content == _lang('[视频]') and length in MESSAGE_ATTRS.VIDEO_MSG_CONTROL_NUM:
            return getattr(msgtype, f'{attr}VideoMessage')(control, parent)
        
        # FileMessage
        elif content == _lang('[文件]') and length in MESSAGE_ATTRS.FILE_MSG_CONTROL_NUM:
            return getattr(msgtype, f'{attr}FileMessage')(control, parent)
    
    # TextMessage
    if length in MESSAGE_ATTRS.TEXT_MSG_CONTROL_NUM:
        return getattr(msgtype, f'{attr}TextMessage')(control, parent)
    
    # VoiceMessage    
    elif (
        rematch := re.compile(_lang('re_语音')).match(content)
        and length in MESSAGE_ATTRS.VOICE_MSG_CONTROL_NUM
    ):
        return getattr(msgtype, f'{attr}VoiceMessage')(control, parent)
    
    return getattr(msgtype, f'{attr}OtherMessage')(control, parent)

def parse_msg(
    control: uia.Control,
    parent
):
    result = parse_msg_attr(control, parent)
    return result