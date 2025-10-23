from .wx import (
    WeChat, 
    Chat,
    WeChatLogin
)
from .param import WxParam
import pythoncom

pythoncom.CoInitialize()

__all__ = [
    'WeChat',
    'Chat',
    'WeChatLogin',
    'WxParam'
]