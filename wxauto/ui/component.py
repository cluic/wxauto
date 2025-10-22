from wxauto.utils import (
    FindWindow,
    SetClipboardText,
    ReadClipboardData,
    GetAllWindows,
    GetWindowRect,
    capture
)
from wxauto.param import (
    WxParam, 
    WxResponse,
)
from wxauto.languages import *
from .base import (
    BaseUISubWnd
)
from wxauto.logger import wxlog
from wxauto.uiautomation import (
    ControlFromHandle,
)
from wxauto.utils.tools import (
    get_file_dir,
    roll_into_view,
)
from PIL import Image
from wxauto import uiautomation as uia
import traceback
import shutil
import time

class EditBox:
    ...

class SelectContactWnd(BaseUISubWnd):
    """选择联系人窗口"""
    _ui_cls_name = 'SelectContactWnd'

    def __init__(self, parent):
        self.parent = parent
        self.root = parent.root
        hwnd = FindWindow(self._ui_cls_name, timeout=1)
        if hwnd:
            self.control = ControlFromHandle(hwnd)
        else:
            self.control = parent.root.control.PaneControl(ClassName=self._ui_cls_name, searchDepth=1)
        
        self.editbox = self.control.EditControl()

    def send(self, target):
        if isinstance(target, str):
            SetClipboardText(target)
            while not self.editbox.HasKeyboardFocus:
                self.editbox.Click()
                time.sleep(0.1)
            self.editbox.SendKeys('{Ctrl}a')
            self.editbox.SendKeys('{Ctrl}v')
            checkbox = self.control.ListControl().CheckBoxControl()
            if checkbox.Exists(1):
                checkbox.Click()
                self.control.ButtonControl(Name='发送').Click()
                return WxResponse.success()
            else:
                self.control.SendKeys('{Esc}')
                wxlog.debug(f'未找到好友：{target}')
                return WxResponse.failure(f'未找到好友：{target}')
            
        elif isinstance(target, list):
            n = 0
            fail = []
            multiselect = self.control.ButtonControl(Name='多选')
            if multiselect.Exists(0):
                multiselect.Click()
            for i in target:
                SetClipboardText(i)
                while not self.editbox.HasKeyboardFocus:
                    self.editbox.Click()
                    time.sleep(0.1)
                self.editbox.SendKeys('{Ctrl}a')
                self.editbox.SendKeys('{Ctrl}v')
                checkbox = self.control.ListControl().CheckBoxControl()
                if checkbox.Exists(1):
                    checkbox.Click()
                    n += 1
                else:
                    fail.append(i)
                    wxlog.debug(f"未找到转发对象：{i}")
            if n > 0:
                self.control.ButtonControl(RegexName='分别发送（\d+）').Click()
                if n == len(target):
                    return WxResponse.success()
                else:
                    return WxResponse.success('存在未转发成功名单', data=fail)
            else:
                self.control.SendKeys('{Esc}')
                wxlog.debug(f'所有好友均未未找到：{target}')
                return WxResponse.failure(f'所有好友均未未找到：{target}')
            
class CMenuWnd(BaseUISubWnd):
    _ui_cls_name = 'CMenuWnd'

    def __init__(self, parent):
        self.parent = parent
        self.root = parent.root
        if menulist := [i for i in GetAllWindows() if 'CMenuWnd' in i]:
            self.control = uia.ControlFromHandle(menulist[0][0])
        else:
            self.control = self.root.control.MenuControl(ClassName=self._ui_cls_name)
    
    def _lang(self, text: str) -> str:
        return MENU_OPTIONS.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)
    
    @property
    def option_controls(self):
        return self.control.ListControl().GetChildren()
    
    @property
    def option_names(self):
        return [c.Name for c in self.option_controls]
    
    def select(self, item):
        if not self.exists(0):
            return WxResponse.failure('菜单窗口不存在')
        if isinstance(item, int):
            self.option_controls[item].Click()
            return WxResponse.success()
        
        item = self._lang(item)
        for c in self.option_controls:
            if c.Name == item:
                c.Click()
                return WxResponse.success()
        if self.exists(0):
            self.close()
        return WxResponse.failure(f'未找到选项：{item}')
    
    def close(self):
        try:
            self.control.SendKeys('{ESC}')
        except Exception as e:
            pass

class NetErrInfoTipsBarWnd(BaseUISubWnd):
    _ui_cls_name = 'NetErrInfoTipsBarWnd'

    def __init__(self, parent):
        self.control = parent.root.control.PaneControl(ClassName=self._ui_cls_name)

    def __bool__(self):
        return self.exists(0)
    
