from wxauto import uia
from wxauto.param import PROJECT_NAME
from wxauto.logger import wxlog
from wxauto.utils.lock import uilock
from abc import ABC, abstractmethod
import win32gui
from typing import Union
import time

class BaseUIWnd(ABC):
    _ui_cls_name: str = None
    _ui_name: str = None
    control: uia.Control

    @abstractmethod
    def _lang(self, text: str):pass

    def __repr__(self):
        return f"<{PROJECT_NAME} - {self.__class__.__name__} at {hex(id(self))}>"
    
    def __eq__(self, other):
        return self.control == other.control
    
    def __bool__(self):
        return self.exists()

    def _show(self):
        if hasattr(self, 'HWND'):
            win32gui.ShowWindow(self.HWND, 1)
            win32gui.SetWindowPos(self.HWND, -1, 0, 0, 0, 0, 3)
            win32gui.SetWindowPos(self.HWND, -2, 0, 0, 0, 0, 3)
        self.control.SwitchToThisWindow()

    @property
    def pid(self):
        return self.control.ProcessId

    @uilock
    def close(self):
        try:
            self.control.SendKeys('{Esc}')
        except:
            pass

    def exists(self, wait=0):
        try:
            result = self.control.Exists(wait)
            return result
        except:
            return False

class BaseUISubWnd(BaseUIWnd):
    root: BaseUIWnd
    parent: None

    def _lang(self, text: str):
        if getattr(self, 'parent'):
            return self.parent._lang(text)
        else:
            return self.root._lang(text)


