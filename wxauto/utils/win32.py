import os
import time
import shutil
import win32ui
import win32gui
import win32api
import win32con
import win32process
import win32clipboard
import pyperclip
import psutil
import ctypes
from PIL import Image
from wxauto import uiautomation as uia

def GetAllWindows():
    """
    获取所有窗口的信息，返回一个列表，每个元素包含 (窗口句柄, 类名, 窗口标题)
    """
    windows = []
    
    def enum_windows_proc(hwnd, extra):
        class_name = win32gui.GetClassName(hwnd)  # 获取窗口类名
        window_title = win32gui.GetWindowText(hwnd)  # 获取窗口标题
        windows.append((hwnd, class_name, window_title))
    
    win32gui.EnumWindows(enum_windows_proc, None)
    return windows

def GetCursorWindow():
    x, y = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint((x, y))
    window_title = win32gui.GetWindowText(hwnd)
    class_name = win32gui.GetClassName(hwnd)
    return hwnd, window_title, class_name

def set_cursor_pos(x, y):
    win32api.SetCursorPos((x, y))
    
def Click(rect):
    x = (rect.left + rect.right) // 2
    y = (rect.top + rect.bottom) // 2
    set_cursor_pos(x, y)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    
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

def GetWindowRect(hwnd):
    return win32gui.GetWindowRect(hwnd)

def capture(hwnd, bbox):
    # 获取窗口的屏幕坐标
    window_rect = win32gui.GetWindowRect(hwnd)
    win_left, win_top, win_right, win_bottom = window_rect
    win_width = win_right - win_left
    win_height = win_bottom - win_top

    # 获取窗口的设备上下文
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    # 创建位图对象保存整个窗口截图
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, win_width, win_height)
    saveDC.SelectObject(saveBitMap)

    # 使用PrintWindow捕获整个窗口（包括被遮挡或最小化的窗口）
    result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

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
    win32gui.ReleaseDC(hwnd, hwndDC)

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

def FindWindow(classname=None, name=None, timeout=0) -> int:
    t0 = time.time()
    while True:
        HWND = win32gui.FindWindow(classname, name)
        if HWND:
            break
        if time.time() - t0 > timeout:
            break
        time.sleep(0.01)
    return HWND

def FindTopLevelControl(classname=None, name=None, timeout=3):
    hwnd = FindWindow(classname, name, timeout)
    if hwnd:
        return uia.ControlFromHandle(hwnd)
    else:
        return None

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

def ClipboardFormats(unit=0, *units):
    units = list(units)
    retry_count = 5
    while retry_count > 0:
        try:
            win32clipboard.OpenClipboard()
            try:
                u = win32clipboard.EnumClipboardFormats(unit)
            finally:
                win32clipboard.CloseClipboard()
            break
        except Exception as e:
            retry_count -= 1
    units.append(u)
    if u:
        units = ClipboardFormats(u, *units)
    return units

def ReadClipboardData():
    Dict = {}
    formats = ClipboardFormats()

    for i in formats:
        if i == 0:
            continue

        retry_count = 5
        while retry_count > 0:
            try:
                win32clipboard.OpenClipboard()
                try:
                    data = win32clipboard.GetClipboardData(i)
                    Dict[str(i)] = data
                finally:
                    win32clipboard.CloseClipboard()
                break
            except Exception as e:
                retry_count -= 1
    return Dict

def SetClipboardText(text: str):
    pyperclip.copy(text)


class DROPFILES(ctypes.Structure):
    _fields_ = [
    ("pFiles", ctypes.c_uint),
    ("x", ctypes.c_long),
    ("y", ctypes.c_long),
    ("fNC", ctypes.c_int),
    ("fWide", ctypes.c_bool),
    ]

pDropFiles = DROPFILES()
pDropFiles.pFiles = ctypes.sizeof(DROPFILES)
pDropFiles.fWide = True
matedata = bytes(pDropFiles)

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

def PasteFile(folder):
    folder = os.path.realpath(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)

    t0 = time.time()
    while True:
        if time.time() - t0 > 10:
            raise TimeoutError(f"读取剪贴板文件超时！")
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                files = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                for file in files:
                    filename = os.path.basename(file)
                    dest_file = os.path.join(folder, filename)
                    shutil.copy2(file, dest_file)
                    return True
            else:
                print("剪贴板中没有文件")
                return False
        except:
            pass
        finally:
            win32clipboard.CloseClipboard()

def IsRedPixel(uicontrol):
    rect = uicontrol.BoundingRectangle
    hwnd = uicontrol.GetAncestorControl(lambda x,y:x.ClassName=='WeChatMainWndForPC').NativeWindowHandle
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    img = capture(hwnd, bbox)
    return any(p[0] > p[1] and p[0] > p[2] for p in img.getdata())