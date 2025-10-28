from .base import *
from wxauto.ui.component import (
    ProfileWnd,
)
from wxauto.utils.tools import (
    parse_wechat_time
)
from typing import (
    Literal,
    Dict,
    List
)
import time


class SystemMessage(BaseMessage):
    attr = 'system'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
        self.sender = 'system'
        self.sender_remark = 'system'

class TickleMessage(SystemMessage):
    attr = 'tickle'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
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
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
        self.time = parse_wechat_time(self.content)

class FriendMessage(HumanMessage):
    attr = 'friend'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
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
            return int(self.head_control.BoundingRectangle.width()*WxParam.BIAS_MULTIPLE)
        return WxParam.DEFAULT_MESSAGE_XBIAS
    
    @uilock
    def sender_info(self) -> Dict:
        """获取发送人信息
        
        Returns:
            Dict: 发送人信息
        """
        self._open_profile()
        if profile_wnd := ProfileWnd(self):
            profile_wnd.close()
            return profile_wnd.info
        profile_wnd.close()
    
    @uilock
    def at(
            self, content: str, 
            quote: bool = False
        ) -> WxResponse:
        """@该消息发送人，并发送指定内容
        
        Args:
            content (str): 要发送的内容
            quote (bool): 是否引用该消息

        Returns:
            WxResponse: 发送结果
        """
        self.roll_into_view()
        self.head_control.RightClick()
        menu = CMenuWnd(self)
        options = menu.option_names
        option_list = [i for i in options if '@' in i]
        if not option_list:
            menu.close()
            return WxResponse.failure('当前聊天窗口没有@功能')
        option = option_list[0]
        menu.select(option)
        if quote:
            self.right_click()
            menu = CMenuWnd(self)
            quote_result = menu.select('引用')
            if not quote_result:
                menu.close()
                wxlog.debug(f'消息引用失败: {quote_result.get("message")}')
        return self.parent.send_text(content)
    
    @uilock
    def add_friend(
            self,
            addmsg: str = None, 
            remark: str = None, 
            tags: List[str] = None, 
            permission: Literal['朋友圈', '仅聊天'] = '朋友圈', 
            timeout: int = 3
        ) -> WxResponse:
        """添加好友

        Args:
            addmsg (str, optional): 添加好友时的附加消息，默认为None
            remark (str, optional): 添加好友后的备注，默认为None
            tags (list, optional): 添加好友后的标签，默认为None
            permission (Literal['朋友圈', '仅聊天'], optional): 添加好友后的权限，默认为'朋友圈'
            timeout (int, optional): 搜索好友的超时时间，默认为3秒
        """
        t0 = time.time()
        while True:
            try:
                self.root._show()
                self.roll_into_view()
                self.head_control.Click()
                if profile_wnd := ProfileWnd(self):
                    result = profile_wnd.add_friend(
                        addmsg=addmsg,
                        remark=remark,
                        tags=tags,
                        permission=permission
                    )
                    return result
            except:
                time.sleep(0.1)
            if time.time() - t0 > timeout:
                return WxResponse.failure('添加好友超时')


class SelfMessage(HumanMessage):
    attr = 'self'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
    
    @property
    def _xbias(self):
        if WxParam.FORCE_MESSAGE_XBIAS:
            return -int(self.head_control.BoundingRectangle.width()*WxParam.BIAS_MULTIPLE)
        return -WxParam.DEFAULT_MESSAGE_XBIAS