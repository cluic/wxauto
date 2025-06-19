from .wx import (
    WeChat, 
    Chat
)
from .param import WxParam
import pythoncom

pythoncom.CoInitialize()

__all__ = [
    'WeChat',
    'Chat',
    'WxParam'
]