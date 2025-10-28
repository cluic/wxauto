from .base import (
    BaseUIWnd,
    BaseUISubWnd
)
from wxauto import uia
from wxauto.param import WxResponse
from .chatbox import ChatBox
from .sessionbox import SessionBox
from .navigationbox import NavigationBox
from .moment import MomentsWnd
from wxauto.param import (
    WxParam, 
    WxResponse, 
    PROJECT_NAME
)
from wxauto.ui.component import (
    NetErrInfoTipsBarWnd,
    NewFriendElement,
    ContactManagerWindow,
    get_wx_browser,
    ProfileWnd,
    WeChatDialog
)
from wxauto.languages import *
from wxauto.utils import (
    GetAllWindows,
    FindWindow,
    FindTopLevelControl,
    get_windows_by_pid
)
from wxauto.utils.tools import now_time
from wxauto.exceptions import *
from wxauto.logger import wxlog
from typing import (
    Union,
    List,
    Literal
)
import time
import winreg
import random
import os
import sys

class WeChatSubWnd(BaseUISubWnd):
    _ui_cls_name: str = 'ChatWnd'
    _chat_api: ChatBox = None
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
            self._chat_api = ChatBox(chatbox_control, self)
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
        return self._chat_api
    
    def _get_windows(self):
        wins = []
        for hwnd in get_windows_by_pid(self.pid):
            try:
                wins.append(uia.ControlFromHandle(hwnd))
            except:
                pass
        ignore_cls = ['basepopupshadow', 'popupshadow']
        return [win for win in wins if win.ClassName not in ignore_cls]
    
    def get_dialog(self, wait=3):
        if dialog := WeChatDialog(self, wait):
            return dialog
    
    def is_online(self):
        return self.control.Exists(0)
    
    def chat_info(self):
        return self._chat_api.get_info()
    
    def load_more_message(self, interval=0.3) -> WxResponse:
        return self._chat_api.load_more(interval)
    
    def at_all(
            self, 
            msg: str, 
            who: str=None,
            exact: bool=False,
        ) -> WxResponse:
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.at_all(msg)
    
    def send_msg(
            self, 
            msg: str,
            who: str=None,
            clear: bool=True, 
            at: Union[str, List[str]]=None,
            exact: bool=False,
            typing: bool=False
        ) -> WxResponse:
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.send_msg(msg, clear, at, typing)
    
    def send_files(
            self, 
            filepath, 
            who=None, 
            exact=False
        ) -> WxResponse:
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.send_file(filepath)
    
    def send_emotion(
            self,
            index: int,
            who: str=None,
            exact: bool=False
        ) -> WxResponse:
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.send_emotion(index)

    def get_group_members(
            self,
            who: str=None,
            exact: bool=False
        ) -> List[str]:
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return []
        return chatbox.get_group_members()
    
    def add_friend_from_group(
            self,
            index: int,
            who: str=None,
            addmsg: str=None,
            remark: str=None,
            tags: List[str]=None,
            permission: Literal['朋友圈', '仅聊天']='朋友圈',
            exact: bool=False
        ):
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.add_friend_from_group(
            index, addmsg, remark, tags, permission
        )
    
    def get_group_member_info(
            self, 
            index: int,
            who: str=None,
            exact: bool=False
        ):
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.get_group_member_info(index)
    
    def get_msgs(self):
        chatbox = self._get_chatbox()
        if chatbox:
            return chatbox.get_msgs()
        return []
    
    def get_new_msgs(self):
        if chatbox := self._get_chatbox():
            return chatbox.get_new_msgs()
        wxlog.debug('未找到聊天框')
        return []
    
    def get_msg_by_id(self, msg_id: str):
        return self._get_chatbox().get_msg_by_id(msg_id)
    
    def add_group_members(
            self,
            who: str=None,
            exact: bool=False,
            members: Union[str, List[str]]=None,
            reason: str=None
        ):
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.add_group_members(members, reason)
    
    def remove_group_members(
            self,
            who: str=None,
            exact: bool=False,
            members: Union[str, List[str]]=None,
    ):
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.remove_group_members(members)
    
    def manage_friend(
            self,
            who: str=None,
            exact: bool=False,
            remark: str=None,
            tags: List[str]=None,
    ) -> WxResponse:
        if all([not remark, not tags]):
            return WxResponse.failure("请至少输入一个参数")
        if isinstance(tags, str):
            tags = [tags]
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.manage_friend(remark, tags)
    
    def manage_group(
        self,
        who: str=None,
        exact: bool=False,
        name: str = None,
        remark: str = None,
        myname: str = None,
        notice: str = None,
        quit: bool = False,
    ) -> WxResponse:
        chatbox = self._get_chatbox(who, exact)
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口：{who}")
        return chatbox.manage_group(name, remark, myname, notice, quit)
    
    def merge_and_forward(
        self,
        targets: Union[List[str], str],
    ) -> WxResponse:
        chatbox = self._get_chatbox()
        if chatbox is None:
            return WxResponse.failure(f"未找到聊天窗口")
        return chatbox.merge_and_forward(targets)
    
    def get_top_msgs(self):
        return self._chat_api.get_top_msgs()


