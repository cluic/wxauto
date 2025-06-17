from __future__ import annotations
from wxauto.ui.component import (
    CMenuWnd
)
from wxauto.param import (
    WxParam, 
    WxResponse,
)
from wxauto.languages import *
from wxauto.utils import (
    SetClipboardText,
)
from wxauto.logger import wxlog
from wxauto.uiautomation import Control
from wxauto.utils.tools import roll_into_view
from typing import (
    List,
    Union
)
import time
import re


class SessionBox:
    def __init__(self, control, parent):
        self.control: Control = control
        self.root = parent.root
        self.parent = parent
        self.top_control = control.GetTopLevelControl()
        self.init()

    def _lang(self, text: str) -> str:
        return WECHAT_SESSION_BOX.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    def init(self):
        self.searchbox = self.control.EditControl(Name=self._lang('搜索'))
        self.session_list =\
            self.control.ListControl(Name=self._lang('会话'), searchDepth=7)
        self.archived_session_list =\
            self.control.ListControl(Name=self._lang('折叠的群聊'), searchDepth=7)

    def get_session(self) -> List[SessionElement]:
        if self.session_list.Exists(0):
            return [SessionElement(i, self) for i in self.session_list.GetChildren()]
        elif self.archived_session_list.Exists(0):
            return [SessionElement(i, self) for i in self.archived_session_list.GetChildren()]
        else:
            return []
    
    def roll_up(self, n: int=5):
        self.control.WheelUp(waitTime=n)

    def roll_down(self, n: int=5):
        self.control.WheelDown(waitTime=n)
    
    def switch_chat(
            self, 
            keywords: str, 
            exact: bool = False,
            force: bool = False,
            force_wait: Union[float, int] = 0.5
        ):
        wxlog.debug(f"切换聊天窗口: {keywords}, {exact}, {force}, {force_wait}")
        self.root._show()
        sessions = self.get_session()
        for session in sessions:
            if (
                keywords == session.name 
                and session.control.BoundingRectangle.height()
            ):
                session.switch()
                return keywords

        self.searchbox.RightClick()
        SetClipboardText(keywords)
        menu = CMenuWnd(self)
        menu.select('粘贴')

        search_result = self.control.ListControl(RegexName='.*?IDS_FAV_SEARCH_RESULT.*?')

        if force:
            time.sleep(force_wait)
            self.searchbox.SendKeys('{ENTER}')
            return ''
        
        t0 = time.time()
        while time.time() -t0 < WxParam.SEARCH_CHAT_TIMEOUT:
            results = []
            search_result_items = search_result.GetChildren()
            highlight_who = re.sub(r'(\s+)', r'</em>\1<em>', keywords)
            for search_result_item in search_result_items:
                item_name = search_result_item.Name
                if (
                    search_result_item.ControlTypeName == 'PaneControl'
                    and search_result_item.TextControl(Name='聊天记录').Exists(0)
                ) or item_name == f'搜索 {keywords}':
                    break
                elif (
                    search_result_item.ControlTypeName == 'ListItemControl'
                    and search_result_item.TextControl(Name=f"微信号: <em>{keywords}</em>").Exists(0)
                ):
                    wxlog.debug(f"{keywords} 匹配到微信号：{item_name}")
                    search_result_item.Click()
                    return item_name
                elif (
                    search_result_item.ControlTypeName == 'ListItemControl'
                    and search_result_item.TextControl(Name=f"昵称: <em>{highlight_who}</em>").Exists(0)
                ):
                    wxlog.debug(f"{keywords} 匹配到昵称：{item_name}")
                    search_result_item.Click()
                    return item_name
                elif (
                    search_result_item.ControlTypeName == 'ListItemControl'
                    and search_result_item.TextControl(Name=f"群聊名称: <em>{highlight_who}</em>").Exists(0)
                ):
                    wxlog.debug(f"{keywords} 匹配到群聊名称：{item_name}")
                    search_result_item.Click()
                    return item_name
                elif (
                    search_result_item.ControlTypeName == 'ListItemControl'
                    and keywords == item_name
                ):
                    wxlog.debug(f"{keywords} 完整匹配")
                    search_result_item.Click()
                    return keywords
                elif (
                    search_result_item.ControlTypeName == 'ListItemControl'
                    and keywords in item_name
                ):
                    results.append(search_result_item)
            
        if exact:
            wxlog.debug(f"{keywords} 未精准匹配，返回None")
            if search_result.Exists(0):
                search_result.SendKeys('{Esc}')
            return None
        if results:
            wxlog.debug(f"{keywords} 匹配到多个结果，返回第一个")
            results[0].Click()
            return results[0].Name
        
        if search_result.Exists(0):
            search_result.SendKeys('{Esc}')


    def open_separate_window(self, name: str):
        wxlog.debug(f"打开独立窗口: {name}")
        sessions = self.get_session()
        for session in sessions:
            if session.name == name:
                wxlog.debug(f"找到会话: {name}")
                while session.control.BoundingRectangle.height():
                    try:
                        session.click()
                        session.double_click()
                    except:
                        pass
                    time.sleep(0.1)
                else:
                    return WxResponse.success(data={'nickname': name})
        wxlog.debug(f"未找到会话: {name}")
        return WxResponse.failure('未找到会话')
    
    def go_top(self):
        wxlog.debug("回到会话列表顶部")
        if self.archived_session_list.Exists(0):
            self.control.ButtonControl(Name=self._lang('返回')).Click()
            time.sleep(0.3)
        first_session_name = self.session_list.GetChildren()[0].Name
        while True:
            self.control.WheelUp(wheelTimes=3)
            time.sleep(0.1)
            if self.session_list.GetChildren()[0].Name == first_session_name:
                break
            else:
                first_session_name = self.session_list.GetChildren()[0].Name


