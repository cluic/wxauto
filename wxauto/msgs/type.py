from wxauto.utils.tools import (
    get_file_dir,
    parse_wechat_time
)
from wxauto.ui.component import (
    NoteWindow,
    CMenuWnd,
    WeChatImage,
    WeChatBrowser,
    get_wx_browser,
    ProfileWnd,
    ChatRecordWnd
)
from wxauto.exceptions import *
from wxauto.utils.win32 import (
    ReadClipboardData,
    SetClipboardText,
    FindWindow,
    GetAllWindows
)
from .base import *
from typing import (
    Union,
    Literal,
    Dict,
    List
)
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_fixed
)
from pathlib import Path
import time
import shutil
import re
import os


class TextMessage(HumanMessage):
    type = 'text'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

class QuoteMessage(HumanMessage):
    type = 'quote'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
        self.content, self.quote_content = \
            re.findall(self._lang('re_引用消息'), self.content, re.DOTALL)[0]
        
    @property
    def info(self) -> Dict:
        _info = self.parent.get_info().copy()
        _info['class'] = self.message_type_name
        _info['id'] = self.id
        _info['type'] = self.type
        _info['attr'] = self.attr
        _info['content'] = self.content
        _info['quote_content'] = self.quote_content
        _info['hash'] = self.hash
        return _info
        
    def download_quote_image(self, dir_path: Union[str, Path] = None, timeout: int = 10) -> Path:
        """下载引用消息中的图片或视频"""
        if self.quote_content not in [self._lang('[图片]'), self._lang('[视频]')]:
            return None
        self.roll_into_view()
        self.control.ButtonControl(Name='').Click()
        imgwnd = WeChatImage()
        return imgwnd.save(dir_path, timeout)
    
    def click_quote(self):
        """点击引用消息"""
        self.roll_into_view()
        self.control.ButtonControl(Name='').Click()

class Downloadable:
    @uilock
    def download(
            self, 
            dir_path: Union[str, Path] = None,
            timeout: int = 10,
            mouse_move: bool = False
        ) -> Path:
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        if self.type == 'image':
            filename = f"wxauto_{self.type}_{time.strftime('%Y%m%d%H%M%S')}{{suffix}}"
        elif self.type == 'video':
            filename = f"wxauto_{self.type}_{time.strftime('%Y%m%d%H%M%S')}{{suffix}}"

        t0 = time.time()
        while True:
            self.click(move=mouse_move)
            if imagewnd := WeChatImage():
                return imagewnd.save(dir_path, timeout)
            # self.right_click()
            # menu = CMenuWnd(self)
            # if menu and menu.select('复制'):
            #     time.sleep(0.2)
            #     try:
            #         clipboard_data = ReadClipboardData()
            #         cpath = clipboard_data['15'][0]
            #         suffix = os.path.splitext(cpath)[1]
            #         break
            #     except:
            #         pass
            # else:
            #     menu.close()
            if time.time() - t0 > timeout:
                return WxResponse.failure(f'下载超时: {self.type}')
            time.sleep(0.1)
        # filepath = get_file_dir(dir_path) / filename.format(suffix=suffix)
        # shutil.copyfile(cpath, filepath)
        # SetClipboardText('')
        # while True:
        #     if imagewnd := WeChatImage():
        #         imagewnd.close()
        #     else:
        #         break
        # return filepath

class ImageMessage(HumanMessage, Downloadable):
    type = 'image'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

class VideoMessage(HumanMessage, Downloadable):
    type = 'video'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

class VoiceMessage(HumanMessage):
    type = 'voice'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

    @retry(wait=wait_fixed(0.5), stop=stop_after_attempt(3))
    def to_text(self):
        """语音转文字"""
        if self.control.GetProgenyControl(8, 4):
            return self.control.GetProgenyControl(8, 4).Name
        voicecontrol = self.control.ButtonControl(Name='')
        if not voicecontrol.Exists(0.5):
            return WxResponse.failure('语音转文字失败')
        self.right_click()
        menu = CMenuWnd(self.parent)
        menu.select('语音转文字')

        text = ''
        while True:
            if not self.control.Exists(0):
                return WxResponse.failure('消息已撤回')
            text_control = self.control.GetProgenyControl(8, 4, refresh=True)
            if text_control is not None:
                if text_control.Name == text:
                    return text
                text = text_control.Name
            time.sleep(0.1)

