from pathlib import Path
from wxauto.uia import uiautomation as uia
from .win32 import FindWindow, GetAllWindows
from datetime import datetime, timedelta
from PIL import Image
import re

def get_file_dir(dir_path=None):
    if dir_path is None:
        dir_path = Path('.').absolute()
    elif isinstance(dir_path, str):
        dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def find_window_from_root(classname=None, name=None, timeout=0):
    hwnd = FindWindow(classname=classname, name=name, timeout=timeout)
    if hwnd:
        control = uia.ControlFromHandle(hwnd)
        return control
    return None

def find_all_windows_from_root(classname:str=None, name:str=None, pid:int=None):
    windows = GetAllWindows()
    targets = []
    for window in windows:
        if (
            (all((classname, name)) and classname == window[1] and name == window[2])
            or (all((classname, not name)) and classname == window[1])
            or (all((not classname, name)) and name == window[2])
        ):
            targets.append(uia.ControlFromHandle(window[0]))
    if pid:
        targets = [w for w in targets if w.ProcessId == pid]
    return targets

def now_time(fmt='%Y%m%d%H%M%S%f'):
    return datetime.now().strftime(fmt)
        
def parse_wechat_time(time_str):
    """
    时间格式转换函数

    Args:
        time_str: 输入的时间字符串

    Returns:
        转换后的时间字符串
    """
    time_str = time_str.replace('星期天', '星期日')
    match = re.match(r'^(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$', time_str)
    if match:
        month, day, hour, minute, second = match.groups()
        current_year = datetime.now().year
        return datetime(current_year, int(month), int(day), int(hour), int(minute), int(second)).strftime('%Y-%m-%d %H:%M:%S')
    
    match = re.match(r'^(\d{1,2}):(\d{1,2})$', time_str)
    if match:
        hour, minute = match.groups()
        return datetime.now().strftime('%Y-%m-%d') + f' {hour}:{minute}:00'

    match = re.match(r'^昨天 (\d{1,2}):(\d{1,2})$', time_str)
    if match:
        hour, minute = match.groups()
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime('%Y-%m-%d') + f' {hour}:{minute}:00'

    match = re.match(r'^星期([一二三四五六日]) (\d{1,2}):(\d{1,2})$', time_str)
    if match:
        weekday, hour, minute = match.groups()
        weekday_num = ['一', '二', '三', '四', '五', '六', '日'].index(weekday)
        today_weekday = datetime.now().weekday()
        delta_days = (today_weekday - weekday_num) % 7
        target_day = datetime.now() - timedelta(days=delta_days)
        return target_day.strftime('%Y-%m-%d') + f' {hour}:{minute}:00'

    match = re.match(r'^(\d{4})年(\d{1,2})月(\d{1,2})日 (\d{1,2}):(\d{1,2})$', time_str)
    if match:
        year, month, day, hour, minute = match.groups()
        return datetime(*[int(i) for i in [year, month, day, hour, minute]]).strftime('%Y-%m-%d %H:%M:%S')
    
    match = re.match(r'^(\d{2})-(\d{2}) (上午|下午) (\d{1,2}):(\d{2})$', time_str)
    if match:
        month, day, period, hour, minute = match.groups()
        current_year = datetime.now().year
        hour = int(hour)
        if period == '下午' and hour != 12:
            hour += 12
        elif period == '上午' and hour == 12:
            hour = 0
        return datetime(current_year, int(month), int(day), hour, int(minute)).strftime('%Y-%m-%d %H:%M:%S')
    
    return time_str


def is_valid_image(file_path):
    path = Path(file_path)
    
    if not path.exists() or not path.is_file():
        return False

    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception as e:
        return False