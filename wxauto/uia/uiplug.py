# cython: language_level=3
import time
import re
import os
import random
import ctypes
import ctypes.wintypes
import win32gui
import win32api
import win32con
import win32ui
from PIL import Image
from typing import Literal, Optional, Tuple, Callable
import sys
import tkinter as tk
import threading
import queue
import weakref

# ===================================================================== 绘图专用 ===================================================================================
# --- Windows 常量/函数 ---
user32 = ctypes.windll.user32
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
SM_CXSCREEN       = 0
SM_CYSCREEN       = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN= 78
SM_CYVIRTUALSCREEN= 79

def _set_dpi_aware():
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def _get_screen_rect(use_virtual_screen: bool):
    if use_virtual_screen:
        x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return x, y, w, h
    else:
        w = user32.GetSystemMetrics(SM_CXSCREEN)
        h = user32.GetSystemMetrics(SM_CYSCREEN)
        return 0, 0, w, h

# -------- 形状基类 --------
class _ShapeBase:
    """所有形状的公共控制接口。所有 GUI 调用都会被投递到 Tk 线程执行。"""
    def __init__(self, overlay: "Overlay", item_id: int):
        self._ov = overlay
        self._id = item_id
        self._blink_job = None     # Tk after 的 job id
        self._visible = True
        self._blink_hidden = False

    # --- 基础操作 ---
    def set_color(self, color: str):
        self._ov._call(lambda: self._ov._canvas.itemconfig(self._id, outline=color, fill=color))

    def set_outline_color(self, color: str):
        self._ov._call(lambda: self._ov._canvas.itemconfig(self._id, outline=color))

    def set_fill_color(self, color: str):
        self._ov._call(lambda: self._ov._canvas.itemconfig(self._id, fill=color))

    def set_width(self, width: int):
        self._ov._call(lambda: self._ov._canvas.itemconfig(self._id, width=width))

    def show(self):
        def _():
            self._ov._canvas.itemconfigure(self._id, state="normal")
        self._visible = True
        self._ov._call(_)

    def hide(self):
        def _():
            self._ov._canvas.itemconfigure(self._id, state="hidden")
        self._visible = False
        self._ov._call(_)

    def remove(self):
        self.stop_blink()
        self._ov._call(lambda: self._ov._canvas.delete(self._id))

    # --- 闪烁控制（可见/隐藏切换）---
    def start_blink(self, interval_ms: int = 500):
        def _tick():
            # 若对象已被删除或 overlay 关闭，不再继续
            if not self._ov._running:
                return
            try:
                st = self._ov._canvas.itemcget(self._id, "state")
            except tk.TclError:
                return
            new_state = "hidden" if st != "hidden" else "normal"
            self._ov._canvas.itemconfigure(self._id, state=new_state)
            self._blink_job = self._ov._root.after(interval_ms, _tick)

        def _start():
            self.stop_blink()  # 防多次启动
            self._blink_job = self._ov._root.after(interval_ms, _tick)

        self._ov._call(_start)

    def stop_blink(self):
        def _stop():
            if self._blink_job is not None:
                try:
                    self._ov._root.after_cancel(self._blink_job)
                except Exception:
                    pass
                self._blink_job = None
                # 恢复为可见状态
                try:
                    self._ov._canvas.itemconfigure(self._id, state="normal")
                except tk.TclError:
                    pass
        self._ov._call(_stop)

    def flash(self, times: int = 3, interval_sec: float = 0.5,
              keep: bool = False, end_visible: bool = True):
        """
        非阻塞闪烁：自动闪烁若干次并结束。
        times: 翻转次数（隐藏/显示各算一次切换）
        interval_sec: 每次翻转的时间间隔（秒）
        keep: False=结束后清除形状(默认)，True=保留
        end_visible: keep=True 时有效，控制最终是否保持可见
        """
        interval_ms = max(1, int(interval_sec * 1000))

        def _start():
            # 若之前有无限闪烁，先停掉，避免互相抢占
            self.stop_blink()

            remaining = int(times)

            def _tick():
                nonlocal remaining
                if not self._ov._running:
                    return
                try:
                    st = self._ov._canvas.itemcget(self._id, "state")
                except tk.TclError:
                    return

                # 翻转一次
                new_state = "hidden" if st != "hidden" else "normal"
                self._ov._canvas.itemconfigure(self._id, state=new_state)
                remaining -= 1

                if remaining > 0:
                    self._ov._root.after(interval_ms, _tick)
                else:
                    # 完成
                    if keep:
                        # 保留，按 end_visible 设置最终状态
                        try:
                            final_state = "normal" if end_visible else "hidden"
                            self._ov._canvas.itemconfigure(self._id, state=final_state)
                        except tk.TclError:
                            pass
                    else:
                        # 默认清除
                        self.remove()

            self._ov._root.after(interval_ms, _tick)

        self._ov._call(_start)

    # --- 占位：子类实现 ---
    def move_to(self, *args, **kwargs):
        raise NotImplementedError

    def resize(self, *args, **kwargs):
        raise NotImplementedError


# -------- 具体形状 --------
class Rect(_ShapeBase):
    """矩形（空心为主；需要填充可 set_fill_color）"""
    def move_to(self, x1: float, y1: float, x2: float, y2: float):
        self._ov._call(lambda: self._ov._canvas.coords(self._id, *self._ov._rect_coords(x1, y1, x2, y2)))

    def resize(self, x1: float, y1: float, x2: float, y2: float):
        self.move_to(x1, y1, x2, y2)


class Circle(_ShapeBase):
    """圆（用椭圆接口；外接正方形）"""
    def __init__(self, overlay: "Overlay", item_id: int, cx: float, cy: float, r: float):
        super().__init__(overlay, item_id)
        self._cx, self._cy, self._r = cx, cy, r

    def move_to(self, cx: float, cy: float):
        self._cx, self._cy = cx, cy
        def _():
            x1, y1 = self._ov._to_canvas(cx - self._r, cy - self._r)
            x2, y2 = self._ov._to_canvas(cx + self._r, cy + self._r)
            self._ov._canvas.coords(self._id, x1, y1, x2, y2)
        self._ov._call(_)

    def resize(self, r: float):
        self._r = r
        self.move_to(self._cx, self._cy)


class Point(_ShapeBase):
    """点（实心小圆），通过半径 r 控制大小。"""
    def __init__(self, overlay: "Overlay", item_id: int, x: float, y: float, r: float):
        super().__init__(overlay, item_id)
        self._x, self._y, self._r = x, y, r

    def move_to(self, x: float, y: float):
        self._x, self._y = x, y
        def _():
            x1, y1 = self._ov._to_canvas(x - self._r, y - self._r)
            x2, y2 = self._ov._to_canvas(x + self._r, y + self._r)
            self._ov._canvas.coords(self._id, x1, y1, x2, y2)
        self._ov._call(_)

    def resize(self, r: float):
        self._r = r
        self.move_to(self._x, self._y)


