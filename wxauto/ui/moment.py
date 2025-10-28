from wxauto import uia
from .base import BaseUISubWnd
from wxauto.param import (
    WxParam,
    WxResponse
)
from wxauto.utils import (
    SetClipboardText,
    FindWindow
)
from .component import (
    WeChatImage,
    ProfileWnd
)
from wxauto.logger import wxlog
from wxauto.languages import *
from pathlib import Path
import time

class MomentsWnd(BaseUISubWnd):
    _ui_cls_name = 'SnsWnd'

    def __init__(self, parent, timeout=3):
        hwnd = FindWindow(classname=self._ui_cls_name, timeout=timeout)
        if hwnd:
            self.control = uia.ControlFromHandle(hwnd)
            self.parent = parent
            self.root = parent.root
            MainControl1 = [i for i in self.control.GetChildren() if not i.ClassName][0]
            self.ToolsBox = MainControl1.ToolBarControl(searchDepth=1)
            self.SnsBox = MainControl1.PaneControl(searchDepth=1)

            # Tools
            self.t_refresh = self.ToolsBox.ButtonControl(Name=self._lang('刷新'))

            self.GetMoments()

    def __repr__(self) -> str:
        return f'<WeChat Moments object at {hex(id(self))}>'
    
    def Refresh(self):
        self.t_refresh.Click()

    def GetMoments(self, next_page=False, speed1=3, speed2=1):
        edit_control = self.control.EditControl(Name=self._lang('评论'))
        if next_page:
            while True:
                if edit_control.Exists(0):
                    edit_control.SendKeys('{Esc}')
                self.control.WheelDown(wheelTimes=speed1)
                moments_controls = [
                    i for i in self.SnsBox.ListControl(Name=self._lang('朋友圈')).GetChildren() 
                    if i.ControlTypeName=='ListItemControl'
                ]
                moments = [Moments(i, self) for i in moments_controls]
                if [i.runtimeid for i in moments_controls][0] == self._ids[-1]:
                    break
                time.sleep(0.05)

            while True:
                if edit_control.Exists(0):
                    edit_control.SendKeys('{Esc}')
                self.control.WheelDown(wheelTimes=speed2)
                moments_controls = [
                    i for i in self.SnsBox.ListControl(Name=self._lang('朋友圈')).GetChildren() 
                    if i.ControlTypeName=='ListItemControl'
                ]
                moments = [Moments(i, self) for i in moments_controls]
                if [i.runtimeid for i in moments_controls][0] != self._ids[-1]:
                    break
                time.sleep(0.01)

        moments_controls = [
            i for i in self.SnsBox.ListControl(Name=self._lang('朋友圈')).GetChildren() 
            if i.ControlTypeName=='ListItemControl'
        ]
        moments = [Moments(i, self) for i in moments_controls]
        self._ids = [i.runtimeid for i in moments_controls]
        return moments