class SessionElement:
    def __init__(
            self, 
            control: Control, 
            parent: SessionBox
        ):
        self.root = parent.root
        self.parent = parent
        self.control = control
        self.name = (
            temp_control.Name 
            if (temp_control := control.GetProgenyControl(4, control_type='TextControl'))
            else None
        )
        self.time = (
            temp_control.Name 
            if (temp_control := control.GetProgenyControl(4, 1, control_type='TextControl')) 
            else None
        )
        self.content = (
            temp_control.Name 
            if (temp_control := control.GetProgenyControl(4, 2, control_type='TextControl')) 
            else None
        )
        self.ismute = (
            True
            if control.GetProgenyControl(4, 1, control_type='PaneControl')
            else False
        )
        self.isnew = (new_tag_control := control.GetProgenyControl(2, 2)) is not None
        self.new_count = 0
        if self.isnew:
            if new_tag_control.Name:
                self.new_count = int(new_tag_control.Name)
            else:
                new_text = re.findall(self._lang('re_条数'), str(self.content))
                if new_text:
                    self.new_count = int(re.findall('\d+', new_text[0])[0])
                    self.content = self.content[len(new_text[0])+1:]
                else: self.new_count = 1
                    

        self.info = {
            'name': self.name,
            'time': self.time,
            'content': self.content,
            'isnew': self.isnew,
            'new_count': self.new_count,
            'ismute': self.ismute
        }

    def _lang(self, text: str) -> str:
        return self.parent._lang(text)
    
    def roll_into_view(self):
        self.root._show()
        roll_into_view(self.control.GetParentControl(), self.control)


    def _click(self, right: bool=False, double: bool=False):
        self.roll_into_view()
        if right:
            self.control.RightClick()
        elif double:
            self.control.DoubleClick()
        else:
            self.control.Click()

    def click(self):
        self._click()

    def right_click(self):
        self._click(right=True)

    def double_click(self):
        self._click(double=True)

    def switch(self):
        self.click()