# -------- 覆盖层主体（非阻塞） --------
class Overlay:
    """
    非阻塞屏幕覆盖层。
    用法：
        ov = Overlay(click_through=True).start()
        rect = ov.add_rect(200, 150, 700, 450, outline="red", width=4)
        dot  = ov.add_point(960, 540, 6, fill="yellow")
        circ = ov.add_circle(1200, 450, 80, outline="lime", width=6)
        rect.flash(400)
        time.sleep(2)
        rect.set_outline_color("cyan")
        rect.stop_blink()
        rect.remove()
        ov.close()
    """
    def __init__(
        self,
        *,
        topmost: bool = True,
        click_through: bool = True,
        transparent_color: str = "white",
        bg_color: Optional[str] = None,
        dpi_aware: bool = True,
        use_virtual_screen: bool = True,
        queue_poll_ms: int = 10,  # 轮询任务队列频率
    ):
        if dpi_aware:
            _set_dpi_aware()

        self.tx = transparent_color
        self.bg = bg_color or transparent_color
        self.topmost = topmost
        self.click_through = click_through
        self.use_virtual_screen = use_virtual_screen

        self._screen = _get_screen_rect(use_virtual_screen)
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._q: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._running = False
        self._queue_poll_ms = queue_poll_ms

    # --- 启动/关闭 ---
    def start(self):
        """非阻塞启动，返回 self。"""
        if self._running:
            return self
        self._running = True
        self._thread = threading.Thread(target=self._tk_thread_main, name="OverlayTk", daemon=True)
        self._thread.start()
        # 等到 Tk 初始化完成
        while self._canvas is None and self._running:
            time.sleep(0.01)
        return self

    def close(self):
        """关闭覆盖层与 Tk 主循环。"""
        if not self._running:
            return
        def _shutdown():
            try:
                self._root.destroy()
            except Exception:
                pass
        self._call(_shutdown)
        self._running = False

    # --- 对外：创建形状 ---
    def add_rect(self, x1, y1, x2, y2, *, outline="red", width=4, fill=""):
        def _create():
            x1c, y1c, x2c, y2c = self._rect_coords(x1, y1, x2, y2)
            iid = self._canvas.create_rectangle(x1c, y1c, x2c, y2c, outline=outline, width=width, fill=fill)
            return Rect(self, iid)
        return self._call(_create, need_result=True)

    def add_circle(self, cx, cy, r, *, outline="lime", width=6, fill=""):
        def _create():
            x1, y1 = self._to_canvas(cx - r, cy - r)
            x2, y2 = self._to_canvas(cx + r, cy + r)
            iid = self._canvas.create_oval(x1, y1, x2, y2, outline=outline, width=width, fill=fill)
            return Circle(self, iid, cx, cy, r)
        return self._call(_create, need_result=True)

    def add_point(self, x, y, r=4, *, fill="yellow", outline=None, width=1):
        def _create():
            x1, y1 = self._to_canvas(x - r, y - r)
            x2, y2 = self._to_canvas(x + r, y + r)
            iid = self._canvas.create_oval(x1, y1, x2, y2,
                                           outline=outline if outline else fill,
                                           width=width,
                                           fill=fill)
            return Point(self, iid, x, y, r)
        return self._call(_create, need_result=True)

    # --- 公共实用 ---
    def set_click_through(self, enabled: bool):
        def _():
            exstyle = ctypes.windll.user32.GetWindowLongW(self._hwnd, GWL_EXSTYLE)
            exstyle |= WS_EX_LAYERED
            if enabled:
                exstyle |= WS_EX_TRANSPARENT
            else:
                exstyle &= ~WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(self._hwnd, GWL_EXSTYLE, exstyle)
        self._call(_)

    # --- 内部：Tk 线程与任务队列 ---
    def _tk_thread_main(self):
        x, y, w, h = self._screen
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", self.topmost)
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.config(bg=self.bg)
        root.attributes("-transparentcolor", self.tx)

        cv = tk.Canvas(root, width=w, height=h, highlightthickness=0, bg=self.bg)
        cv.pack(fill="both", expand=True)

        root.bind("<Escape>", lambda e: self.close())

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        exstyle |= WS_EX_LAYERED
        if self.click_through:
            exstyle |= WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)

        self._root = root
        self._canvas = cv
        self._hwnd = hwnd

        def pump():
            # 从队列取尽可能多的任务执行到 Tk 线程
            try:
                while True:
                    fn = self._q.get_nowait()
                    fn()
            except queue.Empty:
                pass
            if self._running:
                root.after(self._queue_poll_ms, pump)

        root.after(self._queue_poll_ms, pump)
        try:
            root.mainloop()
        finally:
            self._running = False
            self._root = None
            self._canvas = None
            self._hwnd = None

    def _call(self, fn: Callable[[], Optional[object]], need_result: bool = False):
        """把 fn 投递到 Tk 线程执行。need_result=True 时同步等待返回值。"""
        if not self._running:
            raise RuntimeError("Overlay not started. Call start() first.")
        if not need_result:
            self._q.put(fn)
            return None
        # 等待结果
        res_box = {"value": None, "exc": None}
        ev = threading.Event()
        def wrapper():
            try:
                res_box["value"] = fn()
            except Exception as e:
                res_box["exc"] = e
            finally:
                ev.set()
        self._q.put(wrapper)
        ev.wait()
        if res_box["exc"] is not None:
            raise res_box["exc"]
        return res_box["value"]

    # --- 坐标辅助 ---
    def _to_canvas(self, x: float, y: float) -> Tuple[float, float]:
        sx, sy, _, _ = self._screen
        return x - sx, y - sy

    def _rect_coords(self, x1, y1, x2, y2):
        x1c, y1c = self._to_canvas(x1, y1)
        x2c, y2c = self._to_canvas(x2, y2)
        return x1c, y1c, x2c, y2c
    
class _OverlaySingleton:
    _lock = threading.RLock()
    _instance_ref: "weakref.ReferenceType[Overlay] | None" = None

    @classmethod
    def get(cls, **kwargs) -> Overlay:
        """
        获取（或创建）全局唯一 Overlay。
        如果已有实例但已经关闭，会自动重建。
        kwargs 会在首次创建时传入 Overlay(**kwargs)。
        后续调用忽略 kwargs（如需改变参数，请先显式 close）。
        """
        with cls._lock:
            inst = cls._instance_ref() if cls._instance_ref else None
            if inst is not None and inst._running:
                return inst
            # 旧实例不可用：新建
            inst = Overlay(**kwargs).start()
            cls._instance_ref = weakref.ref(inst)
            return inst

    @classmethod
    def close(cls):
        """关闭并清空全局实例。"""
        with cls._lock:
            inst = cls._instance_ref() if cls._instance_ref else None
            if inst is not None:
                try:
                    inst.close()
                finally:
                    cls._instance_ref = None


def get_overlay(**kwargs) -> Overlay:
    """
    便捷函数：获取全局 Overlay 单例。
    示例：ov = get_overlay(click_through=True)
    """
    return _OverlaySingleton.get(**kwargs)
# ===================================================================== 绘图专用End ===================================================================================

GlobalKeyNames = [
    'CONTROL', 
    'ALT', 
    'SHIFT', 
    'WIN', 
    'CTRL', 
    'LWIN', 
    'RWIN'
]

