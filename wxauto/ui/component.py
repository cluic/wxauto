from wxauto.utils import (
    FindWindow,
    SetClipboardText,
    ReadClipboardData,
    GetAllWindows,
    FindTopLevelControl
)
from wxauto.param import (
    WxParam, 
    WxResponse,
)
from wxauto.languages import *
from .base import (
    BaseUIWnd,
    BaseUISubWnd
)
from wxauto.logger import wxlog
from wxauto.uia import (
    ControlFromHandle,
    RollIntoView,
    ListItemControl
)
from wxauto.utils.tools import (
    get_file_dir,
    find_window_from_root,
    find_all_windows_from_root,
    parse_wechat_time,
    now_time,
    is_valid_image
)
from wxauto.exceptions import *
from wxauto import uia
from typing import Literal, List, Union
from pathlib import Path
import traceback
import datetime
import shutil
import time
import os
import re

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

    def send(self, target, message=None, exact=True):
        if isinstance(target, str):
            SetClipboardText(target)
            while not self.editbox.HasKeyboardFocus:
                self.editbox.Click()
                time.sleep(0.1)
            self.editbox.ShortcutSelectAll()
            self.editbox.ShortcutPaste()
            checkboxlist = self.control.ListControl()
            time.sleep(1)
            checkboxs = [i for i in checkboxlist.GetChildren() if i.ControlTypeName=='CheckBoxControl']
            if checkboxs:
                if exact and (exact_checkboxs := [i for i in checkboxs if i.Name==target]):
                    exact_checkboxs[0].Click()
                else:
                    checkboxs[0].Click()

                msgedit = self.control.EditControl(Name='给朋友留言')
                if message and msgedit.Exists(0):
                    msgedit.Click()
                    msgedit.Paste(message)
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
                self.editbox.ShortcutSelectAll()
                self.editbox.ShortcutPaste(click=False)
                checkboxlist = self.control.ListControl()
                time.sleep(1)
                checkboxs = [i for i in checkboxlist.GetChildren() if i.ControlTypeName=='CheckBoxControl']
                if checkboxs:
                    if exact and (exact_checkboxs := [i for i in checkboxs if i.Name==target]):
                        exact_checkboxs[0].Click()
                    else:
                        checkboxs[0].Click()
                    n += 1
                else:
                    fail.append(i)
                    wxlog.debug(f"未找到转发对象：{i}")
            if n > 0:
                msgedit = self.control.EditControl(Name='给朋友留言')
                if message and msgedit.Exists(0):
                    msgedit.Click()
                    msgedit.Paste(message)
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


class AlertDialog(BaseUISubWnd):
    _ui_cls_name = 'AlertDialog'

    def __init__(self, parent):
        self.parent = parent
        self.root = parent.root
        self.control = parent.root.control.WindowControl(ClassName=self._ui_cls_name, searchDepth=1)

    def get_all_text(self):
        return [i.Name for i in self.control.FindAll(control_type='TextControl') if i.Name]
    
    def get_all_buttons(self):
        return [i for i in self.control.FindAll(control_type='ButtonControl')]
    
    def click_button(self, text):
        if (button := self.control.ButtonControl(Name=text)).Exists(0):
            button.Click()
            return WxResponse.success()
        return WxResponse.failure(f"找不到按钮：{text}")
    
class ConfirmDialog(BaseUISubWnd):
    _ui_cls_name = 'ConfirmDialog'

    def __init__(self, parent):
        self.parent = parent
        self.root = parent.root
        self.control = parent.root.control.WindowControl(ClassName=self._ui_cls_name, searchDepth=1)

    def get_all_text(self):
        return [i.Name for i in self.control.FindAll(control_type='TextControl') if i.Name]
    
    def get_all_buttons(self):
        return [i for i in self.control.FindAll(control_type='ButtonControl')]
    
    def click_button(self, text):
        if self.control.ButtonControl(Name=text).Exists(0):
            self.control.ButtonControl(Name=text).Click()
            return WxResponse.success()
        return WxResponse.failure(f"找不到按钮：{text}")

