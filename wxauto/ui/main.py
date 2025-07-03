from .base import (
    BaseUIWnd,
    BaseUISubWnd
)
from wxauto import uiautomation as uia
from wxauto.param import WxResponse
from .chatbox import ChatBox
from .sessionbox import SessionBox
from .navigationbox import NavigationBox
from wxauto.param import (
    WxParam, 
    WxResponse, 
    PROJECT_NAME
)
from wxauto.languages import *
from wxauto.utils import (
    GetAllWindows,
    FindWindow,
)
from wxauto.logger import wxlog
from typing import (
    Union,
    List,
)

class WeChatSubWnd(BaseUISubWnd):
    _ui_cls_name: str = 'ChatWnd'
    chatbox: ChatBox = None
    nickname: str = ''

    def __init__(
            self, 
            key: Union[str, int], 
            parent: 'WeChatMainWnd', 
            timeout: int = 3
        ):
        self.root = self
        self.parent = parent
        if isinstance(key, str):
            hwnd = FindWindow(classname=self._ui_cls_name, name=key, timeout=timeout)
        else:
            hwnd = key
        self.control = uia.ControlFromHandle(hwnd)
        if self.control is not None:
            chatbox_control = self.control.PaneControl(ClassName='', searchDepth=1)
            self.chatbox = ChatBox(chatbox_control, self)
            self.nickname = self.control.Name

    def __repr__(self):
        return f'<{PROJECT_NAME} - {self.__class__.__name__} object("{self.nickname}")>'

    @property
    def pid(self):
        if not hasattr(self, '_pid'):
            self._pid = self.control.ProcessId
        return self._pid
    
    def _get_chatbox(
            self, 
            nickname: str=None, 
            exact: bool=False
        ) -> ChatBox:
        return self.chatbox
    
    def chat_info(self):
        return self.chatbox.get_info()
    
    def load_more_message(self, interval=0.3) -> WxResponse:
        return self.chatbox.load_more(interval)
    
    def send_msg(
            self, 
            msg: str,
            who: str=None,
            clear: bool=True, 
            at: Union[str, List[str]]=None,
            exact: bool=False,
        ) -> WxResponse:
        chatbox = self._get_chatbox(who, exact)
        if not chatbox:
            return WxResponse.failure(f'未找到会话: {who}')
        return chatbox.send_msg(msg, clear, at)
    
    def send_files(
            self, 
            filepath, 
            who=None, 
            exact=False
        ) -> WxResponse:
        chatbox = self._get_chatbox(who, exact)
        if not chatbox:
            return WxResponse.failure(f'未找到会话: {who}')
        return chatbox.send_file(filepath)

    def get_group_members(
            self,
            who: str=None,
            exact: bool=False
        ) -> List[str]:
        chatbox = self._get_chatbox(who, exact)
        if not chatbox:
            return WxResponse.failure(f'未找到会话: {who}')
        return chatbox.get_group_members()
    
    def get_msgs(self):
        chatbox = self._get_chatbox()
        if chatbox:
            return chatbox.get_msgs()
        return []
    
    def get_new_msgs(self):
        return self._get_chatbox().get_new_msgs()