class Keys:
    """Key codes from Win32."""
    VK_LBUTTON = 0x01                       #Left mouse button
    VK_RBUTTON = 0x02                       #Right mouse button
    VK_CANCEL = 0x03                        #Control-break processing
    VK_MBUTTON = 0x04                       #Middle mouse button (three-button mouse)
    VK_XBUTTON1 = 0x05                      #X1 mouse button
    VK_XBUTTON2 = 0x06                      #X2 mouse button
    VK_BACK = 0x08                          #BACKSPACE key
    VK_TAB = 0x09                           #TAB key
    VK_CLEAR = 0x0C                         #CLEAR key
    VK_RETURN = 0x0D                        #ENTER key
    VK_ENTER = 0x0D
    VK_SHIFT = 0x10                         #SHIFT key
    VK_CONTROL = 0x11                       #CTRL key
    VK_MENU = 0x12                          #ALT key
    VK_PAUSE = 0x13                         #PAUSE key
    VK_CAPITAL = 0x14                       #CAPS LOCK key
    VK_KANA = 0x15                          #IME Kana mode
    VK_HANGUEL = 0x15                       #IME Hanguel mode (maintained for compatibility; use VK_HANGUL)
    VK_HANGUL = 0x15                        #IME Hangul mode
    VK_JUNJA = 0x17                         #IME Junja mode
    VK_FINAL = 0x18                         #IME final mode
    VK_HANJA = 0x19                         #IME Hanja mode
    VK_KANJI = 0x19                         #IME Kanji mode
    VK_ESCAPE = 0x1B                        #ESC key
    VK_CONVERT = 0x1C                       #IME convert
    VK_NONCONVERT = 0x1D                    #IME nonconvert
    VK_ACCEPT = 0x1E                        #IME accept
    VK_MODECHANGE = 0x1F                    #IME mode change request
    VK_SPACE = 0x20                         #SPACEBAR
    VK_PRIOR = 0x21                         #PAGE UP key
    VK_PAGEUP = 0x21
    VK_NEXT = 0x22                          #PAGE DOWN key
    VK_PAGEDOWN = 0x22
    VK_END = 0x23                           #END key
    VK_HOME = 0x24                          #HOME key
    VK_LEFT = 0x25                          #LEFT ARROW key
    VK_UP = 0x26                            #UP ARROW key
    VK_RIGHT = 0x27                         #RIGHT ARROW key
    VK_DOWN = 0x28                          #DOWN ARROW key
    VK_SELECT = 0x29                        #SELECT key
    VK_PRINT = 0x2A                         #PRINT key
    VK_EXECUTE = 0x2B                       #EXECUTE key
    VK_SNAPSHOT = 0x2C                      #PRINT SCREEN key
    VK_INSERT = 0x2D                        #INS key
    VK_DELETE = 0x2E                        #DEL key
    VK_HELP = 0x2F                          #HELP key
    VK_0 = 0x30                             #0 key
    VK_1 = 0x31                             #1 key
    VK_2 = 0x32                             #2 key
    VK_3 = 0x33                             #3 key
    VK_4 = 0x34                             #4 key
    VK_5 = 0x35                             #5 key
    VK_6 = 0x36                             #6 key
    VK_7 = 0x37                             #7 key
    VK_8 = 0x38                             #8 key
    VK_9 = 0x39                             #9 key
    VK_A = 0x41                             #A key
    VK_B = 0x42                             #B key
    VK_C = 0x43                             #C key
    VK_D = 0x44                             #D key
    VK_E = 0x45                             #E key
    VK_F = 0x46                             #F key
    VK_G = 0x47                             #G key
    VK_H = 0x48                             #H key
    VK_I = 0x49                             #I key
    VK_J = 0x4A                             #J key
    VK_K = 0x4B                             #K key
    VK_L = 0x4C                             #L key
    VK_M = 0x4D                             #M key
    VK_N = 0x4E                             #N key
    VK_O = 0x4F                             #O key
    VK_P = 0x50                             #P key
    VK_Q = 0x51                             #Q key
    VK_R = 0x52                             #R key
    VK_S = 0x53                             #S key
    VK_T = 0x54                             #T key
    VK_U = 0x55                             #U key
    VK_V = 0x56                             #V key
    VK_W = 0x57                             #W key
    VK_X = 0x58                             #X key
    VK_Y = 0x59                             #Y key
    VK_Z = 0x5A                             #Z key
    VK_LWIN = 0x5B                          #Left Windows key (Natural keyboard)
    VK_RWIN = 0x5C                          #Right Windows key (Natural keyboard)
    VK_APPS = 0x5D                          #Applications key (Natural keyboard)
    VK_SLEEP = 0x5F                         #Computer Sleep key
    VK_NUMPAD0 = 0x60                       #Numeric keypad 0 key
    VK_NUMPAD1 = 0x61                       #Numeric keypad 1 key
    VK_NUMPAD2 = 0x62                       #Numeric keypad 2 key
    VK_NUMPAD3 = 0x63                       #Numeric keypad 3 key
    VK_NUMPAD4 = 0x64                       #Numeric keypad 4 key
    VK_NUMPAD5 = 0x65                       #Numeric keypad 5 key
    VK_NUMPAD6 = 0x66                       #Numeric keypad 6 key
    VK_NUMPAD7 = 0x67                       #Numeric keypad 7 key
    VK_NUMPAD8 = 0x68                       #Numeric keypad 8 key
    VK_NUMPAD9 = 0x69                       #Numeric keypad 9 key
    VK_MULTIPLY = 0x6A                      #Multiply key
    VK_ADD = 0x6B                           #Add key
    VK_SEPARATOR = 0x6C                     #Separator key
    VK_SUBTRACT = 0x6D                      #Subtract key
    VK_DECIMAL = 0x6E                       #Decimal key
    VK_DIVIDE = 0x6F                        #Divide key
    VK_F1 = 0x70                            #F1 key
    VK_F2 = 0x71                            #F2 key
    VK_F3 = 0x72                            #F3 key
    VK_F4 = 0x73                            #F4 key
    VK_F5 = 0x74                            #F5 key
    VK_F6 = 0x75                            #F6 key
    VK_F7 = 0x76                            #F7 key
    VK_F8 = 0x77                            #F8 key
    VK_F9 = 0x78                            #F9 key
    VK_F10 = 0x79                           #F10 key
    VK_F11 = 0x7A                           #F11 key
    VK_F12 = 0x7B                           #F12 key
    VK_F13 = 0x7C                           #F13 key
    VK_F14 = 0x7D                           #F14 key
    VK_F15 = 0x7E                           #F15 key
    VK_F16 = 0x7F                           #F16 key
    VK_F17 = 0x80                           #F17 key
    VK_F18 = 0x81                           #F18 key
    VK_F19 = 0x82                           #F19 key
    VK_F20 = 0x83                           #F20 key
    VK_F21 = 0x84                           #F21 key
    VK_F22 = 0x85                           #F22 key
    VK_F23 = 0x86                           #F23 key
    VK_F24 = 0x87                           #F24 key
    VK_NUMLOCK = 0x90                       #NUM LOCK key
    VK_SCROLL = 0x91                        #SCROLL LOCK key
    VK_LSHIFT = 0xA0                        #Left SHIFT key
    VK_RSHIFT = 0xA1                        #Right SHIFT key
    VK_LCONTROL = 0xA2                      #Left CONTROL key
    VK_RCONTROL = 0xA3                      #Right CONTROL key
    VK_LMENU = 0xA4                         #Left MENU key
    VK_RMENU = 0xA5                         #Right MENU key
    VK_BROWSER_BACK = 0xA6                  #Browser Back key
    VK_BROWSER_FORWARD = 0xA7               #Browser Forward key
    VK_BROWSER_REFRESH = 0xA8               #Browser Refresh key
    VK_BROWSER_STOP = 0xA9                  #Browser Stop key
    VK_BROWSER_SEARCH = 0xAA                #Browser Search key
    VK_BROWSER_FAVORITES = 0xAB             #Browser Favorites key
    VK_BROWSER_HOME = 0xAC                  #Browser Start and Home key
    VK_VOLUME_MUTE = 0xAD                   #Volume Mute key
    VK_VOLUME_DOWN = 0xAE                   #Volume Down key
    VK_VOLUME_UP = 0xAF                     #Volume Up key
    VK_MEDIA_NEXT_TRACK = 0xB0              #Next Track key
    VK_MEDIA_PREV_TRACK = 0xB1              #Previous Track key
    VK_MEDIA_STOP = 0xB2                    #Stop Media key
    VK_MEDIA_PLAY_PAUSE = 0xB3              #Play/Pause Media key
    VK_LAUNCH_MAIL = 0xB4                   #Start Mail key
    VK_LAUNCH_MEDIA_SELECT = 0xB5           #Select Media key
    VK_LAUNCH_APP1 = 0xB6                   #Start Application 1 key
    VK_LAUNCH_APP2 = 0xB7                   #Start Application 2 key
    VK_OEM_1 = 0xBA                         #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the ';:' key
    VK_OEM_PLUS = 0xBB                      #For any country/region, the '+' key
    VK_OEM_COMMA = 0xBC                     #For any country/region, the ',' key
    VK_OEM_MINUS = 0xBD                     #For any country/region, the '-' key
    VK_OEM_PERIOD = 0xBE                    #For any country/region, the '.' key
    VK_OEM_2 = 0xBF                         #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '/?' key
    VK_OEM_3 = 0xC0                         #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '`~' key
    VK_OEM_4 = 0xDB                         #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '[{' key
    VK_OEM_5 = 0xDC                         #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '\|' key
    VK_OEM_6 = 0xDD                         #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the ']}' key
    VK_OEM_7 = 0xDE                         #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the 'single-quote/double-quote' key
    VK_OEM_8 = 0xDF                         #Used for miscellaneous characters; it can vary by keyboard.
    VK_OEM_102 = 0xE2                       #Either the angle bracket key or the backslash key on the RT 102-key keyboard
    VK_PROCESSKEY = 0xE5                    #IME PROCESS key
    VK_PACKET = 0xE7                        #Used to pass Unicode characters as if they were keystrokes. The VK_PACKET key is the low word of a 32-bit Virtual Key value used for non-keyboard input methods. For more information, see Remark in KEYBDINPUT, SendInput, WM_KEYDOWN, and WM_KeyUp
    VK_ATTN = 0xF6                          #Attn key
    VK_CRSEL = 0xF7                         #CrSel key
    VK_EXSEL = 0xF8                         #ExSel key
    VK_EREOF = 0xF9                         #Erase EOF key
    VK_PLAY = 0xFA                          #Play key
    VK_ZOOM = 0xFB                          #Zoom key
    VK_NONAME = 0xFC                        #Reserved
    VK_PA1 = 0xFD                           #PA1 key
    VK_OEM_CLEAR = 0xFE                     #Clear key

