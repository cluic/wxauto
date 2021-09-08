#!python3
# -*- coding: utf-8 -*-
"""
Author: tikic@qq.com
Source: https://github.com/cluic/wxauto
License: MIT License
Version: 3.3.5.3
"""
import uiautomation as uia
import win32gui, win32con
import win32clipboard as wc
import time
import os

AUTHOR_EMAIL = 'tikic@qq.com'
UPDATE = '2021-09-06'
VERSION = '3.3.5.3'

COPYDICT = {}

class WxParam:
    SYS_TEXT_HEIGHT = 33
    TIME_TEXT_HEIGHT = 34
    RECALL_TEXT_HEIGHT = 45
    CHAT_TEXT_HEIGHT = 52
    CHAT_IMG_HEIGHT = 117
    SpecialTypes = ['[文件]', '[图片]', '[视频]', '[音乐]', '[链接]']
    

class WxUtils:
    def SplitMessage(MsgItem):
        uia.SetGlobalSearchTimeout(0)
        MsgItemName = MsgItem.Name
        if MsgItem.BoundingRectangle.height() == WxParam.SYS_TEXT_HEIGHT:
            Msg = ('SYS', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()]))
        elif MsgItem.BoundingRectangle.height() == WxParam.TIME_TEXT_HEIGHT:
            Msg = ('Time', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()]))
        elif MsgItem.BoundingRectangle.height() == WxParam.RECALL_TEXT_HEIGHT:
            if '撤回' in MsgItemName:
                Msg = ('Recall', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()]))
            else:
                Msg = ('SYS', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()]))
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
                Msg = (User.Name, MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()]))
            except:
                Msg = ('SYS', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()]))
        uia.SetGlobalSearchTimeout(10.0)
        return Msg
    
    def SetClipboard(data, dtype='text'):
        '''复制文本信息或图片到剪贴板
        data : 要复制的内容，str 或 Image 图像'''
        if dtype.upper() == 'TEXT':
            type_data = win32con.CF_UNICODETEXT
        elif dtype.upper() == 'IMAGE':
            from io import BytesIO
            type_data = win32con.CF_DIB
            output = BytesIO()
            data.save(output, 'BMP')
            data = output.getvalue()[14:]
        else:
            raise ValueError('param (dtype) only "text" or "image" supported')
        wc.OpenClipboard()
        wc.EmptyClipboard()
        wc.SetClipboardData(type_data, data)
        wc.CloseClipboard()

    def Screenshot(hwnd, to_clipboard=True):
        '''为句柄为hwnd的窗口程序截图
        hwnd : 句柄
        to_clipboard : 是否复制到剪贴板
        '''
        import pyscreenshot as shot
        bbox = win32gui.GetWindowRect(hwnd)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,\
                              win32con.SWP_SHOWWINDOW|win32con.SWP_NOMOVE|win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,\
                              win32con.SWP_SHOWWINDOW|win32con.SWP_NOMOVE|win32con.SWP_NOSIZE)
        win32gui.BringWindowToTop(hwnd)
        im = shot.grab(bbox)
        if to_clipboard:
            WxUtils.SetClipboard(im, 'image')
        return im
    
    def SavePic(savepath=None, filename=None):
        Pic = uia.WindowControl(ClassName='ImagePreviewWnd', Name='图片查看')
        Pic.SendKeys('{Ctrl}s')
        SaveAs = Pic.WindowControl(ClassName='#32770', Name='另存为...')
        SaveAsEdit = SaveAs.EditControl(ClassName='Edit', Name='文件名:')
        SaveButton = Pic.ButtonControl(ClassName='Button', Name='保存(S)')
        PicName, Ex = os.path.splitext(SaveAsEdit.GetValuePattern().Value)
        if not savepath:
            savepath = os.getcwd()
        if not filename:
            filename = PicName
        FilePath = os.path.realpath(os.path.join(savepath, filename + Ex))
        SaveAsEdit.SendKeys(FilePath)
        SaveButton.Click()
        Pic.SendKeys('{Esc}')

    def ControlSize(control):
        locate = control.BoundingRectangle
        size = (locate.width(), locate.height())
        return size
    
    def ClipboardFormats(unit=0, *units):
        units = list(units)
        wc.OpenClipboard()
        u = wc.EnumClipboardFormats(unit)
        wc.CloseClipboard()
        units.append(u)
        if u:
            units = WxUtils.ClipboardFormats(u, *units)
        return units

    def CopyDict():
        Dict = {}
        for i in WxUtils.ClipboardFormats():
            if i == 0:
                continue
            wc.OpenClipboard()
            try:
                content = wc.GetClipboardData(i)
                wc.CloseClipboard()
            except:
                wc.CloseClipboard()
                raise ValueError
            if len(str(i))>=4:
                Dict[str(i)] = content
        return Dict
        
