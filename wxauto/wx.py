from .ui.main import (
    WeChatMainWnd,
    WeChatSubWnd,
    WeChatLoginWnd
)
from .ui.moment import MomentsWnd
from .ui.component import (
    NewFriendElement, 
    WeChatDialog
)
from .utils import GetAllWindows, uilock
from .param import (
    WxResponse, 
    WxParam, 
    PROJECT_NAME,
)
from wxauto.utils.tools import get_file_dir
from .logger import wxlog
from typing import (
    Union, 
    List,
    Dict,
    Literal,
    Callable,
    TYPE_CHECKING
)
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod
from pathlib import Path
import threading
import traceback
import time
import sys
import os

if TYPE_CHECKING:
    from wxauto.msgs.base import Message
    from wxauto.ui.sessionbox import SessionElement

class LoginWnd:
    def __init__(self, app_path=None, hwnd=None):
        self._api = WeChatLoginWnd(app_path=app_path, hwnd=hwnd)

    def exists(self, wait: int = 0):
        return self._api.exists(wait)
    
    def login(self, timeout: int = 10):
        return self._api.login(timeout=timeout)
    
    def get_qrcode(self, path=None):
        """获取登录二维码

        Args:
            path (str): 二维码图片的保存路径，默认为None，即本地目录下的wxauto_qrcode文件夹

        
        Returns:
            str: 二维码图片的保存路径
        """
        return self._api.get_qrcode(path=path)
    
    def reopen(self):
        """重新打开"""
        return self._api.reopen()
    
    def open(self):
        return self._api.open()
    
    def close(self):
        """关闭微信"""
        return self._api.close()

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
        self._excutor = ThreadPoolExecutor(max_workers=WxParam.LISTENER_EXCUTOR_WORKERS)
        if not hasattr(self, 'listen') or not self.listen:
            self.listen = {}
        while not self._listener_stop_event.is_set():
            try:
                self._get_listen_messages()
            except KeyboardInterrupt:
                wxlog.debug("监听消息终止")
                self._listener_stop()
                break
            except:
                wxlog.debug(f'监听消息失败：{traceback.format_exc()}')
            time.sleep(WxParam.LISTEN_INTERVAL)

    def _safe_callback(
            self, 
            callback: Callable[['Message', 'Chat'], None], 
            msg: 'Message', 
            chat: 'Chat'
        ):
        try:
            callback(msg, chat)
        except Exception as e:
            wxlog.debug(f"监听消息回调发生错误：{traceback.format_exc()}")

    def _listener_stop(self):
        self._listener_is_listening = False
        self._listener_stop_event.set()
        self._listener_thread.join()
        self._excutor.shutdown(wait=True)

    @abstractmethod
    def _get_listen_messages(self):
        ...