CharacterCodes = {
    '0': Keys.VK_0,                             #0 key
    '1': Keys.VK_1,                             #1 key
    '2': Keys.VK_2,                             #2 key
    '3': Keys.VK_3,                             #3 key
    '4': Keys.VK_4,                             #4 key
    '5': Keys.VK_5,                             #5 key
    '6': Keys.VK_6,                             #6 key
    '7': Keys.VK_7,                             #7 key
    '8': Keys.VK_8,                             #8 key
    '9': Keys.VK_9,                             #9 key
    'a': Keys.VK_A,                             #A key
    'A': Keys.VK_A,                             #A key
    'b': Keys.VK_B,                             #B key
    'B': Keys.VK_B,                             #B key
    'c': Keys.VK_C,                             #C key
    'C': Keys.VK_C,                             #C key
    'd': Keys.VK_D,                             #D key
    'D': Keys.VK_D,                             #D key
    'e': Keys.VK_E,                             #E key
    'E': Keys.VK_E,                             #E key
    'f': Keys.VK_F,                             #F key
    'F': Keys.VK_F,                             #F key
    'g': Keys.VK_G,                             #G key
    'G': Keys.VK_G,                             #G key
    'h': Keys.VK_H,                             #H key
    'H': Keys.VK_H,                             #H key
    'i': Keys.VK_I,                             #I key
    'I': Keys.VK_I,                             #I key
    'j': Keys.VK_J,                             #J key
    'J': Keys.VK_J,                             #J key
    'k': Keys.VK_K,                             #K key
    'K': Keys.VK_K,                             #K key
    'l': Keys.VK_L,                             #L key
    'L': Keys.VK_L,                             #L key
    'm': Keys.VK_M,                             #M key
    'M': Keys.VK_M,                             #M key
    'n': Keys.VK_N,                             #N key
    'N': Keys.VK_N,                             #N key
    'o': Keys.VK_O,                             #O key
    'O': Keys.VK_O,                             #O key
    'p': Keys.VK_P,                             #P key
    'P': Keys.VK_P,                             #P key
    'q': Keys.VK_Q,                             #Q key
    'Q': Keys.VK_Q,                             #Q key
    'r': Keys.VK_R,                             #R key
    'R': Keys.VK_R,                             #R key
    's': Keys.VK_S,                             #S key
    'S': Keys.VK_S,                             #S key
    't': Keys.VK_T,                             #T key
    'T': Keys.VK_T,                             #T key
    'u': Keys.VK_U,                             #U key
    'U': Keys.VK_U,                             #U key
    'v': Keys.VK_V,                             #V key
    'V': Keys.VK_V,                             #V key
    'w': Keys.VK_W,                             #W key
    'W': Keys.VK_W,                             #W key
    'x': Keys.VK_X,                             #X key
    'X': Keys.VK_X,                             #X key
    'y': Keys.VK_Y,                             #Y key
    'Y': Keys.VK_Y,                             #Y key
    'z': Keys.VK_Z,                             #Z key
    'Z': Keys.VK_Z,                             #Z key
    ' ': Keys.VK_SPACE,                         #Space key
    '`': Keys.VK_OEM_3,                         #` key
    #'~' : Keys.VK_OEM_3,                         #~ key
    '-': Keys.VK_OEM_MINUS,                     #- key
    #'_' : Keys.VK_OEM_MINUS,                     #_ key
    '=': Keys.VK_OEM_PLUS,                      #= key
    #'+' : Keys.VK_OEM_PLUS,                      #+ key
    '[': Keys.VK_OEM_4,                         #[ key
    #'{' : Keys.VK_OEM_4,                         #{ key
    ']': Keys.VK_OEM_6,                         #] key
    #'}' : Keys.VK_OEM_6,                         #} key
    '\\': Keys.VK_OEM_5,                        #\ key
    #'|' : Keys.VK_OEM_5,                         #| key
    ';': Keys.VK_OEM_1,                         #; key
    #':' : Keys.VK_OEM_1,                         #: key
    '\'': Keys.VK_OEM_7,                        #' key
    #'"' : Keys.VK_OEM_7,                         #" key
    ',': Keys.VK_OEM_COMMA,                     #, key
    #'<' : Keys.VK_OEM_COMMA,                     #< key
    '.': Keys.VK_OEM_PERIOD,                    #. key
    #'>' : Keys.VK_OEM_PERIOD,                    #> key
    '/': Keys.VK_OEM_2,                         #/ key
    #'?' : Keys.VK_OEM_2,                         #? key
}