class ProfileWnd(BaseUISubWnd):
    _ui_cls_name = 'ContactProfileWnd'

    def __init__(self, parent):
        self.control = FindTopLevelControl(classname='ContactProfileWnd', timeout=0.1)
        if not self.control:
            self.control = parent.root.control.PaneControl(ClassName=self._ui_cls_name, searchDepth=1)
        self.root = parent.root
        if self.exists(1):
            self.info = self._info()

    def _lang(self, text: str) -> str:
        return PROFILE_WINDOW.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    def _info(self):
        info = {}
        tags = {
            self._lang("昵称"): "nickname",
            self._lang("微信号"): "id",
            self._lang("地区"): "region",
            self._lang("个性签名"): "signature",
            self._lang("来源"): "source",
            self._lang("标签"): "tags",
            self._lang("备注"): "remark",
            self._lang("共同群聊"): "same_group",
        }
        mark = ''
        is_nickname = False
        info['nickname'] = ''
        walk = self.control.Walk()
        for c, d in walk:
            name = c.Name
            # print(name)
            controltype = c.ControlTypeName
            if not info['nickname'] and controltype == 'ButtonControl':
                is_nickname = True
            elif is_nickname and controltype == 'TextControl' and not info['nickname']:
                info['nickname'] = name
                # print(c.runtimeid)
            elif mark and controltype in ['TextControl', 'ButtonControl']:
                info[mark] = name
                mark = ''
            elif name in tags and controltype == 'TextControl':
                mark = tags[name]
                continue
        
        return info
    
    def download_head_image(self) -> Path:
        head = self.control.ButtonControl()
        head.Click()
        imgwnd = WeChatImage()
        path = imgwnd.save()
        imgwnd.close()
        return path
    
    def add_friend(
        self, 
        addmsg=None,
        remark=None, 
        tags=None, 
        permission: Literal['朋友圈', '仅聊天'] = '朋友圈'
    ):
        add_control = self.control.ButtonControl(Name=self._lang('添加到通讯录'))
        if not add_control.Exists(0):
            self.close()
            return WxResponse.failure(f"已经是好友")
        
        add_control.Click()
        NewFriendsWnd = AddFriendWindow(self)
        AlertWnd = self.root.control.WindowControl(ClassName='AlertDialog')
        t0 = time.time()
        status = 0
        while time.time() - t0 < 5:
            if NewFriendsWnd.exists(0.1):
                wxlog.debug("添加朋友窗口存在")
                status = 1
                break
            elif dialog := [i for i in self.root._get_windows() if i.Name=='添加朋友请求']:
                wxlog.debug("从窗口枚举中找到添加朋友请求窗口")
                NewFriendsWnd.control = dialog[0]
                status = 1
                break
            elif AlertWnd.Exists(0.1):
                wxlog.debug("存在意外对话框")
                status = 2
                break
        if status == 0:
            self.close()
            return WxResponse.failure(f"添加失败")
        elif status == 2:
            self.close()
            return WxResponse.failure(f"对方不允许通过群聊添加好友")
        else:
            return NewFriendsWnd.add(addmsg, remark, tags, permission)

    def _choose_menu(self, menu_name):
        more_control = self.control.ButtonControl(Name=self._lang('更多'))
        if not more_control.Exists(0):
            return WxResponse.failure(f"未找到菜单按钮")
        more_control.Click()
        menu = CMenuWnd(self)
        return menu.select(menu_name)
        
    def modify_remark_tags(self, remark: str=None, tags: list=None):
        if all([not remark, not tags]):
            return WxResponse.failure("请至少传入一个参数")
        if not self._choose_menu(self._lang("设置备注和标签")):
            wxlog.debug('该用户不支持修改备注和标签')
            return WxResponse.failure("该用户不支持修改备注和标签")
        time.sleep(0.1)
        dialogwnd = self.control.WindowControl(ClassName='WeUIDialog')
        # self.control.tree
        if not dialogwnd.Exists(5):
            return WxResponse.failure("修改失败")
        if remark:
            edit = dialogwnd.TextControl(Name=self._lang('备注名')).GetParentControl().EditControl()
            edit.Click()
            edit.ShortcutSelectAll()
            SetClipboardText(remark)
            edit.ShortcutPaste(click=False)
        if tags:
            edit_btn = dialogwnd.TextControl(Name=self._lang('标签')).GetParentControl().ButtonControl()
            edit_btn.Click()
            tagwnd = dialogwnd.WindowControl(ClassName='StandardConfirmDialog')
            edit = tagwnd.EditControl(Name=self._lang("输入标签"))
            for ele in edit.GetParentControl().GetChildren():
                if ele.ControlTypeName == 'PaneControl' and ele.Name not in tags:
                    if (btn := ele.ButtonControl()).Exists(0):
                        btn.Click()
            edit.Click()
            for tag in tags:
                edit.Input(tag)
                edit.SendKeys('{Enter}')
            tagwnd.ButtonControl(Name=self._lang('确定')).Click()
        dialogwnd.ButtonControl(Name=self._lang('确定')).Click()
        return WxResponse.success()
    

class WeChatDialog(BaseUISubWnd):
    def __init__(self, parent, wait=3):
        self.root = parent.root
        
        t0 = time.time()
        while True:
            if time.time() - t0 > wait:
                break
            wins = [i for i in self.root._get_windows() if 'Dialog' in i.ClassName]
            if wins:
                self.control = wins[0]
                break
            else:
                self.control = None

    def get_all_text(self):
        return [text for i in self.control.FindAll() if (text:=i.Name)]

    def click_button(self, text: str, move=True):
        if self.control.ButtonControl(Name=text).Exists(0):
            if move:
                self.control.ButtonControl(Name=text).Click(move=True, simulateMove=False)
            else:
                self.control.ButtonControl(Name=text).Click()
            return WxResponse.success()
        return WxResponse.failure('找不到按钮')


