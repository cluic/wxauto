from .ui.main import (
    WeChatMainWnd,
    WeChatSubWnd
)
from .param import (
    WxResponse, 
    WxParam, 
    PROJECT_NAME
)
from .logger import wxlog
from typing import (
    Union, 
    List,
    Dict,
    Callable,
    TYPE_CHECKING
)
from abc import ABC, abstractmethod
import threading
import traceback
import time
import sys

if TYPE_CHECKING:
    from wxauto.msgs.base import Message
    from wxauto.ui.sessionbox import SessionElement


class Listener(ABC):
    def _listener_start(self):
        wxlog.debug('开始监听')
        self._listener_is_listening = True
        self._listener_messages = {}
        self._lock = threading.RLock()
        self._listener_stop_event = threading.Event()
        self._listener_thread = threading.Thread(target=self._listener_listen, daemon=True)
        self._listener_thread.start()

    def _listener_listen(self):
        if not hasattr(self, 'listen') or not self.listen:
            self.listen = {}
        while not self._listener_stop_event.is_set():
            try:
                self._get_listen_messages()
            except:
                wxlog.debug(f'监听消息失败：{traceback.format_exc()}')
            time.sleep(WxParam.LISTEN_INTERVAL)

    def _safe_callback(self, callback, msg, chat):
        try:
            with self._lock:
                callback(msg, chat)
        except Exception as e:
            wxlog.debug(f"监听消息回调发生错误：{traceback.format_exc()}")

    def _listener_stop(self):
        self._listener_is_listening = False
        self._listener_stop_event.set()
        self._listener_thread.join()

    @abstractmethod
    def _get_listen_messages(self):
        ...

class Chat:
    """微信聊天窗口实例"""

    def __init__(self, core: WeChatSubWnd=None):
        self.core = core
        self.who = self.core.nickname

    def __repr__(self):
        return f'<{PROJECT_NAME} - {self.__class__.__name__} object("{self.core.nickname}")>'
    
    def Show(self):
        """显示窗口"""
        self.core._show()

    def ChatInfo(self) -> Dict[str, str]:
        """获取聊天窗口信息
        
        Returns:
            dict: 聊天窗口信息
        """
        return self.core.chatbox.get_info()
    
    def SendMsg(
            self, 
            msg: str,
            who: str=None,
            clear: bool=True, 
            at: Union[str, List[str]]=None,
            exact: bool=False,
        ) -> WxResponse:
        """发送消息

        Args:
            msg (str): 消息内容
            who (str, optional): 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效**
            clear (bool, optional): 发送后是否清空编辑框.
            at (Union[str, List[str]], optional): @对象，不指定则不@任何人
            exact (bool, optional): 搜索who好友时是否精确匹配，默认False，**当子窗口时，该参数无效**

        Returns:
            WxResponse: 是否发送成功
        """
        return self.core.send_msg(msg, who, clear, at, exact)

    def SendFiles(
            self, 
            filepath, 
            who=None, 
            exact=False
        ) -> WxResponse:
        """向当前聊天窗口发送文件
        
        Args:
            filepath (str|list): 要复制文件的绝对路径  
            who (str): 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效**
            exact (bool, optional): 搜索who好友时是否精确匹配，默认False，**当子窗口时，该参数无效**
            
        Returns:
            WxResponse: 是否发送成功
        """
        return self.core.send_files(filepath, who, exact)
    
    def LoadMoreMessage(self, interval: float=0.3) -> WxResponse:
        """加载更多消息

        Args:
            interval (float, optional): 滚动间隔，单位秒，默认0.3
        """
        return self.core.load_more_message(interval)

    def GetAllMessage(self) -> List['Message']:
        """获取当前聊天窗口的所有消息
        
        Returns:
            List[Message]: 当前聊天窗口的所有消息
        """
        return self.core.get_msgs()
    
    def GetNewMessage(self) -> List['Message']:
        """获取当前聊天窗口的新消息

        Returns:
            List[Message]: 当前聊天窗口的新消息
        """
        if not hasattr(self, '_last_chat'):
            self._last_chat = self.ChatInfo().get('chat_name')
        if (_last_chat := self.ChatInfo().get('chat_name')) != self._last_chat:
            self._last_chat = _last_chat
            self.core.chatbox._update_used_msg_ids()
            return []
        return self.core.get_new_msgs()
    
    def GetGroupMembers(self) -> List[str]:
        """获取当前聊天群成员

        Returns:
            list: 当前聊天群成员列表
        """
        return self.core.get_group_members()
    
    def Close(self) -> None:
        """关闭微信窗口"""
        self.core.close()


