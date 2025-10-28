from wxauto.utils import (
    FindWindow,
    SetClipboardText
)
from wxauto.uia import ControlFromHandle
from wxauto.param import WxResponse
from .component import SelectContactWnd
import time

class WxBrowser:
    _cls_name = 'Chrome_WidgetWin_0'

    def __init__(self):
        hwnd = FindWindow(classname=self._cls_name, name='微信')
        if hwnd:
            self.control = ControlFromHandle(hwnd)
        self.more_button = self.control.PaneControl(searchDepth=1, ClassName='').MenuItemControl(Name="更多")
        self.close_button = self.control.PaneControl(searchDepth=1, ClassName='').ButtonControl(Name="关闭")

    def search(self, url):
        search_btn_eles = [
            i for i in self.control.TabControl().GetChildren() 
            if i.BoundingRectangle.height() == i.BoundingRectangle.width()
        ]
        t0 = time.time()
        while time.time() - t0 < 10:
            if search_btn_eles:
                search_btn_eles[0].Click()
                edit = self.control.TabControl().EditControl(Name='地址和搜索栏')
                SetClipboardText(url)
                edit.ShortcutPaste()
                edit.SendKeys('{Enter}')
                return True
            time.sleep(0.1)
        return False
    
    def forward(self, friend, message: str=None):
        t0 = time.time()
        while True:
            if time.time() - t0 > 10:
                raise
            self.more_button.Click()
            time.sleep(0.5)
            copyurl = self.control.PaneControl(ClassName='Chrome_WidgetWin_0').MenuItemControl(Name='转发给朋友')
            if copyurl.Exists(0):
                copyurl.Click()
                break
            self.control.PaneControl(ClassName='Chrome_WidgetWin_0').SendKeys('{Esc}')
        sendwnd = SelectContactWnd()
        return sendwnd.send(friend, message=message)

    def send_card(self, url, friend):
        try:
            if self.search(url):
                return self.forward(friend)
        except Exception as e:
            return WxResponse.failure(msg=str(e))
        finally:
            self.close()

    def close(self):
        try:
            self.close_button.Click()
        except:
            pass