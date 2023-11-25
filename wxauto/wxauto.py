"""
Author: cluic
Update: 2023-11-24
Version: 3.9.8.15
"""

import uiautomation as uia
from .languages import *
from .utils import *
from .errors import *
import warnings
import datetime
import time
import os
import re

class WxParam:
    SYS_TEXT_HEIGHT = 33
    TIME_TEXT_HEIGHT = 34
    RECALL_TEXT_HEIGHT = 45
    CHAT_TEXT_HEIGHT = 52
    CHAT_IMG_HEIGHT = 117

class WeChat:
    def __init__(self, language='cn') -> None:
        """微信UI自动化实例

        Args:
            language (str, optional): 微信客户端语言版本, 可选: cn简体中文  cn_t繁体中文  en英文, 默认cn, 即简体中文
        """
        self.VERSION = '3.9.8.15'
        self.language = language
        self.UiaAPI = uia.WindowControl(ClassName='WeChatMainWndForPC', searchDepth=1)
        self._show()
        self.SessionItemList = []
        MainControl1 = [i for i in self.UiaAPI.GetChildren() if not i.ClassName][0]
        MainControl2 = MainControl1.GetChildren()[0]
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
        print(f'初始化成功，获取到已登录窗口：{self.nickname}')
        
        
        
    def _lang(self, text):
        return MAIN_LANGUAGE[text][self.language]
    
    def _show(self):
        self.HWND = FindWindow(classname='WeChatMainWndForPC')
        win32gui.ShowWindow(self.HWND, 1)
        win32gui.SetWindowPos(self.HWND, -1, 0, 0, 0, 0, 3)
        win32gui.SetWindowPos(self.HWND, -2, 0, 0, 0, 0, 3)
        self.UiaAPI.SwitchToThisWindow()
        
    def _split(self, MsgItem):
        uia.SetGlobalSearchTimeout(0)
        MsgItemName = MsgItem.Name
        if MsgItem.BoundingRectangle.height() == WxParam.SYS_TEXT_HEIGHT:
            Msg = ['SYS', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
        elif MsgItem.BoundingRectangle.height() == WxParam.TIME_TEXT_HEIGHT:
            Msg = ['Time', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
        elif MsgItem.BoundingRectangle.height() == WxParam.RECALL_TEXT_HEIGHT:
            if '撤回' in MsgItemName:
                Msg = ['Recall', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
            else:
                Msg = ['SYS', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
        else:
            Index = 1
            User = MsgItem.ButtonControl(foundIndex=Index)
            try:
                while True:
                    if User.Name == '':
                        Index += 1
                        User = MsgItem.ButtonControl(foundIndex=Index)
                    else:
                        break
                Msg = [User.Name, MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
            except:
                Msg = ['SYS', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
        uia.SetGlobalSearchTimeout(10.0)
        return Msg
    
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
                amount = int([i for i in SessionItem.GetChildren()[0].GetChildren() if type(i) == uia.uiautomation.TextControl][0].Name)
            except:
                pass
        if amount:
            sessionname = SessionItem.Name.replace(f'{amount}条新消息','')
        else:
            sessionname = SessionItem.Name
        return sessionname, amount
    
    def CheckNewMessage(self):
        """是否有新消息"""
        return IsRedPixel(self.A_ChatIcon)
    
    def GetAllNewMessage(self):
        """获取所有新消息"""
        newmessages = {}
        while True:
            if self.CheckNewMessage():
                self.A_ChatIcon.DoubleClick(simulateMove=False)
                sessiondict = self.GetSessionList(newmessage=True)
                for session in sessiondict:
                    self.ChatWith(session)
                    newmessages[session] = self.GetAllMessage()[-sessiondict[session]:]
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
        self.ChatWith(self._lang('文件传输助手'))
            
        if newmessage:
            return {i:SessionList[i] for i in SessionList if SessionList[i] > 0}
        return SessionList
    
    def ChatWith(self, who):
        '''打开某个聊天框
        
        Args:
            who ( str ): 要打开的聊天框好友名;  * 最好完整匹配，不完全匹配只会选取搜索框第一个
            
        Returns:
            chatname ( str ): 匹配值第一个的完整名字
        '''
        self._show()
        sessiondict = self.GetSessionList(True)
        if who in list(sessiondict.keys())[:-1]:
            if sessiondict[who] > 0:
                who1 = f"{who}{sessiondict[who]}条新消息"
            else:
                who1 = who
            self.SessionBox.ListItemControl(Name=who1).Click(simulateMove=False)
            return who
        self.UiaAPI.SendKeys('{Ctrl}f', waitTime=1)
        self.B_Search.SendKeys(who, waitTime=1.5)
        SearchResut = self.SessionBox.GetChildren()[1].GetChildren()[1]
        firstresult = [i for i in SearchResut.GetChildren()[0].GetChildren() if who in i.Name][0]
        if firstresult.Name == f'搜索 {who}':
            if len(self.SessionBox.GetChildren()[1].GetChildren()) > 1:
                self.B_Search.SendKeys('{Esc}')
            raise TargetNotFoundError(f'未查询到目标：{who}')
        chatname = firstresult.Name
        firstresult.Click(simulateMove=False)
        return chatname
    
    def SendMsg(self, msg, who=None, clear=True):
        """发送文本消息

        Args:
            msg (str): 要发送的文本消息
            who (str): 要发送给谁，如果为None，则发送到当前聊天页面。  *最好完整匹配，优先使用备注
            clear (bool, optional): 是否清除原本的内容，
        """
        if not msg:
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
        
        t0 = time.time()
        while True:
            if time.time() - t0 > 10:
                raise TimeoutError(f'发送消息超时 --> {editbox.Name} - {msg}')
            SetClipboardText(msg)
            editbox.SendKeys('{Ctrl}v')
            if editbox.GetValuePattern().Value:
                break
        editbox.SendKeys('{Enter}')
        
    def SendFiles(self, filepath, who=None):
        """向当前聊天窗口发送文件
        
        Args:
            filepath (str|list): 要复制文件的绝对路径  
            who (str): 要发送给谁，如果为None，则发送到当前聊天页面。  *最好完整匹配，优先使用备注
            
        Returns:
            bool: 是否成功发送文件
        """
        filelist = []
        if isinstance(filepath, str):
            if not os.path.exists(filepath):
                warnings.warn(f'未找到文件：{filepath}，无法成功发送')
                return False
            else:
                filelist.append(filepath)
        elif isinstance(filepath, (list, tuple, set)):
            for i in filepath:
                if os.path.exists(i):
                    filelist.append(i)
                else:
                    warnings.warn(f'未找到文件：{i}')
        else:
            warnings.warn(f'filepath参数格式错误：{type(filepath)}，应为str、list、tuple、set格式')
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
            warnings.warn('所有文件都无法成功发送')
            return False
            
    def GetAllMessage(self, savepic=False):
        '''获取当前窗口中加载的所有聊天记录
        
        Args:
            savepic (bool): 是否自动保存聊天图片
            
        Returns:
            list: 聊天记录信息
        '''
        msgs = []
        MsgItems = self.C_MsgList.GetChildren()
        for MsgItem in MsgItems:
            msgs.append(self._split(MsgItem))

        if not [i for i in msgs if i[1] == f"[{self._lang('图片')}]"]:
            return msgs
        if savepic:
            paths = list()
            imgcontrol = self.C_MsgList.ListItemControl(Name=f"[{self._lang('图片')}]").ButtonControl(Name='')
            if imgcontrol.BoundingRectangle.top < self.C_MsgList.BoundingRectangle.top:
                # 上滚动
                while True:
                    self.C_MsgList.WheelUp(wheelTimes=1, waitTime=0.1)
                    if imgcontrol.BoundingRectangle.top > self.C_MsgList.BoundingRectangle.top:
                        break
            elif imgcontrol.BoundingRectangle.bottom > self.C_MsgList.BoundingRectangle.bottom:
                # 下滚动
                while True:
                    self.C_MsgList.WheelDown(wheelTimes=1, waitTime=0.1)
                    if imgcontrol.BoundingRectangle.bottom < self.C_MsgList.BoundingRectangle.bottom:
                        break
            imgcontrol.Click(simulateMove=False)
            imgobj = WeChatImage()
            savepath = imgobj.Save()
            paths.append(savepath)
            while True:
                if imgobj.Next():
                    savepath = imgobj.Save()
                    paths.append(savepath)
                else:
                    imgobj.Close()
                    break
            idx = 0
            for msg in msgs:
                if msg[1] == f"[{self._lang('图片')}]":
                    msg[1] = paths[idx]
                    idx += 1
        return msgs
    
    def LoadMoreMessage(self):
        """加载当前聊天页面更多聊天信息
        
        Returns:
            bool: 是否成功加载更多聊天信息
        """
        loadmore = self.C_MsgList.GetChildren()[0]
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

    
 
class WeChatImage:
    def __init__(self, language='cn') -> None:
        self.language = language
        self.api = uia.WindowControl(ClassName='ImagePreviewWnd', searchDepth=1)
        MainControl1 = [i for i in self.api.GetChildren() if not i.ClassName][0]
        self.ToolsBox, self.PhotoBox = MainControl1.GetChildren()
        
        # tools按钮
        self.t_previous = self.ToolsBox.ButtonControl(Name=self._lang('上一张'))
        self.t_next = self.ToolsBox.ButtonControl(Name=self._lang('下一张'))
        self.t_translate = self.ToolsBox.ButtonControl(Name=self._lang('翻译'))
        self.t_ocr = self.ToolsBox.ButtonControl(Name=self._lang('提取文字'))
        self.t_save = self.ToolsBox.ButtonControl(Name=self._lang('另存为...'))
        self.t_qrcode = self.ToolsBox.ButtonControl(Name=self._lang('识别图中二维码'))
    
    def _lang(self, text):
        return IMAGE_LANGUAGE[text][self.language]
    
    def _show(self):
        HWND = FindWindow(classname='ImagePreviewWnd')
        win32gui.ShowWindow(HWND, 1)
        self.api.SwitchToThisWindow()
        
    def OCR(self):
        result = ''
        ctrls = self.PhotoBox.GetChildren()
        if len(ctrls) == 2:
            self.t_ocr.Click(simulateMove=False)
        ctrls = self.PhotoBox.GetChildren()
        if len(ctrls) != 3:
            warnings.warn('获取文字识别失败')
        else:
            TranslateControl = ctrls[-1]
            result = TranslateControl.TextControl().Name
        return result

    
    def Save(self, savepath='', timeout=10):
        """保存图片

        Args:
            savepath (str): 绝对路径，包括文件名和后缀，例如："D:/Images/微信图片_xxxxxx.jpg"
            （如果不填，则默认为当前脚本文件夹下，新建一个“微信图片”的文件夹，保存在该文件夹内）
        
        Returns:
            str: 文件保存路径，即savepath
        """
        if not savepath:
            savepath = os.path.join(os.getcwd(), '微信图片', f"微信图片_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}.jpg")
        if not os.path.exists(os.path.split(savepath)[0]):
            os.makedirs(os.path.split(savepath)[0])
            
        self.t_save.Click(simulateMove=False)
        t0 = time.time()
        while True:
            if time.time() - t0 > timeout:
                raise TimeoutError('下载超时')
            handle = FindWindow(name='另存为...')
            if handle:
                break
        edithandle = [i for i in GetAllWindowExs(handle) if i[1] == 'Edit' and i[-1]][0][0]
        savehandle = FindWinEx(handle, classname='Button', name='保存(&S)')[0]
        win32gui.SendMessage(edithandle, win32con.WM_SETTEXT, '', str(savepath))
        win32gui.SendMessage(savehandle, win32con.BM_CLICK, 0, 0)
        return savepath
        
    def Previous(self):
        """上一张"""
        if self.t_previous.IsKeyboardFocusable:
            self._show()
            self.t_previous.Click(simulateMove=False)
            return True
        else:
            warnings.warn('上一张按钮不可用')
            return False
        
    def Next(self):
        """下一张"""
        if self.t_next.IsKeyboardFocusable:
            self._show()
            self.t_next.Click(simulateMove=False)
            return True
        else:
            warnings.warn('下一张按钮不可用')
            return False
        
    def Close(self):
        self._show()
        self.api.SendKeys('{Esc}')