class Chat:
    """微信聊天窗口实例"""

    def __init__(self, core: WeChatSubWnd=None):
        self._api = core
        self.who = self._api.nickname

    def __repr__(self):
        return f'<{PROJECT_NAME} - {self.__class__.__name__} object("{self._api.nickname}")>'
    
    def __str__(self):
        if hasattr(self, 'who'):
            return self.who
        else:
            return self.nickname
    
    def __add__(self, other):
        if hasattr(self, 'who'):
            return self.who + other
        else:
            return self.nickname + other

    def __radd__(self, other):
        if hasattr(self, 'who'):
            return other + self.who
        else:
            return other + self.nickname
        
    @property
    def chat_type(self):
        return self._api._chat_api.get_info().get('chat_type', None)
        
    def ScreenShot(self, dir_path: str = None) -> Path:
        """获取窗口截图"""
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        filename = f"wxauto_screenshot_{time.strftime('%Y%m%d%H%M%S')}.png"
        filepath = get_file_dir(dir_path) / filename
        self._api.control.ScreenShot(filepath)
        return Path(filepath)
    
    def GetDialog(self, wait=3) -> WeChatDialog:
        """获取当前窗口的对话框
        
        Args:
            wait (int): 隐性等待时间. 默认3秒"""
        return self._api.get_dialog(wait)
    
    def Show(self):
        """显示窗口"""
        self._api._show()

    def ChatInfo(self) -> Dict[str, str]:
        """获取聊天窗口信息
        
        Returns:
            dict: 聊天窗口信息
        """
        return self._api._chat_api.get_info()
    
    @uilock
    def AtAll(
        self, 
        msg: str,
        who: str=None,
        exact: bool=False,
    ) -> WxResponse:
        """@所有人
        
        Args:
            msg (str): 发送的消息
            who (str, optional): 发送给谁. Defaults to None.
            exact (bool, optional): 是否精确匹配. Defaults to False.

        Returns:
            WxResponse: 发送结果
        """
        return self._api.at_all(msg, who, exact)

    
    @uilock
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
        return self._api.send_msg(msg, who, clear, at, exact)
    
    @uilock
    def SendTypingText(
            self, 
            msg, 
            who=None, 
            clear=True, 
            exact=False
        ) -> WxResponse:
        """发送文本消息（打字机模式），支持换行及@功能

        Args:
            msg (str): 要发送的文本消息
            who (str): 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效**
            clear (bool, optional): 是否清除原本的内容， 默认True
            exact (bool, optional): 搜索who好友时是否精确匹配，默认False，**当子窗口时，该参数无效**

        Returns:
            WxResponse: 是否发送成功

        Example:
            >>> wx = WeChat()
            >>> wx.SendTypingText('你好', who='张三')

            换行及@功能：
            >>> wx.SendTypingText('各位下午好\n{@张三}负责xxx\n{@李四}负责xxxx', who='工作群')
        """
        return self._api.send_msg(msg, who, clear, exact=exact, typing=True)
    
    @uilock
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
        return self._api.send_files(filepath, who, exact)
    
    @uilock
    def SendEmotion(
            self, 
            emotion_index, 
            who=None, 
            exact=False
        ) -> WxResponse:
        """发送自定义表情
        
        Args:
            emotion_index (str): 表情索引，从0开始
            who (str): 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效**
            exact (bool, optional): 搜索who好友时是否精确匹配，默认False，**当子窗口时，该参数无效**

        Returns:
            WxResponse: 是否发送成功
        """
        return self._api.send_emotion(emotion_index, who, exact)
    
    @uilock
    def MergeForward(
        self,
        targets: Union[List[str], str],
    ) -> WxResponse:
        """合并转发

        Args:
            targets (Union[List[str], str]): 合并转发对象

        Returns:
            WxResponse: 是否发送成功
        """
        return self._api.merge_and_forward(targets)
    
    def LoadMoreMessage(self, interval: float=0.3) -> WxResponse:
        """加载更多消息

        Args:
            interval (float, optional): 滚动间隔，单位秒，默认0.3
        """
        return self._api.load_more_message(interval)

    def GetAllMessage(self) -> List['Message']:
        """获取当前聊天窗口的所有消息
        
        Returns:
            List[Message]: 当前聊天窗口的所有消息
        """
        return self._api.get_msgs()
    
    def GetNewMessage(self) -> List['Message']:
        """获取当前聊天窗口的新消息

        Returns:
            List[Message]: 当前聊天窗口的新消息
        """
        if not hasattr(self, '_last_chat'):
            self._last_chat = self.ChatInfo().get('chat_name')
        if (_last_chat := self.ChatInfo().get('chat_name')) != self._last_chat:
            self._last_chat = _last_chat
            self._api._chat_api._update_used_msg_ids()
            return []
        return self._api.get_new_msgs()
    
    def GetMessageById(self, msg_id: str) -> 'Message':
        """根据消息id获取消息

        Args:
            msg_id (str): 消息id

        Returns:
            Message: 消息对象
        """
        return self._api.get_msg_by_id(msg_id)

    def AddGroupMembers(
            self, 
            group: str=None,
            members: Union[str, List[str]]=None,
            reason: str = None
        ) -> WxResponse:
        """添加群成员
        
        Args:
            group (str): 群名
            members (Union[str, List[str]]): 成员名或成员名列表
            reason (str, optional): 申请理由，当群主开启验证时需要，不填写则取消申请

        Returns:
            WxResponse: 是否添加成功
        """
        return self._api.add_group_members(group, True, members, reason)
    
    def RemoveGroupMembers(
            self,
            group: str=None,
            members: Union[str, List[str]]=None
        ) -> WxResponse:
        """移除群成员

        Args:
            group (str): 群名
            members (Union[str, List[str]]): 成员名或成员名列表

        Returns:
            WxResponse: 是否移除成功
        """
        return self._api.remove_group_members(group, True, members)
    
    def GetGroupMembers(self) -> List[str]:
        """获取当前聊天群成员

        Returns:
            list: 当前聊天群成员列表
        """
        return self._api.get_group_members()
    
    def AddFriendFromGroup(
            self,
            index: int,
            who: str=None,
            addmsg: str=None,
            remark: str=None,
            tags: List[str]=None,
            permission: Literal['朋友圈', '仅聊天']='朋友圈',
            exact: bool=False
        ):
        """从群聊中添加好友

        Args:
            index (int): 群聊索引
            who (str, optional): 添加的好友名
            addmsg (str, optional): 申请理由，当群主开启验证时需要，不填写则取消申请
            remark (str, optional): 添加好友后的备注名
            tags (list, optional): 添加好友后的标签
            permission (Literal['朋友圈', '仅聊天'], optional): 添加好友后的权限
            exact (bool, optional): 是否精确匹配群聊名

        Returns:
            WxResponse: 是否添加成功
        """
        return self._api.add_friend_from_group(index, who, addmsg, remark, tags, permission, exact)
    
    def GetGroupMemberInfo(self, index: int=0):
        """获取群成员信息

        Args:
            index (int): 群成员索引

        Returns:
            dict: 群成员信息
        """
        return self._api.get_group_member_info(index)

    def ManageFriend(
            self, 
            remark: str=None, 
            tags: List[str]=None
        ) -> WxResponse:
        """修改备注名或标签
        
        Args:
            remark (str, optional): 备注名
            tags (list, optional): 标签列表

        Returns:
            WxResponse: 是否成功修改备注名或标签
        """
        return self._api.manage_friend(remark=remark, tags=tags)

    def ManageGroup(
            self, 
            name: str=None, 
            remark: str=None, 
            myname: str=None, 
            notice: str=None, 
            quit: bool=False
        ) -> WxResponse:
        """管理当前聊天页面的群聊
        
        Args:
            name (str, optional): 修改群名称
            remark (str, optional): 备注名
            myname (str, optional): 我的群昵称
            notice (str, optional): 群公告
            quit (bool, optional): 是否退出群，当该项为True时，其他参数无效
        
        Returns:
            WxResponse: 修改结果
        """
        return self._api.manage_group(
            name=name, 
            remark=remark, 
            myname=myname, 
            notice=notice, 
            quit=quit
        )
    
    def GetTopMessage(self):
        """获取置顶消息"""
        return self._api.get_top_msgs()
    
    def Close(self) -> None:
        """关闭微信窗口"""
        self._api.close()


