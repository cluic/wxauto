from .base import BaseUISubWnd
from wxauto.ui.component import (
    CMenuWnd,
    ProfileWnd,
    AddMemberWnd,
    SelectContactWnd,
    AlertDialog,
    WeChatDialog
)
from wxauto.param import (
    WxParam, 
    WxResponse,
)
from wxauto.languages import *
from wxauto.utils import (
    SetClipboardText,
    SetClipboardFiles,
    GetAllWindowExs,
    ReadClipboardData,
    uilock
)
from wxauto.msgs import parse_msg
from wxauto import uia
from wxauto.logger import wxlog
from wxauto.uia import RollIntoView, Control
from typing import Union, List,Literal
import threading
import time
import os
import re

def truncate_string(s: str, n: int=8) -> str:
    s = s.replace('\n', '').strip()
    return s if len(s) <= n else s[:n] + '...'

USED_MSG_IDS = {}

class ChatBox:
    def __init__(self, control: uia.Control, parent):
        self.control: Control = control
        self.root = parent
        self.parent = parent  # `wx` or `chat`
        self.init()

    def init(self):
        self.msgbox = self.control.ListControl(Name=self._lang("消息"))
        self.editbox = self.control.EditControl()
        self.sendbtn = self.control.ButtonControl(Name=self._lang('发送'))
        self.tools = self.control.PaneControl().ToolBarControl()
        self._empty = False   # 用于记录是否为完全没有聊天记录的窗口，因为这种窗口之前有不会触发新消息判断的问题
        if (cid := self.id) and cid not in USED_MSG_IDS:
            # print("init chatbox", cid)
            USED_MSG_IDS[cid] = tuple((i.runtimeid for i in self.msgbox.GetChildren()))
            if not USED_MSG_IDS[cid]:
                self._empty = True

    def _lang(self, text: str) -> str:
        return WECHAT_CHAT_BOX.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)
    
    def _update_used_msg_ids(self):
        USED_MSG_IDS[self.id] = tuple((i.runtimeid for i in self.msgbox.GetChildren()))
    
    # @uilock
    def _open_chat_more_info(self):
        for chatinfo_control, depth in self.control.Walk():
            if chatinfo_control.Name == self._lang('聊天信息'):
                chatinfo_control.Click()
                break
        else:
            wxlog.debug("未找到聊天信息按钮")
            return WxResponse.failure('未找到聊天信息按钮')
        return ChatRoomDetailWnd(self)
    
    # @uilock
    def _activate_editbox(self):
        if not self.editbox.HasKeyboardFocus:
            self.editbox.MiddleClick()

    @property
    def who(self):
        if hasattr(self, '_who'):
            return self._who
        self._who = self.editbox.Name
        return self._who

    @property
    def id(self):
        if self.msgbox.Exists(0):
            return self.msgbox.runtimeid
        return None

    @property
    def used_msg_ids(self):
        if self.id not in USED_MSG_IDS:
            USED_MSG_IDS[self.id] = tuple()
        return USED_MSG_IDS[self.id]
    
    def get_info(self):
        chat_info = {}
        walk = self.control.Walk()
        for chat_name_control, depth in walk:
            if isinstance(chat_name_control, uia.TextControl):
                break
        if (
            not isinstance(chat_name_control, uia.TextControl)
            or depth < 8
        ):
            return {}
        
        # chat_name_control = self.control.GetProgenyControl(11)
        chat_name_control_list = chat_name_control.GetParentControl().GetChildren()
        chat_name_control_count = len(chat_name_control_list)
        
        if chat_name_control_count == 1:
            if self.control.ButtonControl(Name='公众号主页', searchDepth=9).Exists(0):
                chat_info['chat_type'] = 'official'
            else:
                chat_info['chat_type'] = 'friend'
            chat_info['chat_name'] = chat_name_control.Name
        elif chat_name_control_count >= 2:
            try:
                second_text = chat_name_control_list[1].Name
                if second_text.startswith('@'):
                    chat_info['company'] = second_text
                    chat_info['chat_type'] = 'service'
                    chat_info['chat_name'] = chat_name_control.Name
                else:
                    chat_info['group_member_count'] =\
                        int(second_text.replace('(', '').replace(')', ''))
                    chat_info['chat_type'] = 'group'
                    chat_info['chat_name'] =\
                        chat_name_control.Name.replace(second_text, '')
            except:
                chat_info['chat_type'] = 'friend'
                chat_info['chat_name'] = chat_name_control.Name
            
            ori_chat_name_control =\
                chat_name_control.GetParentControl().\
                    GetParentControl().TextControl(searchDepth=1)
            if ori_chat_name_control.Exists(0):
                chat_info['chat_remark'] = chat_info['chat_name']
                chat_info['chat_name'] = ori_chat_name_control.Name
        self._info = chat_info
        return chat_info
    
    # @uilock
    def input_at(self, at_list):
        if isinstance(at_list, str):
            at_list = [at_list]
        self._activate_editbox()
        for friend in at_list:
            self.editbox.Input('@'+friend.replace(' ', ''))
            atmenu = AtMenu(self)
            atmenu.select(friend)

    # @uilock
    def clear_edit(self):
        self.editbox.ShortcutSelectAll()
        self.editbox.SendKeys('{DELETE}')

    # @uilock
    def send_text(self, content: str):
        t0 = time.time()
        while True:
            if time.time() - t0 > 10:
                return WxResponse.failure(f'Timeout --> {self.who} - {content}')
            SetClipboardText(content)
            # self._activate_editbox()
            self.editbox.ShortcutPaste(click=False)
            if self.editbox.GetValuePattern().Value.replace('￼', ''):
                break
            self.editbox.ShortcutPaste(click=True)
            if self.editbox.GetValuePattern().Value.replace('￼', ''):
                break
            self.editbox.RightClick(pos='right')
            menu = CMenuWnd(self)
            menu.select('粘贴')
            if self.editbox.GetValuePattern().Value.replace('￼', ''):
                break
        t0 = time.time()
        while self.editbox.GetValuePattern().Value:
            if time.time() - t0 > 10:
                return WxResponse.failure(f'Timeout --> {self.who} - {content}')
            if (toast := self.root.control.PaneControl(ClassName='ToastWnd', searchDepth=2)).Exists(0):
                toast.SendKeys('{Esc}')
                return self.send_text(content)
            self._activate_editbox()

            self.sendbtn.Click()
            # time.sleep(0.2)
        return WxResponse.success(f"success")
    
    # @uilock
    def typing_text(self, content: str):
        def split_content(s):
            pattern = re.compile(r'\{@.*?\}')
            result = []
            last_index = 0
            for match in pattern.finditer(s):
                start, end = match.span()
                if last_index < start:
                    result.append(('text', s[last_index:start]))
                result.append(('at', s[start+2:end-1]))
                last_index = end
            if last_index < len(s):
                result.append(('text', s[last_index:]))
            return result
        content_list = split_content(content)
        for tag, text in content_list:
            if tag == 'text':
                self.editbox.Input(text)
            elif tag == 'at':
                self.input_at(text)
        self.sendbtn.Click()
        return WxResponse.success(f"success")

    # @uilock
    def send_msg(self, content: str, clear: bool=True, at=None, typing: bool=False):
        wxlog.debug(f"发送消息: {content}")
        if not content and not at:
            return WxResponse.failure(f"`content` and `at` can't be empty at the same time")
        
        if clear:
            self.clear_edit()
        if at:
            self.input_at(at)

        if typing:
            return self.typing_text(content)
        else:
            return self.send_text(content)

    @uilock
    def send_file(self, file_path):
        wxlog.debug(f"发送文件: {file_path}")
        if isinstance(file_path, str):
            file_path = [file_path]
        file_path = [os.path.abspath(f) for f in file_path]
        
        self.clear_edit()
        t0 = time.time()
        while True:
            if time.time() - t0 > WxParam.SEND_FILE_TIMEOUT:
                return WxResponse.failure(f'SendFiles Timeout --> {self.who} - {file_path}')
            SetClipboardFiles(file_path)
            wxlog.debug(f"clipboard data: {str(ReadClipboardData())[:500]}")
            if self.editbox.GetValuePattern().Value:
                break
            self.editbox.ShortcutPaste(click=False)
            if self.editbox.GetValuePattern().Value:
                wxlog.debug(f"shortcut paste success")
                break
            self.editbox.ShortcutPaste(click=True)
            if self.editbox.GetValuePattern().Value:
                wxlog.debug(f"click and shortcut paste success")
                break
            self.editbox.RightClick(pos='right')
            menu = CMenuWnd(self)
            menu.select('粘贴')
            if self.editbox.GetValuePattern().Value:
                wxlog.debug(f"right click and paste option success")
                break
            wxlog.debug(f"editbox value: {self.editbox.GetValuePattern().Value}")
            time.sleep(0.1)

        while True:
            if self.editbox.GetValuePattern().Value:
                self.sendbtn.Click()
            else:
                return WxResponse.success(f"success")

    def at_all(self, msg):
        wxlog.debug(f"@所有人：{self.who} --> {msg}")
        
        if not self.editbox.HasKeyboardFocus:
            self.editbox.Click()

        self.editbox.Input('@')
        atmenu = AtMenu(self)
        if not atmenu.select('所有人'):
            return WxResponse.failure("当前无法@所有人")
        if msg:
            if not msg.startswith('\n'):
                msg = '\n' + msg
            self.send_text(msg)
            return WxResponse.success()
        else:
            self.sendbtn.Click()
            return WxResponse.success()

    # @uilock
    def send_emotion(self, index):
        self.tools.ButtonControl(Name=self._lang('表情')).Click()
        emotion_wnd = EmotionWnd(self.parent.control)
        emotion_wnd.switch_to_my_favorite()
        return emotion_wnd.select_emotion(index)
    
    def load_more(self, interval=0.3):
        msg_len = len(self.msgbox.GetChildren())
        loadmore = self.msgbox.GetChildren()[0]
        loadmore_top = loadmore.BoundingRectangle.top
        while True:
            if len(self.msgbox.GetChildren()) > msg_len:
                isload = True
                break
            else:
                msg_len = len(self.msgbox.GetChildren())
                self.msgbox.WheelUp(wheelTimes=10)
                time.sleep(interval)
                if self.msgbox.GetChildren()[0].BoundingRectangle.top == loadmore_top\
                    and len(self.msgbox.GetChildren()) == msg_len:
                    isload = False
                    break
                else:
                    loadmore_top = self.msgbox.GetChildren()[0].BoundingRectangle.top
                    
        self.msgbox.WheelUp(wheelTimes=1, waitTime=0.1)
        if isload:
            return WxResponse.success()
        else:
            return WxResponse.failure("没有更多消息了")
    
    # @uilock
    def get_msgs(self):
        if self.msgbox.Exists(0):
            return [
                parse_msg(msg_control, self) 
                for msg_control 
                in self.msgbox.GetChildren()
                if msg_control.ControlTypeName in ('ListItemControl', 'CheckBoxControl')
            ]
        return []
    
    def get_new_msgs(self):
        if not self.msgbox.Exists(0):
            return []
        msg_controls = self.msgbox.GetChildren()
        now_msg_ids = tuple((i.runtimeid for i in msg_controls))
        if not now_msg_ids:  # 当前没有消息id
            return []
        if self._empty and self.used_msg_ids:
            self._empty = False
        if not self._empty and (
            (not self.used_msg_ids and now_msg_ids)  # 没有使用过的消息id，但当前有消息id
            or now_msg_ids[-1] == self.used_msg_ids[-1] # 当前最后一条消息id和上次一样
            or not set(now_msg_ids)&set(self.used_msg_ids)  # 当前消息id和上次没有交集
        ):
            # wxlog.debug('没有新消息')
            return []
        
        used_msg_ids_set = set(self.used_msg_ids)
        last_one_msgid = max(
            (x for x in now_msg_ids if x in used_msg_ids_set), 
            key=self.used_msg_ids.index, default=None
        )
        new1 = [x for x in now_msg_ids if x not in used_msg_ids_set]
        new2 = now_msg_ids[now_msg_ids.index(last_one_msgid) + 1 :]\
            if last_one_msgid is not None else []
        new = [i for i in new1 if i in new2] if new2 else new1
        USED_MSG_IDS[self.id] = tuple(self.used_msg_ids + tuple(new))[-100:]
        new_controls = [i for i in msg_controls if i.runtimeid in new]
        self.msgbox.MiddleClick()
        return [
                parse_msg(msg_control, self) 
                for msg_control 
                in new_controls
                if msg_control.ControlTypeName == 'ListItemControl'
            ]
    
    def get_msg_by_id(self, msg_id: str):
        if not self.msgbox.Exists(0):
            return []
        msg_controls = self.msgbox.GetChildren()
        if control_list := [i for i in msg_controls if i.runtimeid == msg_id]:
            return parse_msg(control_list[0], self)

    def _get_tail_after_nth_match(self, msgs, last_msg, n):
        matches = [
            i for i, msg in reversed(list(enumerate(msgs))) 
            if msg.content == last_msg
        ]
        if len(matches) >= n:
            wxlog.debug(f'匹配到基准消息：{last_msg}')
        else:
            split_last_msg = last_msg.split('：')
            nickname = split_last_msg[0]
            content = ''.join(split_last_msg[1:])
            matches = [
                i for i, msg in reversed(list(enumerate(msgs))) 
                if msg.content == content
                and msg.sender_remark == nickname
            ]
            if len(matches) >= n:
                wxlog.debug(f'匹配到基准消息：<{nickname}> {content}')
            else:
                wxlog.debug(f"未匹配到基准消息，以最后一条消息为基准：{msgs[-1].content}")
                matches = [
                    i for i, msg in reversed(list(enumerate(msgs))) 
                    if msg.attr in ('self', 'friend')
                ]
        try:
            index = matches[n - 1]
            return msgs[index:]
        except IndexError:
            wxlog.debug(f"未匹配到第{n}条消息，返回空列表")
            return []
    
    def get_next_new_msgs(self, count=None, last_msg=None):
        # 1. 消息列表不存在，则返回空列表
        if not self.msgbox.Exists(0):
            wxlog.debug('消息列表不存在，返回空列表')
            return []
        
        # 2. 判断是否有新消息按钮，有的话点一下
        load_new_button = self.control.ButtonControl(RegexName=self._lang('re_新消息按钮'))
        if load_new_button.Exists(0): 
            wxlog.debug('检测到新消息按钮，点击加载新消息')
            load_new_button.Click()
            time.sleep(0.5)
        t0 = time.time()
        while True:
            msg_controls = self.msgbox.GetChildren()
            if len(msg_controls) > count:
                break
            if time.time() - t0 > 3:
                count = len(msg_controls)
                break
        _used_msg_ids = self.used_msg_ids
        USED_MSG_IDS[self.id] = tuple((i.runtimeid for i in msg_controls))
        msgs = [
            parse_msg(msg_control, self)
            for msg_control
            in msg_controls
            if msg_control.ControlTypeName == 'ListItemControl'
        ]

        # 3. 如果有“以下是新消息”标志，则直接返回该标志下的所有消息即可
        index = next((
            i for i, msg in enumerate(msgs) 
            if self._lang('以下为新消息') == msg.content
        ), None)
        if index is not None:
            new_msgs = msgs[index:]
            return_msgs = [msg for msg in new_msgs if msg.id not in _used_msg_ids]
            wxlog.debug(f'获取以下是新消息下的所有消息(index: {index}, len: {len(return_msgs)})')
            return return_msgs
        
        # 4. 根据会话列表传入的消息数量和最后一条新消息内容来判断新消息
        if count and last_msg:
            wxlog.debug(f'获取{count}条新消息，基准消息内容为：{last_msg}')
            return self._get_tail_after_nth_match(msgs, last_msg, count)
        
                
    def get_group_members(self):
        roominfoWnd = self._open_chat_more_info()
        if isinstance(roominfoWnd, WxResponse):
            wxlog.debug('获取群成员失败，未找到群信息窗口')
            return []
        return roominfoWnd.get_group_members()
    
    def remove_group_members(self, members):
        if isinstance(members, str):
            members = [members]
        roominfoWnd = self._open_chat_more_info()
        result = roominfoWnd.remove_member(members)
        roominfoWnd.close()
        return result
    
    def add_friend_from_group(
        self, 
        index,
        addmsg=None,
        remark=None, 
        tags=None, 
        permission: Literal['朋友圈', '仅聊天'] = '朋友圈'
    ):
        self.root._show()
        roominfoWnd = self._open_chat_more_info()
        if isinstance(roominfoWnd, WxResponse):
            return roominfoWnd
        return roominfoWnd.add_friend(index, addmsg, remark, tags, permission)
    
    def get_group_member_info(self, index):
        self.root._show()
        roominfoWnd = self._open_chat_more_info()
        if isinstance(roominfoWnd, WxResponse):
            return roominfoWnd
        return roominfoWnd.get_member_info(index)
        
    def add_group_members(
        self, 
        members: Union[str, List[str]],
        reason: str = None
    ) -> WxResponse:
        roominfoWnd = self._open_chat_more_info()
        if isinstance(roominfoWnd, WxResponse):
            return roominfoWnd
        if isinstance(members, str):
            members = [members]
        result = roominfoWnd.add_member(members, reason)
        roominfoWnd.close()
        return result

    def manage_friend(
        self,
        remark: str = None,
        tags: List[str] = None,
    ):
        if self.get_info()['chat_type'] != 'friend':
            return WxResponse.failure('当前聊天对象不是好友')
        self.root._show()
        roominfoWnd = self._open_chat_more_info()
        member: uia.Control = roominfoWnd.get_group_members(True)[0]
        member.Click()
        profilewnd = ProfileWnd(self)
        result = profilewnd.modify_remark_tags(remark, tags)
        roominfoWnd.close()
        return result
    
    def manage_group(
        self,
        name: str = None,
        remark: str = None,
        myname: str = None,
        notice: str = None,
        quit: bool = False,
    ):
        if self.get_info()['chat_type'] != 'group':
            return WxResponse.failure('当前聊天对象不是群聊')
        self.root._show()
        roominfoWnd = self._open_chat_more_info()
        if quit:
            roominfoWnd.close()
            return roominfoWnd.quit()
        else:
            result = {}
            if name:
                result['name'] = roominfoWnd.edit_group_name(name)
            if remark:
                result['remark'] = roominfoWnd.edit_remark(remark)
            if myname:
                result['myname'] = roominfoWnd.edit_my_name(myname)
            if notice:
                result['notice'] = roominfoWnd.edit_group_notice(notice)
            roominfoWnd.close()
            return WxResponse.success(data=result)
        
    def merge_and_forward(
        self,
        targets: Union[List[str], str],
        message:str=None
    ):
        wxlog.debug('转发合并消息')
        option_panel = self.control.ToolBarControl(Name=self._lang('多选'), searchDepth=9)
        if not option_panel.Exists(0):
            return WxResponse.failure('请先选择要合并转发的消息')
        if isinstance(targets, str):
            targets = [targets]
        option_panel.ButtonControl(Name=self._lang('合并转发')).Click()
        forwardWnd = SelectContactWnd(self.root)
        t0 = time.time()
        while True:
            if time.time() - t0 > 10:
                if option_panel.Exists(0):
                    option_panel.ButtonControl(Name=self._lang("关闭多选")).Click()
                return WxResponse.failure('合并转发超时')
            if forwardWnd.exists():
                wxlog.debug('获取到转发窗口')
                return forwardWnd.send(targets, message=message)
            if (alert := AlertDialog(self.root)).exists():
                wxlog.debug('获取到警告窗口')
                alert_text = ''.join(alert.get_all_text())
                alert.control.ButtonControl().Click()
                if option_panel.Exists(0):
                    option_panel.ButtonControl(Name=self._lang("关闭多选")).Click()
                return WxResponse.failure(alert_text)

    def get_top_msgs(self) -> List['TopMsg']:
        top_items = []
        if (
            (controls := self.control.GetProgenyControl(5).GetChildren())
            and len(controls) > 1
        ):
            top_control = controls[-1]
            if top_control.ButtonControl(Name='移除').Exists(0):
                return [TopMsg(self, top_control)]
            top_control.ButtonControl().Click()

            if (topmsgwnd := self.root.control.PaneControl(ClassName='ChatRoomTopMsgWnd', searchDepth=3)).Exists(0):
                top_items = [TopMsg(self, i) for i in topmsgwnd.ListControl().GetChildren()]
        return top_items

