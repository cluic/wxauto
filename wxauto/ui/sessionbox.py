from __future__ import annotations
from .base import BaseUISubWnd
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
    SetClipboardFiles,
    uilock
)
from wxauto.logger import wxlog
from wxauto.uia import RollIntoView, Control
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
            return [
                SessionElement(i, self) 
                for i in self.session_list.GetChildren()
                if i.Name != self._lang('折叠置顶聊天')
                and not re.match(self._lang('re_置顶聊天'), i.Name)
                and i.BoundingRectangle.height() != 0
            ]
        elif self.archived_session_list.Exists(0):
            return [SessionElement(i, self) for i in self.archived_session_list.GetChildren()]
        else:
            return []
    
    def roll_up(self, n: int=5):
        self.control.MiddleClick()
        self.control.WheelUp(wheelTimes=n)

    def roll_down(self, n: int=5):
        self.control.MiddleClick()
        self.control.WheelDown(wheelTimes=n)

    def search(
            self, 
            keywords: str,
            force: bool = False,
            force_wait: Union[float, int] = 0.5
        ):
        self.searchbox.RightClick()
        SetClipboardText(keywords)
        menu = CMenuWnd(self)
        menu.select('粘贴')

        search_result = self.control.ListControl(RegexName='.*?IDS_FAV_SEARCH_RESULT.*?')

        if force:
            time.sleep(force_wait)

        return [SearchResultElement(i) for i in search_result.GetChildren()]
    
    def switch_chat(
            self, 
            keywords: str, 
            exact: bool = False,
            force: bool = False,
            force_wait: Union[float, int] = 0.5
        ):
        wxlog.debug(f"切换聊天窗口: {keywords}, {exact}, {force}, {force_wait}")

        sessions = self.get_session()
        for session in sessions:
            if (
                keywords == session.name 
                and session.control.BoundingRectangle.height()
            ):
                session.switch()
                return keywords
        
        search_box = self.control.ListControl(RegexName='.*?IDS_FAV_SEARCH_RESULT.*?')
        search_result = self.search(keywords, force, force_wait)

        t0 = time.time()
        while time.time() -t0 < WxParam.SEARCH_CHAT_TIMEOUT:
            results = []
            search_result_items = search_box.GetChildren()
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
            if search_box.Exists(0):
                search_box.SendKeys('{Esc}')
            return None
        if results:
            wxlog.debug(f"{keywords} 匹配到多个结果，返回第一个")
            results[0].Click()
            return results[0].Name
        
        if search_box.Exists(0):
            search_box.SendKeys('{Esc}')

    # @uilock
    def open_separate_window(self, name: str):
        wxlog.debug(f"打开独立窗口: {name}")
        sessions = self.get_session()
        for session in sessions:
            if session.name == name:
                wxlog.debug(f"找到会话: {name}")
                while session.control.BoundingRectangle.height():
                    if self.parent.get_sub_wnd(name):
                        wxlog.debug(f"已打开会话窗口：{name}")
                        return WxResponse.success(data={'nickname': name})
                    # session.click()
                    session.double_click()
                    time.sleep(0.1)
                else:
                    return WxResponse.success(data={'nickname': name})
        wxlog.debug(f"未找到会话: {name}")
        return WxResponse.failure('未找到会话')
    
    def go_top(self):
        wxlog.debug("回到会话列表顶部")
        self.control.MiddleClick()
        self.control.SendKeys('{Home}')

    def open_contact_manager(self):
        wxlog.debug("打开联系人管理")
        while not (contact_btn := self.control.ButtonControl(Name=self._lang('通讯录管理'))).Exists(0):
            self.go_top()
            self.control.WheelUp(wheelTimes=5)
            time.sleep(0.1)
        contact_btn.Click()


class SessionElement:
    def __init__(
            self, 
            control: Control, 
            parent: SessionBox, 
            debug_output: bool=True
        ):
        self.root = parent.root
        self.parent = parent
        self.control = control
        info_controls = [i for i in self.control.GetProgenyControl(3).GetChildren() if i.ControlTypeName=='TextControl']
        self.name = info_controls[0].Name
        self.time = info_controls[-1].Name
        self.content = (
            temp_control.Name 
            if (temp_control := control.GetProgenyControl(4, -1, control_type='TextControl')) 
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
            if new_tag_name := (new_tag_control.Name):
                try:
                    self.new_count = int(new_tag_name)
                    self.ismute = False
                except ValueError:
                    self.new_count = 999
            else:
                new_text = re.findall(self._lang('re_条数'), str(self.content))
                if new_text:
                    try:
                        self.new_count = int(re.findall('\d+', new_text[0])[0])
                    except ValueError:
                        self.new_count = 999
                    self.content = self.content[len(new_text[0])+1:]
                else: 
                    self.new_count = 1
                    

        self.info = {
            'name': self.name,
            'time': self.time,
            'content': self.content,
            'isnew': self.isnew,
            'new_count': self.new_count,
            'ismute': self.ismute,
        }

    def _lang(self, text: str) -> str:
        return self.parent._lang(text)
    
    def __repr__(self):
        content = str(self.content).replace('\n', ' ')
        if len(content) > 5:
            content = content[:5] + '...'
        return f"<wxauto Session Element({self.name} - {content})>"
    
    @property
    def ishide(self):
        return self.control.BoundingRectangle.height() == 0
    
    def roll_into_view(self):
        RollIntoView(self.control.GetParentControl(), self.control)

    # @uilock
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
        self._click()
        self._click(double=True)

    # @uilock
    def delete(self):
        RollIntoView(self.control.GetParentControl(), self.control)
        self.control.RightClick()
        menu = CMenuWnd(self.parent)
        menu.select('删除聊天')
        dialog = self.root.PaneControl(ClassName='WeUIDialog')
        if dialog.Exists(5):
            dialog.ButtonControl(Name='删除').Click()
            return WxResponse.success()
        return WxResponse.failure('删除聊天失败')

    # @uilock
    def hide(self):
        if self.control.BoundingRectangle.height():
            RollIntoView(self.control.GetParentControl(), self.control)
            self.control.RightClick()
            menu = CMenuWnd(self.parent)
            return menu.select('不显示聊天')
        return WxResponse.success()

    # @uilock
    def switch(self):
        if self.control.BoundingRectangle.height():
            self.click()
        else:
            self.parent.switch_chat(self.name)

    def select_option(self, option: str, wait=0.3):
        self.roll_into_view()
        self.control.RightClick()
        time.sleep(wait)
        menu = CMenuWnd(self.parent)
        return menu.select(option)
    
class SearchResultElement:
    def __init__(self, control):
        self.control = control
        self.type = self.control.ControlTypeName.replace('Control', '').lower()
        self.text = self.control.Name
        if self.type == 'pane':
            if (textcontrol := self.control.TextControl()).Exists(0):
                self.text = textcontrol.Name

    def __repr__(self):
        return f'<wxauto Session Search Result [{self.type}]({self.text})>'

    def get_all_text(self):
        return [text for i in self.control.FindAll() if (text := i.Name)]
    
    def click(self):
        RollIntoView(self.control.GetParentControl(), self.control)
        self.control.Click()

    def close(self):
        self.control.SendKeys('{Esc}')