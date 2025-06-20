from wxauto import uiautomation as uia
from wxauto.logger import wxlog
from wxauto.param import (
    WxResponse,
    WxParam,
    PROJECT_NAME
)
from wxauto.ui.component import (
    CMenuWnd,
    SelectContactWnd
)
from wxauto.utils.tools import roll_into_view
from wxauto.languages import *
from typing import (
    Dict, 
    List, 
    Union,
    TYPE_CHECKING
)
from hashlib import md5
import time

if TYPE_CHECKING:
    from wxauto.ui.chatbox import ChatBox

def truncate_string(s: str, n: int=8) -> str:
    s = s.replace('\n', '').strip()
    return s if len(s) <= n else s[:n] + '...'

class Message:...
class BaseMessage(Message):
    type: str = 'base'
    attr: str = 'base'
    control: uia.Control

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
        ):
        self.control = control
        self.parent = parent
        self.root = parent.root
        self.content = self.control.Name
        self.id = self.control.runtimeid
        self.sender = self.attr
        self.sender_remark = self.attr

    def __repr__(self):
        cls_name = self.__class__.__name__
        content = truncate_string(self.content)
        return f"<{PROJECT_NAME} - {cls_name}({content}) at {hex(id(self))}>"
    
    @property
    def message_type_name(self) -> str:
        return self.__class__.__name__
    
    def chat_info(self) -> Dict:
        if self.control.Exists(0):
            return self.parent.get_info()
    
    def _lang(self, text: str) -> str:
        return MESSAGES.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    def roll_into_view(self) -> WxResponse:
        if roll_into_view(self.control.GetParentControl(), self.control, equal=True) == 'not exist':
            wxlog.warning('消息目标控件不存在，无法滚动至显示窗口')
            return WxResponse.failure('消息目标控件不存在，无法滚动至显示窗口')
        return WxResponse.success('成功')
    
    @property
    def info(self) -> Dict:
        _info = self.parent.get_info().copy()
        _info['class'] = self.message_type_name
        _info['id'] = self.id
        _info['type'] = self.type
        _info['attr'] = self.attr
        _info['content'] = self.content
        return _info


class HumanMessage(BaseMessage):
    attr = 'human'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
        ):
        super().__init__(control, parent)
        self.head_control = self.control.ButtonControl(searchDepth=2)


    def roll_into_view(self) -> WxResponse:
        if roll_into_view(self.control.GetParentControl(), self.head_control, equal=True) == 'not exist':
            return WxResponse.failure('消息目标控件不存在，无法滚动至显示窗口')
        return WxResponse.success('成功')

    def click(self):
        self.roll_into_view()
        self.head_control.Click(x=self._xbias)

    def right_click(self):
        self.roll_into_view()
        self.head_control.Click(x=-self._xbias)
        self.head_control.RightClick(x=self._xbias)

    def select_option(self, option: str, timeout=None) -> WxResponse:
        self.root._show()
        def _select_option(self, option):
            if not (roll_result := self.roll_into_view()):
                return roll_result
            self.right_click()
            menu = CMenuWnd(self.root)
            return menu.select(item=option)
        
        if timeout:
            t0 = time.time()
            while True:
                if (time.time() - t0) > timeout:
                    return WxResponse(False, '引用消息超时')
                if quote_result := _select_option(self, option):
                    return quote_result
                
        else:
            return _select_option(self, option)
    
    def quote(
            self, text: str, 
            at: Union[List[str], str] = None, 
            timeout: int = 3
        ) -> WxResponse:
        """引用消息
        
        Args:
            text (str): 引用内容
            at (List[str], optional): @用户列表
            timeout (int, optional): 超时时间，单位为秒，若为None则不启用超时设置

        Returns:
            WxResponse: 调用结果
        """
        if not self.select_option('引用', timeout=timeout):
            wxlog.debug(f"当前消息无法引用：{self.content}")
            return WxResponse(False, '当前消息无法引用')
        
        if at:
            self.parent.input_at(at)

        return self.parent.send_text(text)
    
    def reply(
            self, text: str, 
            at: Union[List[str], str] = None
        ) -> WxResponse:
        """引用消息
        
        Args:
            text (str): 回复内容
            at (List[str], optional): @用户列表
            timeout (int, optional): 超时时间，单位为秒，若为None则不启用超时设置

        Returns:
            WxResponse: 调用结果
        """
        if at:
            self.parent.input_at(at)

        return self.parent.send_text(text)

    def forward(self, targets: Union[List[str], str], timeout: int = 3) -> WxResponse:
        """转发消息

        Args:
            targets (Union[List[str], str]): 目标用户列表
            timeout (int, optional): 超时时间，单位为秒，若为None则不启用超时设置

        Returns:
            WxResponse: 调用结果
        """
        if not self.select_option('转发', timeout=timeout):
            return WxResponse(False, '当前消息无法转发')
        
        select_wnd = SelectContactWnd(self)
        return select_wnd.send(targets)