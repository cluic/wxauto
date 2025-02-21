"""
Author: Cluic
Update: 2024-07-22
Version: 3.9.11.17.4
"""

from . import uiautomation as uia
from .languages import *
from .utils import *
from .elements import *
from .errors import *
from .color import *
import time
import os
import re
try:
    from typing import Literal
except:
    from typing_extensions import Literal

class WeChat(WeChatBase):
    VERSION: str = '3.9.11.17'
    lastmsgid: str = None
    listen: dict = dict()
    SessionItemList: list = []

    def __init__(
            self,
            uia_api = uia.WindowControl(ClassName='WeChatMainWndForPC', searchDepth=1),
            language: Literal['cn', 'cn_t', 'en'] = 'cn', 
            debug: bool = False
        ) -> None:
        """微信UI自动化实例

        Args:
            language (str, optional): 微信客户端语言版本, 可选: cn简体中文  cn_t繁体中文  en英文, 默认cn, 即简体中文
        """
        self.UiaAPI: uia.WindowControl = uia_api
        set_debug(debug)
        self.language = language
        # self._checkversion()
        self._show()
        MainControl1 = [i for i in self.UiaAPI.GetChildren() if not i.ClassName][0]
        MainControl2 = MainControl1.GetFirstChildControl()
        # 三个布局，导航栏(A)、聊天列表(B)、聊天框(C)
        # _______________
        # |■|———|    -□×|
        # | |———|       |
        # |A| B |   C   |   <--- 微信窗口布局简图示意
        # | |———|———————|
        # |=|———|       |
        # ———————————————
        self.NavigationBox, self.SessionBox, self.ChatBox  = MainControl2.GetChildren()
        
        # 初始化导航栏，以A开头 | self.NavigationBox  -->  A_xxx
        self.A_MyIcon = self.NavigationBox.ButtonControl()
        self.A_ChatIcon = self.NavigationBox.ButtonControl(Name=self._lang('聊天'))
        self.A_ContactsIcon = self.NavigationBox.ButtonControl(Name=self._lang('通讯录'))
        self.A_FavoritesIcon = self.NavigationBox.ButtonControl(Name=self._lang('收藏'))
        self.A_FilesIcon = self.NavigationBox.ButtonControl(Name=self._lang('聊天文件'))
        self.A_MomentsIcon = self.NavigationBox.ButtonControl(Name=self._lang('朋友圈'))
        self.A_MiniProgram = self.NavigationBox.ButtonControl(Name=self._lang('小程序面板'))
        self.A_Phone = self.NavigationBox.ButtonControl(Name=self._lang('手机'))
        self.A_Settings = self.NavigationBox.ButtonControl(Name=self._lang('设置及其他'))
        
        # 初始化聊天列表，以B开头
        self.B_Search = self.SessionBox.EditControl(Name=self._lang('搜索'))
        
        # 初始化聊天栏，以C开头
        self.C_MsgList = self.ChatBox.ListControl(Name=self._lang('消息'))
        
        self.nickname = self.A_MyIcon.Name
        msgs_ = self.GetAllMessage()
        self.usedmsgid = [i[-1] for i in msgs_]
        print(f'初始化成功，获取到已登录窗口：{self.nickname}')
    
    def _checkversion(self):
        self.HWND = FindWindow(classname='WeChatMainWndForPC')
        wxpath = GetPathByHwnd(self.HWND)
        wxversion = GetVersionByPath(wxpath)
        if wxversion != self.VERSION:
            Warnings.lightred(self._lang('版本不一致', 'WARNING').format(wxversion, self.VERSION), stacklevel=2)
            return False
    
    
    def _show(self):
        self.HWND = FindWindow(classname='WeChatMainWndForPC')
        win32gui.ShowWindow(self.HWND, 1)
        win32gui.SetWindowPos(self.HWND, -1, 0, 0, 0, 0, 3)
        win32gui.SetWindowPos(self.HWND, -2, 0, 0, 0, 0, 3)
        self.UiaAPI.SwitchToThisWindow()

    def _refresh(self):
        self.UiaAPI.SendKeys('{Ctrl}{Alt}w')
        self.UiaAPI.SendKeys('{Ctrl}{Alt}w')
        self._show()

    def _get_friend_details(self):
        params = ['昵称：', '微信号：', '地区：', '备注', '电话', '标签', '共同群聊', '个性签名', '来源', '朋友权限', '描述', '实名', '企业']
        info = {}
        controls = GetAllControlList(self.ChatBox)
        for _, i in enumerate(controls):
            rect = i.BoundingRectangle
            text = i.Name
            if text in params or (rect.width() == 57 and rect.height() == 20):
                info[text.replace('：', '')] = controls[_+1].Name
        if '昵称' not in info:
            info['备注'] = ''
            info['昵称'] = controls[0].Name
        wxlog.debug(f'获取到好友详情：{info}')
        return info
    
    def _goto_first_friend(self):
        def find_letter_tag(self):
            items = self.SessionBox.ListControl().GetChildren()
            for index, item in enumerate(items[:-1]):
                if item.TextControl(RegexName='^[A-Z]$').Exists(0):
                    # print('>>> bingo!\n')
                    # GetAllControl(item)
                    return items[index+1]
        while True:
            item = find_letter_tag(self)
            if item is not None:
                self.SessionBox.WheelDown(wheelTimes=3)
                item.Click(simulateMove=False)
                break
            self.SessionBox.WheelDown(wheelTimes=3, interval=0)

    def GetFriendDetails(self, n=None, timeout=0xFFFFF):
        """获取所有好友详情信息
        
        Args:
            n (int, optional): 获取前n个好友详情信息, 默认为None，获取所有好友详情信息
            timeout (int, optional): 获取超时时间（秒），超过该时间则直接返回结果

        Returns:
            list: 所有好友详情信息
            
        注：1. 该方法运行时间较长，约0.5~1秒一个好友的速度，好友多的话可将n设置为一个较小的值，先测试一下
            2. 如果遇到企业微信的好友且为已离职状态，可能导致微信卡死，需重启（此为微信客户端BUG）
            3. 该方法未经过大量测试，可能存在未知问题，如有问题请微信群内反馈
        """
        t0 = time.time()
        self.SwitchToContact()
        self._goto_first_friend()
        details = []
        while True:
            if time.time() - t0 > timeout:
                wxlog.debug('获取好友详情超时，返回结果')
                return details
            _detail = self._get_friend_details()
            if details and _detail == details[-1]:
                return details
            details.append(_detail)
            self.SessionBox.SendKeys('{DOWN}')
            if n and len(details) >= n:
                return details

            
    def GetSessionAmont(self, SessionItem):
        """获取聊天对象名和新消息条数
        
        Args:
            SessionItem (uiautomation.ListItemControl): 聊天对象控件
            
        Returns:
            sessionname (str): 聊天对象名
            amount (int): 新消息条数
        """
        matchobj = re.search('\d+条新消息', SessionItem.Name)
        amount = 0
        if matchobj:
            try:
                amount = int([i for i in SessionItem.GetFirstChildControl().GetChildren() if type(i) == uia.TextControl][0].Name)
            except:
                pass
        sessionname = SessionItem.Name if SessionItem.ButtonControl().Name == 'SessionListItem' else SessionItem.ButtonControl().Name
        return sessionname, amount
    
    def CheckNewMessage(self):
        """是否有新消息"""
        self._show()
        return IsRedPixel(self.A_ChatIcon)
    
    def GetNextNewMessage(self, savepic=False, savefile=False, savevoice=False, timeout=10):
        """获取下一个新消息"""
        msgs_ = self.GetAllMessage()
        msgids = [i[-1] for i in msgs_]

        if not self.usedmsgid:
            self.usedmsgid = msgids
        
        newmsgids = [i for i in msgids if i not in self.usedmsgid]
        oldmsgids = [i for i in self.usedmsgid if i in msgids]
        if newmsgids and oldmsgids:
            MsgItems = self.C_MsgList.GetChildren()
            msgids = [''.join([str(i) for i in i.GetRuntimeId()]) for i in MsgItems]
            new = []
            for i in range(len(msgids)-1, -1, -1):
                if msgids[i] in self.usedmsgid:
                    new = msgids[i+1:]
                    break
            NewMsgItems = [
                i for i in MsgItems 
                if ''.join([str(i) for i in i.GetRuntimeId()]) in new
                and i.ControlTypeName == 'ListItemControl'
            ]
            if NewMsgItems:
                wxlog.debug('获取当前窗口新消息')
                msgs = self._getmsgs(NewMsgItems, savepic, savefile, savevoice)
                self.usedmsgid = msgids
                return {self.CurrentChat(): msgs}

        if self.CheckNewMessage():
            wxlog.debug('获取其他窗口新消息')
            t0 = time.time()
            while True:
                if time.time() - t0 > timeout:
                    wxlog.debug('获取新消息超时')
                    return {}
                self.A_ChatIcon.DoubleClick(simulateMove=False)
                sessiondict = self.GetSessionList(newmessage=True)
                if sessiondict:
                    break
            for session in sessiondict:
                self.ChatWith(session)
                NewMsgItems = self.C_MsgList.GetChildren()[-sessiondict[session]:]
                msgs = self._getmsgs(NewMsgItems, savepic, savefile, savevoice)
                msgs_ = self.GetAllMessage()
                self.usedmsgid = [i[-1] for i in msgs_]
                return {session:msgs}
        else:
            wxlog.debug('没有新消息')
            return {}
    
    def GetAllNewMessage(self, max_round=10):
        """获取所有新消息
        
        Args:
            max_round (int): 最大获取次数  * 这里是为了避免某几个窗口一直有新消息，导致无法停止
        """
        newmessages = {}
        for _ in range(max_round):
            newmsg = self.GetNextNewMessage()
            if newmsg:
                for session in newmsg:
                    if session not in newmessages:
                        newmessages[session] = []
                    newmessages[session].extend(newmsg[session])
            else:
                break
        return newmessages
    
    def GetSessionList(self, reset=False, newmessage=False):
        """获取当前聊天列表中的所有聊天对象
        
        Args:
            reset (bool): 是否重置SessionItemList
            newmessage (bool): 是否只获取有新消息的聊天对象
            
        Returns:
            SessionList (dict): 聊天对象列表，键为聊天对象名，值为新消息条数
        """
        self.SessionItem = self.SessionBox.ListItemControl()
        if reset:
            self.SessionItemList = []
        SessionList = {}
        for i in range(100):
            if self.SessionItem.BoundingRectangle.width() != 0:
                try:
                    name, amount = self.GetSessionAmont(self.SessionItem)
                except:
                    break
                if name not in self.SessionItemList:
                    self.SessionItemList.append(name)
                if name not in SessionList:
                    SessionList[name] = amount
            self.SessionItem = self.SessionItem.GetNextSiblingControl()
            if not self.SessionItem:
                break
            
        if newmessage:
            return {i:SessionList[i] for i in SessionList if SessionList[i] > 0}
        return SessionList
    
    def GetSession(self):
        """获取当前聊天列表中的所有聊天对象

        Returns:
            SessionElement: 聊天对象列表

        Example:
            >>> wx = WeChat()
            >>> sessions = wx.GetSession()
            >>> for session in sessions:
            ...     print(f"聊天对象名称: {session.name}")
            ...     print(f"最后一条消息时间: {session.time}")
            ...     print(f"最后一条消息内容: {session.content}")
            ...     print(f"是否有新消息: {session.isnew}", end='\n\n')
        """
        sessions = self.SessionBox.ListControl()
        return [SessionElement(i) for i in sessions.GetChildren()]
    
    def ChatWith(self, who, timeout=2):
        '''打开某个聊天框
        
        Args:
            who ( str ): 要打开的聊天框好友名;  * 最好完整匹配，不完全匹配只会选取搜索框第一个
            timeout ( num, optional ): 超时时间，默认2秒
            
        Returns:
            chatname ( str ): 匹配值第一个的完整名字
        '''
        self._show()
        sessiondict = self.GetSessionList(True)
        if who in list(sessiondict.keys())[:-1]:
            self.SessionBox.ListItemControl(RegexName=who).Click(simulateMove=False)
            return who
        else:
            self.UiaAPI.SendKeys('{Ctrl}f', waitTime=1)
            self.B_Search.SendKeys(who, waitTime=1.5)
            target_control = self.SessionBox.TextControl(Name=f"<em>{who}</em>")
            if target_control.Exists(timeout):
                wxlog.debug('选择完全匹配项')
                target_control.Click(simulateMove=False)
                return who
            else:
                search_result_control = self.SessionBox.GetChildren()[1].GetChildren()[1].GetFirstChildControl()
                if not search_result_control.PaneControl(searchDepth=1).TextControl(RegexName='联系人|群聊').Exists(0.1):
                    wxlog.debug(f'未找到搜索结果: {who}')
                    self._refresh()
                    return False
                wxlog.debug('选择搜索结果第一个')
                target_control = search_result_control.Control(RegexName=f'.*{who}.*')
                chatname = target_control.Name
                target_control.Click(simulateMove=False)
                return chatname
    
    def AtAll(self, msg=None, who=None):
        """@所有人
        
        Args:
            who (str, optional): 要发送给谁，如果为None，则发送到当前聊天页面。  *最好完整匹配，优先使用备注
            msg (str, optional): 要发送的文本消息
        """
        if FindWindow(name=who, classname='ChatWnd'):
            chat = ChatWnd(who, self.language)
            chat.AtAll(msg)
            return None
        
        self._show()
        if who:
            try:
                editbox = self.ChatBox.EditControl(searchDepth=10)
                if who in self.CurrentChat() and who in editbox.Name:
                    pass
                else:
                    self.ChatWith(who)
                    editbox = self.ChatBox.EditControl(Name=who, searchDepth=10)
            except:
                self.ChatWith(who)
                editbox = self.ChatBox.EditControl(Name=who, searchDepth=10)
        else:
            editbox = self.ChatBox.EditControl(searchDepth=10)
        editbox.SendKeys('@')
        atwnd = self.UiaAPI.PaneControl(ClassName='ChatContactMenu')
        if atwnd.Exists(maxSearchSeconds=0.1):
            atwnd.ListItemControl(Name='所有人').Click(simulateMove=False)
            if msg:
                if not msg.startswith('\n'):
                    msg = '\n' + msg
                self.SendMsg(msg, who=who, clear=False)
            else:
                editbox.SendKeys('{Enter}')

    def InputMsg(self, msg, who=None, clear=True, at=None):
        """输入文本消息，不发送

        Args:
            msg (str): 要发送的文本消息
            who (str): 要发送给谁，如果为None，则发送到当前聊天页面。  *最好完整匹配，优先使用备注
            clear (bool, optional): 是否清除原本的内容，
            at (str|list, optional): 要@的人，可以是一个人或多个人，格式为str或list，例如："张三"或["张三", "李四"]
        """
        if FindWindow(name=who, classname='ChatWnd'):
            chat = ChatWnd(who, self.language)
            chat.SendMsg(msg, at=at)
            return None
        if not msg and not at:
            return None
        if who:
            try:
                editbox = self.ChatBox.EditControl(searchDepth=10)
                if who in self.CurrentChat() and who in editbox.Name:
                    pass
                else:
                    self.ChatWith(who)
                    editbox = self.ChatBox.EditControl(Name=who, searchDepth=10)
            except:
                self.ChatWith(who)
                editbox = self.ChatBox.EditControl(Name=who, searchDepth=10)
        else:
            editbox = self.ChatBox.EditControl(searchDepth=10)
        if clear:
            editbox.SendKeys('{Ctrl}a', waitTime=0)
        self._show()
        if not editbox.HasKeyboardFocus:
            editbox.Click(simulateMove=False)
        
        if at:
            if isinstance(at, str):
                at = [at]
            for i in at:
                editbox.SendKeys('@'+i)
                atwnd = self.UiaAPI.PaneControl(ClassName='ChatContactMenu')
                if atwnd.Exists(maxSearchSeconds=0.1):
                    atwnd.SendKeys('{ENTER}')
                    if msg and not msg.startswith('\n'):
                        msg = '\n' + msg

        if msg:
            t0 = time.time()
            while True:
                if time.time() - t0 > 10:
                    raise TimeoutError(f'发送消息超时 --> {editbox.Name} - {msg}')
                SetClipboardText(msg)
                editbox.SendKeys('{Ctrl}v')
                if editbox.GetValuePattern().Value:
                    break

        return editbox

    def SendMsg(self, msg, who=None, clear=True, at=None):
        """发送文本消息
        Args:
            msg (str): 要发送的文本消息
            who (str): 要发送给谁，如果为None，则发送到当前聊天页面。  *最好完整匹配，优先使用备注
            clear (bool, optional): 是否清除原本的内容，
            at (str|list, optional): 要@的人，可以是一个人或多个人，格式为str或list，例如："张三"或["张三", "李四"]
        """
        editbox =  self.InputMsg(msg, who, clear, at)
        editbox.SendKeys('{Enter}')
        
    def SendFiles(self, filepath, who=None):
        """向当前聊天窗口发送文件
        
        Args:
            filepath (str|list): 要复制文件的绝对路径  
            who (str): 要发送给谁，如果为None，则发送到当前聊天页面。  *最好完整匹配，优先使用备注
            
        Returns:
            bool: 是否成功发送文件
        """
        if FindWindow(name=who, classname='ChatWnd'):
            chat = ChatWnd(who, self.language)
            chat.SendFiles(filepath)
            return None
        filelist = []
        if isinstance(filepath, str):
            if not os.path.exists(filepath):
                Warnings.lightred(f'未找到文件：{filepath}，无法成功发送', stacklevel=2)
                return False
            else:
                filelist.append(os.path.realpath(filepath))
        elif isinstance(filepath, (list, tuple, set)):
            for i in filepath:
                if os.path.exists(i):
                    filelist.append(i)
                else:
                    Warnings.lightred(f'未找到文件：{i}', stacklevel=2)
        else:
            Warnings.lightred(f'filepath参数格式错误：{type(filepath)}，应为str、list、tuple、set格式', stacklevel=2)
            return False
        
        if filelist:
            self._show()
            if who:
                try:
                    if who in self.CurrentChat() and who in self.ChatBox.EditControl(searchDepth=10).Name:
                        pass
                    else:
                        self.ChatWith(who)
                except:
                    self.ChatWith(who)
                editbox = self.ChatBox.EditControl(Name=who)
            else:
                editbox = self.ChatBox.EditControl()
            editbox.SendKeys('{Ctrl}a', waitTime=0)
            t0 = time.time()
            while True:
                if time.time() - t0 > 10:
                    raise TimeoutError(f'发送文件超时 --> {filelist}')
                SetClipboardFiles(filelist)
                time.sleep(0.2)
                editbox.SendKeys('{Ctrl}v')
                if editbox.GetValuePattern().Value:
                    break
            editbox.SendKeys('{Enter}')
            return True
        else:
            Warnings.lightred('所有文件都无法成功发送', stacklevel=2)
            return False
            
    def GetAllMessage(self, savepic=False, savefile=False, savevoice=False):
        '''获取当前窗口中加载的所有聊天记录
        
        Args:
            savepic (bool): 是否自动保存聊天图片
            
        Returns:
            list: 聊天记录信息
        '''
        if not self.C_MsgList.Exists(0.2):
            return []
        MsgItems = self.C_MsgList.GetChildren()
        msgs = self._getmsgs(MsgItems, savepic, savefile=savefile, savevoice=savevoice)
        return msgs
    
    def LoadMoreMessage(self):
        """加载当前聊天页面更多聊天信息
        
        Returns:
            bool: 是否成功加载更多聊天信息
        """
        loadmore = self.C_MsgList.GetFirstChildControl()
        loadmore_top = loadmore.BoundingRectangle.top
        top = self.C_MsgList.BoundingRectangle.top
        while True:
            if loadmore.BoundingRectangle.top > top or loadmore.Name == '':
                isload = True
                break
            else:
                self.C_MsgList.WheelUp(wheelTimes=10, waitTime=0.1)
                if loadmore.BoundingRectangle.top == loadmore_top:
                    isload = False
                    break
                else:
                    loadmore_top = loadmore.BoundingRectangle.top
        self.C_MsgList.WheelUp(wheelTimes=1, waitTime=0.1)
        return isload
    
    def CurrentChat(self):
        '''获取当前聊天对象名'''
        uia.SetGlobalSearchTimeout(1)
        try:
            currentname = self.ChatBox.TextControl(searchDepth=15).Name
            return currentname
        except:
            return None
        finally:
            uia.SetGlobalSearchTimeout(10)

    def GetNewFriends(self):
        """获取新的好友申请列表
        
        Returns:
            list: 新的好友申请列表，元素为NewFriendsElement对象，可直接调用Accept方法

        Example:
            >>> wx = WeChat()
            >>> newfriends = wx.GetNewFriends()
            >>> tags = ['标签1', '标签2']
            >>> for friend in newfriends:
            ...     remark = f'备注{friend.name}'
            ...     friend.Accept(remark=remark, tags=tags)  # 接受好友请求，并设置备注和标签
        """
        self._show()
        self.SwitchToContact()
        self.SessionBox.ButtonControl(Name='ContactListItem').Click(simulateMove=False)
        NewFriendsList = [NewFriendsElement(i, self) for i in self.ChatBox.ListControl(Name='新的朋友').GetChildren()]
        AcceptableNewFriendsList = [i for i in NewFriendsList if i.acceptable]
        wxlog.debug(f'获取到 {len(AcceptableNewFriendsList)} 条新的好友申请')
        return AcceptableNewFriendsList
    
    def AddListenChat(self, who, savepic=False, savefile=False, savevoice=False):
        """添加监听对象
        
        Args:
            who (str): 要监听的聊天对象名
            savepic (bool, optional): 是否自动保存聊天图片，只针对该聊天对象有效
            savefile (bool, optional): 是否自动保存聊天文件，只针对该聊天对象有效
            savevoice (bool, optional): 是否自动保存聊天语音，只针对该聊天对象有效
        """
        exists = uia.WindowControl(searchDepth=1, ClassName='ChatWnd', Name=who).Exists(maxSearchSeconds=0.1)
        if not exists:
            self.ChatWith(who)
            self.SessionBox.ListItemControl(RegexName=who).DoubleClick(simulateMove=False)
        self.listen[who] = ChatWnd(who, self.language)
        self.listen[who].savepic = savepic
        self.listen[who].savefile = savefile
        self.listen[who].savevoice = savevoice

    def GetListenMessage(self, who=None):
        """获取监听对象的新消息
        
        Args:
            who (str, optional): 要获取消息的聊天对象名，如果为None，则获取所有监听对象的消息

        Returns:
            str|dict: 如果
        """
        if who and who in self.listen:
            chat = self.listen[who]
            msg = chat.GetNewMessage(savepic=chat.savepic, savefile=chat.savefile, savevoice=chat.savevoice)
            return msg
        msgs = {}
        for who in self.listen:
            chat = self.listen[who]
            msg = chat.GetNewMessage(savepic=chat.savepic, savefile=chat.savefile, savevoice=chat.savevoice)
            if msg:
                msgs[chat] = msg
        return msgs

    def SwitchToContact(self):
        """切换到通讯录页面"""
        self._show()
        self.A_ContactsIcon.Click(simulateMove=False)

    def SwitchToChat(self):
        """切换到聊天页面"""
        self._show()
        self.A_ChatIcon.Click(simulateMove=False)

    # def DownloadFiles(self, who, amount=1):
    #     """切换到聊天文件页面
        
    #     Args:
    #         who (str): 要下载文件的聊天对象名
    #         amount (int): 要下载的文件数量
    #     """
    #     self._show()
    #     self.A_FilesIcon.Click(simulateMove=False)
    #     files = WeChatFiles()
    #     files.ChatWithFile(who)
    #     files.DownloadFiles(who, amount)
    #     files.Close()

    def GetGroupMembers(self):
        """获取当前聊天群成员

        Returns:
            list: 当前聊天群成员列表
        """
        ele = self.ChatBox.PaneControl(searchDepth=7, foundIndex=6).ButtonControl(Name='聊天信息')
        try:
            uia.SetGlobalSearchTimeout(1)
            rect = ele.BoundingRectangle
            Click(rect)
        except:
            return 
        finally:
            uia.SetGlobalSearchTimeout(10)
        roominfoWnd = self.UiaAPI.Control(ClassName='SessionChatRoomDetailWnd', searchDepth=1)
        more = roominfoWnd.ButtonControl(Name='查看更多', searchDepth=8)
        try:
            uia.SetGlobalSearchTimeout(1)
            rect = more.BoundingRectangle
            Click(rect)
        except:
            pass
        finally:
            uia.SetGlobalSearchTimeout(10)
        members = [i.Name for i in roominfoWnd.ListControl(Name='聊天成员').GetChildren()]
        while members[-1] in ['添加', '移出']:
            members = members[:-1]
        roominfoWnd.SendKeys('{Esc}')
        return members

    def GetAllFriends(self, keywords=None):
        """获取所有好友列表
        注：
            1. 该方法运行时间取决于好友数量，约每秒6~8个好友的速度
            2. 该方法未经过大量测试，可能存在未知问题，如有问题请微信群内反馈
        
        Args:
            keywords (str, optional): 搜索关键词，只返回包含关键词的好友列表
            
        Returns:
            list: 所有好友列表
        """
        self._show()
        self.SwitchToContact()
        self.SessionBox.ListControl(Name="联系人").ButtonControl(Name="通讯录管理").Click(simulateMove=False)
        contactwnd = ContactWnd()
        if keywords:
            contactwnd.Search(keywords)
        friends = contactwnd.GetAllFriends()
        contactwnd.Close()
        self.SwitchToChat()
        return friends
    
    def GetAllListenChat(self):
        """获取所有监听对象"""
        return self.listen
    
    def RemoveListenChat(self, who):
        """移除监听对象"""
        if who in self.listen:
            del self.listen[who]
        else:
            Warnings.lightred(f'未找到监听对象：{who}', stacklevel=2)

    def AddNewFriend(self, keywords, addmsg=None, remark=None, tags=None):
        """添加新的好友

        Args:
            keywords (str): 搜索关键词，微信号、手机号、QQ号
            addmsg (str, optional): 添加好友的消息
            remark (str, optional): 备注名
            tags (list, optional): 标签列表

        Example:
            >>> wx = WeChat()
            >>> keywords = '13800000000'      # 微信号、手机号、QQ号
            >>> addmsg = '你好，我是xxxx'      # 添加好友的消息
            >>> remark = '备注名字'            # 备注名
            >>> tags = ['朋友', '同事']        # 标签列表
            >>> wx.AddNewFriend(keywords, addmsg=addmsg, remark=remark, tags=tags)
        """
        self._show()
        self.SwitchToContact()
        self.SessionBox.ButtonControl(Name='添加朋友').Click(simulateMove=False)
        edit = self.SessionBox.EditControl(Name='微信号/手机号')
        edit.Click(simulateMove=False)
        edit.SendKeys(keywords)
        self.SessionBox.TextControl(Name=f'搜索：{keywords}').Click(simulateMove=False)

        ContactProfileWnd = uia.PaneControl(ClassName='ContactProfileWnd')
        if ContactProfileWnd.Exists(maxSearchSeconds=2):
            # 点击添加到通讯录
            ContactProfileWnd.ButtonControl(Name='添加到通讯录').Click(simulateMove=False)
        else:
            wxlog.debug('未找到联系人')
            return False

        NewFriendsWnd = self.UiaAPI.WindowControl(ClassName='WeUIDialog')
        if NewFriendsWnd.Exists(maxSearchSeconds=2):
            if addmsg:
                msgedit = NewFriendsWnd.TextControl(Name="发送添加朋友申请").GetParentControl().EditControl()
                msgedit.Click(simulateMove=False)
                msgedit.SendKeys('{Ctrl}a', waitTime=0)
                msgedit.SendKeys(addmsg)

            if remark:
                remarkedit = NewFriendsWnd.TextControl(Name='备注名').GetParentControl().EditControl()
                remarkedit.Click(simulateMove=False)
                remarkedit.SendKeys('{Ctrl}a', waitTime=0)
                remarkedit.SendKeys(remark)

            if tags:
                tagedit = NewFriendsWnd.TextControl(Name='标签').GetParentControl().EditControl()
                for tag in tags:
                    tagedit.Click(simulateMove=False)
                    tagedit.SendKeys(tag)
                    NewFriendsWnd.PaneControl(ClassName='DropdownWindow').TextControl().Click(simulateMove=False)

            NewFriendsWnd.ButtonControl(Name='确定').Click(simulateMove=False)
        return True
    
