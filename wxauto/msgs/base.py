from wxauto import uia
from wxauto.logger import wxlog
from wxauto.param import (
    WxResponse,
    WxParam,
    PROJECT_NAME
)
from wxauto.ui.component import (
    CMenuWnd,
    SelectContactWnd,
    ProfileWnd,
    WeChatDialog
)
from wxauto.utils import uilock
from wxauto.languages import *
from typing import (
    Dict, 
    List, 
    Union,
    TYPE_CHECKING
)
from pathlib import Path
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
            sub_control_pointer = None,
        ):
        self.control = control
        self.parent = parent
        self.sub_control_pointer = sub_control_pointer
        self.root = parent.root
        self.content = self.control.Name
        self.id = self.control.runtimeid
        if sub_control_pointer is None:
            self.sub_control_pointer = control.FindAll(return_pointer=True)
        self._get_hash(WxParam.MESSAGE_HASH)
        self.sender = self.attr
        self.sender_remark = self.attr
        
        # wxlog.debug()

    def __repr__(self):
        cls_name = self.__class__.__name__
        content = truncate_string(self.content)
        return f"<{PROJECT_NAME} - {cls_name}({content}) at {hex(id(self))}>"
    
    @property
    def message_type_name(self) -> str:
        return self.__class__.__name__
    
    def chat_info(self) -> Dict:
        """获取聊天窗口信息"""
        if self.control.Exists(0):
            return self.parent.get_info()
    
    def _lang(self, text: str) -> str:
        return MESSAGES.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)
    
    def _get_hash(self, enable: bool = True):
        if enable:
            sub_controls = self.control.FindAll(pointer=self.sub_control_pointer)
            self.structure_data = [(i.ControlTypeName,i.ClassName,i.Name) for i in sub_controls]
            rect = self.control.BoundingRectangle
            self.hash_text = f'({rect.height()},{rect.width()})' + ';'.join([f"{i[0]}:{i[1]},{i[2]}" for i in self.structure_data])
            self.hash = md5(self.hash_text.encode()).hexdigest()
        else:
            self.structure_data = []
            self.hash_text = ''
            self.hash = ''
    
    def get_all_text(self) -> str:
        """获取消息UI控件所有文字内容"""
        if self.control.Exists(0):
            return [text for i in self.control.FindAll() if (text:= i.Name)]
    
    @uilock
    def roll_into_view(self) -> WxResponse:
        """滚动消息至显示窗口"""
        if uia.RollIntoView(self.control.GetParentControl(), self.control, equal=True) == 'not exist':
            wxlog.warning('消息目标控件不存在，无法滚动至显示窗口')
            return WxResponse.failure('消息目标控件不存在，无法滚动至显示窗口')
        return WxResponse.success('成功')
    
    @property
    def info(self) -> Dict:
        # _info = self.parent.get_info().copy()
        _info = {}
        _info['class'] = self.message_type_name
        _info['id'] = self.id
        _info['type'] = self.type
        _info['attr'] = self.attr
        _info['content'] = self.content
        _info['hash'] = self.hash
        return _info
    
    @uilock
    def show_window(self):
        """显示消息窗口"""
        self.root._show()