class WeChatMainWnd(WeChatSubWnd):
    _ui_cls_name: str = 'WeChatMainWndForPC'
    _ui_name: str = '微信'

    def __init__(self, nickname: str = None, hwnd: int = None):
        self.root = self
        self.parent = self
        if hwnd:
            self._setup_ui(hwnd)
        elif nickname:
            wxs = [i for i in GetAllWindows() if i[1] == self._ui_cls_name]
            if len(wxs) == 0:
                raise Exception('未找到已登录的微信主窗口')
            for index, (hwnd, clsname, winname) in enumerate(wxs):
                self._setup_ui(hwnd)
                if self.nickname == nickname:
                    break
                elif index+1 == len(wxs):
                    raise Exception(f'未找到微信窗口：{nickname}')
        else:
            hwnd = FindWindow(classname=self._ui_cls_name)
            if not hwnd:
                raise Exception(f'未找到微信窗口：{nickname}，如您是4.0微信客户端，请在官网下载3.9客户端使用本项目：https://pc.weixin.qq.com')
            self._setup_ui(hwnd)
        # if NetErrInfoTipsBarWnd(self):
        #     raise NetWorkError('微信无法连接到网络')
        
        print(f'初始化成功，获取到已登录窗口：{self.nickname}')

    def _setup_ui(self, hwnd: int):
        try:
            self.HWND = hwnd
            self.control = uia.ControlFromHandle(hwnd)
            MainControl1 = [i for i in self.control.GetChildren() if not i.ClassName][0]
            MainControl2 = MainControl1.GetFirstChildControl()
            navigation_control, sessionbox_control, chatbox_control  = MainControl2.GetChildren()
            self._navigation_api = NavigationBox(navigation_control, self)
            self._session_api = SessionBox(sessionbox_control, self)
            self._chat_api = ChatBox(chatbox_control, self)
            self.nickname = self._navigation_api.my_icon.Name
            self.NavigationBox = self._navigation_api.control
            self.SessionBox = self._session_api.control
            self.ChatBox = self._chat_api.control
        except Exception as e:
            debug_file = os.path.join(os.getcwd(), 'wxauto_DEBUG_INIT.txt')
            with open(debug_file, 'w', encoding='utf8') as f:
                f.write(self.control.tree_text)
            raise Exception(f'WeChat实例初始化失败，请将该文件发给管理员反馈：{debug_file}')

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
                switch_result = self._session_api.switch_chat(keywords=nickname, exact=exact)
                if not switch_result:
                    return None
            if self._chat_api.msgbox.Exists(0.5):
                return self._chat_api
            
    def get_my_info(self):
        return self._navigation_api.get_my_info()
            
    def switch_chat(
            self, 
            keywords: str, 
            exact: bool = False,
            force: bool = False,
            force_wait: Union[float, int] = 0.5
        ):
        return self._session_api.switch_chat(keywords, exact, force, force_wait)
        
    def get_all_sub_wnds(self):
        sub_wxs = [i for i in GetAllWindows() if i[1] == WeChatSubWnd._ui_cls_name]
        return [
            sub_win 
            for i in sub_wxs 
            if (sub_win:= WeChatSubWnd(i[0], self)).pid == self.pid
        ]
    
    def get_sub_wnd(self, who: str, timeout: int=0):
        if hwnd := FindWindow(classname=WeChatSubWnd._ui_cls_name, name=who, timeout=timeout):
            if (sub_win := WeChatSubWnd(hwnd, self)).pid == self.pid:
                return sub_win
        
    def open_separate_window(self, keywords: str) -> WeChatSubWnd:
        if subwin := self.get_sub_wnd(keywords):
            wxlog.debug(f"{keywords} 获取到已存在的子窗口: {subwin}")
            return subwin
        if nickname := self._session_api.switch_chat(keywords):
            wxlog.debug(f"{keywords} 切换到聊天窗口: {nickname}")
            if subwin := self.get_sub_wnd(nickname):
                wxlog.debug(f"{nickname} 获取到已存在的子窗口: {subwin}")
                return subwin
            else:
                keywords = nickname
        if result := self._session_api.open_separate_window(keywords):
            find_nickname = result['data'].get('nickname', keywords)
            return WeChatSubWnd(find_nickname, self)
        
    def open_moments_window(self, timeout: int=3) -> MomentsWnd:
        return self._navigation_api.open_moments(timeout=timeout)
    
    def get_new_friend_request(self, acceptable: bool=False) -> List['NewFriendElement']:
        wait = False
        self._navigation_api.contact_icon.Click()
        cti = self._session_api.control.ListItemControl(Name=self._lang("新的朋友"))
        while not cti.Exists(0):
            wait = True
            self.SessionBox.WheelUp(wheelTimes=3)
        # if wait:
        #     time.sleep(1)
        # self.SessionBox.WheelUp(wheelTimes=3)
        cti.Click()
        new_friend_list = self._chat_api.control.ListControl(Name=self._lang('新的朋友'))
        if not new_friend_list.Exists(0):
            close_icon = self._chat_api.control.ButtonControl(Name='')
            if close_icon.Exists(0):
                close_icon.Click()
            else:
                wxlog.debug('无法获取到新的朋友列表，请将当前页面截图反馈给开发者')

        NewFriendsList = [NewFriendElement(i, self) for i in new_friend_list.GetChildren()]
        if acceptable:
            NewFriendsList = [i for i in NewFriendsList if i.acceptable]
        return NewFriendsList
    
    def _get_next_new_message(self, filter_mute: bool=False):
        def get_new_message(session):
            last_content = session.content
            new_count = session.new_count
            chat_name = session.name
            session.click()
            return self._chat_api.get_next_new_msgs(new_count, last_content)
        
        def get_new_session(filter_mute):
            sessions = self._session_api.get_session()
            if sessions[0].name == self._lang('折叠的群聊'):
                self._navigation_api.chat_icon.DoubleClick()
                sessions = self._session_api.get_session()
            new_sessions = [
                i for i in sessions 
                if i.isnew 
                and i.name != self._lang('折叠的群聊')
            ]
            if filter_mute:
                new_sessions = [i for i in new_sessions if i.ismute == False]
            return new_sessions

        if new_msgs := self._chat_api.get_new_msgs():
            wxlog.debug("获取当前页面新消息")
            return new_msgs
        elif new_sessions := get_new_session(filter_mute):
            wxlog.debug("当前会话列表获取新消息")
            return get_new_message(new_sessions[0])
        else:
            self._session_api.go_top()
            if new_sessions := get_new_session(filter_mute):
                wxlog.debug("当前会话列表获取新消息")
                return get_new_message(new_sessions[0])
            else:
                self._navigation_api.chat_icon.DoubleClick()
            if new_sessions := get_new_session(filter_mute):
                wxlog.debug("翻页会话列表获取新消息")
                return get_new_message(new_sessions[0])
            else:
                wxlog.debug("没有新消息")
                return []

    def get_next_new_message(self, filter_mute: bool=False):
        if not (new_msgs := self.get_new_msgs()):
            if filter_mute and not self._navigation_api.has_new_message():
                wxlog.debug("没有未静音的新消息")
                return {}
            new_msgs = self._get_next_new_message(filter_mute)
        if new_msgs:
            chat_info = self._chat_api.get_info()
            return {
                'chat_name': chat_info['chat_name'],
                'chat_type': chat_info['chat_type'],
                'msg': new_msgs
            }
        else:
            wxlog.debug("未获取到下一条新消息")
            return {}
        
    def send_card(
            self,
            url: str,
            friends: str=None,
            message: str=None,
            timeout: int=10
        ) -> WxResponse:
        if not friends:
            return WxResponse.failure('请指定发送好友')
        if not self._navigation_api.browser_icon.Exists(0):
            return WxResponse.failure('请先在手机端打开`搜一搜`功能')
        # self._navigation_api.browser_icon.Click()
        browser = get_wx_browser(self._navigation_api.browser_icon.Click)
        return browser.send_card(url, friends, message, timeout)

    def add_new_friend(
            self,
            keyword: str,
            addmsg: str=None,
            remark: str=None,
            tags: str=None,
            permission: Literal['朋友圈', '仅聊天'] = '朋友圈', 
            timeout: int=10
    ):
        try:
            self._navigation_api.contact_icon.Click()
            self.SessionBox.ButtonControl(Name=self._lang('添加朋友')).Click()
            edit = self.SessionBox.EditControl()
            edit.Click()
            edit.Input(keyword)
            search_result = self.SessionBox.TextControl(Name=self._lang('搜索结果')+keyword)
            if search_result.Exists(2):
                search_result.Click(move=True, simulateMove=False)
            
            t0 = time.time()
            while True:
                if time.time() - t0 > timeout:
                    return WxResponse.failure('搜索超时')
                if profile_wnd := ProfileWnd(self):
                    return profile_wnd.add_friend(addmsg, remark, tags, permission)
                elif self.SessionBox.ListItemControl(Name=self._lang("找不到相关账号或内容")).Exists(0):
                    return WxResponse.failure('找不到相关账号或内容')
                elif self.SessionBox.ListItemControl(Name="无法找到该用户，请检查你填写的账号是否正确。").Exists(0):
                    return WxResponse.failure('无法找到该用户，请检查你填写的账号是否正确。')
                elif self.control.PaneControl(ClassName='RectToastWnd', searchDepth=1).Exists(0):
                    return WxResponse.success('对方未设置请求确认，已添加成功')
                elif not self.SessionBox.ListControl().GetChildren()[0].Name.startswith(self._lang('搜索结果')):
                    msg = self.SessionBox.ListControl().GetChildren()[0].TextControl().Name
                    wxlog.debug(f"意外情况添加失败：{msg}")
                    return WxResponse.failure(f"意外情况添加失败：{msg}")
        finally:
            cancel_button = self.SessionBox.ButtonControl(Name='取消')
            if cancel_button.Exists(0):
                cancel_button.Click()

    def switch_to_chat_page(self):
        t0 = time.time()
        while not self.SessionBox.ButtonControl(Name=self._lang('发起群聊'),searchDepth=3).Exists(0):
            if time.time() - t0 > 5:
                wxlog.error("切换到聊天页面超时")
                break
            self._navigation_api.switch_to_chat_page()

    def switch_to_contact_page(self):
        t0 = time.time()
        while not self.SessionBox.ButtonControl(Name=self._lang('添加朋友'),searchDepth=3).Exists(0):
            if time.time() - t0 > 5:
                wxlog.error("切换到聊天页面超时")
                break
            self._navigation_api.switch_to_contact_page()

    def get_recent_groups(
            self,
            speed: int = 1,
            interval: float = 0.05
        ) -> Union[WxResponse, List[str]]:
        self.switch_to_contact_page()
        t0 = time.time()
        # 打开联系人窗口
        while True:
            if time.time() - t0 > 5:
                wxlog.error("打开联系人管理窗口超时")
                return WxResponse.failure("打开联系人管理窗口超时")
            self._session_api.open_contact_manager()
            try:
                cmw = ContactManagerWindow(self)
                break
            except WxautoUINotFoundError:
                wxlog.error("未找到联系人管理窗口")
                time.sleep(0.3)
                continue
        recent_groups = cmw.get_all_recent_groups(speed, interval)
        cmw.close()
        self.switch_to_chat_page()
        return recent_groups
    
    def _goto_friends_tag(self, specific='A'):
        wxlog.debug(f"切换到好友标签页，指定标签为{specific}")
        def find_letter_tag(self):
            items = self.SessionBox.ListControl().GetChildren()
            tags = []
            for index, item in enumerate(items[:-1]):
                tag_control = item.TextControl(RegexName='^[A-Z]$')
                if tag_control.Exists(0):
                    tags.append((items[index], items[index+1]))
            for tag in tags:
                if tag[0].TextControl().Name.upper() == specific.upper():
                    return tag
            if tags:
                return tags[0]
                
        now_letter = '0'
        action = []
        while True:
            if len(action) >= 6 and action[-6:] in ([0, 1] * 3, [1, 0] * 3):
                wxlog.debug('检测到上下滚动切换，退出')
                return False
            items = find_letter_tag(self)
            if items is not None:
                item, item1 = items
                now_letter = item.TextControl().Name
                if specific.upper() == now_letter.upper():
                    uia.RollIntoView(self.SessionBox.ListControl(), item1)
                    item1.Click()
                    wxlog.debug('找到指定字母，退出')
                    return True
            if specific.upper() < now_letter.upper():
                self.SessionBox.WheelUp(wheelTimes=3)
                time.sleep(0.001)
                action.append(0)
                continue
            else:
                self.SessionBox.WheelDown(wheelTimes=3)
                time.sleep(0.001)
                action.append(1)
                continue

    def _get_friend_details(self, save_head_image=False, save_head_wait=0):
        params = ['昵称：', '微信号：', '地区：', '电话', '标签', '共同群聊', '个性签名', '来源', '朋友权限', '描述', '实名', '企业']
        info = {}
        if save_head_image:
            time.sleep(save_head_wait)
            save_dir = os.path.join(WxParam.DEFAULT_SAVE_PATH,  '头像')
            if not os.path.exists(save_dir): os.makedirs(save_dir)
            save_path = os.path.join(save_dir, time.strftime('%Y%m%d%H%M%S')+str(random.randint(1000, 9999))+'.png')
            headimg = self.ChatBox.ButtonControl().ScreenShot(save_path)
            info['头像'] = headimg
        controls = self.ChatBox.FindAll()
        for _, i in enumerate(controls):
            rect = i.BoundingRectangle
            text = i.Name
            if i.ControlTypeName == 'ButtonControl' and '昵称' not in info and text:
                info['昵称'] = text
            if text in params or (rect.width() == 57 and rect.height() == 20):
                if text == '昵称：':
                    info['备注'] = info['昵称']
                    info['昵称'] = controls[_+1].Name
                else:
                    info[text.replace('：', '')] = controls[_+1].Name
        wxlog.debug(f'获取到好友详情：{info}')
        return info
    
    def _next_tag(self):
        wxlog.debug('滚动至下一个标签')
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'
        next_click = False
        list_control = self.SessionBox.ListControl()
        while True:
            for ele, d in list_control.Walk():
                if next_click:
                    ele.Click()
                    next_click = False
                    wxlog.debug(f'切换至该标签第一个好友：{ele.Name}')
                    return next_click
                if ele.ControlTypeName == 'TextControl' and d==3 and ele.Name in letters:
                    next_click = ele.Name
            self._session_api.roll_down()
            next_click = False

    
    def get_friends_details(
            self, 
            n=None, 
            tag=None, 
            timeout=0xFFFFF,
            save_head_image=False,
            save_head_wait=0
        ):
        wxlog.debug('获取好友详情')
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'
        t0 = time.time()
        self.switch_to_contact_page()
        ContactListItem = self.SessionBox.ButtonControl(Name='ContactListItem')
        while True:
            if ContactListItem.Exists(0):
                ContactListItem.Click()
                break
            self.SessionBox.WheelUp(wheelTimes=100)

        self._next_tag()

        if tag:
            wxlog.debug(f'跳转到标签为{tag}的好友')
            if tag.upper() not in letters:
                raise ValueError(f"tag参数错误，应为{letters}中的一个字符")
            useletters = letters[letters.index(tag.upper()):]
            for i in useletters:
                if self._goto_friends_tag(i):
                    break
        details = []
        duplicate = 0
        while True:
            if time.time() - t0 > timeout:
                wxlog.debug('获取好友详情超时，返回结果')
                return details
            _detail = self._get_friend_details(save_head_image, save_head_wait)
            if details and _detail == details[-1] and duplicate > 3:
                wxlog.debug('获取好友详情完成，返回结果')
                if duplicate > 3:
                    details = details[:-4]
                return details
            if details and _detail == details[-1]:
                duplicate += 1
            else:
                duplicate = 0
            details.append(_detail)
            self.SessionBox.MiddleClick()
            self.SessionBox.SendKeys('{DOWN}')
            if n and len(details) >= n:
                wxlog.debug(f"获取前{n}个好友详情完成，返回结果")
                return details

    def get_contact_groups(self, speed: int=1, interval: float=0.1):
        def goto_group_tag():
            ContactListItem = self.SessionBox.ButtonControl(Name='ContactListItem')
            while True:
                if ContactListItem.Exists(0):
                    # ContactListItem.Click()
                    break
                self.SessionBox.WheelUp(wheelTimes=100)
            while True:
                items = self.SessionBox.ListControl().GetChildren()
                for index, item in enumerate(items[:-1]):
                    if (
                        item.Name == ''
                        and item.TextControl(Name='群聊').Exists(0)
                    ):
                        items[index+1].Click()
                        return True
                    tag_control = item.TextControl(RegexName='^[A-Z]$')
                    if tag_control.Exists(0):
                        return False
                self.SessionBox.WheelDown(wheelTimes=3)
        self.switch_to_contact_page()
        if goto_group_tag():
            listitems = []
            useditems = []
            start = False
            end = False
            while True:
                items = self.SessionBox.ListControl().GetChildren()
                for item in items:
                    _id = item.runtimeid
                    _name = item.Name
                    _text = txt.Name if (txt := item.TextControl()).Exists(0) else False
                    if (_id, _name, _text) in useditems:
                        continue
                    useditems.append((_id, _name, _text))
                    if item.Name == '' and item.TextControl(Name='群聊').Exists(0):
                        print('查找到群聊标签，开始收集')
                        start = True
                        continue
                    if start:
                        if (
                            item not in listitems
                            and item.Name != ''
                        ):
                            listitems.append(item)
                        if item.Name == '':
                            end = True
                            break
                        print('未结束')
                if end:
                    break
                self.SessionBox.WheelDown(wheelTimes=speed)
                time.sleep(interval)
            groups = [i.Name for i in listitems]
        else:
            groups = []
        self.switch_to_chat_page()
        return groups