class WeChatImage(BaseUISubWnd):
    _ui_cls_name = 'ImagePreviewWnd'

    def __init__(self) -> None:
        self.hwnd = FindWindow(classname=self._ui_cls_name)
        if self.hwnd:
            self.control = ControlFromHandle(self.hwnd)
            self.type = 'image'
            if self.control.PaneControl(ClassName='ImagePreviewLayerWnd').Exists(0):
                self.type = 'video'
            MainControl1 = [i for i in self.control.GetChildren() if not i.ClassName][0]
            self.ToolsBox, self.PhotoBox = MainControl1.GetChildren()
            
            # tools按钮
            self.t_previous = self.ToolsBox.ButtonControl(Name=self._lang('上一张'))
            self.t_next = self.ToolsBox.ButtonControl(Name=self._lang('下一张'))
            self.t_zoom = self.ToolsBox.ButtonControl(Name=self._lang('放大'))
            self.t_translate = self.ToolsBox.ButtonControl(Name=self._lang('翻译'))
            self.t_ocr = self.ToolsBox.ButtonControl(Name=self._lang('提取文字'))
            self.t_save = self.control.ButtonControl(Name=self._lang('另存为...'))
            self.t_qrcode = self.ToolsBox.ButtonControl(Name=self._lang('识别图中二维码'))
    
    def _lang(self, text: str) -> str:
        return IMAGE_WINDOW.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)
    
    def ocr(self, wait=10):
        result = ''
        ctrls = self.PhotoBox.GetChildren()
        if len(ctrls) == 2:
            self.t_ocr.Click()
        t0 = time.time()
        while time.time() - t0 < wait:
            ctrls = self.PhotoBox.GetChildren()
            if len(ctrls) == 3:
                TranslateControl = ctrls[-1]
                result = TranslateControl.TextControl().Name
                if result:
                    return result
            else:
                self.t_ocr.Click()
            time.sleep(0.1)
        return result
    
    def save(self, dir_path=None, timeout=10):
        """保存图片/视频

        Args:
            dir_path (str): 绝对路径，包括文件名和后缀，例如："D:/Images/微信图片_xxxxxx.png"
            timeout (int, optional): 保存超时时间，默认10秒
        
        Returns:
            str: 文件保存路径，即savepath
        """
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        suffix = 'png' if self.type == 'image' else 'mp4'
        filename = f"wxauto_{self.type}_{time.strftime('%Y%m%d%H%M%S')}.{suffix}"
        filepath = get_file_dir(dir_path) / filename
        t0 = time.time()

        SetClipboardText('')
        while True:
            if time.time() - t0 > timeout:
                if self.control.Exists(0):
                    self.control.SendKeys('{Esc}')
                raise TimeoutError('下载超时')
            try:
                self.control.ButtonControl(Name=self._lang('更多')).Click()
                menu = self.control.MenuControl(ClassName='CMenuWnd')
                menu.MenuItemControl(Name=self._lang('复制')).Click()
                clipboard_data = ReadClipboardData()
                path = clipboard_data['15'][0]
                wxlog.debug(f"读取到图片/视频路径：{path}")
                break
            except:
                wxlog.debug(traceback.format_exc())
                time.sleep(0.1)
        shutil.copyfile(path, filepath)
        SetClipboardText('')
        if self.control.Exists(0):
            wxlog.debug("关闭图片窗口")
            self.control.SendKeys('{Esc}')
        return filepath

