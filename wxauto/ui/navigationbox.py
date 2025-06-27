from __future__ import annotations
from wxauto.param import (
    WxParam, 
)
from wxauto.languages import *
from wxauto.uiautomation import Control

class NavigationBox:
    def __init__(self, control, parent):
        self.control: Control = control
        self.root = parent.root
        self.parent = parent
        self.top_control = control.GetTopLevelControl()
        self.init()

    def _lang(self, text: str) -> str:
        return WECHAT_NAVIGATION_BOX.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    def init(self):
        self.my_icon = self.control.ButtonControl()
        self.chat_icon = self.control.ButtonControl(Name=self._lang('聊天'))
        self.contact_icon = self.control.ButtonControl(Name=self._lang('通讯录'))
        self.favorites_icon = self.control.ButtonControl(Name=self._lang('收藏'))
        self.files_icon = self.control.ButtonControl(Name=self._lang('聊天文件'))
        self.moments_icon = self.control.ButtonControl(Name=self._lang('朋友圈'))
        self.browser_icon = self.control.ButtonControl(Name=self._lang('搜一搜'))
        self.video_icon = self.control.ButtonControl(Name=self._lang('视频号'))
        self.stories_icon = self.control.ButtonControl(Name=self._lang('看一看'))
        self.mini_program_icon = self.control.ButtonControl(Name=self._lang('小程序面板'))
        self.phone_icon = self.control.ButtonControl(Name=self._lang('手机'))
        self.settings_icon = self.control.ButtonControl(Name=self._lang('设置及其他'))

    def switch_to_chat_page(self):
        self.chat_icon.Click()

    def switch_to_contact_page(self):
        self.contact_icon.Click()

    def switch_to_favorites_page(self):
        self.favorites_icon.Click()

    def switch_to_files_page(self):
        self.files_icon.Click()

    def switch_to_browser_page(self):
        self.browser_icon.Click()

    # 是否有新消息
    def has_new_message(self):
        from wxauto.utils.win32 import capture

        rect = self.chat_icon.BoundingRectangle
        bbox = rect.left, rect.top, rect.right, rect.bottom
        img = capture(self.root.HWND, bbox)
        return any(p[0] > p[1] and p[0] > p[2] for p in img.getdata())