SpecialKeyNames = {
    'LBUTTON': Keys.VK_LBUTTON,                        #Left mouse button
    'RBUTTON': Keys.VK_RBUTTON,                        #Right mouse button
    'CANCEL': Keys.VK_CANCEL,                          #Control-break processing
    'MBUTTON': Keys.VK_MBUTTON,                        #Middle mouse button (three-button mouse)
    'XBUTTON1': Keys.VK_XBUTTON1,                      #X1 mouse button
    'XBUTTON2': Keys.VK_XBUTTON2,                      #X2 mouse button
    'BACK': Keys.VK_BACK,                              #BACKSPACE key
    'TAB': Keys.VK_TAB,                                #TAB key
    'CLEAR': Keys.VK_CLEAR,                            #CLEAR key
    'RETURN': Keys.VK_RETURN,                          #ENTER key
    'ENTER': Keys.VK_RETURN,                           #ENTER key
    'SHIFT': Keys.VK_SHIFT,                            #SHIFT key
    'CTRL': Keys.VK_CONTROL,                           #CTRL key
    'CONTROL': Keys.VK_CONTROL,                        #CTRL key
    'ALT': Keys.VK_MENU,                               #ALT key
    'PAUSE': Keys.VK_PAUSE,                            #PAUSE key
    'CAPITAL': Keys.VK_CAPITAL,                        #CAPS LOCK key
    'KANA': Keys.VK_KANA,                              #IME Kana mode
    'HANGUEL': Keys.VK_HANGUEL,                        #IME Hanguel mode (maintained for compatibility; use VK_HANGUL)
    'HANGUL': Keys.VK_HANGUL,                          #IME Hangul mode
    'JUNJA': Keys.VK_JUNJA,                            #IME Junja mode
    'FINAL': Keys.VK_FINAL,                            #IME final mode
    'HANJA': Keys.VK_HANJA,                            #IME Hanja mode
    'KANJI': Keys.VK_KANJI,                            #IME Kanji mode
    'ESC': Keys.VK_ESCAPE,                             #ESC key
    'ESCAPE': Keys.VK_ESCAPE,                          #ESC key
    'CONVERT': Keys.VK_CONVERT,                        #IME convert
    'NONCONVERT': Keys.VK_NONCONVERT,                  #IME nonconvert
    'ACCEPT': Keys.VK_ACCEPT,                          #IME accept
    'MODECHANGE': Keys.VK_MODECHANGE,                  #IME mode change request
    'SPACE': Keys.VK_SPACE,                            #SPACEBAR
    'PRIOR': Keys.VK_PRIOR,                            #PAGE UP key
    'PAGEUP': Keys.VK_PRIOR,                           #PAGE UP key
    'NEXT': Keys.VK_NEXT,                              #PAGE DOWN key
    'PAGEDOWN': Keys.VK_NEXT,                           #PAGE DOWN key
    'END': Keys.VK_END,                                #END key
    'HOME': Keys.VK_HOME,                              #HOME key
    'LEFT': Keys.VK_LEFT,                              #LEFT ARROW key
    'UP': Keys.VK_UP,                                  #UP ARROW key
    'RIGHT': Keys.VK_RIGHT,                            #RIGHT ARROW key
    'DOWN': Keys.VK_DOWN,                              #DOWN ARROW key
    'SELECT': Keys.VK_SELECT,                          #SELECT key
    'PRINT': Keys.VK_PRINT,                            #PRINT key
    'EXECUTE': Keys.VK_EXECUTE,                        #EXECUTE key
    'SNAPSHOT': Keys.VK_SNAPSHOT,                      #PRINT SCREEN key
    'PRINTSCREEN': Keys.VK_SNAPSHOT,                    #PRINT SCREEN key
    'INSERT': Keys.VK_INSERT,                          #INS key
    'INS': Keys.VK_INSERT,                             #INS key
    'DELETE': Keys.VK_DELETE,                          #DEL key
    'DEL': Keys.VK_DELETE,                             #DEL key
    'HELP': Keys.VK_HELP,                              #HELP key
    'WIN': Keys.VK_LWIN,                               #Left Windows key (Natural keyboard)
    'LWIN': Keys.VK_LWIN,                              #Left Windows key (Natural keyboard)
    'RWIN': Keys.VK_RWIN,                              #Right Windows key (Natural keyboard)
    'APPS': Keys.VK_APPS,                              #Applications key (Natural keyboard)
    'SLEEP': Keys.VK_SLEEP,                            #Computer Sleep key
    'NUMPAD0': Keys.VK_NUMPAD0,                        #Numeric keypad 0 key
    'NUMPAD1': Keys.VK_NUMPAD1,                        #Numeric keypad 1 key
    'NUMPAD2': Keys.VK_NUMPAD2,                        #Numeric keypad 2 key
    'NUMPAD3': Keys.VK_NUMPAD3,                        #Numeric keypad 3 key
    'NUMPAD4': Keys.VK_NUMPAD4,                        #Numeric keypad 4 key
    'NUMPAD5': Keys.VK_NUMPAD5,                        #Numeric keypad 5 key
    'NUMPAD6': Keys.VK_NUMPAD6,                        #Numeric keypad 6 key
    'NUMPAD7': Keys.VK_NUMPAD7,                        #Numeric keypad 7 key
    'NUMPAD8': Keys.VK_NUMPAD8,                        #Numeric keypad 8 key
    'NUMPAD9': Keys.VK_NUMPAD9,                        #Numeric keypad 9 key
    'MULTIPLY': Keys.VK_MULTIPLY,                      #Multiply key
    'ADD': Keys.VK_ADD,                                #Add key
    'SEPARATOR': Keys.VK_SEPARATOR,                    #Separator key
    'SUBTRACT': Keys.VK_SUBTRACT,                      #Subtract key
    'DECIMAL': Keys.VK_DECIMAL,                        #Decimal key
    'DIVIDE': Keys.VK_DIVIDE,                          #Divide key
    'F1': Keys.VK_F1,                                  #F1 key
    'F2': Keys.VK_F2,                                  #F2 key
    'F3': Keys.VK_F3,                                  #F3 key
    'F4': Keys.VK_F4,                                  #F4 key
    'F5': Keys.VK_F5,                                  #F5 key
    'F6': Keys.VK_F6,                                  #F6 key
    'F7': Keys.VK_F7,                                  #F7 key
    'F8': Keys.VK_F8,                                  #F8 key
    'F9': Keys.VK_F9,                                  #F9 key
    'F10': Keys.VK_F10,                                #F10 key
    'F11': Keys.VK_F11,                                #F11 key
    'F12': Keys.VK_F12,                                #F12 key
    'F13': Keys.VK_F13,                                #F13 key
    'F14': Keys.VK_F14,                                #F14 key
    'F15': Keys.VK_F15,                                #F15 key
    'F16': Keys.VK_F16,                                #F16 key
    'F17': Keys.VK_F17,                                #F17 key
    'F18': Keys.VK_F18,                                #F18 key
    'F19': Keys.VK_F19,                                #F19 key
    'F20': Keys.VK_F20,                                #F20 key
    'F21': Keys.VK_F21,                                #F21 key
    'F22': Keys.VK_F22,                                #F22 key
    'F23': Keys.VK_F23,                                #F23 key
    'F24': Keys.VK_F24,                                #F24 key
    'NUMLOCK': Keys.VK_NUMLOCK,                        #NUM LOCK key
    'SCROLL': Keys.VK_SCROLL,                          #SCROLL LOCK key
    'LSHIFT': Keys.VK_LSHIFT,                          #Left SHIFT key
    'RSHIFT': Keys.VK_RSHIFT,                          #Right SHIFT key
    'LCONTROL': Keys.VK_LCONTROL,                      #Left CONTROL key
    'LCTRL': Keys.VK_LCONTROL,                         #Left CONTROL key
    'RCONTROL': Keys.VK_RCONTROL,                      #Right CONTROL key
    'RCTRL': Keys.VK_RCONTROL,                         #Right CONTROL key
    'LALT': Keys.VK_LMENU,                             #Left MENU key
    'RALT': Keys.VK_RMENU,                             #Right MENU key
    'BROWSER_BACK': Keys.VK_BROWSER_BACK,              #Browser Back key
    'BROWSER_FORWARD': Keys.VK_BROWSER_FORWARD,        #Browser Forward key
    'BROWSER_REFRESH': Keys.VK_BROWSER_REFRESH,        #Browser Refresh key
    'BROWSER_STOP': Keys.VK_BROWSER_STOP,              #Browser Stop key
    'BROWSER_SEARCH': Keys.VK_BROWSER_SEARCH,          #Browser Search key
    'BROWSER_FAVORITES': Keys.VK_BROWSER_FAVORITES,    #Browser Favorites key
    'BROWSER_HOME': Keys.VK_BROWSER_HOME,              #Browser Start and Home key
    'VOLUME_MUTE': Keys.VK_VOLUME_MUTE,                #Volume Mute key
    'VOLUME_DOWN': Keys.VK_VOLUME_DOWN,                #Volume Down key
    'VOLUME_UP': Keys.VK_VOLUME_UP,                    #Volume Up key
    'MEDIA_NEXT_TRACK': Keys.VK_MEDIA_NEXT_TRACK,      #Next Track key
    'MEDIA_PREV_TRACK': Keys.VK_MEDIA_PREV_TRACK,      #Previous Track key
    'MEDIA_STOP': Keys.VK_MEDIA_STOP,                  #Stop Media key
    'MEDIA_PLAY_PAUSE': Keys.VK_MEDIA_PLAY_PAUSE,      #Play/Pause Media key
    'LAUNCH_MAIL': Keys.VK_LAUNCH_MAIL,                #Start Mail key
    'LAUNCH_MEDIA_SELECT': Keys.VK_LAUNCH_MEDIA_SELECT,#Select Media key
    'LAUNCH_APP1': Keys.VK_LAUNCH_APP1,                #Start Application 1 key
    'LAUNCH_APP2': Keys.VK_LAUNCH_APP2,                #Start Application 2 key
    'OEM_1': Keys.VK_OEM_1,                            #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the ';:' key
    'OEM_PLUS': Keys.VK_OEM_PLUS,                      #For any country/region, the '+' key
    'OEM_COMMA': Keys.VK_OEM_COMMA,                    #For any country/region, the ',' key
    'OEM_MINUS': Keys.VK_OEM_MINUS,                    #For any country/region, the '-' key
    'OEM_PERIOD': Keys.VK_OEM_PERIOD,                  #For any country/region, the '.' key
    'OEM_2': Keys.VK_OEM_2,                            #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '/?' key
    'OEM_3': Keys.VK_OEM_3,                            #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '`~' key
    'OEM_4': Keys.VK_OEM_4,                            #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '[{' key
    'OEM_5': Keys.VK_OEM_5,                            #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the '\|' key
    'OEM_6': Keys.VK_OEM_6,                            #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the ']}' key
    'OEM_7': Keys.VK_OEM_7,                            #Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the 'single-quote/double-quote' key
    'OEM_8': Keys.VK_OEM_8,                            #Used for miscellaneous characters; it can vary by keyboard.
    'OEM_102': Keys.VK_OEM_102,                        #Either the angle bracket key or the backslash key on the RT 102-key keyboard
    'PROCESSKEY': Keys.VK_PROCESSKEY,                  #IME PROCESS key
    'PACKET': Keys.VK_PACKET,                          #Used to pass Unicode characters as if they were keystrokes. The VK_PACKET key is the low word of a 32-bit Virtual Key value used for non-keyboard input methods. For more information, see Remark in KEYBDINPUT, SendInput, WM_KEYDOWN, and WM_KeyUp
    'ATTN': Keys.VK_ATTN,                              #Attn key
    'CRSEL': Keys.VK_CRSEL,                            #CrSel key
    'EXSEL': Keys.VK_EXSEL,                            #ExSel key
    'EREOF': Keys.VK_EREOF,                            #Erase EOF key
    'PLAY': Keys.VK_PLAY,                              #Play key
    'ZOOM': Keys.VK_ZOOM,                              #Zoom key
    'NONAME': Keys.VK_NONAME,                          #Reserved
    'PA1': Keys.VK_PA1,                                #PA1 key
    'OEM_CLEAR': Keys.VK_OEM_CLEAR,                    #Clear key
}

