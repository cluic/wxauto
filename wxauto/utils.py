from PIL import ImageGrab
import win32clipboard
import win32process
import win32gui
import win32api
import win32con
from ctypes import (
    Structure,
    c_uint,
    c_long,
    c_int,
    c_bool,
    sizeof
)
import psutil
import time
import os

def GetPathByHwnd(hwnd):
    try:
        thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(process_id)
        return process.exe()
    except Exception as e:
        print(f"Error: {e}")
        return None

def GetVersionByPath(file_path):
    try:
        info = win32api.GetFileVersionInfo(file_path, '\\')
        version = "{}.{}.{}.{}".format(win32api.HIWORD(info['FileVersionMS']),
                                        win32api.LOWORD(info['FileVersionMS']),
                                        win32api.HIWORD(info['FileVersionLS']),
                                        win32api.LOWORD(info['FileVersionLS']))
    except:
        version = None
    return version


def IsRedPixel(uicontrol):
    rect = uicontrol.BoundingRectangle
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    img = ImageGrab.grab(bbox=bbox)
    return any(p[0] > p[1] and p[0] > p[2] for p in img.getdata())

class DROPFILES(Structure):
    _fields_ = [
    ("pFiles", c_uint),
    ("x", c_long),
    ("y", c_long),
    ("fNC", c_int),
    ("fWide", c_bool),
    ]

pDropFiles = DROPFILES()
pDropFiles.pFiles = sizeof(DROPFILES)
pDropFiles.fWide = True
matedata = bytes(pDropFiles)

def SetClipboardText(text):
    t0 = time.time()
    while True:
        if time.time() - t0 > 10:
            raise TimeoutError(f"设置剪贴板超时！ --> {text}")
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            break
        except:
            pass
        finally:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

def SetClipboardFiles(paths):
    for file in paths:
        if not os.path.exists(file):
            raise FileNotFoundError(f"file ({file}) not exists!")
    files = ("\0".join(paths)).replace("/", "\\")
    data = files.encode("U16")[2:]+b"\0\0"
    t0 = time.time()
    while True:
        if time.time() - t0 > 10:
            raise TimeoutError(f"设置剪贴板文件超时！ --> {paths}")
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_HDROP, matedata+data)
            break
        except:
            pass
        finally:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
        
def GetText(HWND):
    length = win32gui.SendMessage(HWND, win32con.WM_GETTEXTLENGTH)*2
    buffer = win32gui.PyMakeBuffer(length)
    win32api.SendMessage(HWND, win32con.WM_GETTEXT, length, buffer)
    address, length_ = win32gui.PyGetBufferAddressAndLen(buffer[:-1])
    text = win32gui.PyGetString(address, length_)[:int(length/2)]
    buffer.release()
    return text

def GetAllWindowExs(HWND):
    if not HWND:
        return
    handles = []
    win32gui.EnumChildWindows(
        HWND, lambda hwnd, param: param.append([hwnd, win32gui.GetClassName(hwnd), GetText(hwnd)]),  handles)
    return handles

def FindWindow(classname=None, name=None) -> int:
    return win32gui.FindWindow(classname, name)

def FindWinEx(HWND, classname=None, name=None) -> list:
    hwnds_classname = []
    hwnds_name = []
    def find_classname(hwnd, classname):
        classname_ = win32gui.GetClassName(hwnd)
        if classname_ == classname:
            if hwnd not in hwnds_classname:
                hwnds_classname.append(hwnd)
    def find_name(hwnd, name):
        name_ = GetText(hwnd)
        if name in name_:
            if hwnd not in hwnds_name:
                hwnds_name.append(hwnd)
    if classname:
        win32gui.EnumChildWindows(HWND, find_classname, classname)
    if name:
        win32gui.EnumChildWindows(HWND, find_name, name)
    if classname and name:
        hwnds = [hwnd for hwnd in hwnds_classname if hwnd in hwnds_name]
    else:
        hwnds = hwnds_classname + hwnds_name
    return hwnds