class WeChatMainWnd(WeChatSubWnd):
    _ui_cls_name: str = 'WeChatMainWndForPC'
    _ui_name: str = '微信'

    def __init__(self, hwnd: int = None):
        self.root = self
        self.parent = self
        if hwnd:
            self._setup_ui(hwnd)
        else:
            hwnd = FindWindow(classname=self._ui_cls_name)
            if not hwnd:
                raise Exception(f'未找到微信窗口')
            self._setup_ui(hwnd)
        
        print(f'初始化成功，获取到已登录窗口：{self.nickname}')

    def _setup_ui(self, hwnd: int):
        self.HWND = hwnd
        self.control = uia.ControlFromHandle(hwnd)
        MainControl1 = [i for i in self.control.GetChildren() if not i.ClassName][0]
        MainControl2 = MainControl1.GetFirstChildControl()
        navigation_control, sessionbox_control, chatbox_control  = MainControl2.GetChildren()
        self.navigation = NavigationBox(navigation_control, self)
        self.sessionbox = SessionBox(sessionbox_control, self)
        self.chatbox = ChatBox(chatbox_control, self)
        self.nickname = self.navigation.my_icon.Name
        self.NavigationBox = self.navigation.control
        self.SessionBox = self.sessionbox.control
        self.ChatBox = self.chatbox.control

    def __repr__(self):
        return f'<{PROJECT_NAME} - {self.__class__.__name__} object("{self.nickname}")>'
        
    def _lang(self, text: str) -> str:
        return WECHAT_MAIN.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)
    
    def _get_chatbox(
            self, 
            nickname: str=None, 
            exact: bool=False
        ) -> ChatBox:
        if nickname and (chatbox := WeChatSubWnd(nickname, self, timeout=0)).control:
            return chatbox._chat_api
        else:
            if nickname:
                switch_result = self.sessionbox.switch_chat(keywords=nickname, exact=exact)
                if not switch_result:
                    return None
            if self._chat_api.msgbox.Exists(0.5):
                return self._chat_api
            
    def switch_chat(
            self, 
            keywords: str, 
            exact: bool = False,
            force: bool = False,
            force_wait: Union[float, int] = 0.5
        ):
        return self.sessionbox.switch_chat(keywords, exact, force, force_wait)
        
    def get_all_sub_wnds(self):
        sub_wxs = [i for i in GetAllWindows() if i[1] == WeChatSubWnd._ui_cls_name]
        return [WeChatSubWnd(i[0], self) for i in sub_wxs]
    
    def get_sub_wnd(self, who: str, timeout: int=0):
        if hwnd := FindWindow(classname=WeChatSubWnd._ui_cls_name, name=who, timeout=timeout):
            return WeChatSubWnd(hwnd, self)
        
    def open_separate_window(self, keywords: str) -> WeChatSubWnd:
        if subwin := self.get_sub_wnd(keywords):
            wxlog.debug(f"{keywords} 获取到已存在的子窗口: {subwin}")
            return subwin
        self._show()
        if nickname := self.sessionbox.switch_chat(keywords):
            wxlog.debug(f"{keywords} 切换到聊天窗口: {nickname}")
            if subwin := self.get_sub_wnd(nickname):
                wxlog.debug(f"{nickname} 获取到已存在的子窗口: {subwin}")
                return subwin
            else:
                keywords = nickname
        if result := self.sessionbox.open_separate_window(keywords):
            find_nickname = result['data'].get('nickname', keywords)
            return WeChatSubWnd(find_nickname, self)
    
    def _get_next_new_message(self, filter_mute: bool=False):
        def get_new_message(session):
            last_content = session.content
            new_count = session.new_count
            chat_name = session.name
            session.click()
            return self.chatbox.get_next_new_msgs(new_count, last_content)
        
        def get_new_session(filter_mute):
            sessions = self.sessionbox.get_session()
            if sessions[0].name == self._lang('折叠的群聊'):
                self.navigation.chat_icon.DoubleClick()
                sessions = self.sessionbox.get_session()
            new_sessions = [
                i for i in sessions 
                if i.isnew 
                and i.name != self._lang('折叠的群聊')
            ]
            if filter_mute:
                new_sessions = [i for i in new_sessions if i.ismute == False]
            return new_sessions

        if new_msgs := self.chatbox.get_new_msgs():
            wxlog.debug("获取当前页面新消息")
            return new_msgs
        elif new_sessions := get_new_session(filter_mute):
            wxlog.debug("当前会话列表获取新消息")
            return get_new_message(new_sessions[0])
        else:
            self.sessionbox.go_top()
            if new_sessions := get_new_session(filter_mute):
                wxlog.debug("当前会话列表获取新消息")
                return get_new_message(new_sessions[0])
            else:
                self.navigation.chat_icon.DoubleClick()
            if new_sessions := get_new_session(filter_mute):
                wxlog.debug("翻页会话列表获取新消息")
                return get_new_message(new_sessions[0])
            else:
                wxlog.debug("没有新消息")
                return []

    def get_next_new_message(self, filter_mute: bool=False):
        if filter_mute and not self.navigation.has_new_message():
            return {}
        new_msgs = self._get_next_new_message(filter_mute)
        if new_msgs:
            chat_info = self.chatbox.get_info()
            return {
                'chat_name': chat_info['chat_name'],
                'chat_type': chat_info['chat_type'],
                'msg': new_msgs
            }
        else:
            return {}