class WeChatLoginWnd(BaseUIWnd):
    _ui_cls_name: str = 'WeChatLoginWndForPC'

    def __init__(self, app_path=None, hwnd=None):
        self.app_path = app_path
        if not hwnd:
            hwnd = FindWindow(classname=self._ui_cls_name)
        if hwnd:
            self.control = uia.ControlFromHandle(hwnd)
        else:
            self.open()

    def __repr__(self) -> str:
        return f"<wxauto LoginWnd Object at {hex(id(self))}>"
    
    def _lang(self, key):
        return key

    @property
    def _app_path(self):
        if self.app_path:
            return self.app_path
        try:
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat", 0, winreg.KEY_READ)
            path, _ = winreg.QueryValueEx(registry_key, "InstallPath")
            winreg.CloseKey(registry_key)
            wxpath = os.path.join(path, "WeChat.exe")
            if os.path.exists(wxpath):
                self.app_path = wxpath
                return wxpath
            else:
                raise Exception('nof found')
        except WindowsError:
            print("未找到微信安装路径，请先打开微信启动页面再次尝试运行该方法！")

    def login(self, timeout=15):
        enter_button = self.control.ButtonControl(Name='进入微信')
        qrcode = self.control.ButtonControl(Name='二维码')
        if enter_button.Exists(0.5):
            enter_button.Click()

            dialog = self.control.PaneControl(ClassName='WeUIDialog')
            # wx = uia.WindowControl(ClassName='WeChatMainWndForPC', searchDepth=1)
            
            t0 = time.time()
            while True:
                if time.time() - t0 > timeout:
                    raise Exception('微信登录超时')
                if FindWindow(classname='WeChatMainWndForPC'):
                    break
                elif dialog.Exists(0):
                    dialog_text = dialog.TextControl().Name
                    wxlog.debug(f"识别到弹窗：{dialog_text}")
                    dialog.SendKeys('{Esc}')
                    time.sleep(0.5)
                    return self.login(timeout)
                elif qrcode.Exists(0):
                    return WxResponse.failure("需扫码登录")
            return WxResponse.success()
        elif qrcode.Exists(0):
            return WxResponse.failure("需扫码登录")
        else:
            return WxResponse.failure("未找到登录按钮")

    def get_qrcode(self, path=None):
        """获取登录二维码

        Args:
            path (str): 二维码图片的保存路径，默认为None，即本地目录下的wxauto_qrcode文件夹

        
        Returns:
            str: 二维码图片的保存路径
        """
        self._show()
        if path is None:
            default_dir = os.path.realpath('wxauto_qrcode')
            if not os.path.exists(default_dir):
                os.mkdir(default_dir)
            path = os.path.join(default_dir, f'qrcode_{now_time()}.png')
        elif os.path.exists(path) and os.path.isdir(path):
            path = os.path.join(path, f'qrcode_{now_time()}.png')
        elif os.path.exists(os.path.dirname(path)) and path.endswith('.png'):
            pass
        else:
            raise ValueError('请输入正确的路径，或不指定path参数以使用默认路径')
        switch_account_button = self.control.ButtonControl(Name='切换账号')
        if switch_account_button.Exists(0.5):
            switch_account_button.Click()
        
        qrcode_control = self.control.ButtonControl(Name='二维码')
        qrcode = qrcode_control.ScreenShot(path)
        return qrcode
    
    def shutdown(self):
        """关闭进程"""
        pid = self.control.ProcessId
        os.system(f'taskkill /f /pid {pid}')

    def reopen(self):
        """重新打开"""
        self.shutdown()
        self.open()

    def open(self):
        path = self._app_path
        os.system(f'"start "" "{path}""')
        hwnd = FindWindow(classname=self._ui_cls_name, timeout=5)
        if hwnd:
            self.control = uia.ControlFromHandle(hwnd)
        if self.control.Exists(10):
            return
        else:
            raise Exception('打开微信失败，请指定微信路径')