class WeChat:
    def __init__(self):
        self.UiaAPI = uia.WindowControl(ClassName='WeChatMainWndForPC')
        self.SessionList = self.UiaAPI.ListControl(Name='会话')
        self.EditMsg = self.UiaAPI.EditControl(Name='输入')
        self.SearchBox = self.UiaAPI.EditControl(Name='搜索')
        self.MsgList = self.UiaAPI.ListControl(Name='消息')
        self.SessionItemList = []
    
    def GetSessionList(self, reset=False):
        '''获取当前会话列表，更新会话列表'''
        self.SessionItem = self.SessionList.ListItemControl()
        SessionList = []
        if reset:
            self.SessionItemList = []
        for i in range(100):
            try:
                name = self.SessionItem.Name
            except:
                break
            if name not in self.SessionItemList:
                self.SessionItemList.append(name)
            if name not in SessionList:
                SessionList.append(name)
            self.SessionItem = self.SessionItem.GetNextSiblingControl()
        return SessionList
        
    def Search(self, keyword):
        '''
        查找微信好友或关键词
        keywords: 要查找的关键词，str   * 最好完整匹配，不完全匹配只会选取搜索框第一个
        '''
        self.UiaAPI.SetFocus()
        time.sleep(0.2)
        self.UiaAPI.SendKeys('{Ctrl}f', waitTime=1)
        self.SearchBox.SendKeys(keyword, waitTime=1.5)
        self.SearchBox.SendKeys('{Enter}')
    
    def ChatWith(self, who, RollTimes=None):
        '''
        打开某个聊天框
        who : 要打开的聊天框好友名，str;  * 最好完整匹配，不完全匹配只会选取搜索框第一个
        RollTimes : 默认向下滚动多少次，再进行搜索
        '''
        self.UiaAPI.SwitchToThisWindow()
        RollTimes = 10 if not RollTimes else RollTimes
        def roll_to(who=who, RollTimes=RollTimes):
            for i in range(RollTimes):
                if who not in self.GetSessionList()[:-1]:
                    self.SessionList.WheelDown(wheelTimes=3, waitTime=0.1*i)
                else:
                    time.sleep(0.5)
                    self.SessionList.ListItemControl(Name=who).Click(simulateMove=False)
                    return 1
            return 0
        rollresult = roll_to()
        if rollresult:
            return 1
        else:
            self.Search(who)
            return roll_to(RollTimes=1)
    
    def SendMsg(self, msg, clear=True):
        '''向当前窗口发送消息
        msg : 要发送的消息
        clear : 是否清除当前已编辑内容
        '''
        self.UiaAPI.SwitchToThisWindow()
        if clear:
            self.EditMsg.SendKeys('{Ctrl}a', waitTime=0)
        self.EditMsg.SendKeys(msg, waitTime=0)
        self.EditMsg.SendKeys('{Enter}', waitTime=0)
    
    def SendFiles(self, *filepath, not_exists='ignore'):
        """向当前聊天窗口发送文件
        not_exists: 如果未找到指定文件，继续或终止程序
        *filepath: 要复制文件的绝对路径"""
        global COPYDICT
        key = ''
        for file in filepath:
            file = os.path.realpath(file)
            if not os.path.exists(file):
                if not_exists.upper() == 'IGNORE':
                    print('File not exists:', file)
                    continue
                elif not_exists.upper() == 'RAISE':
                    raise FileExistsError('File Not Exists: %s'%file)
                else:
                    raise ValueError('param not_exists only "ignore" or "raise" supported')
            key += '<EditElement type="3" filepath="%s" shortcut="" />'%file
        if not key:
            return 0
        if not COPYDICT:
            self.EditMsg.SendKeys(' ', waitTime=0)
            self.EditMsg.SendKeys('{Ctrl}a', waitTime=0)
            self.EditMsg.SendKeys('{Ctrl}c', waitTime=0)
            self.EditMsg.SendKeys('{Delete}', waitTime=0)
            while True:
                try:
                    COPYDICT = WxUtils.CopyDict()
                    break
                except:
                    pass
        wc.OpenClipboard()
        wc.EmptyClipboard()
        wc.SetClipboardData(13, '')
        wc.SetClipboardData(16, b'\x04\x08\x00\x00')
        wc.SetClipboardData(1, b'')
        wc.SetClipboardData(7, b'')
        for i in COPYDICT:
            copydata = COPYDICT[i].replace(b'<EditElement type="0"><![CDATA[ ]]>', key.encode()).replace(b'type="0"', b'type="3"')
            wc.SetClipboardData(int(i), copydata)
        wc.CloseClipboard()
        self.SendClipboard()
        return 1

    def SendClipboard(self):
        '''向当前聊天页面发送剪贴板复制的内容'''
        self.SendMsg('{Ctrl}v')
        
    @property
    def GetAllMessage(self):
        '''获取当前窗口中加载的所有聊天记录'''
        MsgDocker = []
        MsgItems = self.MsgList.GetChildren()
        for MsgItem in MsgItems:
            MsgDocker.append(WxUtils.SplitMessage(MsgItem))
        return MsgDocker
    
    @property
    def GetLastMessage(self):
        '''获取当前窗口中最后一条聊天记录'''
        uia.SetGlobalSearchTimeout(1.0)
        MsgItem = self.MsgList.GetChildren()[-1]
        Msg = WxUtils.SplitMessage(MsgItem)
        uia.SetGlobalSearchTimeout(10.0)
        return Msg
    
    def LoadMoreMessage(self, n=0.1):
        '''定位到当前聊天页面，并往上滚动鼠标滚轮，加载更多聊天记录到内存'''
        n = 0.1 if n<0.1 else 1 if n>1 else n
        self.MsgList.WheelUp(wheelTimes=int(500*n), waitTime=0.1)
        
    def SendScreenshot(self, name=None, classname=None):
        '''发送某个桌面程序的截图，如：微信、记事本...
        name : 要发送的桌面程序名字，如：微信
        classname : 要发送的桌面程序类别名，一般配合 spy 小工具使用，以获取类名，如：微信的类名为 WeChatMainWndForPC'''
        if name and classname:
            return 0
        else:
            hwnd = win32gui.FindWindow(classname, name)
        if hwnd:
            WxUtils.Screenshot(hwnd)
            self.SendClipboard()
            return 1
        else:
            return 0