class WeChatFiles:
    def __init__(self, language='cn') -> None:
        self.language = language
        self.api = uia.WindowControl(ClassName='FileListMgrWnd', searchDepth=1)
        MainControl3 = [i for i in self.api.GetChildren() if not i.ClassName][0]
        self.FileBox ,self.Search ,self.SessionBox = MainControl3.GetChildren()

        self.allfiles = self.SessionBox.ButtonControl(Name=self._lang('全部'))
        self.recentfiles = self.SessionBox.ButtonControl(Name=self._lang('最近使用'))
        self.whofiles = self.SessionBox.ButtonControl(Name=self._lang('发送者'))
        self.chatfiles = self.SessionBox.ButtonControl(Name=self._lang('聊天'))
        self.typefiles = self.SessionBox.ButtonControl(Name=self._lang('类型'))

    def GetSessionName(self, SessionItem):
        """获取聊天对象的名字

        Args:
            SessionItem (uiautomation.ListItemControl): 聊天对象控件

        Returns:
            sessionname (str): 聊天对象名
        """
        return SessionItem.Name

    def GetSessionList(self, reset=False):
        """获取当前聊天列表中的所有聊天对象的名字

        Args:
            reset (bool): 是否重置SessionItemList

        Returns:
            session_names (list): 对象名称列表
        """
        self.SessionItem = self.SessionBox.ListControl(Name='',searchDepth=3).GetChildren()
        if reset:
            self.SessionItemList = []
        session_names = []
        for i in range(len(self.SessionItem)):
            session_names.append(self.GetSessionName(self.SessionItem[i]))

        return session_names

    def __repr__(self) -> str:
        return f"<wxauto WeChat Image at {hex(id(self))}>"

    def _lang(self, text):
        return FILE_LANGUAGE[text][self.language]

    def _show(self):
        HWND = FindWindow(classname='ImagePreviewWnd')
        win32gui.ShowWindow(HWND, 1)
        self.api.SwitchToThisWindow()

    def ChatWithFile(self, who):
        '''打开某个聊天会话

        Args:
            who ( str ): 要打开的聊天框好友名。

        Returns:
            chatname ( str ): 打开的聊天框的名字。
        '''
        self._show()
        self.chatfiles.Click(simulateMove=False)
        sessiondict = self.GetSessionList(True)

        if who in sessiondict:
            # 直接点击已存在的聊天框
            self.SessionBox.ListItemControl(Name=who).Click(simulateMove=False)
            return who
        else:
            # 如果聊天框不在列表中，则抛出异常
            raise TargetNotFoundError(f'未查询到目标：{who}')

    def DownloadFiles(self, who, amount, deadline=None, size=None):
        '''开始下载文件

        Args:
            who ( str )：聊天名称
            amount ( num )：下载的文件数量限制。
            deadline ( str )：截止日期限制。
            size ( str )：文件大小限制。

        Returns:
            result ( bool )：下载是否成功

        '''
        self._show()
        itemlist = self.GetSessionList()
        if who in itemlist:
            self.item = self.SessionBox.ListItemControl(Name=who)
            self.item.Click(simulateMove=False)
        else:
            wxlog.debug(f'未查询到目标：{who}')
        itemfileslist = []

        item = self.SessionBox.ListControl(Name='', searchDepth=7).GetParentControl()
        item = item.GetNextSiblingControl()
        item = item.ListControl(Name='', searchDepth=5).GetChildren()
        del item[0]

        for i in range(amount):
            try:

                itemfileslist.append(item[i].Name)
                self.itemfiles = item[i]
                self.itemfiles.Click()
                time.sleep(0.5)
            except:
                pass

    def Close(self):
        self._show()
        self.api.SendKeys('{Esc}')