class NewFriendElement:
    def __init__(self, control, parent):
        self.parent = parent
        self.root = parent.root
        self.control = control
        self.name = self.control.Name
        self.msg = self.control.GetFirstChildControl().PaneControl(SearchDepth=1).GetChildren()[-1].TextControl().Name
        self.NewFriendsBox = self.root.chatbox.control.ListControl(Name='新的朋友').GetParentControl()
        self.status = self.control.GetFirstChildControl().GetChildren()[-1]
        self.acceptable = isinstance(self.status, uia.ButtonControl)
            
    def __repr__(self) -> str:
        return f"<wxauto New Friends Element at {hex(id(self))} ({self.name}: {self.msg})>"
    
    def delete(self):
        wxlog.info(f'删除好友请求: {self.name}')
        roll_into_view(self.NewFriendsBox, self.control)
        self.control.RightClick()
        menu = CMenuWnd(self.root)
        menu.select('删除')

    def reply(self, text):
        wxlog.debug(f'回复好友请求: {self.name}')
        roll_into_view(self.NewFriendsBox, self.control)
        self.control.Click()
        self.root.ChatBox.ButtonControl(Name='回复').Click()
        edit = self.root.ChatBox.EditControl()
        edit.Click()
        edit.SendKeys('{Ctrl}a')
        SetClipboardText(text)
        edit.SendKeys('{Ctrl}v')
        time.sleep(0.1)
        self.root.ChatBox.ButtonControl(Name='发送').Click()
        dialog = self.root.UiaAPI.PaneControl(ClassName='WeUIDialog')
        while edit.Exists(0):
            if dialog.Exists(0):
                systext = dialog.TextControl().Name
                wxlog.debug(f'系统提示: {systext}')
                dialog.SendKeys('{Esc}')
                self.root.ChatBox.ButtonControl(Name='').Click()
                return WxResponse.failure(msg=systext)
            time.sleep(0.1)
        self.root.ChatBox.ButtonControl(Name='').Click()
        return WxResponse.success()
    
    def accept(self, remark=None, tags=None, permission='朋友圈'):
        """接受好友请求
        
        Args:
            remark (str, optional): 备注名
            tags (list, optional): 标签列表
            permission (str, optional): 朋友圈权限, 可选值：'朋友圈', '仅聊天'
        """
        if not self.acceptable:
            wxlog.debug(f"当前好友状态无法接受好友请求：{self.name}")
            return 
        wxlog.debug(f"接受好友请求：{self.name}  备注：{remark} 标签：{tags}")
        self.root._show()
        roll_into_view(self.NewFriendsBox, self.status)
        self.status.Click()
        NewFriendsWnd = self.root.control.WindowControl(ClassName='WeUIDialog')
        tipscontrol = NewFriendsWnd.TextControl(Name="你的联系人较多，添加新的朋友时需选择权限")

        permission_sns = NewFriendsWnd.CheckBoxControl(Name='聊天、朋友圈、微信运动等')
        permission_chat = NewFriendsWnd.CheckBoxControl(Name='仅聊天')
        if tipscontrol.Exists(0.5):
            permission_sns = tipscontrol.GetParentControl().GetParentControl().TextControl(Name='朋友圈')
            permission_chat = tipscontrol.GetParentControl().GetParentControl().TextControl(Name='仅聊天')

        if remark:
            remarkedit = NewFriendsWnd.TextControl(Name='备注名').GetParentControl().EditControl()
            remarkedit.Click()
            remarkedit.SendKeys('{Ctrl}a')
            remarkedit.SendKeys(remark)
        
        if tags:
            tagedit = NewFriendsWnd.TextControl(Name='标签').GetParentControl().EditControl()
            for tag in tags:
                tagedit.Click()
                tagedit.SendKeys(tag)
                NewFriendsWnd.PaneControl(ClassName='DropdownWindow').TextControl().Click()

        if permission == '朋友圈':
            permission_sns.Click()
        elif permission == '仅聊天':
            permission_chat.Click()

        NewFriendsWnd.ButtonControl(Name='确定').Click()

class WeChatLoginWnd(BaseUISubWnd):
    _ui_cls_name = 'WeChatLoginWndForPC'

    def __init__(self):
        self.hwnd = FindWindow(classname=self._ui_cls_name)
        if self.hwnd:
            self.control = ControlFromHandle(self.hwnd)
            self.enter = self.control.ButtonControl(Name=self._lang('进入微信'))
            if self.enter.Exists(0):
                self.type = 'enter'
            else:
                self.qrcode = self.control.ButtonControl(Name=self._lang('二维码'))
                if self.qrcode.Exists(0):
                    self.type = 'qrcode'
            
    def _lang(self, text: str) -> str:
        return WECHAT_LOGINWND.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)
    
    def login_type(self):
        return self.type
    
    def login(self) -> bool:
        self._show()
        if self.type == 'enter':
            self.enter.Click()
            return True
        else:
            return False

    def get_qrcode(self) -> Image.Image:
        self._show()
        if self.type == 'qrcode':
            window_rect = GetWindowRect(self.hwnd)
            win_left, win_top, win_right, win_bottom = window_rect
            
            bbox = win_left + 62, win_top + 88, win_left + 218, win_top + 245
            return capture(self.hwnd, bbox)
        else:
            return None
        

class WeChatBrowser(BaseUISubWnd):
    _ui_cls_name = 'Chrome_WidgetWin_0'
    _ui_name = '微信'

    def __init__(self):
        self.hwnd = FindWindow(classname=self._ui_cls_name, name=self._ui_name)
        if self.hwnd:
            self.control = ControlFromHandle(self.hwnd)

    def _lang(self, text: str) -> str:
        return WECHAT_BROWSER.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    def get_url(self) -> str:
        self._show()
        tab = self.control.TabItemControl()
        if tab.Exists():
            tab.RightClick()
            copy_link_item = uia.MenuItemControl(Name=self._lang('复制链接'))
            if copy_link_item.Exists():
                copy_link_item.Click()
                clipboard_data = ReadClipboardData()
                url = (clipboard_data.get('13') or
                        clipboard_data.get('1') or
                        None)
                SetClipboardText('')
                return url
            else:
                wxlog.debug(f'找不到复制链接菜单项')
        else:
            wxlog.debug(f'找不到标签页')

    def close(self):
        close_button = self.control.ButtonControl(Name=self._lang('关闭'), foundIndex=1)
        if close_button.Exists():
            close_button.Click()
        close_button = self.control.ButtonControl(Name=self._lang('关闭'), foundIndex=2)
        if close_button.Exists():
            close_button.Click()
        close_button = self.control.ButtonControl(Name=self._lang('关闭'), foundIndex=3)
        if close_button.Exists():
            close_button.Click()