class AddFriendWindow(BaseUISubWnd):
    _ui_cls_name: str = 'WeUIDialog'

    def __init__(self, parent):
        self.root = parent.root
        self.control = self.root.control.WindowControl(ClassName=self._ui_cls_name)

    def _lang(self, text: str) -> str:
        return ADD_NEW_FRIEND_WINDOW.get(text, {WxParam.LANGUAGE: text}).get(WxParam.LANGUAGE)

    def add(
        self, 
        addmsg=None,
        remark=None, 
        tags=None, 
        permission: Literal['朋友圈', '仅聊天'] = '朋友圈'
    ):
        if not self.exists():
            return WxResponse.failure('添加好友窗口不存在')
        tipscontrol = self.control.TextControl(Name=self._lang("你的联系人较多，添加新的朋友时需选择权限"))

        permission_sns = self.control.CheckBoxControl(Name=self._lang('聊天、朋友圈、微信运动等'))
        permission_chat = self.control.CheckBoxControl(Name=self._lang('仅聊天'))
        if tipscontrol.Exists(0.5):
            permission_sns = tipscontrol.GetParentControl().GetParentControl().TextControl(Name=self._lang('朋友圈'))
            permission_chat = tipscontrol.GetParentControl().GetParentControl().TextControl(Name=self._lang('仅聊天'))

        if addmsg:
            msgedit = self.control.TextControl(Name=self._lang("发送添加朋友申请")).GetParentControl().EditControl()
            msgedit.DoubleClick()
            msgedit.Click()
            msgedit.ShortcutSelectAll()
            msgedit.Input(addmsg)

        if remark:
            remarkedit = self.control.TextControl(Name=self._lang('备注名')).GetParentControl().EditControl()
            msgedit.DoubleClick()
            remarkedit.Click()
            remarkedit.ShortcutSelectAll()
            remarkedit.Input(remark)

        if tags:
            tagedit = self.control.TextControl(Name=self._lang('标签')).GetParentControl().EditControl()
            for tag in tags:
                tagedit.Click()
                tagedit.Input(tag)
                self.control.PaneControl(ClassName='DropdownWindow').TextControl().Click()
        
        if permission == '朋友圈':
            permission_sns.Click()
        elif permission == '仅聊天':
            permission_chat.Click()

        self.control.ButtonControl(Name=self._lang('确定')).Click()
        return WxResponse.success('发送请求成功')
        

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
    
    def save(self, dir_path=None, timeout=10) -> Path:
        """保存图片/视频

        Args:
            dir_path (str): 保存文件夹路径
            timeout (int, optional): 保存超时时间，默认10秒
        
        Returns:
            Path: 文件保存路径，即savepath
        """
        image_sufix = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'pic']
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        # suffix = 'png' if self.type == 'image' else 'mp4'
        t0 = time.time()

        n = 1
        SetClipboardText('')
        while True:
            if time.time() - t0 > timeout:
                if self.control.Exists(0):
                    self.control.SendKeys('{Esc}')
                return WxResponse.failure('下载超时')
            if self.control.TextControl(Name="图片过期或已被清理").Exists(0):
                return WxResponse.failure('图片过期或已被清理')
            try:
                self.control.ButtonControl(Name=self._lang('更多')).Click()
                menu = self.control.MenuControl(ClassName='CMenuWnd')
                menu.MenuItemControl(Name=self._lang('复制')).Click()
                # print('读取剪贴板数据')
                clipboard_data = ReadClipboardData()
                # print('读取剪贴板数据成功')
                # wxlog.debug(f"读取到剪贴板数据：{clipboard_data}")
                path = clipboard_data['15'][0]
                if not os.path.exists(path):
                    return WxResponse.failure('微信BUG无法获取该图片，请重新获取')
                suffix = os.path.splitext(path)[1]
                if (
                    suffix in image_sufix
                    and not is_valid_image(path)
                ) or not os.path.getsize(path):
                    wxlog.debug("图片格式不正确，删除文件")
                    os.remove(path)
                    continue
                wxlog.debug(f"读取到图片/视频路径[{os.path.exists(path)}, {os.path.getsize(path)}]：{path}")
                break
            except:
                if n > 3:
                    return WxResponse.failure('微信BUG无法获取该图片，请重新获取')
                n += 1
                wxlog.debug(traceback.format_exc())
            time.sleep(0.1)
        filename = f"wxauto_{self.type}_{now_time()}{suffix}"
        filepath = get_file_dir(dir_path) / filename
        wxlog.debug(f"保存到文件：{filepath}")
        shutil.copyfile(path, filepath)
        SetClipboardText('')
        if self.control.Exists(0):
            wxlog.debug("关闭图片窗口")
            self.control.SendKeys('{Esc}')
        return filepath
    