class HumanMessage(BaseMessage):
    attr = 'human'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
        self.head_control = self.control.ButtonControl(searchDepth=2)

    @uilock
    def roll_into_view(self) -> WxResponse:
        if not self.control.Exists(0):
            return WxResponse.failure('消息目标控件不存在，无法滚动至显示窗口')
        if uia.RollIntoView(self.control.GetParentControl(), self.head_control, equal=True, bias=10) == 'not exist':
            return WxResponse.failure('消息目标控件不存在，无法滚动至显示窗口')
        return WxResponse.success('成功')
    
    @uilock
    def _open_profile(self):
        self.root._show()
        self.roll_into_view()
        self.head_control.Click()
        return ProfileWnd(self)

    @uilock
    def download_head_image(self) -> Path:
        """下载头像图片"""
        t0 = time.time()
        while True:
            if time.time() - t0 > 10:
                return WxResponse.failure('下载超时')
            
            profile = self._open_profile()
            path = profile.download_head_image()
            if isinstance(path, WxResponse):
                if path['message'] == '微信BUG无法获取该图片，请重新获取':
                    profile.close()
                    continue
                else:
                    return path
            elif isinstance(path, Path):
                profile.close()
                return path
            time.sleep(0.1)

    @uilock
    def click(self, move=False):
        """点击消息"""
        if move:
            self.root._show()
        self.roll_into_view()
        self.head_control.Click(x=self._xbias, move=move)

    @uilock
    def right_click(self, move=False):
        """右键点击消息"""
        if move:
            self.root._show()
        self.roll_into_view()
        self.head_control.Click(x=-self._xbias, move=move)
        self.head_control.RightClick(x=self._xbias, move=move)

    @uilock
    def select_option(self, option: str, timeout=None) -> WxResponse:
        """右键点击消息后，选择菜单项"""
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
                    return WxResponse.failure('引用消息超时')
                if quote_result := _select_option(self, option):
                    return quote_result
                
        else:
            return _select_option(self, option)
    
    @uilock
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
            return WxResponse.failure('当前消息无法引用')
        
        if at:
            self.parent.input_at(at)

        return self.parent.send_text(text)
    
    @uilock
    def multi_select(self):
        """多选消息"""
        self.roll_into_view()
        if self.parent.control.ToolBarControl(Name=self.parent._lang('多选'), searchDepth=9).Exists(0):
            self.control.Click()
        else:
            self.select_option(self.parent._lang('多选'))
    
    @uilock
    def reply(
            self, text: str, 
            at: Union[List[str], str] = None
        ) -> WxResponse:
        """回复消息
        
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

    @uilock
    def forward(
        self, 
        targets: Union[List[str], str], 
        message: str=None,
        timeout: int = 3
    ) -> WxResponse:
        """转发消息

        Args:
            targets (Union[List[str], str]): 目标用户列表
            timeout (int, optional): 超时时间，单位为秒，若为None则不启用超时设置

        Returns:
            WxResponse: 调用结果
        """
        if not self.control.Exists(0):
            return WxResponse.failure('消息对象已失效')
        if not self.select_option('转发', timeout=timeout):
            return WxResponse.failure('当前消息无法转发')
        
        select_wnd = SelectContactWnd(self)
        return select_wnd.send(targets, message=message)
    
    @uilock
    def tickle(self):
        """拍一拍该消息发送人"""
        if not self.control.Exists(0):
            return WxResponse.failure('消息对象已失效')
        self.roll_into_view()
        self.head_control.RightClick()
        menu = CMenuWnd(self)
        return menu.select('拍一拍')
    
    @uilock
    def delete(self, wait=3) -> WxResponse:
        """删除消息"""
        if not self.control.Exists(0):
            return WxResponse.failure('消息对象已失效')
        if not self.select_option('删除', timeout=3):
            return WxResponse.failure('当前消息无法删除')
        if (dialog := WeChatDialog(self, wait=wait)).exists(3):
            time.sleep(0.1)
            while dialog.exists(0):
                dialog.click_button('确定')
            if self.control.Exists(0):
                return WxResponse.failure('删除消息失败')
            return WxResponse.success()
        return WxResponse.failure('删除消息失败')
    
    @uilock
    def capture(self, return_obj=False):
        """截图消息
        
        Args:
            return_obj (bool): 是否返回PIL.Image对象，默认为 False
            
        Returns:
            PIL.Image: return_obj为True时返回截图对象
            Path: return_obj为False时返回截图路径
            WxResponse: 操作失败时返回
        """
        if not self.control.Exists(0):
            return WxResponse.failure('消息对象已失效')
        self.roll_into_view()
        if return_obj:
            return self.control.FindAll()[3].ScreenShot(return_img=return_obj)
        else:
            return Path(self.control.FindAll()[3].ScreenShot())