class WeChat(Chat, Listener):
    """微信主窗口实例"""

    def __init__(
            self, 
            debug: bool=False,
            **kwargs
        ):
        hwnd = None
        if 'hwnd' in kwargs:
            hwnd = kwargs['hwnd']
        self.core = WeChatMainWnd(hwnd)
        self.nickname = self.core.nickname
        self.listen = {}
        if debug:
            wxlog.set_debug(True)
            wxlog.debug('Debug mode is on')
        self._listener_start()
        self.Show()

    def _get_listen_messages(self):
        try:
            sys.stdout.flush()
        except:
            pass
        temp_listen = self.listen.copy()
        for who in temp_listen:
            chat, callback = temp_listen.get(who, (None, None))
            try:
                if chat is None or not chat.core.exists():
                    wxlog.debug(f"窗口 {who} 已关闭，移除监听")
                    self.RemoveListenChat(who, close_window=False)
                    continue
            except:
                continue
            with self._lock:
                msgs = chat.GetNewMessage()
                for msg in msgs:
                    wxlog.debug(f"[{msg.attr} {msg.type}]获取到新消息：{who} - {msg.content}")
                    chat.Show()
                    self._safe_callback(callback, msg, chat)
    
    def GetSession(self) -> List['SessionElement']:
        """获取当前会话列表

        Returns:
            List[SessionElement]: 当前会话列表
        """
        return self.core.sessionbox.get_session()

    def ChatWith(
        self, 
        who: str, 
        exact: bool=False,
        force: bool=False,
        force_wait: Union[float, int] = 0.5
    ):
        """打开聊天窗口
        
        Args:
            who (str): 要聊天的对象
            exact (bool, optional): 搜索who好友时是否精确匹配，默认False
            force (bool, optional): 不论是否匹配到都强制切换，若启用则exact参数无效，默认False
                > 注：force原理为输入搜索关键字后，在等待`force_wait`秒后不判断结果直接回车，谨慎使用
            force_wait (Union[float, int], optional): 强制切换时等待时间，默认0.5秒
            
        """
        return self.core.switch_chat(who, exact, force, force_wait)
    

    def AddListenChat(
            self,
            nickname: str,
            callback: Callable[['Message', str], None],
        ) -> WxResponse:
        """添加监听聊天，将聊天窗口独立出去形成Chat对象子窗口，用于监听
        
        Args:
            nickname (str): 要监听的聊天对象
            callback (Callable[[Message, str], None]): 回调函数，参数为(Message对象, 聊天名称)
        """
        if nickname in self.listen:
            return WxResponse.failure('该聊天已监听')
        subwin = self.core.open_separate_window(nickname)
        if subwin is None:
            return WxResponse.failure('找不到聊天窗口')
        name = subwin.nickname
        chat = Chat(subwin)
        self.listen[name] = (chat, callback)
        return chat
    
    def StopListening(self, remove: bool = True) -> None:
        """停止监听"""
        while self._listener_thread.is_alive():
            self._listener_stop()
        if remove:
            listen = self.listen.copy()
            for who in listen:
                self.RemoveListenChat(who)

    def StartListening(self) -> None:
        if not self._listener_thread.is_alive():
            self._listener_start()


    def RemoveListenChat(
            self, 
            nickname: str,
            close_window: bool = True
        ) -> WxResponse:
        """移除监听聊天

        Args:
            nickname (str): 要移除的监听聊天对象
            close_window (bool, optional): 是否关闭聊天窗口. Defaults to True.

        Returns:
            WxResponse: 执行结果
        """
        if nickname not in self.listen:
            return WxResponse.failure('未找到监听对象')
        chat, _ = self.listen[nickname]
        if close_window:
            chat.Close()
        del self.listen[nickname]
        return WxResponse.success()
    
    def GetNextNewMessage(self, filter_mute=False) -> Dict[str, List['Message']]:
        """获取下一个新消息
        
        Args:
            filter_mute (bool, optional): 是否过滤掉免打扰消息. Defaults to False.

        Returns:
            Dict[str, List['Message']]: 消息列表
        """
        return self.core.get_next_new_message(filter_mute)

    def SwitchToChat(self) -> None:
        """切换到聊天页面"""
        self.core.navigation.chat_icon.Click()

    def SwitchToContact(self) -> None:
        """切换到联系人页面"""
        self.core.navigation.contact_icon.Click()

    def GetSubWindow(self, nickname: str) -> 'Chat':
        """获取子窗口实例
        
        Args:
            nickname (str): 要获取的子窗口的昵称
            
        Returns:
            Chat: 子窗口实例
        """
        if subwin := self.core.get_sub_wnd(nickname):
            return Chat(subwin)
        
    def GetAllSubWindow(self) -> List['Chat']:
        """获取所有子窗口实例
        
        Returns:
            List[Chat]: 所有子窗口实例
        """
        return [Chat(subwin) for subwin in self.core.get_all_sub_wnds()]
    
    def KeepRunning(self):
        """保持运行"""
        while not self._listener_stop_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                wxlog.debug(f'wxauto("{self.nickname}") shutdown')
                self.StopListening(True)
                break