from .base import *
from wxauto.utils.tools import (
    parse_wechat_time
)

class SystemMessage(BaseMessage):
    attr = 'system'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)
        self.sender = 'system'
        self.sender_remark = 'system'

class TickleMessage(SystemMessage):
    attr = 'tickle'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)
        self.tickle_list = [
            i.Name for i in 
            control.ListItemControl().GetParentControl().GetChildren()
        ]
        self.content = f"[{len(self.tickle_list)}条]{self.tickle_list[0]}"


class TimeMessage(SystemMessage):
    attr = 'time'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)
        self.time = parse_wechat_time(self.content)

class FriendMessage(HumanMessage):
    attr = 'friend'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)
        self.head_control = self.control.ButtonControl(RegexName='.*?')
        self.sender = self.head_control.Name
        if (
            (remark_control := self.control.TextControl()).Exists(0)
            and remark_control.BoundingRectangle.top < self.head_control.BoundingRectangle.top
        ):
            self.sender_remark = remark_control.Name
        else:
            self.sender_remark = self.sender

    @property
    def _xbias(self):
        if WxParam.FORCE_MESSAGE_XBIAS:
            return int(self.head_control.BoundingRectangle.width()*1.5)
        return WxParam.DEFAULT_MESSAGE_XBIAS


class SelfMessage(HumanMessage):
    attr = 'self'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)
    
    @property
    def _xbias(self):
        if WxParam.FORCE_MESSAGE_XBIAS:
            return -int(self.head_control.BoundingRectangle.width()*1.5)
        return -WxParam.DEFAULT_MESSAGE_XBIAS