class Moments(BaseUISubWnd):
    def __init__(
            self, 
            control: uia.Control, 
            parent: MomentsWnd,
        ) -> None:
        self.control = control
        self.parent = parent
        self.root = parent.root
        self.cmt = self.control.ButtonControl(Name=self._lang('评论'))
        self._parse()
    
    def __getattr__(self, name):
        try:
            return self.info[name]
        except KeyError:
            raise AttributeError(f"'Sns' object has no attribute '{name}'")
        
    def _lang(self, text: str) -> str:
        return MOMENTS.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)
    
    def _parse(self):
        self.info = {
            'type': 'moment',
            'id': self.control.runtimeid,
            'sender': '',
            'content': '',
            'time': '',
            'img_count': 0,
            'comments': [],
            'addr': '',
            'likes': []
        }
        content_control = self.control.GetProgenyControl(4, control_type='TextControl')
        self.info['sender'] = self.control.GetProgenyControl(4, control_type='ButtonControl').Name
        self.info['content'] = content_control.Name if content_control else ''
        self.info['time'] = self.control.ButtonControl(Name=self._lang('评论')).GetParentControl().TextControl().Name
        img_info_control = self.control.PaneControl(RegexName=self._lang('re_图片数'))
        if img_info_control.Exists(0):
            self._img_controls = img_info_control.GetChildren()
            self.info['img_count'] = len(self._img_controls)
        else:
            self.info['img_count'] = 0
            self._img_controls = []

        if self.control.ListControl(Name=self._lang('评论')).Exists(0):
            self.info['comments'] = [i.Name for i in self.control.ListControl(Name=self._lang('评论')).GetChildren()]

        if self.control.TextControl(Name=self._lang('广告')).Exists(0):
            self.info['type'] = 'advertise'

        for i in range(10):
            text_control = self.control.GetProgenyControl(5, i, control_type='ButtonControl')
            if not text_control:
                break
            text_height = text_control.BoundingRectangle.height()
            if text_height == 18 and not self.info['addr']:
                self.info['addr'] = text_control.Name
            # elif text_height == 22:
            #     self.info['sender'] = text_control.Name

        like_control = self.control.GetProgenyControl(6, 0, control_type='TextControl')
        if like_control:
            self.info['likes'] = like_control.Name.split(self._lang('分隔符_点赞'))
        
    def _download_pic(self, msgitem, dir_path=None):
        uia.RollIntoView(self.parent.control.ListControl(), msgitem, bias=self.parent.ToolsBox.BoundingRectangle.height()*2)
        msgitem.Click()
        imgobj = WeChatImage()
        save_path = imgobj.save(dir_path)        
        imgobj.close()
        return save_path
    
    def SaveImages(self, save_index=None, dir_path=None):
        """保存图片
        
        Args:
            save_index (int|list): 保存第几张图片（从0开始），默认为None，保存所有图片
            dir_path (str): 绝对路径，包括文件名和后缀，例如："D:/Images/微信图片_xxxxxx.jpg"
                        （如果不填，则默认为当前脚本文件夹下，新建一个“微信图片(或视频)”的文件夹，保存在该文件夹内）
        """
        images = []
        if save_index:
            if isinstance(save_index, int):
                save_index = [save_index]
            elif not isinstance(save_index, list):
                raise TypeError("save_index must be int or list")

        self._parse()
        for i, msgitem in enumerate(self._img_controls):
            if not msgitem:
                continue
            if save_index and i not in save_index:
                continue
            try:
                imgpath = self._download_pic(msgitem, dir_path)
                images.append(imgpath)
            except Exception as e:
                wxlog.debug(f"下载朋友圈图片失败: {e}")
        return images
            
    def Like(self, like=True):
        uia.RollIntoView(self.parent.SnsBox, self.cmt)
        self.cmt.Click()
        like_panel = self.parent.control.PaneControl(ClassName='SnsLikeToastWnd')
        like_btn = like_panel.ButtonControl(Name=self._lang('赞'))
        cancel_btn = like_panel.ButtonControl(Name=self._lang('取消'))
        if like and like_btn.Exists(0):
            like_btn.Click()
        elif not like and cancel_btn.Exists(0):
            cancel_btn.Click()
        else:
            try:
                like_panel.SendKeys('{ESC}')
            except:
                pass
        return WxResponse.success()

    def Comment(self, text):
        uia.RollIntoView(self.parent.SnsBox, self.cmt)
        self.cmt.Click()
        cmt_btn = self.parent.control.PaneControl(ClassName='SnsLikeToastWnd').ButtonControl(Name=self._lang('评论'))
        cmt_btn.Click()
        edit_control: uia.EditControl = self.parent.control.EditControl(Name=self._lang('评论'))
        t0 = time.time()
        while True:
            if time.time() - t0 > 5:
                if edit_control.Exists(0):
                    edit_control.SendKeys('{Esc}')
                return WxResponse.failure('评论失败')
            if edit_control.GetValuePattern().Value:
                break
            SetClipboardText(text)
            edit_control.ShortcutPaste(click=True)
        edit_control.GetParentControl().ButtonControl(Name=self._lang('发送')).Click()
        return WxResponse.success()

    def sender_info(self):
        
        contact_info = {
            "nickname": None,
            "id": None,
            "remark": None,
            "tags": None,
            "source": None,
            "signature": None,
        }
        
        self.parent._show()
        headcontrol = self.control.ButtonControl(Name=self.sender)
        uia.RollIntoView(self.parent.control.ListControl(), headcontrol, equal=True, bias=self.parent.ToolsBox.BoundingRectangle.height()*2)
        headcontrol.Click()

        if profile_wnd := ProfileWnd(self):
            profile_wnd.close()
            return profile_wnd.info
        profile_wnd.close()