class WeChat(Chat, Listener):
    """微信主窗口实例"""

    def __init__(
            self, 
            nickname: str=None, 
            debug: bool=False,
            **kwargs
        ):
        hwnd = None
        if 'hwnd' in kwargs:
            hwnd = kwargs['hwnd']
        self._api = WeChatMainWnd(nickname, hwnd)
        self.NavigationBox = self._api._navigation_api
        self.SessionBox = self._api._session_api
        self.ChatBox = self._api._chat_api
        self.nickname = self._api.nickname
        self.listen = {}
        if debug:
            wxlog.set_debug(True)
            wxlog.debug('Debug mode is on')
        self._listener_start()

    def _get_listen_messages(self):
        try:
            sys.stdout.flush()
        except:
            pass
        temp_listen = self.listen.copy()
        for who in temp_listen:
            chat, callback = temp_listen.get(who, (None, None))
            try:
                if chat is None or not chat._api.exists():
                    self.RemoveListenChat(who)
                    continue
            except:
                continue
            with self._lock:
                msgs = chat.GetNewMessage()
                for msg in msgs:
                    wxlog.debug(f"[{msg.attr} {msg.type}]获取到新消息：{who} - {msg.content}")
                    self._excutor.submit(self._safe_callback, callback, msg, chat)

    def KeepRunning(self):
        """保持运行"""
        while not self._listener_stop_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                wxlog.debug(f'wxauto("{self.nickname}") shutdown')
                self.StopListening(True)
                break

    def IsOnline(self) -> bool:
        """判断是否在线"""
        return self._api.is_online()

    def GetMyInfo(self) -> Dict[str, str]:
        """获取我的信息"""
        return self._api.get_my_info()
    
    def GetSession(self) -> List['SessionElement']:
        """获取当前会话列表

        Returns:
            List[SessionElement]: 当前会话列表
        """
        return self._api._session_api.get_session()
    
    def SendUrlCard(
            self, 
            url: str, 
            friends: Union[str, List[str]], 
            message: str=None,
            timeout: int=10
        ) -> WxResponse:
        """发送链接卡片

        Args:
            url (str): 链接地址
            friends (Union[str, List[str]], optional): 发送对象
            message (str): 附加消息，默认无
            timeout (int, optional): 等待时间，默认10秒

        Returns:
            WxResponse: 发送结果
        """
        return self._api.send_card(url, friends, message, timeout)
    
    @uilock
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
        return self._api.switch_chat(who, exact, force, force_wait)
    
    def GetSubWindow(self, nickname: str) -> 'Chat':
        """获取子窗口实例
        
        Args:
            nickname (str): 要获取的子窗口的昵称
            
        Returns:
            Chat: 子窗口实例
        """
        if subwin := self._api.get_sub_wnd(nickname):
            return Chat(subwin)
        
    def GetAllSubWindow(self) -> List['Chat']:
        """获取所有子窗口实例
        
        Returns:
            List[Chat]: 所有子窗口实例
        """
        return [Chat(subwin) for subwin in self._api.get_all_sub_wnds()]
    
    @uilock
    def AddListenChat(
            self,
            nickname: str,
            callback: Callable[['Message', Chat], None],
        ) -> WxResponse:
        """添加监听聊天，将聊天窗口独立出去形成Chat对象子窗口，用于监听
        
        Args:
            nickname (str): 要监听的聊天对象
            callback (Callable[['Message', Chat], None]): 回调函数，参数为(Message对象, Chat对象)，返回值为None
        """
        if nickname in self.listen:
            return WxResponse.failure('该聊天已监听')
        subwin = self._api.open_separate_window(nickname)
        if subwin is None:
            return WxResponse.failure('找不到聊天窗口')
        name = subwin.nickname
        chat = Chat(subwin)
        self.listen[name] = (chat, callback)
        return chat
    
    def StopListening(self, remove: bool = True) -> None:
        """停止监听
        
        Args:
            remove (bool, optional): 是否移除监听对象. Defaults to True.
        """
        while self._listener_thread.is_alive():
            self._listener_stop()
        if remove:
            listen = self.listen.copy()
            for who in listen:
                self.RemoveListenChat(who)

    def StartListening(self) -> None:
        if not self._listener_thread.is_alive():
            self._listener_start()

    @uilock
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
        
    def Moments(
            self, 
            timeout: int = 3
        ) -> 'MomentsWnd':
        """进入朋友圈"""
        return self._api.open_moments_window(timeout=timeout)
    
    @uilock
    def GetNextNewMessage(self, filter_mute=False) -> Dict[str, List['Message']]:
        """获取下一个新消息
        
        Args:
            filter_mute (bool, optional): 是否过滤掉免打扰消息. Defaults to False.

        Returns:
            Dict[str, List['Message']]: 消息列表
        """
        return self._api.get_next_new_message(filter_mute)

    def GetNewFriends(
            self,
            acceptable: bool = True
        ) -> List['NewFriendElement']:
        """获取新的好友申请列表

        Args:
            acceptable (bool, optional): 是否过滤掉已接受的好友申请
        
        Returns:
            List['NewFriendElement']: 新的好友申请列表，元素为NewFriendElement对象，可直接调用Accept方法

        Example:
            >>> wx = WeChat()
            >>> newfriends = wx.GetNewFriends(acceptable=True)
            >>> tags = ['标签1', '标签2']
            >>> for friend in newfriends:
            ...     remark = f'备注{friend.name}'
            ...     friend.Accept(remark=remark, tags=tags)  # 接受好友请求，并设置备注和标签
        """
        return self._api.get_new_friend_request(acceptable)

    def AddNewFriend(
            self, 
            keywords: str, 
            addmsg: str = None, 
            remark: str = None, 
            tags: List[str] = None, 
            permission: Literal['朋友圈', '仅聊天'] = '朋友圈', 
            timeout: int = 5
        ) -> WxResponse:
        """添加新的好友

        Args:
            keywords (str): 搜索关键词，可以是昵称、微信号、手机号等
            addmsg (str, optional): 添加好友时的附加消息，默认为None
            remark (str, optional): 添加好友后的备注，默认为None
            tags (list, optional): 添加好友后的标签，默认为None
            permission (Literal['朋友圈', '仅聊天'], optional): 添加好友后的权限，默认为'朋友圈'
            timeout (int, optional): 搜索好友的超时时间，默认为5秒

        Returns:
            WxResponse: 添加好友的结果
        """
        return self._api.add_new_friend(keywords, addmsg, remark, tags, permission, timeout)
    
    def GetAllRecentGroups(
            self,
            speed: int = 1,
            interval: float = 0.05
        ) -> (Union[WxResponse, List[str]]):
        """获取所有最近群聊
        
        Args:
            speed (int, optional): 获取速度，默认为1
            interval (float, optional): 获取间隔，默认为0.05秒

        Returns:
            WxResponse | List[str]: 失败时返回WxResponse，成功时返回所有最近群聊列表
        """
        return self._api.get_recent_groups(speed, interval)
    
    def GetContactGroups(
            self,
            speed: int = 1,
            interval: float = 0.1
    ) -> List[str]:
        """获取通讯录中的所有群聊
        
        Args:
            speed (int, optional): 获取速度，默认为1
            interval (float, optional): 滚动间隔，默认为0.1秒

        Returns:
            List[str]: 所有群聊列表
        """
        return self._api.get_contact_groups(speed, interval)
    
    def GetFriendDetails(
            self, 
            n=None, 
            tag=None, 
            timeout=0xFFFFF,
            save_head_image=False,
            save_head_wait=0
        ) -> List[dict]:
        """获取好友详情

        Args:
            n (int, optional): 获取前n个好友详情信息, 默认为None，获取所有好友详情信息
            tag (str, optional): 从指定标签开始获取好友详情信息，如'A'，默认为None即从第一个好友开始获取
            timeout (int, optional): 获取超时时间（秒），超过该时间则直接返回结果

        Returns:
            List[dict]: 所有好友详情信息
            
        注：1. 该方法运行时间较长，约0.5~1秒一个好友的速度，好友多的话可将n设置为一个较小的值，先测试一下
            2. 如果遇到企业微信的好友且为已离职状态，可能导致微信卡死，需重启（此为微信客户端BUG）
            3. 该方法未经过大量测试，可能存在未知问题，如有问题请微信群内反馈
        """
        return self._api.get_friends_details(n, tag, timeout, save_head_image, save_head_wait)

    def SwitchToChat(self) -> None:
        """切换到聊天页面"""
        self._api._navigation_api.chat_icon.Click()

    def SwitchToContact(self) -> None:
        """切换到联系人页面"""
        self._api._navigation_api.contact_icon.Click()

    def ShutDown(self):
        os.system(f'taskkill /f /pid {self._api.pid}')


def get_wx_clients() -> List[WeChat]:
    """获取当前所有微信客户端
    
    Returns:
        List[WeChat]: 当前所有微信客户端
    """
    win32wins = GetAllWindows()
    return [
        WeChat(hwnd=win[0])
        for win in win32wins
        if win[1] == WeChatMainWnd._ui_cls_name
    ]

def get_wx_logins() -> List[LoginWnd]:
    win32wins = GetAllWindows()
    return [
        LoginWnd(hwnd=win[0])
        for win in win32wins
        if win[1] == WeChatLoginWnd._ui_cls_name
    ]