class TopMsg:
    def __init__(self, parent, control):
        self.parent = parent
        self.root = parent.root
        self.control = control
        self.content = self.control.ButtonControl().Name

    def __repr__(self):
        content = truncate_string(self.content, 8)
        return f"<wxauto Top Message ({content}) at {hex(id(self))}>"

    def remove(self):
        if (remove_btn := self.control.ButtonControl(Name='移除')).Exists(0):
            remove_btn.Click()
            dialog = WeChatDialog(self)
            dialog.click_button('移除')
            return WxResponse.success()
        return WxResponse.failure('移除按钮不存在')

class EmotionWnd(BaseUISubWnd):
    _ui_cls_name: str = 'EmotionWnd'

    def __init__(self, control):
        # self.root = parent.root
        self.control = control.PaneControl(ClassName='EmotionWnd')

    def _lang(self, text: str) -> str:
        return EMOTION_WINDOW.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    def switch_to_my_favorite(self):
        my_emotion_icon = self.control.CheckBoxControl(Name=self._lang('添加的单个表情'))
        while not my_emotion_icon.Exists(0):
            self.control.CheckBoxControl().GetParentControl().WheelUp(wheelTimes=10)
        my_emotion_icon.Click(move=False, simulateMove=False, return_pos=False)

    # @uilock
    def select_emotion(self, index):
        emotion_list = self.control.ListControl()
        while not emotion_list.TextControl(Name="添加的单个表情").Exists(0):
            emotion_list.WheelUp(wheelTimes=10)

        emotions = emotion_list.GetChildren()[1:]
        amount = len(emotions)
        last_one = emotions[-1]
        top0 = emotions[0].BoundingRectangle.top
        for idx, e in enumerate(emotions):
            if e.BoundingRectangle.top != top0:
                break

        def next_page(index, emotion_list, emotions, last_one, idx, amount):
            if index < len(emotions):
                time.sleep(1)
                emotion = emotions[index]
                return emotion
            else:
                while True:
                    position = last_one.BoundingRectangle.top
                    emotions = emotion_list.GetChildren()
                    if last_one.GetRuntimeId() == emotions[idx-1].GetRuntimeId():
                        break
                    emotion_list.WheelDown()
                    time.sleep(0.05)
                    if position == last_one.BoundingRectangle.top:
                        return
                fourth = emotions[idx*2- 1]
                while True:
                    position = fourth.BoundingRectangle.top
                    emotions = emotion_list.GetChildren()
                    if fourth.GetRuntimeId() == emotions[idx-1].GetRuntimeId():
                        new_index = index - amount
                        last_one = emotions[-1]
                        amount = len(emotions)
                        return next_page(new_index, emotion_list, emotions, last_one, idx, amount)
                    emotion_list.WheelDown()
                    time.sleep(0.005)
                    if position == fourth.BoundingRectangle.top:
                        return

        emotion = next_page(index, emotion_list, emotions, last_one, idx, amount)
        if emotion is not None:
            RollIntoView(emotion_list, emotion)
            emotion.Click()
            return WxResponse.success()
        else:
            wxlog.debug(f'未找到表情索引：{index}')
            self.control.SendKeys('{Esc}')
            return WxResponse.failure(f'Not found the index of the emotion: {index}')