class NoteWindow(BaseUISubWnd):
    _ui_cls_name: str = 'NativeNoteWnd'

    def __init__(self, parent=None, timeout=3):
        self.parent = parent
        self.control = find_window_from_root(classname=self._ui_cls_name, timeout=timeout)
        self.dialog_texts = ''
        
    def init(self, wait=0):
        if wait:
            time.sleep(wait)
        if self.control and self.control.Exists(0):
            t0 = time.time()
            while self.control.TextControl(Name='加载中').Exists(0):
                if time.time() - t0 > WxParam.NOTE_LOAD_TIMEOUT:
                    wxlog.debug("微信笔记加载超时")
                    raise WxautoNoteLoadTimeoutError("微信笔记加载超时")
                time.sleep(0.1)
            if (dialog := self.control.PaneControl(ClassName='WeUIDialog')).Exists(0):
                self.dialog_texts = ''.join([i.Name for i in dialog.FindAll(control_type='TextControl')])
                wxlog.debug(f"弹窗内容：{self.dialog_texts}")
                dialog.SendKeys('{Esc}')
                self.close()
            else:
                self._get_metadata()

    def process_dialog(self):
        if (dialog := self.control.PaneControl(ClassName='WeUIDialog')).Exists(0):
            contents = ''.join([i.Name for i in dialog.FindAll(control_type='TextControl')])
            wxlog.debug(f"弹窗内容：{contents}")
            dialog.SendKeys('{Esc}')
            return True

    def save_file(self, file_path: Path, dir_path: Path=None):
        wxlog.debug(f"复制文件：{file_path}")
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        save_dir = get_file_dir(dir_path)
        savepath = save_dir / file_path.name
        return shutil.copyfile(file_path, savepath)
    
    def _get_metadata(self):
        self.control.MiddleClick()
        self.control.ShortcutSelectAll()
        self.control.ShortcutCopy(click=False)
        self.metadata = ReadClipboardData().copy()
        self.control.Click()

    def parse(self) -> List[Union[str, Path]]:
        if hasattr(self, '_parse_data_list'):
            return self._parse_data_list
        types = list(self.metadata.keys())
        if not types:
            return []
        text = self.metadata.get(types[0]).decode('utf-8')
        data_list = []
        if text:
            pattern = (
                r'filepath="(.*?)"|<EditElement type="0">'
                r'<!\[CDATA\[(.*?)\]\]></EditElement>'
            )
            matches = re.findall(pattern, text)
            for match in matches:
                if match[0]:
                    data_list.append(self.save_file(Path(match[0])))
                elif match[1]:
                    data_list.append(match[1])
        elif '15' in self.metadata:
            data_list.append(self.save_file(Path(self.metadata['15'][0])))
        self._parse_data_list = data_list
        return data_list

    def save_all(self, dir_path: Path) -> WxResponse[List[Path]]:
        types = list(self.metadata.keys())
        if not types:
            return WxResponse.failure('未获取到笔记数据')
        if '15' in self.metadata:
            path = Path(self.metadata['15'][0])
            return_data = [self.save_file(path, dir_path)]
        elif types[0] > '10000':
            pathdata = self.metadata[types[0]].decode()
            paths = [Path(p) for p in re.findall('filepath="(.*?)"', pathdata) if os.path.exists(p)]
            return_data = [self.save_file(path, dir_path) for path in paths]
        else:
            wxlog.debug("未找到文件信息")
            return WxResponse.failure("未找到文件信息")
        return WxResponse.success(data=return_data)
    
    def to_markdown(self, dir_path: Path = None) -> Path:
        image_sufix = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pic']
        data_list = self.parse()
        markdown = ''
        for data in data_list:
            if isinstance(data, Path):
                if data.suffix.lower() in image_sufix:
                    markdown += f'![{data.name}]({data.absolute()})\n'
                else:
                    markdown += f'[{data.name}]({data.absolute()})\n'
            else:
                markdown += f'{data}\n'

        file_name = f"wxauto_note_{time.strftime('%Y%m%d%H%M%S')}.md"
        if dir_path is None:
            dir_path = WxParam.DEFAULT_SAVE_PATH
        save_dir = get_file_dir(dir_path)
        savepath = save_dir / file_name

        with open(savepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        return savepath

class AddMemberWnd(BaseUISubWnd):
    def __init__(self, parent) -> None:
        self.parent = parent
        self.control = self.parent.root.control.WindowControl(
            ClassName='AddMemberWnd', searchDepth=3
        )
        self.searchbox = self.control.EditControl(Name=self._lang('搜索'))

    def _lang(self, text: str) -> str:
        return ADD_GROUP_MEMBER_WINDOW.get(
            text, {WxParam.LANGUAGE: text}
        ).get(WxParam.LANGUAGE)
    
    def search(self, keyword) -> List['ListItemControl']:
        """搜索好友
        
        Args:
            keyword (str): 搜索关键词
        """
        wxlog.debug(f"搜索好友：{keyword}")
        self.searchbox.Input(keyword)
        time.sleep(0.5)
        result = self.control.ListControl(
            Name=self._lang("请勾选需要添加的联系人")
        ).GetChildren()
        return result
    
    def add(self, keyword) -> WxResponse:
        """搜索并添加好友
        
        Args:
            keyword (str): 搜索关键词
        """
        result = self.search(keyword)
        if len(result) == 1:
            result[0].ButtonControl().Click()
            wxlog.debug(f"添加好友：{keyword}")
            return WxResponse.success()
        elif len(result) > 1:
            wxlog.warning(f"搜索到多个好友：{keyword}")
            return WxResponse.failure(f"搜索到多个好友：{keyword}")
        else:
            wxlog.debug(f"未找到好友：{keyword}")
            return WxResponse.failure(f"未找到好友：{keyword}")

    def submit(self):
        self.control.ButtonControl(Name=self._lang('完成')).Click()
        wxlog.debug("提交添加好友请求")
        confirmdlg = self.control.WindowControl(ClassName='ConfirmDialog')
        alertdlg = self.control.WindowControl(ClassName='AlertDialog')
        t0 = time.time()
        while True:
            if time.time() - t0 > 5:
                raise TimeoutError("新增群好友等待超时")
            if not self.control.Exists(0.1):
                wxlog.debug("新增群好友成功，无须再次确认")
                return WxResponse.success()
            if confirmdlg.Exists(0.1):
                wxlog.debug("新增群好友成功，确认添加")
                time.sleep(1)
                # confirmdlg.ButtonControl(Name='确定').Click()
                confirmdlg.SendKeys('{ENTER}')
                return WxResponse.success()
            if alertdlg.Exists(0.3):
                content_list = alertdlg.FindAll(control_type='TextControl')
                alert_content = ' '.join([c.Name for c in content_list])
                wxlog.debug(f"新增群好友失败：{alert_content}")
                alertdlg.SendKeys('{Esc}')
                self.close()
                return WxResponse.failure(f"新增群好友失败：{alert_content}")
            
    def reason(self, content: str):
        reasondlg = self.parent.root.control.PaneControl(ClassName='WeUIDialog')
        if reasondlg.Exists(0.3):
            if content:
                editbox = reasondlg.EditControl()
                editbox.Click()
                editbox.Input(content)
                reasondlg.ButtonControl(Name=self._lang('发送')).Click()
                wxlog.debug(f"发送好友申请理由：{content}")
                return WxResponse.success()
            else:
                wxlog.debug("未设置好友申请理由，取消新增群友")
                reasondlg.SendKeys('{Esc}')
                return WxResponse.failure("未设置好友申请理由，取消新增群友")


    def selected_members_count(self) -> int:
        selected = self.control.TableControl(
            Name=self._lang('已选择联系人'), 
            searchDepth=3).GetChildren()
        return len(selected)


class NewFriendElement:
    def __init__(self, control, parent):
        self.parent = parent
        self.root = parent.root
        self.control = control
        self.id = self.control.runtimeid
        self.name = self.control.Name
        self.msg = self.control.GetFirstChildControl().PaneControl(SearchDepth=1).GetChildren()[-1].TextControl().Name
        self.NewFriendsBox = self.root._chat_api.control.ListControl(Name='新的朋友').GetParentControl()
        self.status = self.control.GetFirstChildControl().GetChildren()[-1]
        self.acceptable = isinstance(self.status, uia.ButtonControl)
        self.info = {
            'id': self.id,
            'name': self.name,
            'msg': self.msg,
            'acceptable': self.acceptable
        }
            
    def __repr__(self) -> str:
        return f"<wxauto New Friends Element at {hex(id(self))} ({self.name}: {self.msg})>"
    
    def delete(self):
        wxlog.info(f'删除好友请求: {self.name}')
        RollIntoView(self.NewFriendsBox, self.control)
        self.control.RightClick()
        menu = CMenuWnd(self.root)
        menu.select('删除')

    def reply(self, text):
        wxlog.debug(f'回复好友请求: {self.name}')
        RollIntoView(self.NewFriendsBox, self.control)
        self.control.Click()
        self.root.ChatBox.ButtonControl(Name='回复').Click()
        edit = self.root.ChatBox.EditControl()
        edit.Click()
        edit.ShortcutSelectAll()
        SetClipboardText(text)
        edit.ShortcutPaste()
        time.sleep(0.1)
        self.root.ChatBox.ButtonControl(Name='发送').Click()
        dialog = self.root.control.PaneControl(ClassName='WeUIDialog')
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
        RollIntoView(self.NewFriendsBox, self.status)
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
            remarkedit.ShortcutSelectAll()
            remarkedit.Input(remark)
        
        if tags:
            tagedit = NewFriendsWnd.TextControl(Name='标签').GetParentControl().EditControl()
            for tag in tags:
                tagedit.Click()
                tagedit.Input(tag)
                NewFriendsWnd.PaneControl(ClassName='DropdownWindow').TextControl().Click()

        if permission == '朋友圈':
            permission_sns.Click()
        elif permission == '仅聊天':
            permission_chat.Click()

        NewFriendsWnd.ButtonControl(Name='确定').Click()

    def get_account(self, wait=5):
        """获取好友号
        
        Args:
            wait (int, optional): 等待时间
            
        Returns:
            str: 好友号，如果获取失败则返回None
        """
        wxlog.debug(f"获取好友号：{self.name}")
        self.control.Click()
        tags = ['微信号：', 'WeChat ID: ']
        for tag in tags:
            if (account_tag_control := self.root.ChatBox.TextControl(Name=tag)).Exists(wait):
                account = account_tag_control.GetParentControl().GetChildren()[-1].Name
                self.root.ChatBox.ButtonControl(Name='').Click()
                return account
        self.root.ChatBox.ButtonControl(Name='').Click()
        

class WeChatBrowser:
    _ui_cls_name = 'Chrome_WidgetWin_0'
    _ui_name = '微信'

    class _BrowserMenu:
        def __init__(self, control: uia.Control):
            self.control = control

        @property
        def option_names(self):
            return [
                i.Name for i in self.control.GetChildren() 
                if i.ControlTypeName == "MenuItemControl"
            ]
        
        def select(self, option:str):
            if option not in self.option_names:
                return WxResponse.failure("找不到选项")
            self.control.MenuItemControl(Name=option).Click()
            return WxResponse.success()
        
        def close(self):
            try:
                self.control.SendKeys('{ESC}')
            except:
                pass

    class _PageTab:
        def __init__(self, control: uia.Control):
            self.control = control
            self.page_name = self.control.Name

        def __repr__(self):
            return f'<wx browser tab ({self.page_name})>'

        def switch(self):
            self.control.Click()

        def close(self):
            self.control.Click()
            self.control.ButtonControl().Click()
        

    def __init__(self, hwnd:int=None):
        self.root = self
        self.hwnd = hwnd
        if not hwnd:
            self.hwnd = FindWindow(self._ui_cls_name, self._ui_name)
        self.control  = uia.ControlFromHandle(self.hwnd)
        wxlog.debug(f"获取到微信浏览器窗口: {hwnd}")

    def _lang(self, text: str):
        return WECHAT_BROWSER.get(
            text, {WxParam.LANGUAGE: text}
        ).get(WxParam.LANGUAGE)
    
    def get_tabs(self) -> List[_PageTab]:
        tabitem = self.control.\
            PaneControl(searchDepth=1, ClassName='').\
            TabItemControl()
        if tabitem.Exists(0):
            tabs = tabitem.GetParentControl().GetChildren()
            return [self._PageTab(i) for i in tabs]
        else:
            return []
    
    def search(self, url):
        search_btn_eles = [
            i for i in self.control.TabControl().GetChildren() 
            if i.BoundingRectangle.height() == i.BoundingRectangle.width()
        ]
        t0 = time.time()
        while True:
            if time.time() - t0 > 10:
                return WxResponse.failure("搜索超时")
            if search_btn_eles:
                search_btn_eles[0].Click()
                edit = self.control.TabControl().EditControl(Name=self._lang('地址和搜索栏'))
                if not edit.Exists(0):
                    continue
                SetClipboardText(url)
                edit.ShortcutPaste()
                edit.SendKeys('{Enter}')
                return WxResponse.success()
            time.sleep(0.1)
    
    def forward(self, friend, message, timeout=10):
        t0 = time.time()
        while True:
            if time.time() - t0 > timeout:
                return WxResponse.failure('微信浏览器页面转发超时')
            more_control = self.control.\
                PaneControl(searchDepth=1, ClassName='').\
                    MenuItemControl(Name=self._lang("更多"))
            more_control.Click()
            time.sleep(0.5)
            copyurl = self.control.PaneControl(ClassName='Chrome_WidgetWin_0')\
                .MenuItemControl(Name=self._lang('转发给朋友'))
            if copyurl.Exists(0):
                copyurl.Click()
                break
            self.control.PaneControl(ClassName='Chrome_WidgetWin_0').SendKeys('{Esc}')
        sendwnd = SelectContactWnd(self)
        return sendwnd.send(friend, message)

    def send_card(self, url, friend, message, timeout=10):
        try:
            if self.search(url):
                return self.forward(friend, message, timeout)
        except Exception as e:
            return WxResponse.failure(message=traceback.format_exc())
        finally:
            self.close()
        
    def close(self):
        wxlog.debug('关闭微信浏览器窗口')
        try:
            self.control.\
                PaneControl(searchDepth=1, ClassName='').\
                    ButtonControl(Name=self._lang("关闭")).Click()
        except Exception as e:
            wxlog.debug('关闭微信浏览器窗口失败', exc_info=True)
        
    def select_option(self, option: str):
        more_control = self.control.\
            PaneControl(searchDepth=1, ClassName='').\
                MenuItemControl(Name=self._lang("更多"))
        menu_control =\
            self.control.PaneControl(ClassName='Chrome_WidgetWin_0').MenuControl(searchDepth=5)
        while not menu_control.Exists(0):
            more_control.Click()
            time.sleep(0.1)
        menu = self._BrowserMenu(menu_control)
        result = menu.select(option)
        menu.close()
        return result
    
    def get_url(self, timeout:int=5) -> str:
        """获取当前页面URL"""
        SetClipboardText('')
        t0 = time.time()
        while not self.control.DocumentControl().Exists(0):
            if time.time()-t0>timeout:
                break
            self.hwnd = FindWindow(self._ui_cls_name, self._ui_name)
            self.control  = uia.ControlFromHandle(self.hwnd)
        while (
            not self.control.DocumentControl().GetChildren() 
            or self.control.DocumentControl().TextControl(Name="mp appmsg sec open").Exists(0)
        ):
            if time.time()-t0>timeout:
                break
            time.sleep(0.1)
        while not self.select_option(self._lang("复制链接")):
            if time.time()-t0>timeout:
                return WxResponse.failure('获取链接超时')
            time.sleep(0.1)
        url = ReadClipboardData()['13']
        return url

def get_wx_browser(func, timeout=10) -> WeChatBrowser:
    t0 = time.time()
    func()
    while True:
        if time.time() - t0 > timeout:
            return WxResponse.failure('无法打开微信浏览器')
        wins = [
            i for i in GetAllWindows() 
            if i[1]==WeChatBrowser._ui_cls_name
            and i[-1]==WeChatBrowser._ui_name
        ]
        browsers = [WeChatBrowser(w[0]) for w in wins]
        for browser in browsers:
            if len(browser.get_tabs()) > 0:
                return browser

class ChatRecordWnd(BaseUISubWnd):
    def __init__(self, parent):
        self.parent = parent
        self.root = parent.root
        self.control = FindTopLevelControl(classname='ChatRecordWnd')

    def get_content(self):
        """获取聊天记录内容"""
        
        msgids = []
        msgs = []
        listcontrol = self.control.ListControl()
        while True:
            listitems = listcontrol.GetChildren()
            listitemids = [item.GetRuntimeId() for item in listitems]
            try:
                msgids = msgids[msgids.index(listitemids[0]):]
            except:
                pass
            for item in listitems:
                msgid = item.GetRuntimeId()
                if msgid not in msgids:
                    msgids.append(msgid)
                    sender = item.GetProgenyControl(4, control_type='TextControl').Name
                    msgtime = parse_wechat_time(item.GetProgenyControl(4, 1, control_type='TextControl').Name)
                    if '[图片]' in item.Name:
                        # wait for image loading
                        for _ in range(10):
                            imgcontrol = item.GetProgenyControl(6, control_type='ButtonControl', refresh=True)
                            if imgcontrol:
                                RollIntoView(listcontrol, imgcontrol, True)
                                imgcontrol.Click()
                                img = WeChatImage()
                                imgpath = img.save()
                                img.close()
                                msgs.append([sender, imgpath, msgtime])
                                break
                            else:
                                time.sleep(1)
                    elif item.Name == '' and item.TextControl(Name='视频').Exists(0.3):
                        videocontrol = item.GetProgenyControl(5, control_type='ButtonControl', refresh=True)
                        if videocontrol:
                            RollIntoView(listcontrol, videocontrol, True)
                            videocontrol.Click()
                            video = WeChatImage()
                            videopath = video.save()
                            video.close()
                            msgs.append([sender, videopath, msgtime])
                    else:
                        textcontrols = item.FindAll(control_type='TextControl')
                        who = textcontrols[0].Name
                        try:
                            content = textcontrols[2].Name
                        except IndexError:
                            content = ''
                        msgs.append([sender, content, msgtime])
            topcontrol = listitems[-1]
            top = topcontrol.BoundingRectangle.top
            self.control.WheelDown(wheelTimes=3)
            time.sleep(0.1)
            if (
                topcontrol.Exists(0.1) 
                and top == topcontrol.BoundingRectangle.top 
                and listitemids == [item.GetRuntimeId() for item in listcontrol.GetChildren()]
            ):
                self.control.SendKeys('{Esc}')
                return msgs
            
class ContactManagerWindow(BaseUISubWnd):
    _ui_cls_name: str = 'ContactManagerWindow'
    _ui_name: str = '通讯录管理'

    def __init__(self, parent: BaseUIWnd = None):
        self.parent = parent
        wins = find_all_windows_from_root(self._ui_cls_name, self._ui_name, self.parent.pid)
        if wins:
            self.control = wins[0]
            self.Sidebar, _, self.ContactBox =\
                self.control.PaneControl(ClassName='', searchDepth=3, foundIndex=3).GetChildren()
        else:
            raise WxautoUINotFoundError('未找到通讯录管理窗口')
        
    def get_friend_num(self):
        """获取好友人数"""
        wxlog.debug('获取好友人数')
        numText = self.Sidebar.PaneControl(Name='全部').TextControl(foundIndex=2).Name
        return int(re.findall('\d+', numText)[0])
    
    def search(self, keyword):
        """搜索好友

        Args:
            keyword (str): 搜索关键词
        """
        wxlog.debug(f"搜索好友：{keyword}")
        self.ContactBox.EditControl(Name="搜索").Click()
        self.ContactBox.ShortcutSelectAll(click=False)
        self.ContactBox.Input(keyword)

    def get_all_friends(self, speed: int = 5):
        """获取好友列表
        
        Args:
            speed (int, optional): 滚动速度，数值越大滚动越快，但是太快可能导致遗漏，建议速度1-5之间
            
        Returns:
            list: 好友列表
        """
        wxlog.debug("获取好友列表")
        contacts_list = []
        contact_ele_list = self.ContactBox.ListControl().GetChildren()

        n = 0
        idx = 0
        while n < 5:
            for _, ele in enumerate(contact_ele_list):
                contacts_info = {
                    'nickname': ele.TextControl().Name.replace('</em>', '').replace('<em>', ''),
                    'remark': ele.ButtonControl(foundIndex=2).Name.replace('</em>', '').replace('<em>', ''),
                    'tags': ele.ButtonControl(foundIndex=3).Name.replace('</em>', '').replace('<em>', '').split('，'),
                }
                if contacts_info.get('remark') in ('添加备注', ''):
                    contacts_info['remark'] = None
                if contacts_info.get('tags') in (['添加标签'], ['']):
                    contacts_info['tags'] = None
                # if contacts_info not in contacts_list:
                contacts_list.append(contacts_info)

            lastid = ele.GetRuntimeId()
            top_ele = ele.BoundingRectangle.top

            n = 0
            while n < 5:
                nowlist = [i.GetRuntimeId() for i in self.ContactBox.ListControl().GetChildren()]
                if lastid != nowlist[-1] and lastid in nowlist and top_ele == ele.BoundingRectangle.top:
                    break

                if top_ele == ele.BoundingRectangle.top:
                    self.ContactBox.WheelDown(wheelTimes=speed)
                    time.sleep(0.01)
                    n += 1
                top_ele = ele.BoundingRectangle.top

            while True:
                nowlist = [i.GetRuntimeId() for i in self.ContactBox.ListControl().GetChildren()]
                if lastid in nowlist:
                    break
                time.sleep(0.01)
            idx = nowlist.index(lastid) + 1
            contact_ele_list = self.ContactBox.ListControl().GetChildren()[idx:]
        return contacts_list
    
    def get_all_recent_groups(self, speed: int = 1, wait=0.05):
        """获取群列表
        
        Args:
            speed (int, optional): 滚动速度，数值越大滚动越快，但是太快可能导致遗漏，建议速度1-3之间
            wait (float, optional): 滚动等待时间，建议和speed一起调整，直至适合你电脑配置和微信群数量达到平衡，不遗漏数据
            
        Returns:
            list: 群列表
        """
        self.control.PaneControl(Name='最近群聊').Click()
        group_list_control = self.control.PaneControl(Name='最近群聊').GetParentControl().ListControl()
        groups = []

        n = 0
        idx = 0
        group_list_items = group_list_control.GetChildren()
        while n < 5:
            for _, item in enumerate(group_list_items):
                text_control1, text_control2 = item.TextControl().GetParentControl().GetChildren()
                group_name = text_control1.Name
                group_members = text_control2.Name.strip('(').strip(')')
                groups.append((group_name, group_members))

            try:
                lastid = item.GetRuntimeId()
            except:
                return self.get_all_recent_groups(speed, wait)
            top_ele = item.BoundingRectangle.top

            n = 0
            while n < 5:
                nowlist = [i.GetRuntimeId() for i in group_list_control.GetChildren()]
                if lastid != nowlist[-1] and lastid in nowlist and top_ele == item.BoundingRectangle.top:
                    break

                if top_ele == item.BoundingRectangle.top:
                    group_list_control.WheelDown(wheelTimes=speed)
                    time.sleep(wait)
                    n += 1
                top_ele = item.BoundingRectangle.top

            while True:
                nowlist = [i.GetRuntimeId() for i in group_list_control.GetChildren()]
                if lastid in nowlist:
                    break
                time.sleep(0.01)
            idx = nowlist.index(lastid) + 1
            group_list_items = group_list_control.GetChildren()[idx:]
        return groups