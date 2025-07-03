from wxauto.utils.tools import (
    get_file_dir,
)
from wxauto.ui.component import (
    CMenuWnd,
    WeChatImage,
)
from wxauto.utils.win32 import (
    ReadClipboardData,
    SetClipboardText,
)
from .base import *
from typing import (
    Union,
)
from pathlib import Path
import shutil
import re

class TextMessage(HumanMessage):
    type = 'text'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class QuoteMessage(HumanMessage):
    type = 'quote'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
        ):
        super().__init__(control, parent)
        self.content, self.quote_content = \
            re.findall(self._lang('re_引用消息'), self.content, re.DOTALL)[0]
        
class MediaMessage:

    def download(
            self, 
            dir_path: Union[str, Path] = None,
            timeout: int = 10
        ) -> Path:
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        if self.type == 'image':
            filename = f"wxauto_{self.type}_{time.strftime('%Y%m%d%H%M%S')}.png"
        elif self.type == 'video':
            filename = f"wxauto_{self.type}_{time.strftime('%Y%m%d%H%M%S')}.mp4"
        filepath = get_file_dir(dir_path) / filename

        self.click()

        t0 = time.time()
        while True:
            self.right_click()
            menu = CMenuWnd(self)
            if menu and menu.select('复制'):
                try:
                    clipboard_data = ReadClipboardData()
                    cpath = clipboard_data['15'][0]
                    break
                except:
                    pass
            else:
                menu.close()
            if time.time() - t0 > timeout:
                return WxResponse.failure(f'下载超时: {self.type}')
            time.sleep(0.1)

        shutil.copyfile(cpath, filepath)
        SetClipboardText('')
        if imagewnd := WeChatImage():
            imagewnd.close()
        return filepath

class ImageMessage(HumanMessage, MediaMessage):
    type = 'image'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class VideoMessage(HumanMessage, MediaMessage):
    type = 'video'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class VoiceMessage(HumanMessage):
    type = 'voice'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

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
            text_control = self.control.GetProgenyControl(8, 4)
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
            parent: "ChatBox"
        ):
        super().__init__(control, parent)
        self.filename = control.TextControl().Name
        self.filesize = control.GetProgenyControl(10, control_type='TextControl').Name

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


class OtherMessage(BaseMessage):
    type = 'other'
    
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",

        ):
        super().__init__(control, parent)