class ChatRoomDetailWnd(BaseUISubWnd):
    _ui_cls_name: str = 'SessionChatRoomDetailWnd'

    def __init__(self, parent):
        self.parent = parent
        self.root = parent.root
        self.control = self.root.control.Control(ClassName=self._ui_cls_name, searchDepth=1)

    def _lang(self, text: str) -> str:
        return CHATROOM_DETAIL_WINDOW.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    # @uilock
    def _edit(self, key, value):
        wxlog.debug(f'修改{key}为`{value}`')
        btn = self.control.TextControl(Name=key).GetParentControl().ButtonControl(Name=key)
        if btn.Exists(0):
            RollIntoView(self.control, btn)
            btn.Click()
        else:
            wxlog.debug(f'当前非群聊，无法修改{key}')
            return WxResponse.failure(f'Not a group chat, cannot modify `{key}`')
        while True:
            edit_hwnd_list = [
                i[0] 
                for i in GetAllWindowExs(self.control.NativeWindowHandle) 
                if i[1] == 'EditWnd'
            ]
            if edit_hwnd_list:
                edit_hwnd = edit_hwnd_list[0]
                break
            btn.Click()
        edit_win32 = uia.Win32(edit_hwnd)
        edit_win32.shortcut_select_all()
        edit_win32.send_keys_shortcut('{DELETE}')
        edit_win32.input(value)
        edit_win32.send_keys_shortcut('{ENTER}')
        return WxResponse.success()
    
    def add_member(
            self, 
            members: Union[str, List[str]],
            reason: str = None
        ) -> WxResponse:
        """添加群成员
        
        Args:
            members (str | list[str]): 群成员的昵称或微信号
            reason (str, optional): 添加理由. Defaults to None.

        Returns:
            WxResponse: 操作结果
        """
        if isinstance(members, str):
            members = [members]
        self.control.ButtonControl(Name=self._lang('添加')).GetParentControl().GetChildren()[0].Click()
        addWnd = AddMemberWnd(self)
        for member in members:
            addWnd.add(member)
            time.sleep(0.3)
        if addWnd.selected_members_count() == 0:
            addWnd.close()
            return WxResponse.failure('没有找到成员')
        time.sleep(0.5)
        try:
            submit_result = addWnd.submit()
        except:
            submit_result = WxResponse.failure('意外错误')
        if (reason_result := addWnd.reason(reason)) is not None:
            return reason_result
        return submit_result
    
    def remove_member(self, members: Union[str, List[str]]) -> WxResponse:
        """移除群成员

        Args:
            members (str | list[str]): 群成员的昵称或微信号

        Returns:
            WxResponse: 操作结果
        """
        if isinstance(members, str):
            members = [members]
        self.control.ButtonControl(Name=self._lang('移出')).GetParentControl().GetChildren()[0].Click()
        removeWnd = DeleteMemberWnd(self)
        for member in members:
            removeWnd.remove(member)
        if removeWnd.selected_members_count() == 0:
            removeWnd.close()
            return WxResponse.failure('没有找到成员')
        removeWnd.submit()
        if removeWnd.exists():
            return WxResponse.failure('移除失败')
        return WxResponse.success()
        

    
    def edit_group_name(self, new_name: str) -> WxResponse:
        """编辑群聊名称
        
        Args:
            new_name (str): 新的群聊名称
        """
        key = self._lang('群聊名称')
        return self._edit(key, new_name)

    def edit_remark(self, remark):
        """编辑群聊备注
        
        Args:
            remark (str): 新的群聊备注
        """
        if self.control.TextControl(Name=self._lang('仅群主或管理员可以修改')).Exists(0):
            wxlog.debug('当前用户无权限修改群聊备注')
            return False
        key = self._lang('备注')
        return self._edit(key, remark)

    def edit_my_name(self, my_name):
        """编辑我在本群的昵称
        
        Args:
            my_name (str): 新的昵称
        """
        key = self._lang('我在本群的昵称')
        return self._edit(key, my_name)

    def edit_group_notice(self, notice: Union[str, List[str]]) -> WxResponse:
        """编辑群公告
        
        Args:
            notice (str | list): 新的群公告
        """
        self.control.TextControl(Name=self._lang('群公告')).\
            GetParentControl().ButtonControl(Name=self._lang('点击编辑群公告')).Click()
        announcementwnd = uia.WindowControl(ClassName='ChatRoomAnnouncementWnd', searchDepth=1)
        if announcementwnd.TextControl(Name=self._lang("仅群主和管理员可编辑")).Exists(0):
            wxlog.debug('当前用户无权限修改群公告')
            announcementwnd.SendKeys('{Esc}')
            return False
        edit_btn_control = announcementwnd.ButtonControl(Name=self._lang('编辑'))
        if edit_btn_control.Exists(0):
            edit_btn_control.Click()
        edit = announcementwnd.EditControl()
        edit.Click()
        edit.ShortcutSelectAll(click=False)
        if isinstance(notice, str):
            # edit.Input(notice)
            SetClipboardText(notice)
            edit.ShortcutPaste(click=False)
        elif isinstance(notice, list) and notice:
            SetClipboardText(notice[0])
            edit.ShortcutPaste(click=False)
            for i in notice[1:]:
                announcementwnd.ButtonControl(Name=self._lang('分隔线')).Click()
                SetClipboardText(i)
                edit.ShortcutPaste(click=False)
        announcementwnd.ButtonControl(Name=self._lang('完成')).Click()
        announcementwnd.PaneControl(ClassName='WeUIDialog').ButtonControl(Name=self._lang('发布')).Click()
        return WxResponse.success()

    def get_group_members(self, control=False):
        """获取群成员"""
        wxlog.debug('获取群成员')
        more = self.control.ButtonControl(Name=self._lang('查看更多'), searchDepth=8)
        if more.Exists(0.5):
            more.Click()
        members = [i for i in self.control.ListControl(Name=self._lang('聊天成员')).GetChildren()]
        while members[-1].Name in [self._lang('添加'), self._lang('移出')]:
            members = members[:-1]
        if control:
            return members
        member_names = [i.Name for i in members]
        self.close()
        return member_names
    
    def add_friend(
            self, 
            index,
            addmsg: str=None,
            remark: str=None, 
            tags: List[str]=None, 
            permission: Literal['朋友圈', '仅聊天'] = '朋友圈'
        ):
        """添加好友"""
        more = self.control.ButtonControl(Name=self._lang('查看更多'), searchDepth=8)
        t0 = time.time()
        while True:
            if time.time() - t0 > 10: 
                return WxResponse.failure(self._lang('添加好友超时'))
            if more.Exists(0.5):
                more.Click()
            group_member_window = self.control.ListControl(Name=self._lang('聊天成员'))
            if group_member_window.Exists(0.5):
                break
        members = [i for i in group_member_window.GetChildren()]
        while members[-1].Name in [self._lang('添加'), self._lang('移出')]:
            members = members[:-1]
        # time.sleep(1)
        RollIntoView(self.control, members[index], bias=100)
        # more = self.control.ButtonControl(Name=self._lang('查看更多'), searchDepth=8)
        # if more.Exists(0.5):
        #     more.Click()
        group_member = GroupMemberElement(members[index], self)
        result = group_member.add_friend(addmsg, remark, tags, permission)
        self.close()
        return result
    
    def get_member_info(self, index: int):
        more = self.control.ButtonControl(Name=self._lang('查看更多'), searchDepth=8)
        t0 = time.time()
        while True:
            if time.time() - t0 > 10: 
                return WxResponse.failure(self._lang('添加好友超时'))
            if more.Exists(0.5):
                more.Click()
            group_member_window = self.control.ListControl(Name=self._lang('聊天成员'))
            if group_member_window.Exists(0.5):
                break
        members = [i for i in group_member_window.GetChildren()]
        while members[-1].Name in [self._lang('添加'), self._lang('移出')]:
            members = members[:-1]
        # time.sleep(1)
        if index > 16:
            RollIntoView(self.control, members[index], bias=100)
        else:
            RollIntoView(self.control, members[index])

        group_member = GroupMemberElement(members[index], self)
        result = group_member.get_info()
        self.close()
        return result

    def quit(self):
        """退出群聊"""
        quit_btn = self.control.ButtonControl(Name=self._lang('退出群聊'))
        if quit_btn.Exists(0):
            quit_btn.Click()
        else:
            wxlog.debug('当前非群聊，无法退出')
            return
        RollIntoView(self.control, quit_btn)
        quit_btn.Click()
        dialog = self.root.control.PaneControl(ClassName='WeUIDialog')
        if dialog.TextControl(RegexName=self._lang('re_退出群聊')).Exists(0):
            dialog.ButtonControl(Name=self._lang('退出')).Click()

