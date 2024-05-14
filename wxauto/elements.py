from . import uiautomation as uia
from .languages import *
from .utils import *
from .color import *
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
    DEFALUT_IMAGE_SAVEPATH = os.path.join(os.getcwd(), '微信图片')

class WeChatBase:
    def _lang(self, text, langtype='MAIN'):
        if langtype == 'MAIN':
            return MAIN_LANGUAGE[text][self.language]
        elif langtype == 'WARNING':
            return WARNING[text][self.language]

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
                winrect = MsgItem.BoundingRectangle
                mid = (winrect.left + winrect.right)/2
                if User.BoundingRectangle.left < mid:
                    if MsgItem.TextControl().BoundingRectangle.top < User.BoundingRectangle.top:
                        name = (User.Name, MsgItem.TextControl().Name)
                    else:
                        name = (User.Name, User.Name)
                else:
                    name = 'Self'
                Msg = [name, MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
            except:
                Msg = ['SYS', MsgItemName, ''.join([str(i) for i in MsgItem.GetRuntimeId()])]
        uia.SetGlobalSearchTimeout(10.0)
        return ParseMessage(Msg)
    
    def _getmsgs(self, msgitems, savepic=False):
        msgs = []
        for MsgItem in msgitems:
            msgs.append(self._split(MsgItem))

        if not [i for i in msgs if i[1] == f"[{self._lang('图片')}]"]:
            return msgs

        if savepic:
            self._show()
            paths = list()
            ImgItems = [i for i in msgitems if i.Name == f"[{self._lang('图片')}]" and i.ButtonControl(Name='').Exists(maxSearchSeconds=0.1)]
            if not ImgItems:
                return msgs
            imgcontrol = ImgItems[0].ButtonControl(Name='')
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
                if imgobj.Next(warning=False):
                    savepath = imgobj.Save()
                    paths.append(savepath)
                else:
                    imgobj.Close()
                    break
            idx = 0
            for msg in msgs:
                if msg[1] == f"[{self._lang('图片')}]":
                    msg.info[1] = paths[idx]
                    msg.content = paths[idx]
                    idx += 1
        return msgs
    

class ChatWnd(WeChatBase):
    def __init__(self, who, language='cn'):
        self.who = who
        self.language = language
        self.UiaAPI = uia.WindowControl(searchDepth=1, ClassName='ChatWnd', Name=who)
        self.editbox = self.UiaAPI.EditControl()
        self.C_MsgList = self.UiaAPI.ListControl()
        self.GetAllMessage()

        self.savepic = False   # 该参数用于在自动监听的情况下是否自动保存聊天图片

    def __repr__(self) -> str:
        return f"<wxauto Chat Window at {hex(id(self))} for {self.who}>"

    def _show(self):
        self.HWND = FindWindow(name=self.who, classname='ChatWnd')
        win32gui.ShowWindow(self.HWND, 1)
        win32gui.SetWindowPos(self.HWND, -1, 0, 0, 0, 0, 3)
        win32gui.SetWindowPos(self.HWND, -2, 0, 0, 0, 0, 3)
        self.UiaAPI.SwitchToThisWindow()

    def AtAll(self, msg=None):
        """@所有人
        
        Args:
            msg (str, optional): 要发送的文本消息
        """
        self._show()
        if not self.editbox.HasKeyboardFocus:
            self.editbox.Click(simulateMove=False)

        self.editbox.SendKeys('@')
        atwnd = self.UiaAPI.PaneControl(ClassName='ChatContactMenu')
        if atwnd.Exists(maxSearchSeconds=0.1):
            atwnd.ListItemControl(Name='所有人').Click(simulateMove=False)
            if msg:
                if not msg.startswith('\n'):
                    msg = '\n' + msg
                self.SendMsg(msg)
            else:
                self.editbox.SendKeys('{Enter}')

    def SendMsg(self, msg, at=None):
        """发送文本消息

        Args:
            msg (str): 要发送的文本消息
            at (str|list, optional): 要@的人，可以是一个人或多个人，格式为str或list，例如："张三"或["张三", "李四"]
        """
        self._show()
        if not self.editbox.HasKeyboardFocus:
            self.editbox.Click(simulateMove=False)

        if at:
            if isinstance(at, str):
                at = [at]
            for i in at:
                self.editbox.SendKeys('@'+i)
                atwnd = self.UiaAPI.PaneControl(ClassName='ChatContactMenu')
                if atwnd.Exists(maxSearchSeconds=0.1):
                    atwnd.SendKeys('{ENTER}')
                    if msg and not msg.startswith('\n'):
                        msg = '\n' + msg

        t0 = time.time()
        while True:
            if time.time() - t0 > 10:
                raise TimeoutError(f'发送消息超时 --> {self.who} - {msg}')
            SetClipboardText(msg)
            self.editbox.SendKeys('{Ctrl}v')
            if self.editbox.GetValuePattern().Value:
                break
        self.editbox.SendKeys('{Enter}')

    def SendFiles(self, filepath):
        """向当前聊天窗口发送文件
        
        Args:
            filepath (str|list): 要复制文件的绝对路径  
            
        Returns:
            bool: 是否成功发送文件
        """
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
            self.editbox.SendKeys('{Ctrl}a', waitTime=0)
            t0 = time.time()
            while True:
                if time.time() - t0 > 10:
                    raise TimeoutError(f'发送文件超时 --> {filelist}')
                SetClipboardFiles(filelist)
                time.sleep(0.2)
                self.editbox.SendKeys('{Ctrl}v')
                if self.editbox.GetValuePattern().Value:
                    break
            self.editbox.SendKeys('{Enter}')
            return True
        else:
            Warnings.lightred('所有文件都无法成功发送', stacklevel=2)
            return False
        
    def GetAllMessage(self, savepic=False):
        '''获取当前窗口中加载的所有聊天记录
        
        Args:
            savepic (bool): 是否自动保存聊天图片
            
        Returns:
            list: 聊天记录信息
        '''
        MsgItems = self.C_MsgList.GetChildren()
        msgs = self._getmsgs(MsgItems, savepic)
        self.lastmsgid = msgs[-1][-1] if msgs else None
        return msgs
    
    def GetNewMessage(self, savepic=False):
        '''获取当前窗口中加载的新聊天记录

        Args:
            savepic (bool): 是否自动保存聊天图片
        
        Returns:
            list: 新聊天记录信息
        '''
        lastmsgid = self.lastmsgid
        msgs = self.GetAllMessage()
        msgids = [i[-1] for i in msgs]
        if lastmsgid:
            index = (msgids.index(lastmsgid) if lastmsgid in msgids else -1)+1
        else:
            index = 0
        MsgItems = self.C_MsgList.GetChildren()[index:]
        newmsgs = self._getmsgs(MsgItems, savepic)
        self.lastmsgid = newmsgs[-1][-1] if newmsgs else lastmsgid
        return newmsgs
    
    def LoadMoreMessage(self):
        """加载当前聊天页面更多聊天信息
        
        Returns:
            bool: 是否成功加载更多聊天信息
        """
        self._show()
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

    def GetGroupMembers(self):
        """获取当前聊天群成员

        Returns:
            list: 当前聊天群成员列表
        """
        ele = self.UiaAPI.PaneControl(searchDepth=7, foundIndex=6).ButtonControl(Name='聊天信息')
        try:
            uia.SetGlobalSearchTimeout(1)
            rect = ele.BoundingRectangle
            Click(rect)
        except:
            return 
        finally:
            uia.SetGlobalSearchTimeout(10)
        roominfoWnd = self.UiaAPI.WindowControl(ClassName='SessionChatRoomDetailWnd', searchDepth=1)
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

class WeChatImage:
    def __init__(self, language='cn') -> None:
        self.language = language
        self.api = uia.WindowControl(ClassName='ImagePreviewWnd', searchDepth=1)
        MainControl1 = [i for i in self.api.GetChildren() if not i.ClassName][0]
        self.ToolsBox, self.PhotoBox = MainControl1.GetChildren()
        
        # tools按钮
        self.t_previous = self.ToolsBox.ButtonControl(Name=self._lang('上一张'))
        self.t_next = self.ToolsBox.ButtonControl(Name=self._lang('下一张'))
        self.t_zoom = self.ToolsBox.ButtonControl(Name=self._lang('放大'))
        self.t_translate = self.ToolsBox.ButtonControl(Name=self._lang('翻译'))
        self.t_ocr = self.ToolsBox.ButtonControl(Name=self._lang('提取文字'))
        self.t_save = self.ToolsBox.ButtonControl(Name=self._lang('另存为...'))
        self.t_qrcode = self.ToolsBox.ButtonControl(Name=self._lang('识别图中二维码'))

    def __repr__(self) -> str:
        return f"<wxauto WeChat Image at {hex(id(self))}>"
    
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
            Warnings.lightred('获取文字识别失败', stacklevel=2)
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
            savepath = os.path.join(WxParam.DEFALUT_IMAGE_SAVEPATH, f"微信图片_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}.jpg")
        if not os.path.exists(os.path.split(savepath)[0]):
            os.makedirs(os.path.split(savepath)[0])
            
        if self.t_zoom.Exists(maxSearchSeconds=5):
            self.t_save.Click(simulateMove=False)
        else:
            raise TimeoutError('下载超时')
        t0 = time.time()
        while True:
            if time.time() - t0 > timeout:
                raise TimeoutError('下载超时')
            handle = FindWindow(name='另存为...')
            if handle:
                break
        t0 = time.time()
        while True:
            if time.time() - t0 > timeout:
                raise TimeoutError('下载超时')
            try:
                edithandle = [i for i in GetAllWindowExs(handle) if i[1] == 'Edit' and i[-1]][0][0]
                savehandle = FindWinEx(handle, classname='Button', name='保存(&S)')[0]
                if edithandle and savehandle:
                    break
            except:
                pass
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
            Warnings.lightred('上一张按钮不可用', stacklevel=2)
            return False
        
    def Next(self, warning=True):
        """下一张"""
        if self.t_next.IsKeyboardFocusable:
            self._show()
            self.t_next.Click(simulateMove=False)
            return True
        else:
            if warning:
                Warnings.lightred('已经是最新的图片了', stacklevel=2)
            return False
        
    def Close(self):
        self._show()
        self.api.SendKeys('{Esc}')
    
class TextElement:
    def __init__(self, ele, wx) -> None:
        self._wx = wx
        chatname = wx.CurrentChat()
        self.ele = ele
        self.sender = ele.ButtonControl(foundIndex=1, searchDepth=2)
        _ = ele.GetChildren()[0].GetChildren()[1].GetChildren()
        if len(_) == 1:
            self.content = _[0].TextControl().Name
            self.chattype = 'friend'
            self.chatname = chatname
        else:
            self.sender_remark = _[0].TextControl().Name
            self.content = _[1].TextControl().Name
            self.chattype = 'group'
            numtext = re.findall(' \(\d+\)', chatname)[-1]
            self.chatname = chatname[:-len(numtext)]
            
        self.info = {
            'sender': self.sender.Name,
            'content': self.content,
            'chatname': self.chatname,
            'chattype': self.chattype,
            'sender_remark': self.sender_remark if hasattr(self, 'sender_remark') else ''
        }

    def __repr__(self) -> str:
        return f"<wxauto Text Element at {hex(id(self))} ({self.sender.Name}: {self.content})>"

class NewFriendsElement:
    def __init__(self, ele, wx):
        self._wx = wx
        self.ele = ele
        self.name = self.ele.Name
        self.msg = self.ele.GetChildren()[0].PaneControl(SearchDepth=1).GetChildren()[-1].TextControl().Name
        self.ele.GetChildren()[-1]
        self.Status = self.ele.GetChildren()[0].GetChildren()[-1]
        self.acceptable = False
        if isinstance(self.Status, uia.ButtonControl):
            self.acceptable = True

    def __repr__(self) -> str:
        return f"<wxauto New Friends Element at {hex(id(self))} ({self.name}: {self.msg})>"

    def Accept(self, remark=None, tags=None):
        """接受好友请求
        
        Args:
            remark (str, optional): 备注名
            tags (list, optional): 标签列表
        """
        self._wx._show()
        self.Status.Click(simulateMove=False)
        NewFriendsWnd = self._wx.UiaAPI.WindowControl(ClassName='WeUIDialog')

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


class ContactWnd:
    def __init__(self):
        self.UiaAPI = uia.WindowControl(ClassName='ContactManagerWindow', searchDepth=1)
        self.Sidebar, _, self.ContactBox = self.UiaAPI.PaneControl(ClassName='', searchDepth=3, foundIndex=3).GetChildren()

    def __repr__(self) -> str:
        return f"<wxauto Contact Window at {hex(id(self))}>"

    def _show(self):
        self.HWND = FindWindow(classname='ContactManagerWindow')
        win32gui.ShowWindow(self.HWND, 1)
        win32gui.SetWindowPos(self.HWND, -1, 0, 0, 0, 0, 3)
        win32gui.SetWindowPos(self.HWND, -2, 0, 0, 0, 0, 3)
        self.UiaAPI.SwitchToThisWindow()

    def GetFriendNum(self):
        """获取好友人数"""
        numText = self.Sidebar.PaneControl(Name='全部').TextControl(foundIndex=2).Name
        return int(re.findall('\d+', numText)[0])
    
    def Search(self, keyword):
        """搜索好友

        Args:
            keyword (str): 搜索关键词
        """
        self.ContactBox.EditControl(Name="搜索").Click(simulateMove=False)
        self.ContactBox.SendKeys('{Ctrl}{A}')
        self.ContactBox.SendKeys(keyword)

    def GetAllFriends(self):
        """获取好友列表"""
        self._show()
        contacts_list = []
        while True:
            contact_ele_list = self.ContactBox.ListControl().GetChildren()
            for ele in contact_ele_list:
                contacts_info = {
                    'nickname': ele.TextControl().Name,
                    'remark': ele.ButtonControl(foundIndex=2).Name,
                    'tags': ele.ButtonControl(foundIndex=3).Name.split('，'),
                }
                if contacts_info.get('remark') in ('添加备注', ''):
                    contacts_info['remark'] = None
                if contacts_info.get('tags') in (['添加标签'], ['']):
                    contacts_info['tags'] = None
                if contacts_info not in contacts_list:
                    contacts_list.append(contacts_info)
            bottom = self.ContactBox.ListControl().GetChildren()[-1].BoundingRectangle.top
            self.ContactBox.WheelDown(wheelTimes=5, waitTime=0.1)
            if bottom == self.ContactBox.ListControl().GetChildren()[-1].BoundingRectangle.top:
                return contacts_list
    
    def Close(self):
        """关闭联系人窗口"""
        self._show()
        self.UiaAPI.SendKeys('{Esc}')


class ContactElement:
    def __init__(self, ele):
        self.element = ele
        self.nickname = ele.TextControl().Name
        self.remark = ele.ButtonControl(foundIndex=2).Name
        self.tags = ele.ButtonControl(foundIndex=3).Name.split('，')

    def __repr__(self) -> str:
        return f"<wxauto Contact Element at {hex(id(self))} ({self.nickname}: {self.remark})>"
    
    def EditRemark(self, remark: str):
        """修改好友备注名
        
        Args:
            remark (str): 新备注名
        """
        self.element.ButtonControl(foundIndex=2).Click(simulateMove=False)
        self.element.SendKeys('{Ctrl}a')
        self.element.SendKeys(remark)
        self.element.SendKeys('{Enter}')


class Message:
    type = 'message'

    def __getitem__(self, index):
        return self.info[index]
    
    def __str__(self):
        return self.content
    
    def __repr__(self):
        return str(self.info[:2])
    

class SysMessage(Message):
    type = 'sys'
    
    def __init__(self, info):
        self.info = info
        self.sender = info[0]
        self.content = info[1]
        self.id = info[-1]
    
    # def __repr__(self):
    #     return f'<wxauto SysMessage at {hex(id(self))}>'
    

class TimeMessage(Message):
    type = 'time'
    
    def __init__(self, info):
        self.info = info
        self.time = ParseWeChatTime(info[1])
        self.sender = info[0]
        self.content = info[1]
        self.id = info[-1]
    
    # def __repr__(self):
    #     return f'<wxauto TimeMessage at {hex(id(self))}>'
    

class RecallMessage(Message):
    type = 'recall'
    
    def __init__(self, info):
        self.info = info
        self.sender = info[0]
        self.content = info[1]
        self.id = info[-1]
    
    # def __repr__(self):
    #     return f'<wxauto RecallMessage at {hex(id(self))}>'
    

class SelfMessage(Message):
    type = 'self'
    
    def __init__(self, info):
        self.info = info
        self.sender = info[0]
        self.content = info[1]
        self.id = info[-1]
    
    # def __repr__(self):
    #     return f'<wxauto SelfMessage at {hex(id(self))}>'
    

class FriendMessage(Message):
    type = 'friend'
    
    def __init__(self, info):
        self.info = info
        self.sender = info[0][0]
        self.sender_remark = info[0][1]
        self.content = info[1]
        self.id = info[-1]
        self.info[0] = info[0][0]
    
    # def __repr__(self):
    #     return f'<wxauto FriendMessage at {hex(id(self))}>'


message_types = {
    'SYS': SysMessage,
    'Time': TimeMessage,
    'Recall': RecallMessage,
    'Self': SelfMessage
}

def ParseMessage(data):
    return message_types.get(data[0], FriendMessage)(data)