class FileMessage(HumanMessage):
    type = 'file'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
        self.filename = control.GetProgenyControl(9, control_type='TextControl').Name
        self.filesize = control.GetProgenyControl(10, control_type='TextControl').Name

    @uilock
    def download(
            self, 
            dir_path: Union[str, Path] = None,
            force_click: bool = False,
            timeout: int = 10
        ) -> Path:
        """下载文件"""
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        filepath = get_file_dir(dir_path) / self.filename
        t0 = time.time()
        def open_file_menu():
            while not (menu := CMenuWnd(self.parent)):
                self.roll_into_view()
                self.right_click()
            return menu
        if force_click:
            self.click()
        while True:
            if time.time() - t0 > timeout:
                return WxResponse.failure("文件下载超时")
            try:
                if self.control.TextControl(Name=self._lang('接收中')).Exists(0):
                    time.sleep(0.1)
                    continue
                menu = open_file_menu()
                if (option := self._lang('复制')) in menu.option_names:
                    menu.select(option)
                    temp_filepath = Path(ReadClipboardData().get('15')[0])
                    break
            except:
                time.sleep(0.1)

        t0 = time.time()
        while True:
            if time.time() - t0 > 2:
                return WxResponse.failure("文件下载超时")
            try:
                shutil.copyfile(temp_filepath, filepath)
                SetClipboardText('')
                return filepath
            except:
                time.sleep(0.01)

class LocationMessage(HumanMessage):
    type = 'location'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)
        self.address = self._address()

    def _address(self):
        """获取位置信息"""
        location_control1 = self.control.GetProgenyControl(7, 1)
        location_control2 = self.control.GetProgenyControl(7)
        self.location_data = {
            'location': '' if location_control1 is None else location_control1.Name,
            'point': location_control2.Name
        }
        return self.location_data['location'] + self.location_data['point']


class LinkMessage(HumanMessage):
    type = 'link'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

    @uilock
    @retry(wait=wait_fixed(0.5), stop=stop_after_attempt(3))
    def get_url(self, timeout=10) -> str:
        """获取链接"""
        try:
            browser = get_wx_browser(self.click, timeout)
            if isinstance(browser, WxResponse):
                return browser
            url = browser.get_url()
            wxlog.debug(f'get url: {url}')
            return url
        finally:
            browser.close()
        

class EmotionMessage(HumanMessage):
    type = 'emotion'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

class MergeMessage(HumanMessage):
    type = 'merge'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

    def get_messages(self):
        """获取合并消息中的所有消息"""
        self.click()
        chatrecordwnd = ChatRecordWnd(self.parent)
        time.sleep(2)
        msgs = chatrecordwnd.get_content()
        return msgs

class PersonalCardMessage(HumanMessage):
    type = 'personal_card'

    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

    def add_friend(
            self,
            addmsg: str = None, 
            remark: str = None, 
            tags: List[str] = None, 
            permission: Literal['朋友圈', '仅聊天'] = '朋友圈', 
        ) -> WxResponse:
        """添加好友

        Args:
            addmsg (str, optional): 添加好友时的附加消息，默认为None
            remark (str, optional): 添加好友后的备注，默认为None
            tags (List[str], optional): 添加好友后的标签，默认为None
            permission (Literal['朋友圈', '仅聊天'], optional): 添加好友后的权限，默认为'朋友圈'
            timeout (int, optional): 搜索好友的超时时间，默认为3秒
        """
        self.click()
        if profile_wnd := ProfileWnd(self):
            result = profile_wnd.add_friend(
                addmsg=addmsg,
                remark=remark,
                tags=tags,
                permission=permission
            )
            return result
        return WxResponse.failure('未找到好友资料窗口')


class NoteMessage(HumanMessage):
    type = 'note'

    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)

    @uilock
    def get_content(self, wait=0) -> List[str]:
        """获取笔记内容
        
        Returns:
            List[str]: 笔记内容
        """
        try:
            self.click()
            if notewnd := NoteWindow(self):
                notewnd.init(wait=wait)
                return notewnd.parse()
            else:
                return WxResponse.failure(notewnd.dialog_texts)
        except WxautoNoteLoadTimeoutError as e:
            return WxResponse.failure(str(e))
        finally:
            notewnd.close()

    @uilock
    def save_files(
            self, 
            dir_path: Union[str, Path] = None,
        ):
        """保存笔记中的文件
        
        Args:
            dir_path (Union[str, Path], optional): 保存路径. Defaults to None.
        Returns:
            WxResponse: 保存结果
        """
        try:
            self.click()
            notewnd = NoteWindow(self)
            notewnd.init()
            result = notewnd.save_all(dir_path)
            return result
        except WxautoNoteLoadTimeoutError as e:
            return WxResponse.failure(str(e))
        finally:
            notewnd.close()
    
    @uilock
    def to_markdown(
            self,
            dir_path: Union[str, Path] = None,
        ) -> Path:
        """将笔记转换为Markdown格式并保存
        
        Args:
            dir_path (Union[str, Path], optional): 保存路径. Defaults to None.
        Returns:
            WxResponse: 保存结果
        """
        try:
            self.click()
            notewnd = NoteWindow(self)
            notewnd.init()
            result = notewnd.to_markdown(dir_path)
            return result
        except WxautoNoteLoadTimeoutError as e:
            return WxResponse.failure(str(e))
        finally:
            notewnd.close()


class OtherMessage(BaseMessage):
    type = 'other'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_control_pointer = None,
        ):
        super().__init__(control, parent, sub_control_pointer)