class GroupMemberElement:
    def __init__(self, control, parent) -> None:
        self.control = control
        self.parent = parent
        self.root = self.parent.root
        self.nickname = self.control.Name

    def __repr__(self) -> str:
        return f"<wxauto Group Member Element at {hex(id(self))}>"
    
    def add_friend(self, addmsg=None, remark=None, tags=None, permission='朋友圈'):
        """添加新的好友

        Args:
            addmsg (str, optional): 添加好友的消息
            remark (str, optional): 备注名
            tags (list, optional): 标签列表
            permission (str, optional): 朋友圈权限, 可选值：'朋友圈', '仅聊天'

        Returns:
            int
            0 - 添加失败
            1 - 发送请求成功
            2 - 已经是好友
            3 - 对方不允许通过群聊添加好友
                
        Example:
            >>> addmsg = '你好，我是xxxx'      # 添加好友的消息
            >>> remark = '备注名字'            # 备注名
            >>> tags = ['朋友', '同事']        # 标签列表
            >>> msg.add_friend(keywords, addmsg=addmsg, remark=remark, tags=tags)
        """
        # RollIntoView(self.parent.control, self.control)
        if not (profile_window := ProfileWnd(self)):
            self.control.Click(move=False)
            profile_window = ProfileWnd(self)
        return profile_window.add_friend(addmsg, remark, tags, permission)
    
    def get_info(self):
        if not (profile_window := ProfileWnd(self)):
            self.control.Click(move=False)
            profile_window = ProfileWnd(self)
        return profile_window.info
        