def SetClipboardText(text: str) -> bool:
    """
    Return bool, True if succeed otherwise False.
    """
    if ctypes.windll.user32.OpenClipboard(0):
        ctypes.windll.user32.EmptyClipboard()
        textByteLen = (len(text) + 1) * 2
        hClipboardData = ctypes.windll.kernel32.GlobalAlloc(0, textByteLen)  # GMEM_FIXED=0
        hDestText = ctypes.windll.kernel32.GlobalLock(ctypes.c_void_p(hClipboardData))
        ctypes.cdll.msvcrt.wcsncpy(ctypes.c_wchar_p(hDestText), ctypes.c_wchar_p(text), ctypes.c_size_t(textByteLen // 2))
        ctypes.windll.kernel32.GlobalUnlock(ctypes.c_void_p(hClipboardData))
        # system owns hClipboardData after calling SetClipboardData,
        # application can not write to or free the data once ownership has been transferred to the system
        ctypes.windll.user32.SetClipboardData(ctypes.c_uint(13), ctypes.c_void_p(hClipboardData))  # CF_TEXT=1, CF_UNICODETEXT=13
        ctypes.windll.user32.CloseClipboard()
        return True
    return False

# Add by Cluic
class Win32:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        # print(time.time())
    #     self._check_hwnd()

    # def _check_hwnd(self):
    #     if not win32gui.IsWindow(self.hwnd):
    #         raise Exception("Window not found")

    @property
    def _overlay(self):
        return get_overlay()

    def activate(self):
        """
        Activate the window.
        """
        win32gui.ShowWindow(self.hwnd, 1)
        win32gui.SetWindowPos(self.hwnd, -1, 0, 0, 0, 0, 3)
        win32gui.SetWindowPos(self.hwnd, -2, 0, 0, 0, 0, 3)
    
    def click(self, x: int, y: int, button: Literal["left", "right", "mid"] = "left", activate: bool = False, move: bool = False):
        """
        Click at the specified client coordinates, with an option to move the mouse first.
        
        Args:
            x: The x-coordinate.
            y: The y-coordinate.
            button: The button to click. Default is "left".
            activate: Whether to activate the window before clicking.
            move: Whether to move the mouse to the position before clicking and trigger a mouse click event.
        """
        if os.environ.get('wxauto4_DEVELOP'):
            self._overlay.add_point(x, y, 6, fill='red').flash()
        
        if activate:
            self.activate()

        if move:
            self.activate()
            # Move the mouse to (x, y)
            win32api.SetCursorPos((x, y))

            # Simulate a mouse click using mouse_event
            if button.lower() == "left":
                # Simulate left mouse button down and up (click)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            elif button.lower() == "right":
                # Simulate right mouse button down and up (click)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y)
            elif button.lower() == "mid":
                # Simulate middle mouse button down and up (click)
                win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, x, y)
                win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, x, y)
            else:
                raise ValueError("Invalid button")
        else:
            # If move is False, proceed with the original message sending logic
            x1, y1 = win32gui.ScreenToClient(self.hwnd, (x, y))

            if button.lower() == "left":
                win32api.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, win32api.MAKELONG(x1, y1))
                win32api.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, win32api.MAKELONG(x1, y1))
            elif button.lower() == "right":
                win32api.SendMessage(self.hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, win32api.MAKELONG(x1, y1))
                win32api.SendMessage(self.hwnd, win32con.WM_RBUTTONUP, 0, win32api.MAKELONG(x1, y1))
            elif button.lower() == "mid":
                win32api.SendMessage(self.hwnd, win32con.WM_MBUTTONDOWN, win32con.MK_MBUTTON, win32api.MAKELONG(x1, y1))
                win32api.SendMessage(self.hwnd, win32con.WM_MBUTTONUP, 0, win32api.MAKELONG(x1, y1))
            else:
                raise ValueError("Invalid button")
        
    def hover(self, x: int, y: int):
        """
        Move the mouse to the specified client coordinates.
        """
        x, y = win32gui.ScreenToClient(self.hwnd, (x, y))
        # win32api.SendMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, win32api.MAKELONG(x, y))
        ctypes.windll.user32.PostMessageW(self.hwnd, win32con.WM_MOUSEMOVE, 0, win32api.MAKELONG(x, y))

    def double_click(self, x: int, y: int, activate: bool = False, move: bool = False):
        """
        Double click at the specified client coordinates, with an option to move the mouse first.
        
        Args:
            x: The x-coordinate.
            y: The y-coordinate.
            activate: Whether to activate the window before clicking.
            move: Whether to move the mouse to the position before double-clicking.
        """
        if activate:
            self.activate()

        if move:
            self.activate()
            # Move the mouse to (x, y)
            win32api.SetCursorPos((x, y))

            # Simulate a double-click using mouse_event
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y)
        else:
            # If move is False, proceed with the original message sending logic
            x1, y1 = win32gui.ScreenToClient(self.hwnd, (x, y))
            win32api.SendMessage(self.hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, win32api.MAKELONG(x1, y1))


    def hover_by_bbox(self, bbox, pos: Literal["center", "top", "bottom", "right", "left"] = "center", xbias: int = 0, ybias: int = 0):
        """
        Move the mouse to the specified position relative to the bounding box.

        Args:
            bbox: The bounding box (left, top, right, bottom).
            pos: The position to move to. Default is "center".
            xbias: The x-coordinate bias. Default is 0.
            ybias: The y-coordinate bias. Default is 0.
        """
        # Support for uiautomation package Rect object
        if type(bbox).__name__ == "Rect":
            bbox = (bbox.left, bbox.top, bbox.right, bbox.bottom)

        left, top, right, bottom = bbox
        if pos.lower() == "center":
            x = (left + right) // 2
            y = (top + bottom) // 2
        elif pos.lower() == "top":
            x = (left + right) // 2
            y = top
        elif pos.lower() == "bottom":
            x = (left + right) // 2
            y = bottom
        elif pos.lower() == "right":
            x = right
            y = (top + bottom) // 2
        elif pos.lower() == "left":
            x = left
            y = (top + bottom) // 2
        elif pos.lower() == "lefttop":
            x = left
            y = top
        elif pos.lower() == "leftbottom":
            x = left
            y = bottom
        elif pos.lower() == "righttop":
            x = right
            y = top
        elif pos.lower() == "rightbottom":
            x = right
            y = bottom
        elif pos.lower() == "rightcenter":
            x = right
            y = (top + bottom) // 2
        elif pos.lower() == "leftcenter":
            x = left
            y = (top + bottom) // 2
        elif pos.lower() == "topcenter":
            x = (left + right) // 2
            y = top
        elif pos.lower() == "bottomcenter":
            x = (left + right) // 2
            y = bottom
        else:
            raise ValueError("Invalid position")
        if not xbias:
            xbias = 0
        if not ybias:
            ybias = 0
        x += xbias
        y += ybias
        self.hover(x, y)

    def click_by_bbox(
            self, 
            bbox, 
            pos: Literal["center", "top", "bottom", "right", "left"] = "center",
            button: Literal["left", "right", "mid"] = "left",
            double_click: bool = False,
            xbias: int = 0,
            ybias: int = 0,
            activate: bool = False,
            move: bool = False
        ):
        """
        Click at the specified position relative to the bounding box.

        Args:
            bbox: The bounding box (left, top, right, bottom).
            pos: The position to click. Default is "center".
            button: The button to click. Default is "left". When `double_click` is True, this argument is ignored.
            double_click: Whether to double click. Default is False.
            xbias: The x-coordinate bias. Default is 0.
            ybias: The y-coordinate bias. Default is 0.
        """
        # Support for uiautomation package Rect object
        if type(bbox).__name__ == "Rect":
            bbox = (bbox.left, bbox.top, bbox.right, bbox.bottom)
        
        # Calculate the click position
        left, top, right, bottom = bbox
        if pos.lower() == "center":
            x = (left + right) // 2
            y = (top + bottom) // 2
        elif pos.lower() == "top":
            x = (left + right) // 2
            y = top
        elif pos.lower() == "bottom":
            x = (left + right) // 2
            y = bottom
        elif pos.lower() == "right":
            x = right
            y = (top + bottom) // 2
        elif pos.lower() == "left":
            x = left
            y = (top + bottom) // 2
        elif pos.lower() == "lefttop":
            x = left
            y = top
        elif pos.lower() == "leftbottom":
            x = left
            y = bottom
        elif pos.lower() == "righttop":
            x = right
            y = top
        elif pos.lower() == "rightbottom":
            x = right
            y = bottom
        else:
            raise ValueError("Invalid position")
        if not xbias:
            xbias = 0
        if not ybias:
            ybias = 0
        x += xbias
        y += ybias
        if double_click:
            self.double_click(x, y, activate, move=move)
        else:
            self.click(x, y, button, activate, move=move)

    def scroll_wheel(self, bbox, delta=120):
        """
        Scroll the mouse wheel at the specified client coordinates.

        Args:
            client_x: The x-coordinate.
            client_y: The y-coordinate.
            delta: The amount to scroll. Default is 120. Positive values scroll up, negative values scroll down.
        """
        if type(bbox).__name__ == "Rect":
            bbox = (bbox.left, bbox.top, bbox.right, bbox.bottom)
        x = (bbox[0] + bbox[2]) // 2
        y = (bbox[1] + bbox[3]) // 2
        wParam = win32api.MAKELONG(0, delta)
        lParam = win32api.MAKELONG(x, y)
        win32api.SendMessage(self.hwnd, win32con.WM_MOUSEWHEEL, wParam, lParam)

    # def input(self, content: str, delay: float = -1):
    #     """
    #     Input text.
        
    #     Args:
    #         content: The text to input.
    #         delay: The delay between each character. Default is random between 0.01 and 0.05
    #     """
    #     for char in content:
    #         if char == '\n':
    #             self.send_keys_shortcut('{SHIFT}{ENTER}')
    #         win32api.SendMessage(self.hwnd, win32con.WM_CHAR, ord(char), 0)
    #         if delay < 0:
    #             time.sleep(random.uniform(0.01, 0.05))
    #         else:
    #             time.sleep(delay)

    def input(self, content: str, delay: float = -1):
        """
        Input text.
        
        Args:
            content: The text to input.
            delay: The delay between each character. Default is random between 0.01 and 0.05
        """
        for char in content:
            try:
                if char == '\n':
                #     win32api.PostMessage(self.hwnd, win32con.WM_CHAR, 0x0A, 0)
                #     win32api.PostMessage(self.hwnd, win32con.WM_CHAR, 0x0D, 0)
                    # self.send_keys_shortcut('{SHIFT}{ENTER}')
                    SetClipboardText('\n')
                    self.shortcut_paste()
                    continue
                
                # 判断是否是基本多语言平面字符
                if ord(char) <= 0xFFFF:
                    # 普通字符直接发送
                    win32api.SendMessage(self.hwnd, win32con.WM_CHAR, ord(char), 0)
                else:
                    # 处理超出基本多语言平面的字符 (例如 emoji)
                    utf16 = char.encode("utf-16-le")  # 转为 UTF-16
                    high_surrogate = int.from_bytes(utf16[:2], "little")  # 高代理
                    low_surrogate = int.from_bytes(utf16[2:], "little")  # 低代理
                    
                    # 分别发送高代理和低代理
                    win32api.SendMessage(self.hwnd, win32con.WM_CHAR, high_surrogate, 0)
                    win32api.SendMessage(self.hwnd, win32con.WM_CHAR, low_surrogate, 0)
            
            except Exception as e:
                print(f"Error processing character '{char}': {e}")

            if delay <= 0:
                time.sleep(random.uniform(0.01, 0.05))
            else:
                time.sleep(delay)

    def send_keys_shortcut(self, keys: str):
        """
        Send a key combination.

        Args:
            keys: The key combination. str

        Example:
            send_keys_shortcut('{LCTRL}{V}')  # Paste
        """
        keys = re.findall(r'\{(.*?)\}', keys)
        hold_keys = []
        for key in keys:
            _key = SpecialKeyNames.get(key.upper(), CharacterCodes.get(key, None))
            if key.upper() in GlobalKeyNames:
                win32api.keybd_event(_key, 0, 0, 0)
            elif _key is not None:
                win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, _key, 0)
                time.sleep(0.05)
            else:
                continue
            hold_keys.append(_key)

        for _key in hold_keys[::-1]:
            win32api.keybd_event(_key, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

    def shortcut_paste(self):
        """
        Paste the clipboard content.
        """
        win32api.keybd_event(win32con.VK_CONTROL, 0,0,0)
        time.sleep(0.1)
        win32gui.SendMessage(self.hwnd, win32con.WM_KEYDOWN, 86, 0)
        win32api.keybd_event(86, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

    def shortcut_copy(self):
        """
        Copy the selected content.
        """
        win32api.keybd_event(win32con.VK_CONTROL, 0,0,0)
        time.sleep(0.1)
        win32gui.SendMessage(self.hwnd, win32con.WM_KEYDOWN, 67, 0)
        win32api.keybd_event(67, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

    def shortcut_search(self):
        """
        Open the search dialog.
        """
        win32api.keybd_event(win32con.VK_CONTROL, 0,0,0)
        time.sleep(0.1)
        win32gui.SendMessage(self.hwnd, win32con.WM_KEYDOWN, 70, 0)
        win32api.keybd_event(70, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

    def shortcut_select_all(self):
        """
        Select all text.
        """
        win32api.keybd_event(win32con.VK_CONTROL, 0,0,0)
        time.sleep(0.1)
        win32gui.SendMessage(self.hwnd, win32con.WM_KEYDOWN, 65, 0)
        win32api.keybd_event(65, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

    def capture(self, bbox):
        # 获取窗口的屏幕坐标
        window_rect = win32gui.GetWindowRect(self.hwnd)
        win_left, win_top, win_right, win_bottom = window_rect
        win_width = win_right - win_left
        win_height = win_bottom - win_top

        # 获取窗口的设备上下文
        hwndDC = win32gui.GetWindowDC(self.hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # 创建位图对象保存整个窗口截图
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, win_width, win_height)
        saveDC.SelectObject(saveBitMap)

        # 使用PrintWindow捕获整个窗口（包括被遮挡或最小化的窗口）
        result = ctypes.windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 3)

        # 转换为PIL图像
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)

        # 释放资源
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwndDC)

        # 计算bbox相对于窗口左上角的坐标
        bbox_left, bbox_top, bbox_right, bbox_bottom = bbox
        # 转换为截图图像中的相对坐标
        crop_left = bbox_left - win_left
        crop_top = bbox_top - win_top
        crop_right = bbox_right - win_left
        crop_bottom = bbox_bottom - win_top

        # 裁剪目标区域
        cropped_im = im.crop((crop_left, crop_top, crop_right, crop_bottom))
        
        return cropped_im
    
def RollIntoView(win, ele, equal=True, bias=0):
    """
    将目标元素滚动到主窗口内可见区域
    
    参数:
        win: 主窗口元素 (uiautomation.Control对象)
        ele: 目标元素 (uiautomation.Control对象)  
        bias: 偏移量，元素边缘需要超过这个量才算完全在窗口内 (默认为0)
    """
    # 获取窗口和元素的边界矩形
    win_rect = win.BoundingRectangle
    ele_rect = ele.BoundingRectangle
    
    # 计算窗口的有效显示区域（考虑bias偏移）
    win_top = win_rect.top + bias
    win_bottom = win_rect.bottom - bias
    win_height = win_bottom - win_top
    
    # 获取元素的位置信息
    ele_top = ele_rect.top
    ele_bottom = ele_rect.bottom
    ele_height = ele_rect.height()
    ele_ycenter = ele_rect.ycenter()
    
    # 如果元素高度超过窗口高度，只需要确保元素中心在窗口内
    if ele_height > win_height:
        # 元素太高，只需要中心点在窗口内即可
        target_top = ele_ycenter
        target_bottom = ele_ycenter
    else:
        # 元素高度适中，需要整个元素都在窗口内
        target_top = ele_top
        target_bottom = ele_bottom
    
    # 执行滚动操作
    max_attempts = 100  # 防止无限循环
    attempt = 0
    
    while attempt < max_attempts:
        # 重新获取当前位置（滚动后位置会变化）
        current_ele_rect = ele.BoundingRectangle
        
        if ele_height > win_height:
            # 元素太高的情况，检查中心点
            current_ycenter = current_ele_rect.ycenter()
            if win_top <= current_ycenter <= win_bottom:
                break  # 中心点已在窗口内，停止滚动
                
            if current_ycenter < win_top:
                # 中心点在窗口上方，需要向下滚动
                # print('下滚动')
                win.WheelUp()
                time.sleep(0.1)
            elif current_ycenter > win_bottom:
                # 中心点在窗口下方，需要向上滚动  
                # print('上滚动')
                win.WheelDown()
                time.sleep(0.1)
        else:
            # 元素高度适中的情况，检查整个元素
            current_top = current_ele_rect.top
            current_bottom = current_ele_rect.bottom
            
            # 检查是否已经完全在窗口内
            if win_top <= current_top and current_bottom <= win_bottom:
                break  # 元素已完全在窗口内，停止滚动
            
            if current_top < win_top:
                # 元素顶部在窗口上方，需要向下滚动
                # print('下滚动')
                win.WheelUp()
                time.sleep(0.1)
            elif current_bottom > win_bottom:
                # 元素底部在窗口下方，需要向上滚动
                # print('上滚动')
                win.WheelDown()
                time.sleep(0.1)
            else:
                # 理论上不应该到达这里
                break
        
        attempt += 1
    
    if attempt >= max_attempts:
        print(f"Warning: 滚动操作达到最大尝试次数({max_attempts})，可能元素无法完全滚动到视图内")

# def RollIntoView(win, ele, equal=False, bias=0):
#     while ele.BoundingRectangle.ycenter() < win.BoundingRectangle.top + bias or ele.BoundingRectangle.ycenter() >= win.BoundingRectangle.bottom - bias:
#         if ele.BoundingRectangle.ycenter() < win.BoundingRectangle.top + bias:
#             # 上滚动
#             while True:
#                 if not ele.Exists(0):
#                     return 'not exist'
#                 win.WheelUp(wheelTimes=1)
#                 time.sleep(0.1)
#                 if equal:
#                     if ele.BoundingRectangle.ycenter() >= win.BoundingRectangle.top + bias:
#                         break
#                 else:
#                     if ele.BoundingRectangle.ycenter() > win.BoundingRectangle.top + bias:
#                         break

#         elif ele.BoundingRectangle.ycenter() >= win.BoundingRectangle.bottom - bias:
#             # 下滚动
#             while True:
#                 if not ele.Exists(0):
#                     return 'not exist'
#                 win.WheelDown(wheelTimes=1)
#                 time.sleep(0.1)
#                 if equal:
#                     if ele.BoundingRectangle.ycenter() <= win.BoundingRectangle.bottom - bias:
#                         break
#                 else:
#                     if ele.BoundingRectangle.ycenter() < win.BoundingRectangle.bottom - bias:
#                         break
#         time.sleep(0.3)

def CheckElementPosition(win, ele, bias=0):
    """
    判断目标元素相对于主窗口的位置关系
    
    参数:
        win: 主窗口元素 (uiautomation.Control对象)
        ele: 目标元素 (uiautomation.Control对象)
        bias: 偏移量，调整判断的边界 (默认为0)
    
    返回:
        dict: 包含各种位置关系判断结果的字典
    """
    # 获取窗口和元素的边界矩形
    win_rect = win.BoundingRectangle
    ele_rect = ele.BoundingRectangle
    
    # 计算实际的判断边界（考虑bias）
    win_top = win_rect.top + bias
    win_bottom = win_rect.bottom - bias
    win_left = win_rect.left + bias
    win_right = win_rect.right - bias
    
    # 元素的边界
    ele_top = ele_rect.top
    ele_bottom = ele_rect.bottom
    ele_left = ele_rect.left
    ele_right = ele_rect.right
    
    # 各种位置关系判断
    result = {
        # 垂直方向的关系
        'ele_top_above_win_top': ele_top < win_top,                    # ele顶部高于win顶部
        'ele_bottom_below_win_bottom': ele_bottom > win_bottom,        # ele底部低于win底部
        'ele_completely_above_win': ele_bottom <= win_top,             # ele完全在win上方
        'ele_completely_below_win': ele_top >= win_bottom,             # ele完全在win下方
        'ele_vertically_inside_win': win_top <= ele_top and ele_bottom <= win_bottom,  # ele垂直方向完全在win内
        'win_vertically_inside_ele': ele_top <= win_top and win_bottom <= ele_bottom,  # win垂直方向完全在ele内
        
        # 水平方向的关系
        'ele_left_before_win_left': ele_left < win_left,              # ele左边在win左边之前
        'ele_right_after_win_right': ele_right > win_right,           # ele右边在win右边之后
        'ele_completely_left_of_win': ele_right <= win_left,          # ele完全在win左侧
        'ele_completely_right_of_win': ele_left >= win_right,         # ele完全在win右侧
        'ele_horizontally_inside_win': win_left <= ele_left and ele_right <= win_right,  # ele水平方向完全在win内
        'win_horizontally_inside_ele': ele_left <= win_left and win_right <= ele_right,  # win水平方向完全在ele内
        
        # 综合关系
        'ele_completely_inside_win': False,                           # ele完全在win内部
        'win_completely_inside_ele': False,                           # win完全在ele内部
        'ele_and_win_overlap': False,                                 # ele和win有重叠
        'ele_and_win_separate': False,                                # ele和win完全分离
    }
    
    # 计算综合关系
    result['ele_completely_inside_win'] = (result['ele_vertically_inside_win'] and 
                                          result['ele_horizontally_inside_win'])
    
    result['win_completely_inside_ele'] = (result['win_vertically_inside_ele'] and 
                                          result['win_horizontally_inside_ele'])
    
    # 判断是否有重叠（在两个方向上都有重叠）
    vertical_overlap = not (result['ele_completely_above_win'] or result['ele_completely_below_win'])
    horizontal_overlap = not (result['ele_completely_left_of_win'] or result['ele_completely_right_of_win'])
    result['ele_and_win_overlap'] = vertical_overlap and horizontal_overlap
    
    # 判断是否完全分离
    result['ele_and_win_separate'] = not result['ele_and_win_overlap']
    
    return result


def IsElementInWindow(win, ele, bias=0):
    """
    简化版本：判断元素是否在窗口内（仅垂直方向）
    
    参数:
        win: 主窗口元素 (uiautomation.Control对象)
        ele: 目标元素 (uiautomation.Control对象)
        bias: 偏移量 (默认为0)
    
    返回:
        bool: True表示元素在窗口内，False表示不在
    """
    position_info = CheckElementPosition(win, ele, bias)
    return position_info['ele_vertically_inside_win']


def GetElementPositionDescription(win, ele, bias=0):
    """
    获取元素位置的文字描述
    
    参数:
        win: 主窗口元素 (uiautomation.Control对象)
        ele: 目标元素 (uiautomation.Control对象)
        bias: 偏移量 (默认为0)
    
    返回:
        str: 位置关系的文字描述
    """
    result = CheckElementPosition(win, ele, bias)
    
    if result['ele_completely_inside_win']:
        return "元素完全在窗口内部"
    elif result['win_completely_inside_ele']:
        return "窗口完全在元素内部"
    elif result['ele_completely_above_win']:
        return "元素完全在窗口上方"
    elif result['ele_completely_below_win']:
        return "元素完全在窗口下方"
    elif result['ele_completely_left_of_win']:
        return "元素完全在窗口左侧"
    elif result['ele_completely_right_of_win']:
        return "元素完全在窗口右侧"
    elif result['ele_and_win_overlap']:
        descriptions = []
        if result['ele_top_above_win_top']:
            descriptions.append("元素顶部高于窗口顶部")
        if result['ele_bottom_below_win_bottom']:
            descriptions.append("元素底部低于窗口底部")
        if result['ele_left_before_win_left']:
            descriptions.append("元素左边超出窗口左边")
        if result['ele_right_after_win_right']:
            descriptions.append("元素右边超出窗口右边")
        
        if descriptions:
            return "元素与窗口重叠，" + "，".join(descriptions)
        else:
            return "元素与窗口重叠"
    else:
        return "元素与窗口完全分离"