class AtMenu(BaseUISubWnd):
    _ui_cls_name = 'ChatContactMenu'

    def __init__(self, parent):
        self.root = parent.root
        self.control = parent.parent.control.PaneControl(ClassName='ChatContactMenu')
        # self.control.Exists(1)

    def clear(self, friend):
        if self.exists():
            self.control.SendKeys('{ESC}')
        for _ in range(len(friend)+1):
            self.root._chat_api.editbox.SendKeys('{BACK}')

    def select(self, friend):
        friend_ = friend.replace(' ', '')
        if self.exists():
            ateles = self.control.ListControl().GetChildren()
            if len(ateles) == 1:
                ateles[0].Click()
                return WxResponse.success()
            else:
                atele = self.control.ListItemControl(Name=friend)
                if atele.Exists(0):
                    RollIntoView(self.control, atele)
                    atele.Click()
                    return WxResponse.success()
                else:
                    self.clear(friend_)
                    return WxResponse.failure('@对象不存在')
        else:
            self.clear(friend_)
            return WxResponse.failure('@选择窗口不存在')
        
class DeleteMemberWnd(BaseUISubWnd):
    def __init__(self, parent) -> None:
        self.parent = parent
        self.root = parent.root
        self.control = self.root.control.WindowControl(ClassName='DeleteMemberWnd', searchDepth=3)
        self.searchbox = self.control.EditControl(Name='搜索')

    def selected_members_count(self) -> int:
        selected = self.control.TableControl().GetChildren()
        return len(selected)
    
    def search(self, keyword):
        """搜索群成员
        
        Args:
            keyword (str): 搜索关键词
        """
        wxlog.debug(f"搜索群成员：{keyword}")
        self.searchbox.Click()
        self.searchbox.ShortcutSelectAll()
        self.searchbox.Input(keyword)
        time.sleep(0.5)
        result = self.control.ListControl(Name="请勾选需要添加的联系人").GetChildren()
        return result
    
    def remove(self, keyword):
        """搜索并移出群成员
        
        Args:
            keyword (str): 搜索关键词
        """
        result = self.search(keyword)
        if len(result) == 1:
            result[0].ButtonControl().Click()
            target = result[0].ButtonControl().Name
            wxlog.debug(f"移出群成员：{target}")
            return target
        elif len(result) > 1:
            wxlog.warning(f"搜索到多个群成员：{keyword}")
            for item in result:
                if item.TextControl().Exists(0) and (item.TextControl().Name == keyword or item.ButtonControl().Name == keyword):
                    item.ButtonControl().Click()
                    wxlog.debug(f"移出完全匹配项群成员：{keyword}")
                    return item.ButtonControl().Name
        else:
            wxlog.error(f"未找到群成员：{keyword}")

    def submit(self):
        """提交移出群成员请求"""
        submit_btn = self.control.ButtonControl(Name='完成')
        threading.Thread(target=submit_btn.Click).start()
        time.sleep(0.5)
        wxlog.debug("提交移出群成员请求")
        confirmdlg = self.control.WindowControl(ClassName='ConfirmDialog')
        t0 = time.time()
        while True:
            wxlog.debug("等待移出群成员确认对话框")
            if time.time() - t0 > 5:
                raise TimeoutError("移出群成员等待超时")
            if not self.control.Exists(0.1):
                wxlog.debug("移出群成员成功，无须再次确认")
                return
            if confirmdlg.Exists(0.1):
                wxlog.debug("移出群成员成功")
                time.sleep(1)
                confirmdlg.SendKeys('{ENTER}')
                return