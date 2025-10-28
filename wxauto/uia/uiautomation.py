#!python3
# -*- coding: utf-8 -*-
# cython: language_level=3
"""
uiautomation for Python 3.
Author: yinkaisheng@live.com
Source: https://github.com/yinkaisheng/Python-UIAutomation-for-Windows

This module is for UIAutomation on Windows(Windows XP with SP3, Windows Vista and Windows 7/8/8.1/10).
It supports UIAutomation for the applications which implmented IUIAutomation, such as MFC, Windows Form, WPF, Modern UI(Metro UI), Qt, Firefox and Chrome.
Run 'automation.py -h' for help.

uiautomation is shared under the Apache Licene 2.0.
This means that the code can be freely copied and distributed, and costs nothing to use.
"""
import os
import sys
import time
import datetime
import re
import random
import threading
import ctypes
import _ctypes
import ctypes.wintypes
import comtypes #need pip install comtypes
import comtypes.client
import win32gui
import win32api
import win32con
import win32ui
import pyperclip
from PIL import ImageGrab
from typing import (Any, Callable, Dict, List, Iterable, Tuple)  # need pip install typing for Python3.4 or lower
from .uiplug import *
from hashlib import md5

comtypes.CoInitialize()
TreeNode = Any

# print('uia done')
AUTHOR_MAIL = 'yinkaisheng@live.com'
METRO_WINDOW_CLASS_NAME = 'Windows.UI.Core.CoreWindow'  # for Windows 8 and 8.1
SEARCH_INTERVAL = 0.01  # search control interval seconds
MAX_MOVE_SECOND = 1  # simulate mouse move or drag max seconds
TIME_OUT_SECOND = 10
OPERATION_WAIT_TIME = 0.5
MAX_PATH = 260
DEBUG_SEARCH_TIME = False
DEBUG_EXIST_DISAPPEAR = False
S_OK = 0

IsNT6orHigher = os.sys.getwindowsversion().major >= 6
ProcessTime = time.perf_counter  #this returns nearly 0 when first call it if python version <= 3.6
ProcessTime()  # need to call it once if python version <= 3.6

try:
    from anytree import Node, RenderTree

    def PrintAllControlTree(ele, max=9999999):
        def findall(ele, n=0, node=None):
            if n >= max:
                return node
            nn = '\n'
            nodename = f"[{ele.ControlTypeName} {n}](\"{ele.ClassName}\", \"{ele.Name.replace(nn, '')}\", \"{ele.AutomationId}\", \"{''.join([str(i) for i in ele.GetRuntimeId()])}\")"
            if not node:
                node1 = Node(nodename)
            else:
                node1 = Node(nodename, parent=node)
            eles = ele.GetChildren()
            for ele1 in eles:
                findall(ele1, n+1, node1)
            return node1
        tree = RenderTree(findall(ele))
        tree_text = ''
        for pre, fill, node in tree:
            tree_text += f"{pre}{node.name}\n"
        return tree_text
except:
    pass

import tempfile
import os

def create_temp_png_path(prefix='image_', suffix='.png'):
    """
    创建一个临时 PNG 图片路径（不创建文件），你可以将图片保存到这个路径。

    Args:
        prefix (str): 文件名前缀，默认是'image_'
        suffix (str): 文件扩展名，默认是'.png'

    Returns:
        str: 临时 PNG 图片路径
    """
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(fd)  # 关闭文件描述符，不保留文件
    os.remove(path)  # 删除实际文件，只保留路径
    return path

class _AutomationClient:
    _instance = None

    @classmethod
    def instance(cls) -> '_AutomationClient':
        """Singleton instance (this prevents com creation on import)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        tryCount = 3
        for retry in range(tryCount):
            try:
                self.UIAutomationCore = comtypes.client.GetModule("UIAutomationCore.dll")
                self.IUIAutomation = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=self.UIAutomationCore.IUIAutomation)
                self.ViewWalker = self.IUIAutomation.RawViewWalker
                break
            except Exception as ex:
                if retry + 1 == tryCount:
                    Logger.WriteLine('Can not load UIAutomationCore.dll.\nYou may need to install Windows Update KB971513.\nhttps://github.com/yinkaisheng/WindowsUpdateKB971513ForIUIAutomation', ConsoleColor.Yellow)
                    raise ex
        #Windows dll
        ctypes.windll.user32.GetClipboardData.restype = ctypes.c_void_p
        ctypes.windll.user32.GetWindowDC.restype = ctypes.c_void_p
        ctypes.windll.user32.OpenDesktopW.restype = ctypes.c_void_p
        ctypes.windll.user32.WindowFromPoint.restype = ctypes.c_void_p
        ctypes.windll.user32.SendMessageW.restype = ctypes.wintypes.LONG
        ctypes.windll.user32.GetForegroundWindow.restype = ctypes.c_void_p
        ctypes.windll.user32.GetWindowLongW.restype = ctypes.wintypes.LONG
        ctypes.windll.kernel32.GlobalLock.restype = ctypes.c_void_p
        ctypes.windll.kernel32.GlobalAlloc.restype = ctypes.c_void_p
        ctypes.windll.kernel32.GetStdHandle.restype = ctypes.c_void_p
        ctypes.windll.kernel32.OpenProcess.restype = ctypes.c_void_p
        ctypes.windll.kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p

        SetDpiAwareness(dpiAwarenessPerMonitor=True)


class _DllClient:
    _instance = None

    @classmethod
    def instance(cls) -> '_DllClient':
        """Singleton instance (this prevents com creation on import)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        binPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
        os.environ["PATH"] = binPath + os.pathsep + os.environ["PATH"]
        load = False
        if sys.version >= '3.8':
            os.add_dll_directory(binPath)
        if sys.maxsize > 0xFFFFFFFF:
            try:
                self.dll = ctypes.cdll.UIAutomationClient_VC140_X64
                load = True
            except Exception as ex:
                print(ex)
        else:
            try:
                self.dll = ctypes.cdll.UIAutomationClient_VC140_X86
                load = True
            except Exception as ex:
                print(ex)
        if load:
            self.dll.BitmapCreate.restype = ctypes.c_size_t
            self.dll.BitmapFromWindow.argtypes = (ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
            self.dll.BitmapFromWindow.restype = ctypes.c_size_t
            self.dll.BitmapFromFile.argtypes = (ctypes.c_wchar_p, )
            self.dll.BitmapFromFile.restype = ctypes.c_size_t
            self.dll.BitmapToFile.argtypes = (ctypes.c_size_t, ctypes.c_wchar_p, ctypes.c_wchar_p)
            self.dll.BitmapRelease.argtypes = (ctypes.c_size_t, )
            self.dll.BitmapGetWidthAndHeight.argtypes = (ctypes.c_size_t, )
            self.dll.BitmapGetPixel.argtypes = (ctypes.c_size_t, ctypes.c_int, ctypes.c_int)
            self.dll.BitmapSetPixel.argtypes = (ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_uint)

            self.dll.Initialize()
        else:
            self.dll = None
            Logger.WriteLine('Can not load dll.\nFunctionalities related to Bitmap are not available.\nYou may need to install Microsoft Visual C++ 2015 Redistributable Package.', ConsoleColor.Yellow)
    def __del__(self):
        if self.dll:
            self.dll.Uninitialize()


class ControlType:
    """
    ControlType from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/WinAuto/uiauto-controltype-ids
    """
    AppBarControl = 50040
    ButtonControl = 50000
    CalendarControl = 50001
    CheckBoxControl = 50002
    ComboBoxControl = 50003
    CustomControl = 50025
    DataGridControl = 50028
    DataItemControl = 50029
    DocumentControl = 50030
    EditControl = 50004
    GroupControl = 50026
    HeaderControl = 50034
    HeaderItemControl = 50035
    HyperlinkControl = 50005
    ImageControl = 50006
    ListControl = 50008
    ListItemControl = 50007
    MenuBarControl = 50010
    MenuControl = 50009
    MenuItemControl = 50011
    PaneControl = 50033
    ProgressBarControl = 50012
    RadioButtonControl = 50013
    ScrollBarControl = 50014
    SemanticZoomControl = 50039
    SeparatorControl = 50038
    SliderControl = 50015
    SpinnerControl = 50016
    SplitButtonControl = 50031
    StatusBarControl = 50017
    TabControl = 50018
    TabItemControl = 50019
    TableControl = 50036
    TextControl = 50020
    ThumbControl = 50027
    TitleBarControl = 50037
    ToolBarControl = 50021
    ToolTipControl = 50022
    TreeControl = 50023
    TreeItemControl = 50024
    WindowControl = 50032


ControlTypeNames = {
    ControlType.AppBarControl: 'AppBarControl',
    ControlType.ButtonControl: 'ButtonControl',
    ControlType.CalendarControl: 'CalendarControl',
    ControlType.CheckBoxControl: 'CheckBoxControl',
    ControlType.ComboBoxControl: 'ComboBoxControl',
    ControlType.CustomControl: 'CustomControl',
    ControlType.DataGridControl: 'DataGridControl',
    ControlType.DataItemControl: 'DataItemControl',
    ControlType.DocumentControl: 'DocumentControl',
    ControlType.EditControl: 'EditControl',
    ControlType.GroupControl: 'GroupControl',
    ControlType.HeaderControl: 'HeaderControl',
    ControlType.HeaderItemControl: 'HeaderItemControl',
    ControlType.HyperlinkControl: 'HyperlinkControl',
    ControlType.ImageControl: 'ImageControl',
    ControlType.ListControl: 'ListControl',
    ControlType.ListItemControl: 'ListItemControl',
    ControlType.MenuBarControl: 'MenuBarControl',
    ControlType.MenuControl: 'MenuControl',
    ControlType.MenuItemControl: 'MenuItemControl',
    ControlType.PaneControl: 'PaneControl',
    ControlType.ProgressBarControl: 'ProgressBarControl',
    ControlType.RadioButtonControl: 'RadioButtonControl',
    ControlType.ScrollBarControl: 'ScrollBarControl',
    ControlType.SemanticZoomControl: 'SemanticZoomControl',
    ControlType.SeparatorControl: 'SeparatorControl',
    ControlType.SliderControl: 'SliderControl',
    ControlType.SpinnerControl: 'SpinnerControl',
    ControlType.SplitButtonControl: 'SplitButtonControl',
    ControlType.StatusBarControl: 'StatusBarControl',
    ControlType.TabControl: 'TabControl',
    ControlType.TabItemControl: 'TabItemControl',
    ControlType.TableControl: 'TableControl',
    ControlType.TextControl: 'TextControl',
    ControlType.ThumbControl: 'ThumbControl',
    ControlType.TitleBarControl: 'TitleBarControl',
    ControlType.ToolBarControl: 'ToolBarControl',
    ControlType.ToolTipControl: 'ToolTipControl',
    ControlType.TreeControl: 'TreeControl',
    ControlType.TreeItemControl: 'TreeItemControl',
    ControlType.WindowControl: 'WindowControl',
}


class PatternId:
    """
    PatternId from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/WinAuto/uiauto-controlpattern-ids
    """
    AnnotationPattern = 10023
    CustomNavigationPattern = 10033
    DockPattern = 10011
    DragPattern = 10030
    DropTargetPattern = 10031
    ExpandCollapsePattern = 10005
    GridItemPattern = 10007
    GridPattern = 10006
    InvokePattern = 10000
    ItemContainerPattern = 10019
    LegacyIAccessiblePattern = 10018
    MultipleViewPattern = 10008
    ObjectModelPattern = 10022
    RangeValuePattern = 10003
    ScrollItemPattern = 10017
    ScrollPattern = 10004
    SelectionItemPattern = 10010
    SelectionPattern = 10001
    SpreadsheetItemPattern = 10027
    SpreadsheetPattern = 10026
    StylesPattern = 10025
    SynchronizedInputPattern = 10021
    TableItemPattern = 10013
    TablePattern = 10012
    TextChildPattern = 10029
    TextEditPattern = 10032
    TextPattern = 10014
    TextPattern2 = 10024
    TogglePattern = 10015
    TransformPattern = 10016
    TransformPattern2 = 10028
    ValuePattern = 10002
    VirtualizedItemPattern = 10020
    WindowPattern = 10009


PatternIdNames = {
    PatternId.AnnotationPattern: 'AnnotationPattern',
    PatternId.CustomNavigationPattern: 'CustomNavigationPattern',
    PatternId.DockPattern: 'DockPattern',
    PatternId.DragPattern: 'DragPattern',
    PatternId.DropTargetPattern: 'DropTargetPattern',
    PatternId.ExpandCollapsePattern: 'ExpandCollapsePattern',
    PatternId.GridItemPattern: 'GridItemPattern',
    PatternId.GridPattern: 'GridPattern',
    PatternId.InvokePattern: 'InvokePattern',
    PatternId.ItemContainerPattern: 'ItemContainerPattern',
    PatternId.LegacyIAccessiblePattern: 'LegacyIAccessiblePattern',
    PatternId.MultipleViewPattern: 'MultipleViewPattern',
    PatternId.ObjectModelPattern: 'ObjectModelPattern',
    PatternId.RangeValuePattern: 'RangeValuePattern',
    PatternId.ScrollItemPattern: 'ScrollItemPattern',
    PatternId.ScrollPattern: 'ScrollPattern',
    PatternId.SelectionItemPattern: 'SelectionItemPattern',
    PatternId.SelectionPattern: 'SelectionPattern',
    PatternId.SpreadsheetItemPattern: 'SpreadsheetItemPattern',
    PatternId.SpreadsheetPattern: 'SpreadsheetPattern',
    PatternId.StylesPattern: 'StylesPattern',
    PatternId.SynchronizedInputPattern: 'SynchronizedInputPattern',
    PatternId.TableItemPattern: 'TableItemPattern',
    PatternId.TablePattern: 'TablePattern',
    PatternId.TextChildPattern: 'TextChildPattern',
    PatternId.TextEditPattern: 'TextEditPattern',
    PatternId.TextPattern: 'TextPattern',
    PatternId.TextPattern2: 'TextPattern2',
    PatternId.TogglePattern: 'TogglePattern',
    PatternId.TransformPattern: 'TransformPattern',
    PatternId.TransformPattern2: 'TransformPattern2',
    PatternId.ValuePattern: 'ValuePattern',
    PatternId.VirtualizedItemPattern: 'VirtualizedItemPattern',
    PatternId.WindowPattern: 'WindowPattern',
}

class TreeScope:
    Element = 1
    Children = 2
    Parent = 4
    Descendants = 8
    Subtree = 7
    Ancestors = 16
    All = 31

class PropertyId:
    """
    PropertyId from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/WinAuto/uiauto-automation-element-propids
    Refer https://docs.microsoft.com/en-us/windows/desktop/WinAuto/uiauto-control-pattern-propids
    """
    AcceleratorKeyProperty = 30006
    AccessKeyProperty = 30007
    AnnotationAnnotationTypeIdProperty = 30113
    AnnotationAnnotationTypeNameProperty = 30114
    AnnotationAuthorProperty = 30115
    AnnotationDateTimeProperty = 30116
    AnnotationObjectsProperty = 30156
    AnnotationTargetProperty = 30117
    AnnotationTypesProperty = 30155
    AriaPropertiesProperty = 30102
    AriaRoleProperty = 30101
    AutomationIdProperty = 30011
    BoundingRectangleProperty = 30001
    CenterPointProperty = 30165
    ClassNameProperty = 30012
    ClickablePointProperty = 30014
    ControlTypeProperty = 30003
    ControllerForProperty = 30104
    CultureProperty = 30015
    DescribedByProperty = 30105
    DockDockPositionProperty = 30069
    DragDropEffectProperty = 30139
    DragDropEffectsProperty = 30140
    DragGrabbedItemsProperty = 30144
    DragIsGrabbedProperty = 30138
    DropTargetDropTargetEffectProperty = 30142
    DropTargetDropTargetEffectsProperty = 30143
    ExpandCollapseExpandCollapseStateProperty = 30070
    FillColorProperty = 30160
    FillTypeProperty = 30162
    FlowsFromProperty = 30148
    FlowsToProperty = 30106
    FrameworkIdProperty = 30024
    FullDescriptionProperty = 30159
    GridColumnCountProperty = 30063
    GridItemColumnProperty = 30065
    GridItemColumnSpanProperty = 30067
    GridItemContainingGridProperty = 30068
    GridItemRowProperty = 30064
    GridItemRowSpanProperty = 30066
    GridRowCountProperty = 30062
    HasKeyboardFocusProperty = 30008
    HelpTextProperty = 30013
    IsAnnotationPatternAvailableProperty = 30118
    IsContentElementProperty = 30017
    IsControlElementProperty = 30016
    IsCustomNavigationPatternAvailableProperty = 30151
    IsDataValidForFormProperty = 30103
    IsDockPatternAvailableProperty = 30027
    IsDragPatternAvailableProperty = 30137
    IsDropTargetPatternAvailableProperty = 30141
    IsEnabledProperty = 30010
    IsExpandCollapsePatternAvailableProperty = 30028
    IsGridItemPatternAvailableProperty = 30029
    IsGridPatternAvailableProperty = 30030
    IsInvokePatternAvailableProperty = 30031
    IsItemContainerPatternAvailableProperty = 30108
    IsKeyboardFocusableProperty = 30009
    IsLegacyIAccessiblePatternAvailableProperty = 30090
    IsMultipleViewPatternAvailableProperty = 30032
    IsObjectModelPatternAvailableProperty = 30112
    IsOffscreenProperty = 30022
    IsPasswordProperty = 30019
    IsPeripheralProperty = 30150
    IsRangeValuePatternAvailableProperty = 30033
    IsRequiredForFormProperty = 30025
    IsScrollItemPatternAvailableProperty = 30035
    IsScrollPatternAvailableProperty = 30034
    IsSelectionItemPatternAvailableProperty = 30036
    IsSelectionPattern2AvailableProperty = 30168
    IsSelectionPatternAvailableProperty = 30037
    IsSpreadsheetItemPatternAvailableProperty = 30132
    IsSpreadsheetPatternAvailableProperty = 30128
    IsStylesPatternAvailableProperty = 30127
    IsSynchronizedInputPatternAvailableProperty = 30110
    IsTableItemPatternAvailableProperty = 30039
    IsTablePatternAvailableProperty = 30038
    IsTextChildPatternAvailableProperty = 30136
    IsTextEditPatternAvailableProperty = 30149
    IsTextPattern2AvailableProperty = 30119
    IsTextPatternAvailableProperty = 30040
    IsTogglePatternAvailableProperty = 30041
    IsTransformPattern2AvailableProperty = 30134
    IsTransformPatternAvailableProperty = 30042
    IsValuePatternAvailableProperty = 30043
    IsVirtualizedItemPatternAvailableProperty = 30109
    IsWindowPatternAvailableProperty = 30044
    ItemStatusProperty = 30026
    ItemTypeProperty = 30021
    LabeledByProperty = 30018
    LandmarkTypeProperty = 30157
    LegacyIAccessibleChildIdProperty = 30091
    LegacyIAccessibleDefaultActionProperty = 30100
    LegacyIAccessibleDescriptionProperty = 30094
    LegacyIAccessibleHelpProperty = 30097
    LegacyIAccessibleKeyboardShortcutProperty = 30098
    LegacyIAccessibleNameProperty = 30092
    LegacyIAccessibleRoleProperty = 30095
    LegacyIAccessibleSelectionProperty = 30099
    LegacyIAccessibleStateProperty = 30096
    LegacyIAccessibleValueProperty = 30093
    LevelProperty = 30154
    LiveSettingProperty = 30135
    LocalizedControlTypeProperty = 30004
    LocalizedLandmarkTypeProperty = 30158
    MultipleViewCurrentViewProperty = 30071
    MultipleViewSupportedViewsProperty = 30072
    NameProperty = 30005
    NativeWindowHandleProperty = 30020
    OptimizeForVisualContentProperty = 30111
    OrientationProperty = 30023
    OutlineColorProperty = 30161
    OutlineThicknessProperty = 30164
    PositionInSetProperty = 30152
    ProcessIdProperty = 30002
    ProviderDescriptionProperty = 30107
    RangeValueIsReadOnlyProperty = 30048
    RangeValueLargeChangeProperty = 30051
    RangeValueMaximumProperty = 30050
    RangeValueMinimumProperty = 30049
    RangeValueSmallChangeProperty = 30052
    RangeValueValueProperty = 30047
    RotationProperty = 30166
    RuntimeIdProperty = 30000
    ScrollHorizontalScrollPercentProperty = 30053
    ScrollHorizontalViewSizeProperty = 30054
    ScrollHorizontallyScrollableProperty = 30057
    ScrollVerticalScrollPercentProperty = 30055
    ScrollVerticalViewSizeProperty = 30056
    ScrollVerticallyScrollableProperty = 30058
    Selection2CurrentSelectedItemProperty = 30171
    Selection2FirstSelectedItemProperty = 30169
    Selection2ItemCountProperty = 30172
    Selection2LastSelectedItemProperty = 30170
    SelectionCanSelectMultipleProperty = 30060
    SelectionIsSelectionRequiredProperty = 30061
    SelectionItemIsSelectedProperty = 30079
    SelectionItemSelectionContainerProperty = 30080
    SelectionSelectionProperty = 30059
    SizeOfSetProperty = 30153
    SizeProperty = 30167
    SpreadsheetItemAnnotationObjectsProperty = 30130
    SpreadsheetItemAnnotationTypesProperty = 30131
    SpreadsheetItemFormulaProperty = 30129
    StylesExtendedPropertiesProperty = 30126
    StylesFillColorProperty = 30122
    StylesFillPatternColorProperty = 30125
    StylesFillPatternStyleProperty = 30123
    StylesShapeProperty = 30124
    StylesStyleIdProperty = 30120
    StylesStyleNameProperty = 30121
    TableColumnHeadersProperty = 30082
    TableItemColumnHeaderItemsProperty = 30085
    TableItemRowHeaderItemsProperty = 30084
    TableRowHeadersProperty = 30081
    TableRowOrColumnMajorProperty = 30083
    ToggleToggleStateProperty = 30086
    Transform2CanZoomProperty = 30133
    Transform2ZoomLevelProperty = 30145
    Transform2ZoomMaximumProperty = 30147
    Transform2ZoomMinimumProperty = 30146
    TransformCanMoveProperty = 30087
    TransformCanResizeProperty = 30088
    TransformCanRotateProperty = 30089
    ValueIsReadOnlyProperty = 30046
    ValueValueProperty = 30045
    VisualEffectsProperty = 30163
    WindowCanMaximizeProperty = 30073
    WindowCanMinimizeProperty = 30074
    WindowIsModalProperty = 30077
    WindowIsTopmostProperty = 30078
    WindowWindowInteractionStateProperty = 30076
    WindowWindowVisualStateProperty = 30075


PropertyIdNames = {
    PropertyId.AcceleratorKeyProperty: 'AcceleratorKeyProperty',
    PropertyId.AccessKeyProperty: 'AccessKeyProperty',
    PropertyId.AnnotationAnnotationTypeIdProperty: 'AnnotationAnnotationTypeIdProperty',
    PropertyId.AnnotationAnnotationTypeNameProperty: 'AnnotationAnnotationTypeNameProperty',
    PropertyId.AnnotationAuthorProperty: 'AnnotationAuthorProperty',
    PropertyId.AnnotationDateTimeProperty: 'AnnotationDateTimeProperty',
    PropertyId.AnnotationObjectsProperty: 'AnnotationObjectsProperty',
    PropertyId.AnnotationTargetProperty: 'AnnotationTargetProperty',
    PropertyId.AnnotationTypesProperty: 'AnnotationTypesProperty',
    PropertyId.AriaPropertiesProperty: 'AriaPropertiesProperty',
    PropertyId.AriaRoleProperty: 'AriaRoleProperty',
    PropertyId.AutomationIdProperty: 'AutomationIdProperty',
    PropertyId.BoundingRectangleProperty: 'BoundingRectangleProperty',
    PropertyId.CenterPointProperty: 'CenterPointProperty',
    PropertyId.ClassNameProperty: 'ClassNameProperty',
    PropertyId.ClickablePointProperty: 'ClickablePointProperty',
    PropertyId.ControlTypeProperty: 'ControlTypeProperty',
    PropertyId.ControllerForProperty: 'ControllerForProperty',
    PropertyId.CultureProperty: 'CultureProperty',
    PropertyId.DescribedByProperty: 'DescribedByProperty',
    PropertyId.DockDockPositionProperty: 'DockDockPositionProperty',
    PropertyId.DragDropEffectProperty: 'DragDropEffectProperty',
    PropertyId.DragDropEffectsProperty: 'DragDropEffectsProperty',
    PropertyId.DragGrabbedItemsProperty: 'DragGrabbedItemsProperty',
    PropertyId.DragIsGrabbedProperty: 'DragIsGrabbedProperty',
    PropertyId.DropTargetDropTargetEffectProperty: 'DropTargetDropTargetEffectProperty',
    PropertyId.DropTargetDropTargetEffectsProperty: 'DropTargetDropTargetEffectsProperty',
    PropertyId.ExpandCollapseExpandCollapseStateProperty: 'ExpandCollapseExpandCollapseStateProperty',
    PropertyId.FillColorProperty: 'FillColorProperty',
    PropertyId.FillTypeProperty: 'FillTypeProperty',
    PropertyId.FlowsFromProperty: 'FlowsFromProperty',
    PropertyId.FlowsToProperty: 'FlowsToProperty',
    PropertyId.FrameworkIdProperty: 'FrameworkIdProperty',
    PropertyId.FullDescriptionProperty: 'FullDescriptionProperty',
    PropertyId.GridColumnCountProperty: 'GridColumnCountProperty',
    PropertyId.GridItemColumnProperty: 'GridItemColumnProperty',
    PropertyId.GridItemColumnSpanProperty: 'GridItemColumnSpanProperty',
    PropertyId.GridItemContainingGridProperty: 'GridItemContainingGridProperty',
    PropertyId.GridItemRowProperty: 'GridItemRowProperty',
    PropertyId.GridItemRowSpanProperty: 'GridItemRowSpanProperty',
    PropertyId.GridRowCountProperty: 'GridRowCountProperty',
    PropertyId.HasKeyboardFocusProperty: 'HasKeyboardFocusProperty',
    PropertyId.HelpTextProperty: 'HelpTextProperty',
    PropertyId.IsAnnotationPatternAvailableProperty: 'IsAnnotationPatternAvailableProperty',
    PropertyId.IsContentElementProperty: 'IsContentElementProperty',
    PropertyId.IsControlElementProperty: 'IsControlElementProperty',
    PropertyId.IsCustomNavigationPatternAvailableProperty: 'IsCustomNavigationPatternAvailableProperty',
    PropertyId.IsDataValidForFormProperty: 'IsDataValidForFormProperty',
    PropertyId.IsDockPatternAvailableProperty: 'IsDockPatternAvailableProperty',
    PropertyId.IsDragPatternAvailableProperty: 'IsDragPatternAvailableProperty',
    PropertyId.IsDropTargetPatternAvailableProperty: 'IsDropTargetPatternAvailableProperty',
    PropertyId.IsEnabledProperty: 'IsEnabledProperty',
    PropertyId.IsExpandCollapsePatternAvailableProperty: 'IsExpandCollapsePatternAvailableProperty',
    PropertyId.IsGridItemPatternAvailableProperty: 'IsGridItemPatternAvailableProperty',
    PropertyId.IsGridPatternAvailableProperty: 'IsGridPatternAvailableProperty',
    PropertyId.IsInvokePatternAvailableProperty: 'IsInvokePatternAvailableProperty',
    PropertyId.IsItemContainerPatternAvailableProperty: 'IsItemContainerPatternAvailableProperty',
    PropertyId.IsKeyboardFocusableProperty: 'IsKeyboardFocusableProperty',
    PropertyId.IsLegacyIAccessiblePatternAvailableProperty: 'IsLegacyIAccessiblePatternAvailableProperty',
    PropertyId.IsMultipleViewPatternAvailableProperty: 'IsMultipleViewPatternAvailableProperty',
    PropertyId.IsObjectModelPatternAvailableProperty: 'IsObjectModelPatternAvailableProperty',
    PropertyId.IsOffscreenProperty: 'IsOffscreenProperty',
    PropertyId.IsPasswordProperty: 'IsPasswordProperty',
    PropertyId.IsPeripheralProperty: 'IsPeripheralProperty',
    PropertyId.IsRangeValuePatternAvailableProperty: 'IsRangeValuePatternAvailableProperty',
    PropertyId.IsRequiredForFormProperty: 'IsRequiredForFormProperty',
    PropertyId.IsScrollItemPatternAvailableProperty: 'IsScrollItemPatternAvailableProperty',
    PropertyId.IsScrollPatternAvailableProperty: 'IsScrollPatternAvailableProperty',
    PropertyId.IsSelectionItemPatternAvailableProperty: 'IsSelectionItemPatternAvailableProperty',
    PropertyId.IsSelectionPattern2AvailableProperty: 'IsSelectionPattern2AvailableProperty',
    PropertyId.IsSelectionPatternAvailableProperty: 'IsSelectionPatternAvailableProperty',
    PropertyId.IsSpreadsheetItemPatternAvailableProperty: 'IsSpreadsheetItemPatternAvailableProperty',
    PropertyId.IsSpreadsheetPatternAvailableProperty: 'IsSpreadsheetPatternAvailableProperty',
    PropertyId.IsStylesPatternAvailableProperty: 'IsStylesPatternAvailableProperty',
    PropertyId.IsSynchronizedInputPatternAvailableProperty: 'IsSynchronizedInputPatternAvailableProperty',
    PropertyId.IsTableItemPatternAvailableProperty: 'IsTableItemPatternAvailableProperty',
    PropertyId.IsTablePatternAvailableProperty: 'IsTablePatternAvailableProperty',
    PropertyId.IsTextChildPatternAvailableProperty: 'IsTextChildPatternAvailableProperty',
    PropertyId.IsTextEditPatternAvailableProperty: 'IsTextEditPatternAvailableProperty',
    PropertyId.IsTextPattern2AvailableProperty: 'IsTextPattern2AvailableProperty',
    PropertyId.IsTextPatternAvailableProperty: 'IsTextPatternAvailableProperty',
    PropertyId.IsTogglePatternAvailableProperty: 'IsTogglePatternAvailableProperty',
    PropertyId.IsTransformPattern2AvailableProperty: 'IsTransformPattern2AvailableProperty',
    PropertyId.IsTransformPatternAvailableProperty: 'IsTransformPatternAvailableProperty',
    PropertyId.IsValuePatternAvailableProperty: 'IsValuePatternAvailableProperty',
    PropertyId.IsVirtualizedItemPatternAvailableProperty: 'IsVirtualizedItemPatternAvailableProperty',
    PropertyId.IsWindowPatternAvailableProperty: 'IsWindowPatternAvailableProperty',
    PropertyId.ItemStatusProperty: 'ItemStatusProperty',
    PropertyId.ItemTypeProperty: 'ItemTypeProperty',
    PropertyId.LabeledByProperty: 'LabeledByProperty',
    PropertyId.LandmarkTypeProperty: 'LandmarkTypeProperty',
    PropertyId.LegacyIAccessibleChildIdProperty: 'LegacyIAccessibleChildIdProperty',
    PropertyId.LegacyIAccessibleDefaultActionProperty: 'LegacyIAccessibleDefaultActionProperty',
    PropertyId.LegacyIAccessibleDescriptionProperty: 'LegacyIAccessibleDescriptionProperty',
    PropertyId.LegacyIAccessibleHelpProperty: 'LegacyIAccessibleHelpProperty',
    PropertyId.LegacyIAccessibleKeyboardShortcutProperty: 'LegacyIAccessibleKeyboardShortcutProperty',
    PropertyId.LegacyIAccessibleNameProperty: 'LegacyIAccessibleNameProperty',
    PropertyId.LegacyIAccessibleRoleProperty: 'LegacyIAccessibleRoleProperty',
    PropertyId.LegacyIAccessibleSelectionProperty: 'LegacyIAccessibleSelectionProperty',
    PropertyId.LegacyIAccessibleStateProperty: 'LegacyIAccessibleStateProperty',
    PropertyId.LegacyIAccessibleValueProperty: 'LegacyIAccessibleValueProperty',
    PropertyId.LevelProperty: 'LevelProperty',
    PropertyId.LiveSettingProperty: 'LiveSettingProperty',
    PropertyId.LocalizedControlTypeProperty: 'LocalizedControlTypeProperty',
    PropertyId.LocalizedLandmarkTypeProperty: 'LocalizedLandmarkTypeProperty',
    PropertyId.MultipleViewCurrentViewProperty: 'MultipleViewCurrentViewProperty',
    PropertyId.MultipleViewSupportedViewsProperty: 'MultipleViewSupportedViewsProperty',
    PropertyId.NameProperty: 'NameProperty',
    PropertyId.NativeWindowHandleProperty: 'NativeWindowHandleProperty',
    PropertyId.OptimizeForVisualContentProperty: 'OptimizeForVisualContentProperty',
    PropertyId.OrientationProperty: 'OrientationProperty',
    PropertyId.OutlineColorProperty: 'OutlineColorProperty',
    PropertyId.OutlineThicknessProperty: 'OutlineThicknessProperty',
    PropertyId.PositionInSetProperty: 'PositionInSetProperty',
    PropertyId.ProcessIdProperty: 'ProcessIdProperty',
    PropertyId.ProviderDescriptionProperty: 'ProviderDescriptionProperty',
    PropertyId.RangeValueIsReadOnlyProperty: 'RangeValueIsReadOnlyProperty',
    PropertyId.RangeValueLargeChangeProperty: 'RangeValueLargeChangeProperty',
    PropertyId.RangeValueMaximumProperty: 'RangeValueMaximumProperty',
    PropertyId.RangeValueMinimumProperty: 'RangeValueMinimumProperty',
    PropertyId.RangeValueSmallChangeProperty: 'RangeValueSmallChangeProperty',
    PropertyId.RangeValueValueProperty: 'RangeValueValueProperty',
    PropertyId.RotationProperty: 'RotationProperty',
    PropertyId.RuntimeIdProperty: 'RuntimeIdProperty',
    PropertyId.ScrollHorizontalScrollPercentProperty: 'ScrollHorizontalScrollPercentProperty',
    PropertyId.ScrollHorizontalViewSizeProperty: 'ScrollHorizontalViewSizeProperty',
    PropertyId.ScrollHorizontallyScrollableProperty: 'ScrollHorizontallyScrollableProperty',
    PropertyId.ScrollVerticalScrollPercentProperty: 'ScrollVerticalScrollPercentProperty',
    PropertyId.ScrollVerticalViewSizeProperty: 'ScrollVerticalViewSizeProperty',
    PropertyId.ScrollVerticallyScrollableProperty: 'ScrollVerticallyScrollableProperty',
    PropertyId.Selection2CurrentSelectedItemProperty: 'Selection2CurrentSelectedItemProperty',
    PropertyId.Selection2FirstSelectedItemProperty: 'Selection2FirstSelectedItemProperty',
    PropertyId.Selection2ItemCountProperty: 'Selection2ItemCountProperty',
    PropertyId.Selection2LastSelectedItemProperty: 'Selection2LastSelectedItemProperty',
    PropertyId.SelectionCanSelectMultipleProperty: 'SelectionCanSelectMultipleProperty',
    PropertyId.SelectionIsSelectionRequiredProperty: 'SelectionIsSelectionRequiredProperty',
    PropertyId.SelectionItemIsSelectedProperty: 'SelectionItemIsSelectedProperty',
    PropertyId.SelectionItemSelectionContainerProperty: 'SelectionItemSelectionContainerProperty',
    PropertyId.SelectionSelectionProperty: 'SelectionSelectionProperty',
    PropertyId.SizeOfSetProperty: 'SizeOfSetProperty',
    PropertyId.SizeProperty: 'SizeProperty',
    PropertyId.SpreadsheetItemAnnotationObjectsProperty: 'SpreadsheetItemAnnotationObjectsProperty',
    PropertyId.SpreadsheetItemAnnotationTypesProperty: 'SpreadsheetItemAnnotationTypesProperty',
    PropertyId.SpreadsheetItemFormulaProperty: 'SpreadsheetItemFormulaProperty',
    PropertyId.StylesExtendedPropertiesProperty: 'StylesExtendedPropertiesProperty',
    PropertyId.StylesFillColorProperty: 'StylesFillColorProperty',
    PropertyId.StylesFillPatternColorProperty: 'StylesFillPatternColorProperty',
    PropertyId.StylesFillPatternStyleProperty: 'StylesFillPatternStyleProperty',
    PropertyId.StylesShapeProperty: 'StylesShapeProperty',
    PropertyId.StylesStyleIdProperty: 'StylesStyleIdProperty',
    PropertyId.StylesStyleNameProperty: 'StylesStyleNameProperty',
    PropertyId.TableColumnHeadersProperty: 'TableColumnHeadersProperty',
    PropertyId.TableItemColumnHeaderItemsProperty: 'TableItemColumnHeaderItemsProperty',
    PropertyId.TableItemRowHeaderItemsProperty: 'TableItemRowHeaderItemsProperty',
    PropertyId.TableRowHeadersProperty: 'TableRowHeadersProperty',
    PropertyId.TableRowOrColumnMajorProperty: 'TableRowOrColumnMajorProperty',
    PropertyId.ToggleToggleStateProperty: 'ToggleToggleStateProperty',
    PropertyId.Transform2CanZoomProperty: 'Transform2CanZoomProperty',
    PropertyId.Transform2ZoomLevelProperty: 'Transform2ZoomLevelProperty',
    PropertyId.Transform2ZoomMaximumProperty: 'Transform2ZoomMaximumProperty',
    PropertyId.Transform2ZoomMinimumProperty: 'Transform2ZoomMinimumProperty',
    PropertyId.TransformCanMoveProperty: 'TransformCanMoveProperty',
    PropertyId.TransformCanResizeProperty: 'TransformCanResizeProperty',
    PropertyId.TransformCanRotateProperty: 'TransformCanRotateProperty',
    PropertyId.ValueIsReadOnlyProperty: 'ValueIsReadOnlyProperty',
    PropertyId.ValueValueProperty: 'ValueValueProperty',
    PropertyId.VisualEffectsProperty: 'VisualEffectsProperty',
    PropertyId.WindowCanMaximizeProperty: 'WindowCanMaximizeProperty',
    PropertyId.WindowCanMinimizeProperty: 'WindowCanMinimizeProperty',
    PropertyId.WindowIsModalProperty: 'WindowIsModalProperty',
    PropertyId.WindowIsTopmostProperty: 'WindowIsTopmostProperty',
    PropertyId.WindowWindowInteractionStateProperty: 'WindowWindowInteractionStateProperty',
    PropertyId.WindowWindowVisualStateProperty: 'WindowWindowVisualStateProperty',
}


class AccessibleRole:
    """
    AccessibleRole from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/dotnet/api/system.windows.forms.accessiblerole?view=netframework-4.8
    """
    TitleBar = 0x1
    MenuBar = 0x2
    ScrollBar = 0x3
    Grip = 0x4
    Sound = 0x5
    Cursor = 0x6
    Caret = 0x7
    Alert = 0x8
    Window = 0x9
    Client = 0xa
    MenuPopup = 0xb
    MenuItem = 0xc
    ToolTip = 0xd
    Application = 0xe
    Document = 0xf
    Pane = 0x10
    Chart = 0x11
    Dialog = 0x12
    Border = 0x13
    Grouping = 0x14
    Separator = 0x15
    Toolbar = 0x16
    StatusBar = 0x17
    Table = 0x18
    ColumnHeader = 0x19
    RowHeader = 0x1a
    Column = 0x1b
    Row = 0x1c
    Cell = 0x1d
    Link = 0x1e
    HelpBalloon = 0x1f
    Character = 0x20
    List = 0x21
    ListItem = 0x22
    Outline = 0x23
    OutlineItem = 0x24
    PageTab = 0x25
    PropertyPage = 0x26
    Indicator = 0x27
    Graphic = 0x28
    StaticText = 0x29
    Text = 0x2a
    PushButton = 0x2b
    CheckButton = 0x2c
    RadioButton = 0x2d
    ComboBox = 0x2e
    DropList = 0x2f
    ProgressBar = 0x30
    Dial = 0x31
    HotkeyField = 0x32
    Slider = 0x33
    SpinButton = 0x34
    Diagram = 0x35
    Animation = 0x36
    Equation = 0x37
    ButtonDropDown = 0x38
    ButtonMenu = 0x39
    ButtonDropDownGrid = 0x3a
    WhiteSpace = 0x3b
    PageTabList = 0x3c
    Clock = 0x3d
    SplitButton = 0x3e
    IpAddress = 0x3f
    OutlineButton = 0x40


class AccessibleState():
    """
    AccessibleState from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/dotnet/api/system.windows.forms.accessiblestates?view=netframework-4.8
    """
    Normal = 0
    Unavailable = 0x1
    Selected = 0x2
    Focused = 0x4
    Pressed = 0x8
    Checked = 0x10
    Mixed = 0x20
    Indeterminate = 0x20
    ReadOnly = 0x40
    HotTracked = 0x80
    Default = 0x100
    Expanded = 0x200
    Collapsed = 0x400
    Busy = 0x800
    Floating = 0x1000
    Marqueed = 0x2000
    Animated = 0x4000
    Invisible = 0x8000
    Offscreen = 0x10000
    Sizeable = 0x20000
    Moveable = 0x40000
    SelfVoicing = 0x80000
    Focusable = 0x100000
    Selectable = 0x200000
    Linked = 0x400000
    Traversed = 0x800000
    MultiSelectable = 0x1000000
    ExtSelectable = 0x2000000
    AlertLow = 0x4000000
    AlertMedium = 0x8000000
    AlertHigh = 0x10000000
    Protected = 0x20000000
    Valid = 0x7fffffff
    HasPopup = 0x40000000


class AccessibleSelection:
    """
    AccessibleSelection from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/dotnet/api/system.windows.forms.accessibleselection?view=netframework-4.8
    """
    None_ = 0
    TakeFocus = 0x1
    TakeSelection = 0x2
    ExtendSelection = 0x4
    AddSelection = 0x8
    RemoveSelection = 0x10


class AnnotationType:
    """
    AnnotationType from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/WinAuto/uiauto-annotation-type-identifiers
    """
    AdvancedProofingIssue = 60020
    Author = 60019
    CircularReferenceError = 60022
    Comment = 60003
    ConflictingChange = 60018
    DataValidationError = 60021
    DeletionChange = 60012
    EditingLockedChange = 60016
    Endnote = 60009
    ExternalChange = 60017
    Footer = 60007
    Footnote = 60010
    FormatChange = 60014
    FormulaError = 60004
    GrammarError = 60002
    Header = 60006
    Highlighted = 60008
    InsertionChange = 60011
    Mathematics = 60023
    MoveChange = 60013
    SpellingError = 60001
    TrackChanges = 60005
    Unknown = 60000
    UnsyncedChange = 60015


class NavigateDirection:
    """
    NavigateDirection from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-navigatedirection
    """
    Parent = 0
    NextSibling = 1
    PreviousSibling = 2
    FirstChild = 3
    LastChild = 4


class DockPosition:
    """
    DockPosition from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-dockposition
    """
    Top = 0
    Left = 1
    Bottom = 2
    Right = 3
    Fill = 4
    None_ = 5


class ScrollAmount:
    """
    ScrollAmount from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-scrollamount
    """
    LargeDecrement = 0
    SmallDecrement = 1
    NoAmount = 2
    LargeIncrement = 3
    SmallIncrement = 4


class StyleId:
    """
    StyleId from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/WinAuto/uiauto-style-identifiers
    """
    Custom = 70000
    Heading1 = 70001
    Heading2 = 70002
    Heading3 = 70003
    Heading4 = 70004
    Heading5 = 70005
    Heading6 = 70006
    Heading7 = 70007
    Heading8 = 70008
    Heading9 = 70009
    Title = 70010
    Subtitle = 70011
    Normal = 70012
    Emphasis = 70013
    Quote = 70014
    BulletedList = 70015
    NumberedList = 70016


class RowOrColumnMajor:
    """
    RowOrColumnMajor from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-roworcolumnmajor
    """
    RowMajor = 0
    ColumnMajor = 1
    Indeterminate = 2


class ExpandCollapseState:
    """
    ExpandCollapseState from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-expandcollapsestate
    """
    Collapsed = 0
    Expanded = 1
    PartiallyExpanded = 2
    LeafNode = 3


class OrientationType:
    """
    OrientationType from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-orientationtype
    """
    None_ = 0
    Horizontal = 1
    Vertical = 2


class ToggleState:
    """
    ToggleState from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-togglestate
    """
    Off = 0
    On = 1
    Indeterminate = 2


class TextPatternRangeEndpoint:
    """
    TextPatternRangeEndpoint from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-textpatternrangeendpoint
    """
    Start = 0
    End = 1

class TextAttributeId:
    """
    TextAttributeId from IUIAutomation.
    Refer https://docs.microsoft.com/zh-cn/windows/desktop/WinAuto/uiauto-textattribute-ids
    """
    AfterParagraphSpacingAttribute = 40042
    AnimationStyleAttribute = 40000
    AnnotationObjectsAttribute = 40032
    AnnotationTypesAttribute = 40031
    BackgroundColorAttribute = 40001
    BeforeParagraphSpacingAttribute = 40041
    BulletStyleAttribute = 40002
    CapStyleAttribute = 40003
    CaretBidiModeAttribute = 40039
    CaretPositionAttribute = 40038
    CultureAttribute = 40004
    FontNameAttribute = 40005
    FontSizeAttribute = 40006
    FontWeightAttribute = 40007
    ForegroundColorAttribute = 40008
    HorizontalTextAlignmentAttribute = 40009
    IndentationFirstLineAttribute = 40010
    IndentationLeadingAttribute = 40011
    IndentationTrailingAttribute = 40012
    IsActiveAttribute = 40036
    IsHiddenAttribute = 40013
    IsItalicAttribute = 40014
    IsReadOnlyAttribute = 40015
    IsSubscriptAttribute = 40016
    IsSuperscriptAttribute = 40017
    LineSpacingAttribute = 40040
    LinkAttribute = 40035
    MarginBottomAttribute = 40018
    MarginLeadingAttribute = 40019
    MarginTopAttribute = 40020
    MarginTrailingAttribute = 40021
    OutlineStylesAttribute = 40022
    OverlineColorAttribute = 40023
    OverlineStyleAttribute = 40024
    SayAsInterpretAsAttribute = 40043
    SelectionActiveEndAttribute = 40037
    StrikethroughColorAttribute = 40025
    StrikethroughStyleAttribute = 40026
    StyleIdAttribute = 40034
    StyleNameAttribute = 40033
    TabsAttribute = 40027
    TextFlowDirectionsAttribute = 40028
    UnderlineColorAttribute = 40029
    UnderlineStyleAttribute = 40030


class TextUnit:
    """
    TextUnit from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-textunit
    """
    Character = 0
    Format = 1
    Word = 2
    Line = 3
    Paragraph = 4
    Page = 5
    Document = 6


class ZoomUnit:
    """
    ZoomUnit from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-zoomunit
    """
    NoAmount = 0
    LargeDecrement = 1
    SmallDecrement = 2
    LargeIncrement = 3
    SmallIncrement = 4


class WindowInteractionState:
    """
    WindowInteractionState from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-windowinteractionstate
    """
    Running = 0
    Closing = 1
    ReadyForUserInteraction = 2
    BlockedByModalWindow = 3
    NotResponding = 4


class WindowVisualState:
    """
    WindowVisualState from IUIAutomation.
    Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationcore/ne-uiautomationcore-windowvisualstate
    """
    Normal = 0
    Maximized = 1
    Minimized = 2


class ConsoleColor:
    """ConsoleColor from Win32."""
    Default = -1
    Black = 0
    DarkBlue = 1
    DarkGreen = 2
    DarkCyan = 3
    DarkRed = 4
    DarkMagenta = 5
    DarkYellow = 6
    Gray = 7
    DarkGray = 8
    Blue = 9
    Green = 10
    Cyan = 11
    Red = 12
    Magenta = 13
    Yellow = 14
    White = 15


class GAFlag:
    """GAFlag from Win32."""
    Parent = 1
    Root = 2
    RootOwner = 3


class MouseEventFlag:
    """MouseEventFlag from Win32."""
    Move = 0x0001
    LeftDown = 0x0002
    LeftUp = 0x0004
    RightDown = 0x0008
    RightUp = 0x0010
    MiddleDown = 0x0020
    MiddleUp = 0x0040
    XDown = 0x0080
    XUp = 0x0100
    Wheel = 0x0800
    HWheel = 0x1000
    MoveNoCoalesce = 0x2000
    VirtualDesk = 0x4000
    Absolute = 0x8000


class KeyboardEventFlag:
    """KeyboardEventFlag from Win32."""
    KeyDown = 0x0000
    ExtendedKey = 0x0001
    KeyUp = 0x0002
    KeyUnicode = 0x0004
    KeyScanCode = 0x0008


class InputType:
    """InputType from Win32"""
    Mouse = 0
    Keyboard = 1
    Hardware = 2


class ModifierKey:
    """ModifierKey from Win32."""
    Alt = 0x0001
    Control = 0x0002
    Shift = 0x0004
    Win = 0x0008
    NoRepeat = 0x4000


class SW:
    """ShowWindow params from Win32."""
    Hide = 0
    ShowNormal = 1
    Normal = 1
    ShowMinimized = 2
    ShowMaximized = 3
    Maximize = 3
    ShowNoActivate = 4
    Show = 5
    Minimize = 6
    ShowMinNoActive = 7
    ShowNA = 8
    Restore = 9
    ShowDefault = 10
    ForceMinimize = 11
    Max = 11


class SWP:
    """SetWindowPos params from Win32."""
    HWND_Top = 0
    HWND_Bottom = 1
    HWND_Topmost = -1
    HWND_NoTopmost = -2
    SWP_NoSize = 0x0001
    SWP_NoMove = 0x0002
    SWP_NoZOrder = 0x0004
    SWP_NoRedraw = 0x0008
    SWP_NoActivate = 0x0010
    SWP_FrameChanged = 0x0020  # The frame changed: send WM_NCCALCSIZE
    SWP_ShowWindow = 0x0040
    SWP_HideWindow = 0x0080
    SWP_NoCopyBits = 0x0100
    SWP_NoOwnerZOrder = 0x0200  # Don't do owner Z ordering
    SWP_NoSendChanging = 0x0400  # Don't send WM_WINDOWPOSCHANGING
    SWP_DrawFrame = SWP_FrameChanged
    SWP_NoReposition = SWP_NoOwnerZOrder
    SWP_DeferErase = 0x2000
    SWP_AsyncWindowPos = 0x4000


class MB:
    """MessageBox flags from Win32."""
    Ok = 0x00000000
    OkCancel = 0x00000001
    AbortRetryIgnore = 0x00000002
    YesNoCancel = 0x00000003
    YesNo = 0x00000004
    RetryCancel = 0x00000005
    CancelTryContinue = 0x00000006
    IconHand = 0x00000010
    IconQuestion = 0x00000020
    IconExclamation = 0x00000030
    IconAsterisk = 0x00000040
    UserIcon = 0x00000080
    IconWarning = 0x00000030
    IconError = 0x00000010
    IconInformation = 0x00000040
    IconStop = 0x00000010
    DefButton1 = 0x00000000
    DefButton2 = 0x00000100
    DefButton3 = 0x00000200
    DefButton4 = 0x00000300
    ApplModal = 0x00000000
    SystemModal = 0x00001000
    TaskModal = 0x00002000
    Help = 0x00004000 # help button
    NoFocus = 0x00008000
    SetForeground = 0x00010000
    DefaultDesktopOnly = 0x00020000
    Topmost = 0x00040000
    Right = 0x00080000
    RtlReading = 0x00100000
    ServiceNotification = 0x00200000
    ServiceNotificationNT3X = 0x00040000

    TypeMask = 0x0000000f
    IconMask = 0x000000f0
    DefMask = 0x00000f00
    ModeMask = 0x00003000
    MiscMask = 0x0000c000

    IdOk = 1
    IdCancel = 2
    IdAbort = 3
    IdRetry = 4
    IdIgnore = 5
    IdYes = 6
    IdNo = 7
    IdClose = 8
    IdHelp = 9
    IdTryAgain = 10
    IdContinue = 11
    IdTimeout = 32000


class GWL:
    ExStyle = -20
    HInstance = -6
    HwndParent = -8
    ID = -12
    Style = -16
    UserData = -21
    WndProc = -4


class ProcessDpiAwareness:
    ProcessDpiUnaware = 0
    ProcessSystemDpiAware = 1
    ProcessPerMonitorDpiAware = 2


class DpiAwarenessContext:
    DpiAwarenessContextUnaware = -1
    DpiAwarenessContextSystemAware = -2
    DpiAwarenessContextPerMonitorAware = -3
    DpiAwarenessContextPerMonitorAwareV2 = -4
    DpiAwarenessContextUnawareGdiScaled = -5


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

GlobalKeyNames = [
    'CONTROL', 
    'ALT', 
    'SHIFT', 
    'WIN', 
    'CTRL', 
    'LWIN', 
    'RWIN'
]

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


class ConsoleScreenBufferInfo(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.wintypes._COORD),
        ('dwCursorPosition', ctypes.wintypes._COORD),
        ('wAttributes', ctypes.c_uint),
        ('srWindow', ctypes.wintypes.SMALL_RECT),
        ('dwMaximumWindowSize', ctypes.wintypes._COORD),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (('dx', ctypes.wintypes.LONG),
                ('dy', ctypes.wintypes.LONG),
                ('mouseData', ctypes.wintypes.DWORD),
                ('dwFlags', ctypes.wintypes.DWORD),
                ('time', ctypes.wintypes.DWORD),
                ('dwExtraInfo', ctypes.wintypes.PULONG))

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (('wVk', ctypes.wintypes.WORD),
                ('wScan', ctypes.wintypes.WORD),
                ('dwFlags', ctypes.wintypes.DWORD),
                ('time', ctypes.wintypes.DWORD),
                ('dwExtraInfo', ctypes.wintypes.PULONG))

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (('uMsg', ctypes.wintypes.DWORD),
                ('wParamL', ctypes.wintypes.WORD),
                ('wParamH', ctypes.wintypes.WORD))

class _INPUTUnion(ctypes.Union):
    _fields_ = (('mi', MOUSEINPUT),
                ('ki', KEYBDINPUT),
                ('hi', HARDWAREINPUT))

class INPUT(ctypes.Structure):
    _fields_ = (('type', ctypes.wintypes.DWORD),
                ('union', _INPUTUnion))

class Rect():
    """
    class Rect, like `ctypes.wintypes.RECT`.
    """
    def __init__(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom
    
    @property
    def info(self) -> Dict[str, int]:
        return {
            'left': self.left,
            'top': self.top,
            'right': self.right,
            'bottom': self.bottom,
            'width': self.width(),
            'height': self.height(),
            'xcenter': self.xcenter(),
            'ycenter': self.ycenter()
        }

    def width(self) -> int:
        return self.right - self.left

    def height(self) -> int:
        return self.bottom - self.top

    def xcenter(self) -> int:
        return self.left + self.width() // 2

    def ycenter(self) -> int:
        return self.top + self.height() // 2

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom
    
    def __eq__(self, rect):
        return self.left == rect.left and self.top == rect.top and self.right == rect.right and self.bottom == rect.bottom

    def __str__(self) -> str:
        return '({},{},{},{})[{}x{}]'.format(self.left, self.top, self.right, self.bottom, self.width(), self.height())

    def __repr__(self) -> str:
        return '{}({},{},{},{})[{}x{}]'.format(self.__class__.__name__, self.left, self.top, self.right, self.bottom, self.width(), self.height())


_StdOutputHandle = -11
_ConsoleOutputHandle = ctypes.c_void_p(0)
_DefaultConsoleColor = None


def GetClipboardText() -> str:
    if ctypes.windll.user32.OpenClipboard(0):
        if ctypes.windll.user32.IsClipboardFormatAvailable(13): # CF_TEXT=1, CF_UNICODETEXT=13
            hClipboardData = ctypes.windll.user32.GetClipboardData(13)
            hText = ctypes.windll.kernel32.GlobalLock(ctypes.c_void_p(hClipboardData))
            text = ctypes.c_wchar_p(hText).value[:]
            ctypes.windll.kernel32.GlobalUnlock(ctypes.c_void_p(hClipboardData))
            ctypes.windll.user32.CloseClipboard()
            return text
    return ''


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


def SetConsoleColor(color: int) -> bool:
    """
    Change the text color on console window.
    color: int, a value in class `ConsoleColor`.
    Return bool, True if succeed otherwise False.
    """
    global _ConsoleOutputHandle
    global _DefaultConsoleColor
    if not _DefaultConsoleColor:
        if not _ConsoleOutputHandle:
            _ConsoleOutputHandle = ctypes.c_void_p(ctypes.windll.kernel32.GetStdHandle(_StdOutputHandle))
        bufferInfo = ConsoleScreenBufferInfo()
        ctypes.windll.kernel32.GetConsoleScreenBufferInfo(_ConsoleOutputHandle, ctypes.byref(bufferInfo))
        _DefaultConsoleColor = int(bufferInfo.wAttributes & 0xFF)
    if sys.stdout:
        sys.stdout.flush()
    return bool(ctypes.windll.kernel32.SetConsoleTextAttribute(_ConsoleOutputHandle, ctypes.c_ushort(color)))


def ResetConsoleColor() -> bool:
    """
    Reset to the default text color on console window.
    Return bool, True if succeed otherwise False.
    """
    if sys.stdout:
        sys.stdout.flush()
    return bool(ctypes.windll.kernel32.SetConsoleTextAttribute(_ConsoleOutputHandle, ctypes.c_ushort(_DefaultConsoleColor)))


def WindowFromPoint(x: int, y: int) -> int:
    """
    WindowFromPoint from Win32.
    Return int, a native window handle.
    """
    return ctypes.windll.user32.WindowFromPoint(ctypes.wintypes.POINT(x, y))  # or ctypes.windll.user32.WindowFromPoint(x, y)


def GetCursorPos() -> Tuple[int, int]:
    """
    GetCursorPos from Win32.
    Get current mouse cursor positon.
    Return Tuple[int, int], two ints tuple (x, y).
    """
    point = ctypes.wintypes.POINT(0, 0)
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def SetCursorPos(x: int, y: int) -> bool:
    """
    SetCursorPos from Win32.
    Set mouse cursor to point x, y.
    x: int.
    y: int.
    Return bool, True if succeed otherwise False.
    """
    return bool(ctypes.windll.user32.SetCursorPos(x, y))


def GetDoubleClickTime() -> int:
    """
    GetDoubleClickTime from Win32.
    Return int, in milliseconds.
    """
    return ctypes.windll.user32.GetDoubleClickTime()


def mouse_event(dwFlags: int, dx: int, dy: int, dwData: int, dwExtraInfo: int) -> None:
    """mouse_event from Win32."""
    ctypes.windll.user32.mouse_event(dwFlags, dx, dy, dwData, dwExtraInfo)


def keybd_event(bVk: int, bScan: int, dwFlags: int, dwExtraInfo: int) -> None:
    """keybd_event from Win32."""
    ctypes.windll.user32.keybd_event(bVk, bScan, dwFlags, dwExtraInfo)


def PostMessage(handle: int, msg: int, wParam: int, lParam: int) -> bool:
    """
    PostMessage from Win32.
    Return bool, True if succeed otherwise False.
    """
    return bool(ctypes.windll.user32.PostMessageW(ctypes.c_void_p(handle), ctypes.c_uint(msg), ctypes.wintypes.WPARAM(wParam), ctypes.wintypes.LPARAM(lParam)))


def SendMessage(handle: int, msg: int, wParam: int, lParam: int) -> int:
    """
    SendMessage from Win32.
    Return int, the return value specifies the result of the message processing;
                it depends on the message sent.
    """
    return ctypes.windll.user32.SendMessageW(ctypes.c_void_p(handle), ctypes.c_uint(msg), ctypes.wintypes.WPARAM(wParam), ctypes.wintypes.LPARAM(lParam))


def Click(x: int, y: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse click at point x, y.
    x: int.
    y: int.
    waitTime: float.
    """
    SetCursorPos(x, y)
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.LeftDown | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(0.05)
    mouse_event(MouseEventFlag.LeftUp | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def MiddleClick(x: int, y: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse middle click at point x, y.
    x: int.
    y: int.
    waitTime: float.
    """
    SetCursorPos(x, y)
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.MiddleDown | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(0.05)
    mouse_event(MouseEventFlag.MiddleUp | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def RightClick(x: int, y: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse right click at point x, y.
    x: int.
    y: int.
    waitTime: float.
    """
    SetCursorPos(x, y)
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.RightDown | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(0.05)
    mouse_event(MouseEventFlag.RightUp | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def PressMouse(x: int, y: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Press left mouse.
    x: int.
    y: int.
    waitTime: float.
    """
    SetCursorPos(x, y)
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.LeftDown | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def ReleaseMouse(waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Release left mouse.
    waitTime: float.
    """
    x, y = GetCursorPos()
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.LeftUp | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def RightPressMouse(x: int, y: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Press right mouse.
    x: int.
    y: int.
    waitTime: float.
    """
    SetCursorPos(x, y)
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.RightDown | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def RightReleaseMouse(waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Release right mouse.
    waitTime: float.
    """
    x, y = GetCursorPos()
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.RightUp | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def MiddlePressMouse(x: int, y: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Press middle mouse.
    x: int.
    y: int.
    waitTime: float.
    """
    SetCursorPos(x, y)
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.MiddleDown | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def MiddleReleaseMouse(waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Release middle mouse.
    waitTime: float.
    """
    x, y = GetCursorPos()
    screenWidth, screenHeight = GetScreenSize()
    mouse_event(MouseEventFlag.MiddleUp | MouseEventFlag.Absolute, x * 65535 // screenWidth, y * 65535 // screenHeight, 0, 0)
    time.sleep(waitTime)


def MoveTo(x: int, y: int, moveSpeed: float = 1, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse move to point x, y from current cursor.
    x: int.
    y: int.
    moveSpeed: float, 1 normal speed, < 1 move slower, > 1 move faster.
    waitTime: float.
    """
    if moveSpeed <= 0:
        moveTime = 0
    else:
        moveTime = MAX_MOVE_SECOND / moveSpeed
    curX, curY = GetCursorPos()
    xCount = abs(x - curX)
    yCount = abs(y - curY)
    maxPoint = max(xCount, yCount)
    screenWidth, screenHeight = GetScreenSize()
    maxSide = max(screenWidth, screenHeight)
    minSide = min(screenWidth, screenHeight)
    if maxPoint > minSide:
        maxPoint = minSide
    if maxPoint < maxSide:
        maxPoint = 100 + int((maxSide - 100) / maxSide * maxPoint)
        moveTime = moveTime * maxPoint * 1.0 / maxSide
    stepCount = maxPoint // 20
    if stepCount > 1:
        xStep = (x - curX) * 1.0 / stepCount
        yStep = (y - curY) * 1.0 / stepCount
        interval = moveTime / stepCount
        for i in range(stepCount):
            cx = curX + int(xStep * i)
            cy = curY + int(yStep * i)
            # upper-left(0,0), lower-right(65536,65536)
            # mouse_event(MouseEventFlag.Move | MouseEventFlag.Absolute, cx*65536//screenWidth, cy*65536//screenHeight, 0, 0)
            SetCursorPos(cx, cy)
            time.sleep(interval)
    SetCursorPos(x, y)
    time.sleep(waitTime)


def DragDrop(x1: int, y1: int, x2: int, y2: int, moveSpeed: float = 1, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse left button drag from point x1, y1 drop to point x2, y2.
    x1: int.
    y1: int.
    x2: int.
    y2: int.
    moveSpeed: float, 1 normal speed, < 1 move slower, > 1 move faster.
    waitTime: float.
    """
    PressMouse(x1, y1, 0.05)
    MoveTo(x2, y2, moveSpeed, 0.05)
    ReleaseMouse(waitTime)


def RightDragDrop(x1: int, y1: int, x2: int, y2: int, moveSpeed: float = 1, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse right button drag from point x1, y1 drop to point x2, y2.
    x1: int.
    y1: int.
    x2: int.
    y2: int.
    moveSpeed: float, 1 normal speed, < 1 move slower, > 1 move faster.
    waitTime: float.
    """
    RightPressMouse(x1, y1, 0.05)
    MoveTo(x2, y2, moveSpeed, 0.05)
    RightReleaseMouse(waitTime)


def MiddleDragDrop(x1: int, y1: int, x2: int, y2: int, moveSpeed: float = 1, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse middle button drag from point x1, y1 drop to point x2, y2.
    x1: int.
    y1: int.
    x2: int.
    y2: int.
    moveSpeed: float, 1 normal speed, < 1 move slower, > 1 move faster.
    waitTime: float.
    """
    MiddlePressMouse(x1, y1, 0.05)
    MoveTo(x2, y2, moveSpeed, 0.05)
    MiddleReleaseMouse(waitTime)


def WheelDown(wheelTimes: int = 1, interval: float = 0.05, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse wheel down.
    wheelTimes: int.
    interval: float.
    waitTime: float.
    """
    for i in range(wheelTimes):
        mouse_event(MouseEventFlag.Wheel, 0, 0, -120, 0)    #WHEEL_DELTA=120
        time.sleep(interval)
    time.sleep(waitTime)


def WheelUp(wheelTimes: int = 1, interval: float = 0.05, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate mouse wheel up.
    wheelTimes: int.
    interval: float.
    waitTime: float.
    """
    for i in range(wheelTimes):
        mouse_event(MouseEventFlag.Wheel, 0, 0, 120, 0) #WHEEL_DELTA=120
        time.sleep(interval)
    time.sleep(waitTime)


def SetDpiAwareness(dpiAwarenessPerMonitor: bool = True) -> int:
    '''
    Call SetThreadDpiAwarenessContext(Windows 10 version 1607+) or SetProcessDpiAwareness(Windows 8.1+).
    You should call this function with True if you enable DPI scaling. uiautomation calls this function when it initializes.
    dpiAwarenessPerMonitor: bool.
    Return int.
    '''
    try:
        # https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext
        # Windows 10 1607+
        ctypes.windll.user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        context = DpiAwarenessContext.DpiAwarenessContextPerMonitorAware if dpiAwarenessPerMonitor else DpiAwarenessContext.DpiAwarenessContextUnaware 
        oldContext = ctypes.windll.user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(context))
        return oldContext
    except Exception as ex:
        try:
            # https://docs.microsoft.com/en-us/windows/win32/api/shellscalingapi/nf-shellscalingapi-setprocessdpiawareness
            # Once SetProcessDpiAwareness is set for an app, any future calls to SetProcessDpiAwareness will fail.
            # Windows 8.1+
            if dpiAwarenessPerMonitor:
                return ctypes.windll.shcore.SetProcessDpiAwareness(ProcessDpiAwareness.ProcessPerMonitorDpiAware)
        except Exception as ex2:
            pass


def GetScreenSize(dpiAwarenessPerMonitor: bool = True) -> Tuple[int, int]:
    """
    dpiAwarenessPerMonitor: bool.
    Return Tuple[int, int], two ints tuple (width, height).
    """
    SetDpiAwareness(dpiAwarenessPerMonitor)
    SM_CXSCREEN = 0
    SM_CYSCREEN = 1
    w = ctypes.windll.user32.GetSystemMetrics(SM_CXSCREEN)
    h = ctypes.windll.user32.GetSystemMetrics(SM_CYSCREEN)
    return w, h


def GetVirtualScreenSize(dpiAwarenessPerMonitor: bool = True) -> Tuple[int, int]:
    """
    dpiAwarenessPerMonitor: bool.
    Return Tuple[int, int], two ints tuple (width, height).
    """
    SetDpiAwareness(dpiAwarenessPerMonitor)
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79
    w = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return w, h


def GetMonitorsRect(dpiAwarenessPerMonitor: bool = False) -> List[Rect]:
    """
    Get monitors' rect.
    dpiAwarenessPerMonitor: bool.
    Return List[Rect].
    """
    SetDpiAwareness(dpiAwarenessPerMonitor)
    MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_size_t, ctypes.c_size_t, ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_size_t)
    rects = []
    def MonitorCallback(hMonitor: int, hdcMonitor: int, lprcMonitor: ctypes.POINTER(ctypes.wintypes.RECT), dwData: int):
        rect = Rect(lprcMonitor.contents.left, lprcMonitor.contents.top, lprcMonitor.contents.right, lprcMonitor.contents.bottom)
        rects.append(rect)
        return 1
    ret = ctypes.windll.user32.EnumDisplayMonitors(ctypes.c_void_p(0), ctypes.c_void_p(0), MonitorEnumProc(MonitorCallback), 0)
    return rects


def GetPixelColor(x: int, y: int, handle: int = 0) -> int:
    """
    Get pixel color of a native window.
    x: int.
    y: int.
    handle: int, the handle of a native window.
    Return int, the bgr value of point (x,y).
    r = bgr & 0x0000FF
    g = (bgr & 0x00FF00) >> 8
    b = (bgr & 0xFF0000) >> 16
    If handle is 0, get pixel from Desktop window(root control).
    Note:
    Not all devices support GetPixel.
    An application should call GetDeviceCaps to determine whether a specified device supports this function.
    For example, console window doesn't support.
    """
    hdc = ctypes.windll.user32.GetWindowDC(ctypes.c_void_p(handle))
    bgr = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(ctypes.c_void_p(handle), ctypes.c_void_p(hdc))
    return bgr


def MessageBox(content: str, title: str, flags: int = MB.Ok) -> int:
    """
    MessageBox from Win32.
    content: str.
    title: str.
    flags: int, a value or some combined values in class `MB`.
    Return int, a value in MB whose name starts with Id, such as MB.IdOk
    """
    return ctypes.windll.user32.MessageBoxW(ctypes.c_void_p(0), ctypes.c_wchar_p(content), ctypes.c_wchar_p(title), ctypes.c_uint(flags))


def SetForegroundWindow(handle: int) -> bool:
    """
    SetForegroundWindow from Win32.
    handle: int, the handle of a native window.
    Return bool, True if succeed otherwise False.
    """
    return bool(ctypes.windll.user32.SetForegroundWindow(ctypes.c_void_p(handle)))


def BringWindowToTop(handle: int) -> bool:
    """
    BringWindowToTop from Win32.
    handle: int, the handle of a native window.
    Return bool, True if succeed otherwise False.
    """
    return bool(ctypes.windll.user32.BringWindowToTop(ctypes.c_void_p(handle)))


def SwitchToThisWindow(handle: int) -> None:
    """
    SwitchToThisWindow from Win32.
    handle: int, the handle of a native window.
    """
    ctypes.windll.user32.SwitchToThisWindow(ctypes.c_void_p(handle), ctypes.c_int(1)) #void function, no return


def GetAncestor(handle: int, flag: int) -> int:
    """
    GetAncestor from Win32.
    handle: int, the handle of a native window.
    index: int, a value in class `GAFlag`.
    Return int, a native window handle.
    """
    return ctypes.windll.user32.GetAncestor(ctypes.c_void_p(handle), ctypes.c_int(flag))


def IsTopLevelWindow(handle: int) -> bool:
    """
    IsTopLevelWindow from Win32.
    handle: int, the handle of a native window.
    Return bool.
    Only available on Windows 7 or Higher.
    """
    return bool(ctypes.windll.user32.IsTopLevelWindow(ctypes.c_void_p(handle)))


def GetWindowLong(handle: int, index: int) -> int:
    """
    GetWindowLong from Win32.
    handle: int, the handle of a native window.
    index: int.
    """
    return ctypes.windll.user32.GetWindowLongW(ctypes.c_void_p(handle), ctypes.c_int(index))


def SetWindowLong(handle: int, index: int, value: int) -> int:
    """
    SetWindowLong from Win32.
    handle: int, the handle of a native window.
    index: int.
    value: int.
    Return int, the previous value before set.
    """
    return ctypes.windll.user32.SetWindowLongW(ctypes.c_void_p(handle), index, value)


def IsIconic(handle: int) -> bool:
    """
    IsIconic from Win32.
    Determine whether a native window is minimized.
    handle: int, the handle of a native window.
    Return bool.
    """
    return bool(ctypes.windll.user32.IsIconic(ctypes.c_void_p(handle)))


def IsZoomed(handle: int) -> bool:
    """
    IsZoomed from Win32.
    Determine whether a native window is maximized.
    handle: int, the handle of a native window.
    Return bool.
    """
    return bool(ctypes.windll.user32.IsZoomed(ctypes.c_void_p(handle)))


def IsWindowVisible(handle: int) -> bool:
    """
    IsWindowVisible from Win32.
    handle: int, the handle of a native window.
    Return bool.
    """
    return bool(ctypes.windll.user32.IsWindowVisible(ctypes.c_void_p(handle)))


def ShowWindow(handle: int, cmdShow: int) -> bool:
    """
    ShowWindow from Win32.
    handle: int, the handle of a native window.
    cmdShow: int, a value in clas `SW`.
    Return bool, True if succeed otherwise False.
    """
    return ctypes.windll.user32.ShowWindow(ctypes.c_void_p(handle), ctypes.c_int(cmdShow))


def MoveWindow(handle: int, x: int, y: int, width: int, height: int, repaint: int = 1) -> bool:
    """
    MoveWindow from Win32.
    handle: int, the handle of a native window.
    x: int.
    y: int.
    width: int.
    height: int.
    repaint: int, use 1 or 0.
    Return bool, True if succeed otherwise False.
    """
    return bool(ctypes.windll.user32.MoveWindow(ctypes.c_void_p(handle), ctypes.c_int(x), ctypes.c_int(y), ctypes.c_int(width), ctypes.c_int(height), ctypes.c_int(repaint)))


def SetWindowPos(handle: int, hWndInsertAfter: int, x: int, y: int, width: int, height: int, flags: int) -> bool:
    """
    SetWindowPos from Win32.
    handle: int, the handle of a native window.
    hWndInsertAfter: int, a value whose name starts with 'HWND' in class SWP.
    x: int.
    y: int.
    width: int.
    height: int.
    flags: int, values whose name starts with 'SWP' in class `SWP`.
    Return bool, True if succeed otherwise False.
    """
    return ctypes.windll.user32.SetWindowPos(ctypes.c_void_p(handle), ctypes.c_void_p(hWndInsertAfter), ctypes.c_int(x), ctypes.c_int(y), ctypes.c_int(width), ctypes.c_int(height), ctypes.c_uint(flags))


def SetWindowTopmost(handle: int, isTopmost: bool) -> bool:
    """
    handle: int, the handle of a native window.
    isTopmost: bool
    Return bool, True if succeed otherwise False.
    """
    topValue = SWP.HWND_Topmost if isTopmost else SWP.HWND_NoTopmost
    return bool(SetWindowPos(handle, topValue, 0, 0, 0, 0, SWP.SWP_NoSize | SWP.SWP_NoMove))


def GetWindowText(handle: int) -> str:
    """
    GetWindowText from Win32.
    handle: int, the handle of a native window.
    Return str.
    """
    arrayType = ctypes.c_wchar * MAX_PATH
    values = arrayType()
    ctypes.windll.user32.GetWindowTextW(ctypes.c_void_p(handle), values, ctypes.c_int(MAX_PATH))
    return values.value


def SetWindowText(handle: int, text: str) -> bool:
    """
    SetWindowText from Win32.
    handle: int, the handle of a native window.
    text: str.
    Return bool, True if succeed otherwise False.
    """
    return bool(ctypes.windll.user32.SetWindowTextW(ctypes.c_void_p(handle), ctypes.c_wchar_p(text)))


def GetEditText(handle: int) -> str:
    """
    Get text of a native Win32 Edit.
    handle: int, the handle of a native window.
    Return str.
    """
    textLen = SendMessage(handle, 0x000E, 0, 0) + 1  #WM_GETTEXTLENGTH
    arrayType = ctypes.c_wchar * textLen
    values = arrayType()
    SendMessage(handle, 0x000D, textLen, values)  #WM_GETTEXT
    return values.value


def GetConsoleOriginalTitle() -> str:
    """
    GetConsoleOriginalTitle from Win32.
    Return str.
    Only available on Windows Vista or higher.
    """
    if IsNT6orHigher:
        arrayType = ctypes.c_wchar * MAX_PATH
        values = arrayType()
        ctypes.windll.kernel32.GetConsoleOriginalTitleW(values, ctypes.c_uint(MAX_PATH))
        return values.value
    else:
        raise RuntimeError('GetConsoleOriginalTitle is not supported on Windows XP or lower.')


def GetConsoleTitle() -> str:
    """
    GetConsoleTitle from Win32.
    Return str.
    """
    arrayType = ctypes.c_wchar * MAX_PATH
    values = arrayType()
    ctypes.windll.kernel32.GetConsoleTitleW(values, ctypes.c_uint(MAX_PATH))
    return values.value


def SetConsoleTitle(text: str) -> bool:
    """
    SetConsoleTitle from Win32.
    text: str.
    Return bool, True if succeed otherwise False.
    """
    return bool(ctypes.windll.kernel32.SetConsoleTitleW(ctypes.c_wchar_p(text)))


def GetForegroundWindow() -> int:
    """
    GetForegroundWindow from Win32.
    Return int, the native handle of the foreground window.
    """
    return ctypes.windll.user32.GetForegroundWindow()


def IsDesktopLocked() -> bool:
    """
    Check if desktop is locked.
    Return bool.
    Desktop is locked if press Win+L, Ctrl+Alt+Del or in remote desktop mode.
    """
    isLocked = False
    desk = ctypes.windll.user32.OpenDesktopW(ctypes.c_wchar_p('Default'), ctypes.c_uint(0), ctypes.c_int(0), ctypes.c_uint(0x0100))  # DESKTOP_SWITCHDESKTOP = 0x0100
    if desk:
        isLocked = not ctypes.windll.user32.SwitchDesktop(ctypes.c_void_p(desk))
        ctypes.windll.user32.CloseDesktop(ctypes.c_void_p(desk))
    return isLocked


def PlayWaveFile(filePath: str = r'C:\Windows\Media\notify.wav', isAsync: bool = False, isLoop: bool = False) -> bool:
    """
    Call PlaySound from Win32.
    filePath: str, if emtpy, stop playing the current sound.
    isAsync: bool, if True, the sound is played asynchronously and returns immediately.
    isLoop: bool, if True, the sound plays repeatedly until PlayWaveFile(None) is called again, must also set isAsync to True.
    Return bool, True if succeed otherwise False.
    """
    if filePath:
        SND_ASYNC = 0x0001
        SND_NODEFAULT = 0x0002
        SND_LOOP = 0x0008
        SND_FILENAME = 0x20000
        flags = SND_NODEFAULT | SND_FILENAME
        if isAsync:
            flags |= SND_ASYNC
        if isLoop:
            flags |= SND_LOOP
            flags |= SND_ASYNC
        return bool(ctypes.windll.winmm.PlaySoundW(ctypes.c_wchar_p(filePath), ctypes.c_void_p(0), ctypes.c_uint(flags)))
    else:
        return bool(ctypes.windll.winmm.PlaySoundW(ctypes.c_wchar_p(0), ctypes.c_void_p(0), ctypes.c_uint(0)))


def IsProcess64Bit(processId: int) -> bool:
    """
    Return True if process is 64 bit.
    Return False if process is 32 bit.
    Return None if unknown, maybe caused by having no acess right to the process.
    """
    try:
        func = ctypes.windll.ntdll.ZwWow64ReadVirtualMemory64  #only 64 bit OS has this function
    except Exception as ex:
        return False
    try:
        IsWow64Process = ctypes.windll.kernel32.IsWow64Process
    except Exception as ex:
        return False
    hProcess = ctypes.windll.kernel32.OpenProcess(0x1000, 0, processId)  #PROCESS_QUERY_INFORMATION=0x0400,PROCESS_QUERY_LIMITED_INFORMATION=0x1000
    if hProcess:
        is64Bit = ctypes.c_int32()
        if IsWow64Process(ctypes.c_void_p(hProcess), ctypes.byref(is64Bit)):
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(hProcess))
            return False if is64Bit.value else True
        else:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(hProcess))


def IsUserAnAdmin() -> bool:
    """
    IsUserAnAdmin from Win32.
    Return bool.
    Minimum supported OS: Windows XP, Windows Server 2003
    """
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def RunScriptAsAdmin(argv: List[str], workingDirectory: str = None, showFlag: int = SW.ShowNormal) -> bool:
    """
    Run a python script as administrator.
    System will show a popup dialog askes you whether to elevate as administrator if UAC is enabled.
    argv: List[str], a str list like sys.argv, argv[0] is the script file, argv[1:] are other arguments.
    workingDirectory: str, the working directory for the script file.
    showFlag: int, a value in class `SW`.
    Return bool, True if succeed.
    """
    args = ' '.join('"{}"'.format(arg) for arg in argv)
    return ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, workingDirectory, showFlag) > 32


def SendKey(key: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate typing a key.
    key: int, a value in class `Keys`.
    """
    keybd_event(key, 0, KeyboardEventFlag.KeyDown | KeyboardEventFlag.ExtendedKey, 0)
    keybd_event(key, 0, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey, 0)
    time.sleep(waitTime)


def PressKey(key: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate a key down for key.
    key: int, a value in class `Keys`.
    waitTime: float.
    """
    keybd_event(key, 0, KeyboardEventFlag.KeyDown | KeyboardEventFlag.ExtendedKey, 0)
    time.sleep(waitTime)


def ReleaseKey(key: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
    """
    Simulate a key up for key.
    key: int, a value in class `Keys`.
    waitTime: float.
    """
    keybd_event(key, 0, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey, 0)
    time.sleep(waitTime)


def IsKeyPressed(key: int) -> bool:
    """
    key: int, a value in class `Keys`.
    Return bool.
    """
    state = ctypes.windll.user32.GetAsyncKeyState(key)
    return bool(state & 0x8000)


def _CreateInput(structure) -> INPUT:
    """
    Create Win32 struct `INPUT` for `SendInput`.
    Return `INPUT`.
    """
    if isinstance(structure, MOUSEINPUT):
        return INPUT(InputType.Mouse, _INPUTUnion(mi=structure))
    if isinstance(structure, KEYBDINPUT):
        return INPUT(InputType.Keyboard, _INPUTUnion(ki=structure))
    if isinstance(structure, HARDWAREINPUT):
        return INPUT(InputType.Hardware, _INPUTUnion(hi=structure))
    raise TypeError('Cannot create INPUT structure!')


def MouseInput(dx: int, dy: int, mouseData: int = 0, dwFlags: int = MouseEventFlag.LeftDown, time_: int = 0) -> INPUT:
    """
    Create Win32 struct `MOUSEINPUT` for `SendInput`.
    Return `INPUT`.
    """
    return _CreateInput(MOUSEINPUT(dx, dy, mouseData, dwFlags, time_, None))


def KeyboardInput(wVk: int, wScan: int, dwFlags: int = KeyboardEventFlag.KeyDown, time_: int = 0) -> INPUT:
    """Create Win32 struct `KEYBDINPUT` for `SendInput`."""
    return _CreateInput(KEYBDINPUT(wVk, wScan, dwFlags, time_, None))


def HardwareInput(uMsg: int, param: int = 0) -> INPUT:
    """Create Win32 struct `HARDWAREINPUT` for `SendInput`."""
    return _CreateInput(HARDWAREINPUT(uMsg, param & 0xFFFF, param >> 16 & 0xFFFF))


def SendInput(*inputs) -> int:
    """
    SendInput from Win32.
    input: `INPUT`.
    Return int, the number of events that it successfully inserted into the keyboard or mouse input stream.
                If the function returns zero, the input was already blocked by another thread.
    """
    cbSize = ctypes.c_int(ctypes.sizeof(INPUT))
    for ip in inputs:
        ret = ctypes.windll.user32.SendInput(1, ctypes.byref(ip), cbSize)
    return ret
    #or one call
    #nInputs = len(inputs)
    #LPINPUT = INPUT * nInputs
    #pInputs = LPINPUT(*inputs)
    #cbSize = ctypes.c_int(ctypes.sizeof(INPUT))
    #return ctypes.windll.user32.SendInput(nInputs, ctypes.byref(pInputs), cbSize)


def SendUnicodeChar(char: str, charMode: bool = True) -> int:
    """
    Type a single unicode char.
    char: str, len(char) must equal to 1.
    charMode: bool, if False, the char typied is depend on the input method if a input method is on.
    Return int, the number of events that it successfully inserted into the keyboard or mouse input stream.
                If the function returns zero, the input was already blocked by another thread.
    """
    if charMode:
        vk = 0
        scan = ord(char)
        flag = KeyboardEventFlag.KeyUnicode
    else:
        res = ctypes.windll.user32.VkKeyScanW(ctypes.wintypes.WCHAR(char))
        if (res >> 8) & 0xFF == 0:
            vk = res & 0xFF
            scan = 0
            flag = 0
        else:
            vk = 0
            scan = ord(char)
            flag = KeyboardEventFlag.KeyUnicode
    return SendInput(KeyboardInput(vk, scan, flag | KeyboardEventFlag.KeyDown),
                     KeyboardInput(vk, scan, flag | KeyboardEventFlag.KeyUp))


_SCKeys = {
    Keys.VK_LSHIFT: 0x02A,
    Keys.VK_RSHIFT: 0x136,
    Keys.VK_LCONTROL: 0x01D,
    Keys.VK_RCONTROL: 0x11D,
    Keys.VK_LMENU: 0x038,
    Keys.VK_RMENU: 0x138,
    Keys.VK_LWIN: 0x15B,
    Keys.VK_RWIN: 0x15C,
    Keys.VK_NUMPAD0: 0x52,
    Keys.VK_NUMPAD1: 0x4F,
    Keys.VK_NUMPAD2: 0x50,
    Keys.VK_NUMPAD3: 0x51,
    Keys.VK_NUMPAD4: 0x4B,
    Keys.VK_NUMPAD5: 0x4C,
    Keys.VK_NUMPAD6: 0x4D,
    Keys.VK_NUMPAD7: 0x47,
    Keys.VK_NUMPAD8: 0x48,
    Keys.VK_NUMPAD9: 0x49,
    Keys.VK_DECIMAL: 0x53,
    Keys.VK_NUMLOCK: 0x145,
    Keys.VK_DIVIDE: 0x135,
    Keys.VK_MULTIPLY: 0x037,
    Keys.VK_SUBTRACT: 0x04A,
    Keys.VK_ADD: 0x04E,
}


def _VKtoSC(key: int) -> int:
    """
    This function is only for internal use in SendKeys.
    key: int, a value in class `Keys`.
    Return int.
    """
    if key in _SCKeys:
        return _SCKeys[key]
    scanCode = ctypes.windll.user32.MapVirtualKeyA(key, 0)
    if not scanCode:
        return 0
    keyList = [Keys.VK_APPS, Keys.VK_CANCEL, Keys.VK_SNAPSHOT, Keys.VK_DIVIDE, Keys.VK_NUMLOCK]
    if key in keyList:
        scanCode |= 0x0100
    return scanCode


def SendKeys(text: str, interval: float = 0.01, waitTime: float = OPERATION_WAIT_TIME, charMode: bool = True, debug: bool = False) -> None:
    """
    Simulate typing keys on keyboard.
    text: str, keys to type.
    interval: float, seconds between keys.
    waitTime: float.
    charMode: bool, if False, the text typied is depend on the input method if a input method is on.
    debug: bool, if True, print the keys.
    Examples:
    {Ctrl}, {Delete} ... are special keys' name in SpecialKeyNames.
    SendKeys('{Ctrl}a{Delete}{Ctrl}v{Ctrl}s{Ctrl}{Shift}s{Win}e{PageDown}') #press Ctrl+a, Delete, Ctrl+v, Ctrl+s, Ctrl+Shift+s, Win+e, PageDown
    SendKeys('{Ctrl}(AB)({Shift}(123))') #press Ctrl+A+B, type (, press Shift+1+2+3, type ), if () follows a hold key, hold key won't release util )
    SendKeys('{Ctrl}{a 3}') #press Ctrl+a at the same time, release Ctrl+a, then type a 2 times
    SendKeys('{a 3}{B 5}') #type a 3 times, type B 5 times
    SendKeys('{{}Hello{}}abc {a}{b}{c} test{} 3}{!}{a} (){(}{)}') #type: {Hello}abc abc test}}}!a ()()
    SendKeys('0123456789{Enter}')
    SendKeys('ABCDEFGHIJKLMNOPQRSTUVWXYZ{Enter}')
    SendKeys('abcdefghijklmnopqrstuvwxyz{Enter}')
    SendKeys('`~!@#$%^&*()-_=+{Enter}')
    SendKeys('[]{{}{}}\\|;:\'\",<.>/?{Enter}')
    """
    holdKeys = ('WIN', 'LWIN', 'RWIN', 'SHIFT', 'LSHIFT', 'RSHIFT', 'CTRL', 'CONTROL', 'LCTRL', 'RCTRL', 'LCONTROL', 'LCONTROL', 'ALT', 'LALT', 'RALT')
    keys = []
    printKeys = []
    i = 0
    insertIndex = 0
    length = len(text)
    hold = False
    include = False
    lastKeyValue = None
    while True:
        if text[i] == '{':
            rindex = text.find('}', i)
            if rindex == i + 1:#{}}
                rindex = text.find('}', i + 2)
            if rindex == -1:
                raise ValueError('"{" or "{}" is not valid, use "{{}" for "{", use "{}}" for "}"')
            key = text[i + 1:rindex]
            key = [it for it in key.split(' ') if it]
            if not key:
                raise ValueError('"{}" is not valid, use "{{Space}}" or " " for " "'.format(text[i:rindex + 1]))
            if (len(key) == 2 and not key[1].isdigit()) or len(key) > 2:
                raise ValueError('"{}" is not valid'.format(text[i:rindex + 1]))
            upperKey = key[0].upper()
            count = 1
            if len(key) > 1:
                count = int(key[1])
            for j in range(count):
                if hold:
                    if upperKey in SpecialKeyNames:
                        keyValue = SpecialKeyNames[upperKey]
                        if type(lastKeyValue) == type(keyValue) and lastKeyValue == keyValue:
                            insertIndex += 1
                        printKeys.insert(insertIndex, (key[0], 'KeyDown | ExtendedKey'))
                        printKeys.insert(insertIndex + 1, (key[0], 'KeyUp | ExtendedKey'))
                        keys.insert(insertIndex, (keyValue, KeyboardEventFlag.KeyDown | KeyboardEventFlag.ExtendedKey))
                        keys.insert(insertIndex + 1, (keyValue, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey))
                        lastKeyValue = keyValue
                    elif key[0] in CharacterCodes:
                        keyValue = CharacterCodes[key[0]]
                        if type(lastKeyValue) == type(keyValue) and lastKeyValue == keyValue:
                            insertIndex += 1
                        printKeys.insert(insertIndex, (key[0], 'KeyDown | ExtendedKey'))
                        printKeys.insert(insertIndex + 1, (key[0], 'KeyUp | ExtendedKey'))
                        keys.insert(insertIndex, (keyValue, KeyboardEventFlag.KeyDown | KeyboardEventFlag.ExtendedKey))
                        keys.insert(insertIndex + 1, (keyValue, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey))
                        lastKeyValue = keyValue
                    else:
                        printKeys.insert(insertIndex, (key[0], 'UnicodeChar'))
                        keys.insert(insertIndex, (key[0], 'UnicodeChar'))
                        lastKeyValue = key[0]
                    if include:
                        insertIndex += 1
                    else:
                        if upperKey in holdKeys:
                            insertIndex += 1
                        else:
                            hold = False
                else:
                    if upperKey in SpecialKeyNames:
                        keyValue = SpecialKeyNames[upperKey]
                        printKeys.append((key[0], 'KeyDown | ExtendedKey'))
                        printKeys.append((key[0], 'KeyUp | ExtendedKey'))
                        keys.append((keyValue, KeyboardEventFlag.KeyDown | KeyboardEventFlag.ExtendedKey))
                        keys.append((keyValue, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey))
                        lastKeyValue = keyValue
                        if upperKey in holdKeys:
                            hold = True
                            insertIndex = len(keys) - 1
                        else:
                            hold = False
                    else:
                        printKeys.append((key[0], 'UnicodeChar'))
                        keys.append((key[0], 'UnicodeChar'))
                        lastKeyValue = key[0]
            i = rindex + 1
        elif text[i] == '(':
            if hold:
                include = True
            else:
                printKeys.append((text[i], 'UnicodeChar'))
                keys.append((text[i], 'UnicodeChar'))
                lastKeyValue = text[i]
            i += 1
        elif text[i] == ')':
            if hold:
                include = False
                hold = False
            else:
                printKeys.append((text[i], 'UnicodeChar'))
                keys.append((text[i], 'UnicodeChar'))
                lastKeyValue = text[i]
            i += 1
        else:
            if hold:
                if text[i] in CharacterCodes:
                    keyValue = CharacterCodes[text[i]]
                    if include and type(lastKeyValue) == type(keyValue) and lastKeyValue == keyValue:
                        insertIndex += 1
                    printKeys.insert(insertIndex, (text[i], 'KeyDown | ExtendedKey'))
                    printKeys.insert(insertIndex + 1, (text[i], 'KeyUp | ExtendedKey'))
                    keys.insert(insertIndex, (keyValue, KeyboardEventFlag.KeyDown | KeyboardEventFlag.ExtendedKey))
                    keys.insert(insertIndex + 1, (keyValue, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey))
                    lastKeyValue = keyValue
                else:
                    printKeys.append((text[i], 'UnicodeChar'))
                    keys.append((text[i], 'UnicodeChar'))
                    lastKeyValue = text[i]
                if include:
                    insertIndex += 1
                else:
                    hold = False
            else:
                printKeys.append((text[i], 'UnicodeChar'))
                keys.append((text[i], 'UnicodeChar'))
                lastKeyValue = text[i]
            i += 1
        if i >= length:
            break
    hotkeyInterval = 0.01
    for i, key in enumerate(keys):
        if key[1] == 'UnicodeChar':
            SendUnicodeChar(key[0], charMode)
            time.sleep(interval)
            if debug:
                Logger.ColorfullyWrite('<Color=DarkGreen>{}</Color>, sleep({})\n'.format(printKeys[i], interval), writeToFile=False)
        else:
            scanCode = _VKtoSC(key[0])
            keybd_event(key[0], scanCode, key[1], 0)
            if debug:
                Logger.Write(printKeys[i], ConsoleColor.DarkGreen, writeToFile=False)
            if i + 1 == len(keys):
                time.sleep(interval)
                if debug:
                    Logger.Write(', sleep({})\n'.format(interval), writeToFile=False)
            else:
                if key[1] & KeyboardEventFlag.KeyUp:
                    if keys[i + 1][1] == 'UnicodeChar' or keys[i + 1][1] & KeyboardEventFlag.KeyUp == 0:
                        time.sleep(interval)
                        if debug:
                            Logger.Write(', sleep({})\n'.format(interval), writeToFile=False)
                    else:
                        time.sleep(hotkeyInterval)  #must sleep for a while, otherwise combined keys may not be caught
                        if debug:
                            Logger.Write(', sleep({})\n'.format(hotkeyInterval), writeToFile=False)
                else:  #KeyboardEventFlag.KeyDown
                    time.sleep(hotkeyInterval)
                    if debug:
                        Logger.Write(', sleep({})\n'.format(hotkeyInterval), writeToFile=False)
    #make sure hold keys are not pressed
    #win = ctypes.windll.user32.GetAsyncKeyState(Keys.VK_LWIN)
    #ctrl = ctypes.windll.user32.GetAsyncKeyState(Keys.VK_CONTROL)
    #alt = ctypes.windll.user32.GetAsyncKeyState(Keys.VK_MENU)
    #shift = ctypes.windll.user32.GetAsyncKeyState(Keys.VK_SHIFT)
    #if win & 0x8000:
        #Logger.WriteLine('ERROR: WIN is pressed, it should not be pressed!', ConsoleColor.Red)
        #keybd_event(Keys.VK_LWIN, 0, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey, 0)
    #if ctrl & 0x8000:
        #Logger.WriteLine('ERROR: CTRL is pressed, it should not be pressed!', ConsoleColor.Red)
        #keybd_event(Keys.VK_CONTROL, 0, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey, 0)
    #if alt & 0x8000:
        #Logger.WriteLine('ERROR: ALT is pressed, it should not be pressed!', ConsoleColor.Red)
        #keybd_event(Keys.VK_MENU, 0, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey, 0)
    #if shift & 0x8000:
        #Logger.WriteLine('ERROR: SHIFT is pressed, it should not be pressed!', ConsoleColor.Red)
        #keybd_event(Keys.VK_SHIFT, 0, KeyboardEventFlag.KeyUp | KeyboardEventFlag.ExtendedKey, 0)
    time.sleep(waitTime)


class Logger:
    """
    Logger for print and log. Support for printing log with different colors on console.
    """
    FileName = '@AutomationLog.txt'
    _SelfFileName = os.path.split(__file__)[1]
    ColorNames = {
        "Black": ConsoleColor.Black,
        "DarkBlue": ConsoleColor.DarkBlue,
        "DarkGreen": ConsoleColor.DarkGreen,
        "DarkCyan": ConsoleColor.DarkCyan,
        "DarkRed": ConsoleColor.DarkRed,
        "DarkMagenta": ConsoleColor.DarkMagenta,
        "DarkYellow": ConsoleColor.DarkYellow,
        "Gray": ConsoleColor.Gray,
        "DarkGray": ConsoleColor.DarkGray,
        "Blue": ConsoleColor.Blue,
        "Green": ConsoleColor.Green,
        "Cyan": ConsoleColor.Cyan,
        "Red": ConsoleColor.Red,
        "Magenta": ConsoleColor.Magenta,
        "Yellow": ConsoleColor.Yellow,
        "White": ConsoleColor.White,
    }

    @staticmethod
    def SetLogFile(path: str) -> None:
        Logger.FileName = path

    @staticmethod
    def Write(log: Any, consoleColor: int = ConsoleColor.Default, writeToFile: bool = True, printToStdout: bool = True, logFile: str = None, printTruncateLen: int = 0) -> None:
        """
        log: any type.
        consoleColor: int, a value in class `ConsoleColor`, such as `ConsoleColor.DarkGreen`.
        writeToFile: bool.
        printToStdout: bool.
        logFile: str, log file path.
        printTruncateLen: int, if <= 0, log is not truncated when print.
        """
        # if not isinstance(log, str):
        #     log = str(log)
        # if printToStdout and sys.stdout:
        #     isValidColor = (consoleColor >= ConsoleColor.Black and consoleColor <= ConsoleColor.White)
        #     if isValidColor:
        #         SetConsoleColor(consoleColor)
        #     try:
        #         if printTruncateLen > 0 and len(log) > printTruncateLen:
        #             sys.stdout.write(log[:printTruncateLen] + '...')
        #         else:
        #             sys.stdout.write(log)
        #     except Exception as ex:
        #         SetConsoleColor(ConsoleColor.Red)
        #         isValidColor = True
        #         sys.stdout.write(ex.__class__.__name__ + ': can\'t print the log!')
        #         if log.endswith('\n'):
        #             sys.stdout.write('\n')
        #     if isValidColor:
        #         ResetConsoleColor()
        #     sys.stdout.flush()
        # if not writeToFile:
        #     return
        # fileName = logFile if logFile else Logger.FileName
        # fout = None
        # try:
        #     fout = open(fileName, 'a+', encoding='utf-8')
        #     fout.write(log)
        # except Exception as ex:
        #     if sys.stdout:
        #         sys.stdout.write(ex.__class__.__name__ + ': can\'t write the log!')
        # finally:
        #     if fout:
        #         fout.close()

    @staticmethod
    def WriteLine(log: Any, consoleColor: int = -1, writeToFile: bool = True, printToStdout: bool = True, logFile: str = None) -> None:
        """
        log: any type.
        consoleColor: int, a value in class `ConsoleColor`, such as `ConsoleColor.DarkGreen`.
        writeToFile: bool.
        printToStdout: bool.
        logFile: str, log file path.
        """
        Logger.Write('{}\n'.format(log), consoleColor, writeToFile, printToStdout, logFile)

    @staticmethod
    def ColorfullyWrite(log: str, consoleColor: int = -1, writeToFile: bool = True, printToStdout: bool = True, logFile: str = None) -> None:
        """
        log: str.
        consoleColor: int, a value in class `ConsoleColor`, such as `ConsoleColor.DarkGreen`.
        writeToFile: bool.
        printToStdout: bool.
        logFile: str, log file path.
        ColorfullyWrite('Hello <Color=Green>Green</Color> !!!'), color name must be in Logger.ColorNames.
        """
        text = []
        start = 0
        while True:
            index1 = log.find('<Color=', start)
            if index1 >= 0:
                if index1 > start:
                    text.append((log[start:index1], consoleColor))
                index2 = log.find('>', index1)
                colorName = log[index1+7:index2]
                index3 = log.find('</Color>', index2 + 1)
                text.append((log[index2 + 1:index3], Logger.ColorNames[colorName]))
                start = index3 + 8
            else:
                if start < len(log):
                    text.append((log[start:], consoleColor))
                break
        for t, c in text:
            Logger.Write(t, c, writeToFile, printToStdout, logFile)

    @staticmethod
    def ColorfullyWriteLine(log: str, consoleColor: int = -1, writeToFile: bool = True, printToStdout: bool = True, logFile: str = None) -> None:
        """
        log: str.
        consoleColor: int, a value in class `ConsoleColor`, such as `ConsoleColor.DarkGreen`.
        writeToFile: bool.
        printToStdout: bool.
        logFile: str, log file path.

        ColorfullyWriteLine('Hello <Color=Green>Green</Color> !!!'), color name must be in Logger.ColorNames.
        """
        Logger.ColorfullyWrite(log + '\n', consoleColor, writeToFile, printToStdout, logFile)

    @staticmethod
    def Log(log: Any = '', consoleColor: int = -1, writeToFile: bool = True, printToStdout: bool = True, logFile: str = None) -> None:
        """
        log: any type.
        consoleColor: int, a value in class `ConsoleColor`, such as `ConsoleColor.DarkGreen`.
        writeToFile: bool.
        printToStdout: bool.
        logFile: str, log file path.
        """
        frameCount = 1
        while True:
            frame = sys._getframe(frameCount)
            _, scriptFileName = os.path.split(frame.f_code.co_filename)
            if scriptFileName != Logger._SelfFileName:
                break
            frameCount += 1

        t = datetime.datetime.now()
        log = '{}-{:02}-{:02} {:02}:{:02}:{:02}.{:03} {}[{}] {} -> {}\n'.format(t.year, t.month, t.day,
            t.hour, t.minute, t.second, t.microsecond // 1000, scriptFileName, frame.f_lineno, frame.f_code.co_name, log)
        Logger.Write(log, consoleColor, writeToFile, printToStdout, logFile)

    @staticmethod
    def ColorfullyLog(log: str = '', consoleColor: int = -1, writeToFile: bool = True, printToStdout: bool = True, logFile: str = None) -> None:
        """
        log: any type.
        consoleColor: int, a value in class ConsoleColor, such as ConsoleColor.DarkGreen.
        writeToFile: bool.
        printToStdout: bool.
        logFile: str, log file path.

        ColorfullyLog('Hello <Color=Green>Green</Color> !!!'), color name must be in Logger.ColorNames
        """
        frameCount = 1
        while True:
            frame = sys._getframe(frameCount)
            _, scriptFileName = os.path.split(frame.f_code.co_filename)
            if scriptFileName != Logger._SelfFileName:
                break
            frameCount += 1

        t = datetime.datetime.now()
        log = '{}-{:02}-{:02} {:02}:{:02}:{:02}.{:03} {}[{}] {} -> {}\n'.format(t.year, t.month, t.day,
            t.hour, t.minute, t.second, t.microsecond // 1000, scriptFileName, frame.f_lineno, frame.f_code.co_name, log)
        Logger.ColorfullyWrite(log, consoleColor, writeToFile, printToStdout, logFile)

    @staticmethod
    def DeleteLog() -> None:
        """Delete log file."""
        if os.path.exists(Logger.FileName):
            os.remove(Logger.FileName)


class Bitmap:
    """
    A simple Bitmap class wraps Windows GDI+ Gdiplus::Bitmap, but may not have high efficiency.
    """
    def __init__(self, width: int = 0, height: int = 0):
        """
        Create a black bimap of size(width, height).
        """
        self._width = width
        self._height = height
        self._bitmap = 0
        if width > 0 and height > 0:
            self._bitmap = _DllClient.instance().dll.BitmapCreate(width, height)

    def __del__(self):
        self.Release()

    def _getsize(self) -> None:
        size = _DllClient.instance().dll.BitmapGetWidthAndHeight(self._bitmap)
        self._width = size & 0xFFFF
        self._height = size >> 16

    def Release(self) -> None:
        if self._bitmap:
            _DllClient.instance().dll.BitmapRelease(self._bitmap)
            self._bitmap = 0
            self._width = 0
            self._height = 0

    @property
    def Width(self) -> int:
        """
        Property Width.
        Return int.
        """
        return self._width

    @property
    def Height(self) -> int:
        """
        Property Height.
        Return int.
        """
        return self._height

    def FromHandle(self, hwnd: int, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> bool:
        """
        Capture a native window to Bitmap by its handle.
        hwnd: int, the handle of a native window.
        left: int.
        top: int.
        right: int.
        bottom: int.
        left, top, right and bottom are control's internal postion(from 0,0).
        Return bool, True if succeed otherwise False.
        """
        self.Release()
        root = GetRootControl()
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        left, top, right, bottom = left + rect.left, top + rect.top, right + rect.left, bottom + rect.top
        self._bitmap = _DllClient.instance().dll.BitmapFromWindow(root.NativeWindowHandle, left, top, right, bottom)
        self._getsize()
        return self._bitmap > 0

    def FromControl(self, control: 'Control', x: int = 0, y: int = 0, width: int = 0, height: int = 0) -> bool:
        """
        Capture a control to Bitmap.
        control: `Control` or its subclass.
        x: int.
        y: int.
        width: int.
        height: int.
        x, y: the point in control's internal position(from 0,0)
        width, height: image's width and height from x, y, use 0 for entire area,
        If width(or height) < 0, image size will be control's width(or height) - width(or height).
        Return bool, True if succeed otherwise False.
        """
        rect = control.BoundingRectangle
        while rect.width() == 0 or rect.height() == 0:
            #some controls maybe visible but their BoundingRectangle are all 0, capture its parent util valid
            control = control.GetParentControl()
            if not control:
                return False
            rect = control.BoundingRectangle
        if width <= 0:
            width = rect.width() + width
        if height <= 0:
            height = rect.height() + height
        handle = control.NativeWindowHandle
        if handle:
            left = x
            top = y
            right = left + width
            bottom = top + height
        else:
            while True:
                control = control.GetParentControl()
                handle = control.NativeWindowHandle
                if handle:
                    pRect = control.BoundingRectangle
                    left = rect.left - pRect.left + x
                    top = rect.top - pRect.top + y
                    right = left + width
                    bottom = top + height
                    break
        return self.FromHandle(handle, left, top, right, bottom)

    def FromFile(self, filePath: str) -> bool:
        """
        Load image from a file.
        filePath: str.
        Return bool, True if succeed otherwise False.
        """
        self.Release()
        self._bitmap = _DllClient.instance().dll.BitmapFromFile(ctypes.c_wchar_p(filePath))
        self._getsize()
        return self._bitmap > 0

    def ToFile(self, savePath: str) -> bool:
        """
        Save to a file.
        savePath: str, should end with .bmp, .jpg, .jpeg, .png, .gif, .tif, .tiff.
        Return bool, True if succeed otherwise False.
        """
        name, ext = os.path.splitext(savePath)
        extMap = {'.bmp': 'image/bmp'
                  , '.jpg': 'image/jpeg'
                  , '.jpeg': 'image/jpeg'
                  , '.gif': 'image/gif'
                  , '.tif': 'image/tiff'
                  , '.tiff': 'image/tiff'
                  , '.png': 'image/png'
                  }
        gdiplusImageFormat = extMap.get(ext.lower(), 'image/png')
        return bool(_DllClient.instance().dll.BitmapToFile(self._bitmap, ctypes.c_wchar_p(savePath), ctypes.c_wchar_p(gdiplusImageFormat)))

    def GetPixelColor(self, x: int, y: int) -> int:
        """
        Get color value of a pixel.
        x: int.
        y: int.
        Return int, argb color.
        b = argb & 0x0000FF
        g = (argb & 0x00FF00) >> 8
        r = (argb & 0xFF0000) >> 16
        a = (argb & 0xFF0000) >> 24
        """
        return _DllClient.instance().dll.BitmapGetPixel(self._bitmap, x, y)

    def SetPixelColor(self, x: int, y: int, argb: int) -> bool:
        """
        Set color value of a pixel.
        x: int.
        y: int.
        argb: int, color value.
        Return bool, True if succeed otherwise False.
        """
        return _DllClient.instance().dll.BitmapSetPixel(self._bitmap, x, y, argb)

    def GetPixelColorsHorizontally(self, x: int, y: int, count: int) -> ctypes.Array:
        """
        x: int.
        y: int.
        count: int.
        Return `ctypes.Array`, an iterable array of int values in argb form point x,y horizontally.
        """
        arrayType = ctypes.c_uint32 * count
        values = arrayType()
        _DllClient.instance().dll.BitmapGetPixelsHorizontally(ctypes.c_size_t(self._bitmap), x, y, values, count)
        return values

    def SetPixelColorsHorizontally(self, x: int, y: int, colors: Iterable[int]) -> bool:
        """
        Set pixel colors form x,y horizontally.
        x: int.
        y: int.
        colors: Iterable[int], an iterable list of int color values in argb.
        Return bool, True if succeed otherwise False.
        """
        count = len(colors)
        arrayType = ctypes.c_uint32 * count
        values = arrayType(*colors)
        return _DllClient.instance().dll.BitmapSetPixelsHorizontally(ctypes.c_size_t(self._bitmap), x, y, values, count)

    def GetPixelColorsVertically(self, x: int, y: int, count: int) -> ctypes.Array:
        """
        x: int.
        y: int.
        count: int.
        Return `ctypes.Array`, an iterable array of int values in argb form point x,y vertically.
        """
        arrayType = ctypes.c_uint32 * count
        values = arrayType()
        _DllClient.instance().dll.BitmapGetPixelsVertically(ctypes.c_size_t(self._bitmap), x, y, values, count)
        return values

    def SetPixelColorsVertically(self, x: int, y: int, colors: Iterable[int]) -> bool:
        """
        Set pixel colors form x,y vertically.
        x: int.
        y: int.
        colors: Iterable[int], an iterable list of int color values in argb.
        Return bool, True if succeed otherwise False.
        """
        count = len(colors)
        arrayType = ctypes.c_uint32 * count
        values = arrayType(*colors)
        return _DllClient.instance().dll.BitmapSetPixelsVertically(ctypes.c_size_t(self._bitmap), x, y, values, count)

    def GetPixelColorsOfRow(self, y: int) -> ctypes.Array:
        """
        y: int, row index.
        Return `ctypes.Array`, an iterable array of int values in argb of y row.
        """
        return self.GetPixelColorsOfRect(0, y, self.Width, 1)

    def GetPixelColorsOfColumn(self, x: int) -> ctypes.Array:
        """
        x: int, column index.
        Return `ctypes.Array`, an iterable array of int values in argb of x column.
        """
        return self.GetPixelColorsOfRect(x, 0, 1, self.Height)

    def GetPixelColorsOfRect(self, x: int, y: int, width: int, height: int) -> ctypes.Array:
        """
        x: int.
        y: int.
        width: int.
        height: int.
        Return `ctypes.Array`, an iterable array of int values in argb of the input rect.
        """
        arrayType = ctypes.c_uint32 * (width * height)
        values = arrayType()
        _DllClient.instance().dll.BitmapGetPixelsOfRect(ctypes.c_size_t(self._bitmap), x, y, width, height, values)
        return values

    def SetPixelColorsOfRect(self, x: int, y: int, width: int, height: int, colors: Iterable[int]) -> bool:
        """
        x: int.
        y: int.
        width: int.
        height: int.
        colors: Iterable[int], an iterable list of int values in argb, it's length must equal to width*height.
        Return bool.
        """
        arrayType = ctypes.c_uint32 * (width * height)
        values = arrayType(*colors)
        return bool(_DllClient.instance().dll.BitmapSetPixelsOfRect(ctypes.c_size_t(self._bitmap), x, y, width, height, values))

    def GetPixelColorsOfRects(self, rects: List[Tuple[int, int, int, int]]) -> List[ctypes.Array]:
        """
        rects: List[Tuple[int, int, int, int]], such as [(0,0,10,10), (10,10,20,20), (x,y,width,height)].
        Return List[ctypes.Array], a list whose elements are ctypes.Array which is an iterable array of int values in argb.
        """
        rects2 = [(x, y, x + width, y + height) for x, y, width, height in rects]
        left, top, right, bottom = zip(*rects2)
        left, top, right, bottom = min(left), min(top), max(right), max(bottom)
        width, height = right - left, bottom - top
        allColors = self.GetPixelColorsOfRect(left, top, width, height)
        colorsOfRects = []
        for x, y, w, h in rects:
            x -= left
            y -= top
            colors = []
            for row in range(h):
                colors.extend(allColors[(y + row) * width + x:(y + row) * width + x + w])
            colorsOfRects.append(colors)
        return colorsOfRects

    def GetAllPixelColors(self) -> ctypes.Array:
        """
        Return `ctypes.Array`, an iterable array of int values in argb.
        """
        return self.GetPixelColorsOfRect(0, 0, self.Width, self.Height)

    def GetSubBitmap(self, x: int, y: int, width: int, height: int) -> 'Bitmap':
        """
        x: int.
        y: int.
        width: int.
        height: int.
        Return `Bitmap`, a sub bitmap of the input rect.
        """
        colors = self.GetPixelColorsOfRect(x, y, width, height)
        bitmap = Bitmap(width, height)
        bitmap.SetPixelColorsOfRect(0, 0, width, height, colors)
        return bitmap


_PatternIdInterfaces = None
def GetPatternIdInterface(patternId: int):
    """
    Get pattern COM interface by pattern id.
    patternId: int, a value in class `PatternId`.
    Return comtypes._cominterface_meta.
    """
    global _PatternIdInterfaces
    if not _PatternIdInterfaces:
        _PatternIdInterfaces = {
            # PatternId.AnnotationPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationAnnotationPattern,
            # PatternId.CustomNavigationPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationCustomNavigationPattern,
            PatternId.DockPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationDockPattern,
            # PatternId.DragPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationDragPattern,
            # PatternId.DropTargetPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationDropTargetPattern,
            PatternId.ExpandCollapsePattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationExpandCollapsePattern,
            PatternId.GridItemPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationGridItemPattern,
            PatternId.GridPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationGridPattern,
            PatternId.InvokePattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationInvokePattern,
            PatternId.ItemContainerPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationItemContainerPattern,
            PatternId.LegacyIAccessiblePattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationLegacyIAccessiblePattern,
            PatternId.MultipleViewPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationMultipleViewPattern,
            # PatternId.ObjectModelPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationObjectModelPattern,
            PatternId.RangeValuePattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationRangeValuePattern,
            PatternId.ScrollItemPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationScrollItemPattern,
            PatternId.ScrollPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationScrollPattern,
            PatternId.SelectionItemPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationSelectionItemPattern,
            PatternId.SelectionPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationSelectionPattern,
            # PatternId.SpreadsheetItemPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationSpreadsheetItemPattern,
            # PatternId.SpreadsheetPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationSpreadsheetPattern,
            # PatternId.StylesPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationStylesPattern,
            PatternId.SynchronizedInputPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationSynchronizedInputPattern,
            PatternId.TableItemPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationTableItemPattern,
            PatternId.TablePattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationTablePattern,
            # PatternId.TextChildPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationTextChildPattern,
            # PatternId.TextEditPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationTextEditPattern,
            PatternId.TextPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationTextPattern,
            # PatternId.TextPattern2: _AutomationClient.instance().UIAutomationCore.IUIAutomationTextPattern2,
            PatternId.TogglePattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationTogglePattern,
            PatternId.TransformPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationTransformPattern,
            # PatternId.TransformPattern2: _AutomationClient.instance().UIAutomationCore.IUIAutomationTransformPattern2,
            PatternId.ValuePattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationValuePattern,
            PatternId.VirtualizedItemPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationVirtualizedItemPattern,
            PatternId.WindowPattern: _AutomationClient.instance().UIAutomationCore.IUIAutomationWindowPattern,
        }
        debug = False
        #the following patterns doesn't exist on Windows 7 or lower
        try:
            _PatternIdInterfaces[PatternId.AnnotationPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationAnnotationPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have AnnotationPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.CustomNavigationPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationCustomNavigationPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have CustomNavigationPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.DragPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationDragPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have DragPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.DropTargetPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationDropTargetPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have DropTargetPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.ObjectModelPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationObjectModelPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have ObjectModelPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.SpreadsheetItemPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationSpreadsheetItemPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have SpreadsheetItemPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.SpreadsheetPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationSpreadsheetPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have SpreadsheetPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.StylesPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationStylesPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have StylesPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.TextChildPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationTextChildPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have TextChildPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.TextEditPattern] = _AutomationClient.instance().UIAutomationCore.IUIAutomationTextEditPattern
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have TextEditPattern.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.TextPattern2] = _AutomationClient.instance().UIAutomationCore.IUIAutomationTextPattern2
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have TextPattern2.', ConsoleColor.Yellow)
        try:
            _PatternIdInterfaces[PatternId.TransformPattern2] = _AutomationClient.instance().UIAutomationCore.IUIAutomationTransformPattern2
        except:
            if debug: Logger.WriteLine('UIAutomationCore does not have TransformPattern2.', ConsoleColor.Yellow)
    return _PatternIdInterfaces[patternId]


"""
Control Pattern Mapping for UI Automation Clients.
Refer https://docs.microsoft.com/en-us/previous-versions//dd319586(v=vs.85)
"""


class AnnotationPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationannotationpattern"""
        self.pattern = pattern

    @property
    def AnnotationTypeId(self) -> int:
        """
        Property AnnotationTypeId.
        Call IUIAutomationAnnotationPattern::get_CurrentAnnotationTypeId.
        Return int, a value in class `AnnotationType`.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationannotationpattern-get_currentannotationtypeid
        """
        return self.pattern.CurrentAnnotationTypeId

    @property
    def AnnotationTypeName(self) -> str:
        """
        Property AnnotationTypeName.
        Call IUIAutomationAnnotationPattern::get_CurrentAnnotationTypeName.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationannotationpattern-get_currentannotationtypename
        """
        return self.pattern.CurrentAnnotationTypeName

    @property
    def Author(self) -> str:
        """
        Property Author.
        Call IUIAutomationAnnotationPattern::get_CurrentAuthor.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationannotationpattern-get_currentauthor
        """
        return self.pattern.CurrentAuthor

    @property
    def DateTime(self) -> str:
        """
        Property DateTime.
        Call IUIAutomationAnnotationPattern::get_CurrentDateTime.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationannotationpattern-get_currentdatetime
        """
        return self.pattern.CurrentDateTime

    @property
    def Target(self) -> 'Control':
        """
        Property Target.
        Call IUIAutomationAnnotationPattern::get_CurrentTarget.
        Return `Control` subclass, the element that is being annotated.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationannotationpattern-get_currenttarget
        """
        ele = self.pattern.CurrentTarget
        return Control.CreateControlFromElement(ele)


class CustomNavigationPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationcustomnavigationpattern"""
        self.pattern = pattern

    def Navigate(self, direction: int) -> 'Control':
        """
        Call IUIAutomationCustomNavigationPattern::Navigate.
        Get the next control in the specified direction within the logical UI tree.
        direction: int, a value in class `NavigateDirection`.
        Return `Control` subclass or None.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationcustomnavigationpattern-navigate
        """
        ele = self.pattern.Navigate(direction)
        return Control.CreateControlFromElement(ele)


class DockPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationdockpattern"""
        self.pattern = pattern

    @property
    def DockPosition(self) -> int:
        """
        Property DockPosition.
        Call IUIAutomationDockPattern::get_CurrentDockPosition.
        Return int, a value in class `DockPosition`.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdockpattern-get_currentdockposition
        """
        return self.pattern.CurrentDockPosition

    def SetDockPosition(self, dockPosition: int, waitTime: float = OPERATION_WAIT_TIME) -> int:
        """
        Call IUIAutomationDockPattern::SetDockPosition.
        dockPosition: int, a value in class `DockPosition`.
        waitTime: float.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdockpattern-setdockposition
        """
        ret = self.pattern.SetDockPosition(dockPosition)
        time.sleep(waitTime)
        return ret


class DragPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationdragpattern"""
        self.pattern = pattern

    @property
    def DropEffect(self) -> str:
        """
        Property DropEffect.
        Call IUIAutomationDragPattern::get_CurrentDropEffect.
        Return str, a localized string that indicates what happens
                    when the user drops this element as part of a drag-drop operation.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdragpattern-get_currentdropeffect
        """
        return self.pattern.CurrentDropEffect

    @property
    def DropEffects(self) -> List[str]:
        """
        Property DropEffects.
        Call IUIAutomationDragPattern::get_CurrentDropEffects, todo SAFEARRAY.
        Return List[str], a list of localized strings that enumerate the full set of effects
                     that can happen when this element as part of a drag-and-drop operation.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdragpattern-get_currentdropeffects
        """
        return self.pattern.CurrentDropEffects

    @property
    def IsGrabbed(self) -> bool:
        """
        Property IsGrabbed.
        Call IUIAutomationDragPattern::get_CurrentIsGrabbed.
        Return bool, indicates whether the user has grabbed this element as part of a drag-and-drop operation.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdragpattern-get_currentisgrabbed
        """
        return bool(self.pattern.CurrentIsGrabbed)

    def GetGrabbedItems(self) -> List['Control']:
        """
        Call IUIAutomationDragPattern::GetCurrentGrabbedItems.
        Return List[Control], a list of `Control` subclasses that represent the full set of items
                     that the user is dragging as part of a drag operation.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdragpattern-getcurrentgrabbeditems
        """
        eleArray = self.pattern.GetCurrentGrabbedItems()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []


class DropTargetPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationdroptargetpattern"""
        self.pattern = pattern

    @property
    def DropTargetEffect(self) -> str:
        """
        Property DropTargetEffect.
        Call IUIAutomationDropTargetPattern::get_CurrentDropTargetEffect.
        Return str, a localized string that describes what happens
                    when the user drops the grabbed element on this drop target.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdragpattern-get_currentdroptargeteffect
        """
        return self.pattern.CurrentDropTargetEffect

    @property
    def DropTargetEffects(self) -> List[str]:
        """
        Property DropTargetEffects.
        Call IUIAutomationDropTargetPattern::get_CurrentDropTargetEffects, todo SAFEARRAY.
        Return List[str], a list of localized strings that enumerate the full set of effects
                     that can happen when the user drops a grabbed element on this drop target
                     as part of a drag-and-drop operation.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationdragpattern-get_currentdroptargeteffects
        """
        return self.pattern.CurrentDropTargetEffects


class ExpandCollapsePattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationexpandcollapsepattern"""
        self.pattern = pattern

    @property
    def ExpandCollapseState(self) -> int:
        """
        Property ExpandCollapseState.
        Call IUIAutomationExpandCollapsePattern::get_CurrentExpandCollapseState.
        Return int, a value in class ExpandCollapseState.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationexpandcollapsepattern-get_currentexpandcollapsestate
        """
        return self.pattern.CurrentExpandCollapseState

    def Collapse(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationExpandCollapsePattern::Collapse.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationexpandcollapsepattern-collapse
        """
        ret = self.pattern.Collapse() == S_OK
        time.sleep(waitTime)
        return ret

    def Expand(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationExpandCollapsePattern::Expand.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationexpandcollapsepattern-expand
        """
        ret = self.pattern.Expand() == S_OK
        time.sleep(waitTime)
        return ret


class GridItemPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationgriditempattern"""
        self.pattern = pattern

    @property
    def Column(self) -> int:
        """
        Property Column.
        Call IUIAutomationGridItemPattern::get_CurrentColumn.
        Return int, the zero-based index of the column that contains the item.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgriditempattern-get_currentcolumn
        """
        return self.pattern.CurrentColumn

    @property
    def ColumnSpan(self) -> int:
        """
        Property ColumnSpan.
        Call IUIAutomationGridItemPattern::get_CurrentColumnSpan.
        Return int, the number of columns spanned by the grid item.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgriditempattern-get_currentcolumnspan
        """
        return self.pattern.CurrentColumnSpan

    @property
    def ContainingGrid(self) -> 'Control':
        """
        Property ContainingGrid.
        Call IUIAutomationGridItemPattern::get_CurrentContainingGrid.
        Return `Control` subclass, the element that contains the grid item.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgriditempattern-get_currentcontaininggrid
        """
        return Control.CreateControlFromElement(self.pattern.CurrentContainingGrid)

    @property
    def Row(self) -> int:
        """
        Property Row.
        Call IUIAutomationGridItemPattern::get_CurrentRow.
        Return int, the zero-based index of the row that contains the grid item.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgriditempattern-get_currentrow
        """
        return self.pattern.CurrentRow

    @property
    def RowSpan(self) -> int:
        """
        Property RowSpan.
        Call IUIAutomationGridItemPattern::get_CurrentRowSpan.
        Return int, the number of rows spanned by the grid item.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgriditempattern-get_currentrowspan
        """
        return self.pattern.CurrentRowSpan


class GridPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationgridpattern"""
        self.pattern = pattern

    @property
    def ColumnCount(self) -> int:
        """
        Property ColumnCount.
        Call IUIAutomationGridPattern::get_CurrentColumnCount.
        Return int, the number of columns in the grid.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgridpattern-get_currentcolumncount
        """
        return self.pattern.CurrentColumnCount

    @property
    def RowCount(self) -> int:
        """
        Property RowCount.
        Call IUIAutomationGridPattern::get_CurrentRowCount.
        Return int, the number of rows in the grid.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgridpattern-get_currentrowcount
        """
        return self.pattern.CurrentRowCount

    def GetItem(self) -> 'Control':
        """
        Call IUIAutomationGridPattern::GetItem.
        Return `Control` subclass, a control representing an item in the grid.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationgridpattern-getitem
        """
        return Control.CreateControlFromElement(self.pattern.GetItem())

class InvokePattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationinvokepattern"""
        self.pattern = pattern

    def Invoke(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationInvokePattern::Invoke.
        Invoke the action of a control, such as a button click.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationinvokepattern-invoke
        """
        ret = self.pattern.Invoke() == S_OK
        time.sleep(waitTime)
        return ret


class ItemContainerPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationitemcontainerpattern"""
        self.pattern = pattern

    def FindItemByProperty(self, control: 'Control', propertyId: int, propertyValue) -> 'Control':
        """
        Call IUIAutomationItemContainerPattern::FindItemByProperty.
        control: `Control` or its subclass.
        propertyValue: COM VARIANT according to propertyId? todo.
        propertyId: int, a value in class `PropertyId`.
        Return `Control` subclass, a control within a containing element, based on a specified property value.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationitemcontainerpattern-finditembyproperty
        """
        ele = self.pattern.FindItemByProperty(control.Element, propertyId, propertyValue)
        return Control.CreateControlFromElement(ele)


class LegacyIAccessiblePattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationlegacyiaccessiblepattern"""
        self.pattern = pattern

    @property
    def ChildId(self) -> int:
        """
        Property ChildId.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentChildId.
        Return int, the Microsoft Active Accessibility child identifier for the element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentchildid
        """
        return self.pattern.CurrentChildId

    @property
    def DefaultAction(self) -> str:
        """
        Property DefaultAction.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentDefaultAction.
        Return str, the Microsoft Active Accessibility current default action for the element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentdefaultaction
        """
        return self.pattern.CurrentDefaultAction

    @property
    def Description(self) -> str:
        """
        Property Description.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentDescription.
        Return str, the Microsoft Active Accessibility description of the element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentdescription
        """
        return self.pattern.CurrentDescription

    @property
    def Help(self) -> str:
        """
        Property Help.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentHelp.
        Return str, the Microsoft Active Accessibility help string for the element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currenthelp
        """
        return self.pattern.CurrentHelp

    @property
    def KeyboardShortcut(self) -> str:
        """
        Property KeyboardShortcut.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentKeyboardShortcut.
        Return str, the Microsoft Active Accessibility keyboard shortcut property for the element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentkeyboardshortcut
        """
        return self.pattern.CurrentKeyboardShortcut

    @property
    def Name(self) -> str:
        """
        Property Name.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentName.
        Return str, the Microsoft Active Accessibility name property of the element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentname
        """
        return self.pattern.CurrentName or ''    # CurrentName may be None

    @property
    def Role(self) -> int:
        """
        Property Role.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentRole.
        Return int, a value in calss `AccessibleRole`, the Microsoft Active Accessibility role identifier.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentrole
        """
        return self.pattern.CurrentRole

    @property
    def State(self) -> int:
        """
        Property State.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentState.
        Return int, a value in calss `AccessibleState`, the Microsoft Active Accessibility state identifier.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentstate
        """
        return self.pattern.CurrentState

    @property
    def Value(self) -> str:
        """
        Property Value.
        Call IUIAutomationLegacyIAccessiblePattern::get_CurrentValue.
        Return str, the Microsoft Active Accessibility value property.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-get_currentvalue
        """
        return self.pattern.CurrentValue

    def DoDefaultAction(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationLegacyIAccessiblePattern::DoDefaultAction.
        Perform the Microsoft Active Accessibility default action for the element.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-dodefaultaction
        """
        ret = self.pattern.DoDefaultAction() == S_OK
        time.sleep(waitTime)
        return ret

    def GetSelection(self) -> List['Control']:
        """
        Call IUIAutomationLegacyIAccessiblePattern::GetCurrentSelection.
        Return List[Control], a list of `Control` subclasses,
                     the Microsoft Active Accessibility property that identifies the selected children of this element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-getcurrentselection
        """
        eleArray = self.pattern.GetCurrentSelection()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []

    def GetIAccessible(self):
        """
        Call IUIAutomationLegacyIAccessiblePattern::GetIAccessible, todo.
        Return an IAccessible object that corresponds to the Microsoft UI Automation element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-getiaccessible
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/oleacc/nn-oleacc-iaccessible
        """
        return self.pattern.GetIAccessible()

    def Select(self, flagsSelect: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationLegacyIAccessiblePattern::Select.
        Perform a Microsoft Active Accessibility selection.
        flagsSelect: int, a value in `AccessibleSelection`.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-select
        """
        ret = self.pattern.Select(flagsSelect) == S_OK
        time.sleep(waitTime)
        return ret

    def SetValue(self, value: str, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationLegacyIAccessiblePattern::SetValue.
        Set the Microsoft Active Accessibility value property for the element.
        value: str.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationlegacyiaccessiblepattern-setvalue
        """
        ret = self.pattern.SetValue(value) == S_OK
        time.sleep(waitTime)
        return ret


class MultipleViewPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationmultipleviewpattern"""
        self.pattern = pattern

    @property
    def CurrentView(self) -> int:
        """
        Property CurrentView.
        Call IUIAutomationMultipleViewPattern::get_CurrentCurrentView.
        Return int, the control-specific identifier of the current view of the control.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationmultipleviewpattern-get_currentcurrentview
        """
        return self.pattern.CurrentCurrentView

    def GetSupportedViews(self) -> List[int]:
        """
        Call IUIAutomationMultipleViewPattern::GetCurrentSupportedViews, todo.
        Return List[int], a list of int, control-specific view identifiers.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationmultipleviewpattern-getcurrentsupportedviews
        """
        return self.pattern.GetCurrentSupportedViews()

    def GetViewName(self, view: int) -> str:
        """
        Call IUIAutomationMultipleViewPattern::GetViewName.
        view: int, the control-specific view identifier.
        Return str, the name of a control-specific view.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationmultipleviewpattern-getviewname
        """
        return self.pattern.GetViewName(view)

    def SetView(self, view: int) -> bool:
        """
        Call IUIAutomationMultipleViewPattern::SetCurrentView.
        Set the view of the control.
        view: int, the control-specific view identifier.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationmultipleviewpattern-setcurrentview
        """
        return self.pattern.SetCurrentView(view) == S_OK


class ObjectModelPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationobjectmodelpattern"""
        self.pattern = pattern

    def GetUnderlyingObjectModel(self) -> ctypes.POINTER(comtypes.IUnknown):
        """
        Call IUIAutomationObjectModelPattern::GetUnderlyingObjectModel, todo.
        Return `ctypes.POINTER(comtypes.IUnknown)`, an interface used to access the underlying object model of the provider.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationobjectmodelpattern-getunderlyingobjectmodel
        """
        return self.pattern.GetUnderlyingObjectModel()


class RangeValuePattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationrangevaluepattern"""
        self.pattern = pattern

    @property
    def IsReadOnly(self) -> bool:
        """
        Property IsReadOnly.
        Call IUIAutomationRangeValuePattern::get_CurrentIsReadOnly.
        Return bool, indicates whether the value of the element can be changed.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationrangevaluepattern-get_currentisreadonly
        """
        return self.pattern.CurrentIsReadOnly

    @property
    def LargeChange(self) -> float:
        """
        Property LargeChange.
        Call IUIAutomationRangeValuePattern::get_CurrentLargeChange.
        Return float, the value that is added to or subtracted from the value of the control
                      when a large change is made, such as when the PAGE DOWN key is pressed.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationrangevaluepattern-get_currentlargechange
        """
        return self.pattern.CurrentLargeChange

    @property
    def Maximum(self) -> float:
        """
        Property Maximum.
        Call IUIAutomationRangeValuePattern::get_CurrentMaximum.
        Return float, the maximum value of the control.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationrangevaluepattern-get_currentmaximum
        """
        return self.pattern.CurrentMaximum

    @property
    def Minimum(self) -> float:
        """
        Property Minimum.
        Call IUIAutomationRangeValuePattern::get_CurrentMinimum.
        Return float, the minimum value of the control.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationrangevaluepattern-get_currentminimum
        """
        return self.pattern.CurrentMinimum

    @property
    def SmallChange(self) -> float:
        """
        Property SmallChange.
        Call IUIAutomationRangeValuePattern::get_CurrentSmallChange.
        Return float, the value that is added to or subtracted from the value of the control
                      when a small change is made, such as when an arrow key is pressed.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationrangevaluepattern-get_currentsmallchange
        """
        return self.pattern.CurrentSmallChange

    @property
    def Value(self) -> float:
        """
        Property Value.
        Call IUIAutomationRangeValuePattern::get_CurrentValue.
        Return float, the value of the control.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationrangevaluepattern-get_currentvalue
        """
        return self.pattern.CurrentValue

    def SetValue(self, value: float, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationRangeValuePattern::SetValue.
        Set the value of the control.
        value: int.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationrangevaluepattern-setvalue
        """
        ret = self.pattern.SetValue(value) == S_OK
        time.sleep(waitTime)
        return ret


class ScrollItemPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationscrollitempattern"""
        self.pattern = pattern

    def ScrollIntoView(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationScrollItemPattern::ScrollIntoView.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollitempattern-scrollintoview
        """
        ret = self.pattern.ScrollIntoView() == S_OK
        time.sleep(waitTime)
        return ret


class ScrollPattern():
    NoScrollValue = -1
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationscrollpattern"""
        self.pattern = pattern

    @property
    def HorizontallyScrollable(self) -> bool:
        """
        Property HorizontallyScrollable.
        Call IUIAutomationScrollPattern::get_CurrentHorizontallyScrollable.
        Return bool, indicates whether the element can scroll horizontally.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currenthorizontallyscrollable
        """
        return bool(self.pattern.CurrentHorizontallyScrollable)

    @property
    def HorizontalScrollPercent(self) -> float:
        """
        Property HorizontalScrollPercent.
        Call IUIAutomationScrollPattern::get_CurrentHorizontalScrollPercent.
        Return float, the horizontal scroll position.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currenthorizontalscrollpercent
        """
        return self.pattern.CurrentHorizontalScrollPercent

    @property
    def HorizontalViewSize(self) -> float:
        """
        Property HorizontalViewSize.
        Call IUIAutomationScrollPattern::get_CurrentHorizontalViewSize.
        Return float, the horizontal size of the viewable region of a scrollable element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currenthorizontalviewsize
        """
        return self.pattern.CurrentHorizontalViewSize

    @property
    def VerticallyScrollable(self) -> bool:
        """
        Property VerticallyScrollable.
        Call IUIAutomationScrollPattern::get_CurrentVerticallyScrollable.
        Return bool, indicates whether the element can scroll vertically.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currentverticallyscrollable
        """
        return bool(self.pattern.CurrentVerticallyScrollable)

    @property
    def VerticalScrollPercent(self) -> float:
        """
        Property VerticalScrollPercent.
        Call IUIAutomationScrollPattern::get_CurrentVerticalScrollPercent.
        Return float, the vertical scroll position.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currentverticalscrollpercent
        """
        return self.pattern.CurrentVerticalScrollPercent

    @property
    def VerticalViewSize(self) -> float:
        """
        Property VerticalViewSize.
        Call IUIAutomationScrollPattern::get_CurrentVerticalViewSize.
        Return float, the vertical size of the viewable region of a scrollable element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currentverticalviewsize
        """
        return self.pattern.CurrentVerticalViewSize

    def Scroll(self, horizontalAmount: int, verticalAmount: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationScrollPattern::Scroll.
        Scroll the visible region of the content area horizontally and vertically.
        horizontalAmount: int, a value in ScrollAmount.
        verticalAmount: int, a value in ScrollAmount.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-scroll
        """
        ret = self.pattern.Scroll(horizontalAmount, verticalAmount) == S_OK
        time.sleep(waitTime)
        return ret

    def SetScrollPercent(self, horizontalPercent: float, verticalPercent: float, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationScrollPattern::SetScrollPercent.
        Set the horizontal and vertical scroll positions as a percentage of the total content area within the UI Automation element.
        horizontalPercent: float or int, a value in [0, 100] or ScrollPattern.NoScrollValue(-1) if no scroll.
        verticalPercent: float or int, a value  in [0, 100] or ScrollPattern.NoScrollValue(-1) if no scroll.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-setscrollpercent
        """
        ret = self.pattern.SetScrollPercent(horizontalPercent, verticalPercent) == S_OK
        time.sleep(waitTime)
        return ret


class SelectionItemPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationselectionitempattern"""
        self.pattern = pattern

    def AddToSelection(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationSelectionItemPattern::AddToSelection.
        Add the current element to the collection of selected items.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionitempattern-addtoselection
        """
        ret = self.pattern.AddToSelection() == S_OK
        time.sleep(waitTime)
        return ret

    @property
    def IsSelected(self) -> bool:
        """
        Property IsSelected.
        Call IUIAutomationScrollPattern::get_CurrentIsSelected.
        Return bool, indicates whether this item is selected.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currentisselected
        """
        return bool(self.pattern.CurrentIsSelected)

    @property
    def SelectionContainer(self) -> 'Control':
        """
        Property SelectionContainer.
        Call IUIAutomationScrollPattern::get_CurrentSelectionContainer.
        Return `Control` subclass, the element that supports IUIAutomationSelectionPattern and acts as the container for this item.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationscrollpattern-get_currentselectioncontainer
        """
        ele = self.pattern.CurrentSelectionContainer
        return Control.CreateControlFromElement(ele)

    def RemoveFromSelection(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationSelectionItemPattern::RemoveFromSelection.
        Remove this element from the selection.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionitempattern-removefromselection
        """
        ret = self.pattern.RemoveFromSelection() == S_OK
        time.sleep(waitTime)
        return ret

    def Select(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationSelectionItemPattern::Select.
        Clear any selected items and then select the current element.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionitempattern-select
        """
        ret = self.pattern.Select() == S_OK
        time.sleep(waitTime)
        return ret


class SelectionPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationselectionpattern"""
        self.pattern = pattern

    @property
    def CanSelectMultiple(self) -> bool:
        """
        Property CanSelectMultiple.
        Call IUIAutomationSelectionPattern::get_CurrentCanSelectMultiple.
        Return bool, indicates whether more than one item in the container can be selected at one time.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionpattern-get_currentcanselectmultiple
        """
        return bool(self.pattern.CurrentCanSelectMultiple)

    @property
    def IsSelectionRequired(self) -> bool:
        """
        Property IsSelectionRequired.
        Call IUIAutomationSelectionPattern::get_CurrentIsSelectionRequired.
        Return bool, indicates whether at least one item must be selected at all times.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionpattern-get_currentisselectionrequired
        """
        return bool(self.pattern.CurrentIsSelectionRequired)

    def GetSelection(self) -> List['Control']:
        """
        Call IUIAutomationSelectionPattern::GetCurrentSelection.
        Return List[Control], a list of `Control` subclasses, the selected elements in the container..
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionpattern-getcurrentselection
        """
        eleArray = self.pattern.GetCurrentSelection()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []


class SpreadsheetItemPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationspreadsheetitempattern"""
        self.pattern = pattern

    @property
    def Formula(self) -> str:
        """
        Property Formula.
        Call IUIAutomationSpreadsheetItemPattern::get_CurrentFormula.
        Return str, the formula for this cell.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationspreadsheetitempattern-get_currentformula
        """
        return self.pattern.CurrentFormula

    def GetAnnotationObjects(self) -> List['Control']:
        """
        Call IUIAutomationSelectionPattern::GetCurrentAnnotationObjects.
        Return List[Control], a list of `Control` subclasses representing the annotations associated with this spreadsheet cell.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationspreadsheetitempattern-getcurrentannotationobjects
        """
        eleArray = self.pattern.GetCurrentAnnotationObjects()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []

    def GetAnnotationTypes(self) -> List[int]:
        """
        Call IUIAutomationSelectionPattern::GetCurrentAnnotationTypes.
        Return List[int], a list of int values in class `AnnotationType`,
                     indicating the types of annotations that are associated with this spreadsheet cell.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionpattern-getcurrentannotationtypes
        """
        return self.pattern.GetCurrentAnnotationTypes()


class SpreadsheetPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationspreadsheetpattern"""
        self.pattern = pattern

    def GetItemByName(self, name: str) -> 'Control':
        """
        Call IUIAutomationSpreadsheetPattern::GetItemByName.
        name: str.
        Return `Control` subclass or None, represents the spreadsheet cell that has the specified name..
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationspreadsheetpattern-getitembyname
        """
        ele = self.pattern.GetItemByName(name)
        return Control.CreateControlFromElement(element=ele)


class StylesPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationstylespattern"""
        self.pattern = pattern

    @property
    def ExtendedProperties(self) -> str:
        """
        Property ExtendedProperties.
        Call IUIAutomationStylesPattern::get_CurrentExtendedProperties.
        Return str, a localized string that contains the list of extended properties for an element in a document.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationstylespattern-get_currentextendedproperties
        """
        return self.pattern.CurrentExtendedProperties

    @property
    def FillColor(self) -> int:
        """
        Property FillColor.
        Call IUIAutomationStylesPattern::get_CurrentFillColor.
        Return int, the fill color of an element in a document.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationstylespattern-get_currentfillcolor
        """
        return self.pattern.CurrentFillColor

    @property
    def FillPatternColor(self) -> int:
        """
        Property FillPatternColor.
        Call IUIAutomationStylesPattern::get_CurrentFillPatternColor.
        Return int, the color of the pattern used to fill an element in a document.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationstylespattern-get_currentfillpatterncolor
        """
        return self.pattern.CurrentFillPatternColor

    @property
    def Shape(self) -> str:
        """
        Property Shape.
        Call IUIAutomationStylesPattern::get_CurrentShape.
        Return str, the shape of an element in a document.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationstylespattern-get_currentshape
        """
        return self.pattern.CurrentShape

    @property
    def StyleId(self) -> int:
        """
        Property StyleId.
        Call IUIAutomationStylesPattern::get_CurrentStyleId.
        Return int, a value in class `StyleId`, the visual style associated with an element in a document.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationstylespattern-get_currentstyleid
        """
        return self.pattern.CurrentStyleId

    @property
    def StyleName(self) -> str:
        """
        Property StyleName.
        Call IUIAutomationStylesPattern::get_CurrentStyleName.
        Return str, the name of the visual style associated with an element in a document.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationstylespattern-get_currentstylename
        """
        return self.pattern.CurrentStyleName


class SynchronizedInputPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationsynchronizedinputpattern"""
        self.pattern = pattern

    def Cancel(self) -> bool:
        """
        Call IUIAutomationSynchronizedInputPattern::Cancel.
        Cause the Microsoft UI Automation provider to stop listening for mouse or keyboard input.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationsynchronizedinputpattern-cancel
        """
        return self.pattern.Cancel() == S_OK

    def StartListening(self) -> bool:
        """
        Call IUIAutomationSynchronizedInputPattern::StartListening.
        Cause the Microsoft UI Automation provider to start listening for mouse or keyboard input.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationsynchronizedinputpattern-startlistening
        """
        return self.pattern.StartListening() == S_OK


class TableItemPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtableitempattern"""
        self.pattern = pattern

    def GetColumnHeaderItems(self) -> List['Control']:
        """
        Call IUIAutomationTableItemPattern::GetCurrentColumnHeaderItems.
        Return List[Control], a list of `Control` subclasses, the column headers associated with a table item or cell.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtableitempattern-getcurrentcolumnheaderitems
        """
        eleArray = self.pattern.GetCurrentColumnHeaderItems()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []

    def GetRowHeaderItems(self) -> List['Control']:
        """
        Call IUIAutomationTableItemPattern::GetCurrentRowHeaderItems.
        Return List[Control], a list of `Control` subclasses, the row headers associated with a table item or cell.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtableitempattern-getcurrentrowheaderitems
        """
        eleArray = self.pattern.GetCurrentRowHeaderItems()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []


class TablePattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtablepattern"""
        self.pattern = pattern

    @property
    def RowOrColumnMajor(self) -> int:
        """
        Property RowOrColumnMajor.
        Call IUIAutomationTablePattern::get_CurrentRowOrColumnMajor.
        Return int, a value in class `RowOrColumnMajor`, the primary direction of traversal for the table.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtablepattern-get_currentroworcolumnmajor
        """
        return self.pattern.CurrentRowOrColumnMajor

    def GetColumnHeaders(self) -> List['Control']:
        """
        Call IUIAutomationTablePattern::GetCurrentColumnHeaders.
        Return List[Control], a list of `Control` subclasses, representing all the column headers in a table..
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtablepattern-getcurrentcolumnheaders
        """
        eleArray = self.pattern.GetCurrentColumnHeaders()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []

    def GetRowHeaders(self) -> List['Control']:
        """
        Call IUIAutomationTablePattern::GetCurrentRowHeaders.
        Return List[Control], a list of `Control` subclasses, representing all the row headers in a table.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtablepattern-getcurrentrowheaders
        """
        eleArray = self.pattern.GetCurrentRowHeaders()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []


class TextRange():
    def __init__(self, textRange=None):
        """
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtextrange
        """
        self.textRange = textRange

    def AddToSelection(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTextRange::AddToSelection.
        Add the text range to the collection of selected text ranges in a control that supports multiple, disjoint spans of selected text.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-addtoselection
        """
        ret = self.textRange.AddToSelection() == S_OK
        time.sleep(waitTime)
        return ret

    def Clone(self) -> 'TextRange':
        """
        Call IUIAutomationTextRange::Clone.
        return `TextRange`, identical to the original and inheriting all properties of the original.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-clone
        """
        return TextRange(textRange=self.textRange.Clone())

    def Compare(self, textRange: 'TextRange') -> bool:
        """
        Call IUIAutomationTextRange::Compare.
        textRange: `TextRange`.
        Return bool, specifies whether this text range has the same endpoints as another text range.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-compare
        """
        return bool(self.textRange.Compare(textRange.textRange))

    def CompareEndpoints(self, srcEndPoint: int, textRange: 'TextRange', targetEndPoint: int) -> int:
        """
        Call IUIAutomationTextRange::CompareEndpoints.
        srcEndPoint: int, a value in class `TextPatternRangeEndpoint`.
        textRange: `TextRange`.
        targetEndPoint: int, a value in class `TextPatternRangeEndpoint`.
        Return int, a negative value if the caller's endpoint occurs earlier in the text than the target endpoint;
                    0 if the caller's endpoint is at the same location as the target endpoint;
                    or a positive value if the caller's endpoint occurs later in the text than the target endpoint.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-compareendpoints
        """
        return self.textRange.CompareEndpoints(srcEndPoint, textRange, targetEndPoint)

    def ExpandToEnclosingUnit(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTextRange::ExpandToEnclosingUnit.
        Normalize the text range by the specified text unit.
            The range is expanded if it is smaller than the specified unit,
            or shortened if it is longer than the specified unit.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-expandtoenclosingunit
        """
        ret = self.textRange.ExpandToEnclosingUnit() == S_OK
        time.sleep(waitTime)
        return ret

    def FindAttribute(self, textAttributeId: int, val, backward: bool) -> 'TextRange':
        """
        Call IUIAutomationTextRange::FindAttribute.
        textAttributeID: int, a value in class `TextAttributeId`.
        val: COM VARIANT according to textAttributeId? todo.
        backward: bool, True if the last occurring text range should be returned instead of the first; otherwise False.
        return `TextRange` or None, a text range subset that has the specified text attribute value.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-findattribute
        """
        textRange = self.textRange.FindAttribute(textAttributeId, val, int(backward))
        if textRange:
            return TextRange(textRange=textRange)

    def FindText(self, text: str, backward: bool, ignoreCase: bool) -> 'TextRange':
        """
        Call IUIAutomationTextRange::FindText.
        text: str,
        backward: bool, True if the last occurring text range should be returned instead of the first; otherwise False.
        ignoreCase: bool, True if case should be ignored; otherwise False.
        return `TextRange` or None, a text range subset that contains the specified text.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-findtext
        """
        textRange = self.textRange.FindText(text, int(backward), int(ignoreCase))
        if textRange:
            return TextRange(textRange=textRange)

    def GetAttributeValue(self, textAttributeId: int) -> ctypes.POINTER(comtypes.IUnknown):
        """
        Call IUIAutomationTextRange::GetAttributeValue.
        textAttributeId: int, a value in class `TextAttributeId`.
        Return `ctypes.POINTER(comtypes.IUnknown)` or None, the value of the specified text attribute across the entire text range, todo.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-getattributevalue
        """
        return self.textRange.GetAttributeValue(textAttributeId)

    def GetBoundingRectangles(self) -> List[Rect]:
        """
        Call IUIAutomationTextRange::GetBoundingRectangles.
        textAttributeId: int, a value in class `TextAttributeId`.
        Return List[Rect], a list of `Rect`.
            bounding rectangles for each fully or partially visible line of text in a text range..
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-getboundingrectangles

        for rect in textRange.GetBoundingRectangles():
            print(rect.left, rect.top, rect.right, rect.bottom, rect.width(), rect.height(), rect.xcenter(), rect.ycenter())
        """
        floats = self.textRange.GetBoundingRectangles()
        rects = []
        for i in range(len(floats) // 4):
            rect = Rect(int(floats[i * 4]), int(floats[i * 4 + 1]),
                                        int(floats[i * 4]) + int(floats[i * 4 + 2]), int(floats[i * 4 + 1]) + int(floats[i * 4 + 3]))
            rects.append(rect)
        return rects

    def GetChildren(self) -> List['Control']:
        """
        Call IUIAutomationTextRange::GetChildren.
        textAttributeId: int, a value in class `TextAttributeId`.
        Return List[Control], a list of `Control` subclasses, embedded objects that fall within the text range..
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-getchildren
        """
        eleArray = self.textRange.GetChildren()
        if eleArray:
            controls = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                con = Control.CreateControlFromElement(element=ele)
                if con:
                    controls.append(con)
            return controls
        return []

    def GetEnclosingControl(self) -> 'Control':
        """
        Call IUIAutomationTextRange::GetEnclosingElement.
        Return `Control` subclass, the innermost UI Automation element that encloses the text range.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-getenclosingelement
        """
        return Control.CreateControlFromElement(self.textRange.GetEnclosingElement())

    def GetText(self, maxLength: int = -1) -> str:
        """
        Call IUIAutomationTextRange::GetText.
        maxLength: int, the maximum length of the string to return, or -1 if no limit is required.
        Return str, the plain text of the text range.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-gettext
        """
        return self.textRange.GetText(maxLength)

    def Move(self, unit: int, count: int, waitTime: float = OPERATION_WAIT_TIME) -> int:
        """
        Call IUIAutomationTextRange::Move.
        Move the text range forward or backward by the specified number of text units.
        unit: int, a value in class `TextUnit`.
        count: int, the number of text units to move.
               A positive value moves the text range forward.
               A negative value moves the text range backward. Zero has no effect.
        waitTime: float.
        Return: int, the number of text units actually moved.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-move
        """
        ret = self.textRange.Move(unit, count)
        time.sleep(waitTime)
        return ret

    def MoveEndpointByRange(self, srcEndPoint: int, textRange: 'TextRange', targetEndPoint: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTextRange::MoveEndpointByRange.
        Move one endpoint of the current text range to the specified endpoint of a second text range.
        srcEndPoint: int, a value in class `TextPatternRangeEndpoint`.
        textRange: `TextRange`.
        targetEndPoint: int, a value in class `TextPatternRangeEndpoint`.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-moveendpointbyrange
        """
        ret = self.textRange.MoveEndpointByRange(srcEndPoint, textRange.textRange, targetEndPoint) == S_OK
        time.sleep(waitTime)
        return ret

    def MoveEndpointByUnit(self, endPoint: int, unit: int, count: int, waitTime: float = OPERATION_WAIT_TIME) -> int:
        """
        Call IUIAutomationTextRange::MoveEndpointByUnit.
        Move one endpoint of the text range the specified number of text units within the document range.
        endPoint: int, a value in class `TextPatternRangeEndpoint`.
        unit: int, a value in class `TextUnit`.
        count: int, the number of units to move.
                    A positive count moves the endpoint forward.
                    A negative count moves backward.
                    A count of 0 has no effect.
        waitTime: float.
        Return int, the count of units actually moved.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-moveendpointbyunit
        """
        ret = self.textRange.MoveEndpointByUnit(endPoint, unit, count)
        time.sleep(waitTime)
        return ret

    def RemoveFromSelection(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTextRange::RemoveFromSelection.
        Remove the text range from an existing collection of selected text in a text container that supports multiple, disjoint selections.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-removefromselection
        """
        ret = self.textRange.RemoveFromSelection() == S_OK
        time.sleep(waitTime)
        return ret

    def ScrollIntoView(self, alignTop: bool = True, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTextRange::ScrollIntoView.
        Cause the text control to scroll until the text range is visible in the viewport.
        alignTop: bool, True if the text control should be scrolled so that the text range is flush with the top of the viewport;
                        False if it should be flush with the bottom of the viewport.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-scrollintoview
        """
        ret = self.textRange.ScrollIntoView(int(alignTop)) == S_OK
        time.sleep(waitTime)
        return ret

    def Select(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTextRange::Select.
        Select the span of text that corresponds to this text range, and remove any previous selection.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextrange-select
        """
        ret = self.textRange.Select() == S_OK
        time.sleep(waitTime)
        return ret


class TextChildPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtextchildpattern"""
        self.pattern = pattern

    @property
    def TextContainer(self) -> 'Control':
        """
        Property TextContainer.
        Call IUIAutomationSelectionContainer::get_TextContainer.
        Return `Control` subclass, the nearest ancestor element that supports the Text control pattern.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextchildpattern-get_textcontainer
        """
        return Control.CreateControlFromElement(self.pattern.TextContainer)

    @property
    def TextRange(self) -> TextRange:
        """
        Property TextRange.
        Call IUIAutomationSelectionContainer::get_TextRange.
        Return `TextRange`, a text range that encloses this child element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextchildpattern-get_textrange
        """
        return TextRange(self.pattern.TextRange)


class TextEditPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtexteditpattern"""
        self.pattern = pattern

    def GetActiveComposition(self) -> TextRange:
        """
        Call IUIAutomationTextEditPattern::GetActiveComposition.
        Return `TextRange` or None, the active composition.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtexteditpattern-getactivecomposition
        """
        textRange = self.pattern.GetActiveComposition()
        if textRange:
            return TextRange(textRange=textRange)

    def GetConversionTarget(self) -> TextRange:
        """
        Call IUIAutomationTextEditPattern::GetConversionTarget.
        Return `TextRange` or None, the current conversion target range..
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtexteditpattern-getconversiontarget
        """
        textRange = self.pattern.GetConversionTarget()
        if textRange:
            return TextRange(textRange=textRange)


class TextPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtextpattern"""
        self.pattern = pattern

    @property
    def DocumentRange(self) -> TextRange:
        """
        Property DocumentRange.
        Call IUIAutomationTextPattern::get_DocumentRange.
        Return `TextRange`, a text range that encloses the main text of a document.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-get_documentrange
        """
        return TextRange(self.pattern.DocumentRange)

    @property
    def SupportedTextSelection(self) -> bool:
        """
        Property SupportedTextSelection.
        Call IUIAutomationTextPattern::get_SupportedTextSelection.
        Return bool, specifies the type of text selection that is supported by the control.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-get_supportedtextselection
        """
        return bool(self.pattern.SupportedTextSelection)

    def GetSelection(self) -> List[TextRange]:
        """
        Call IUIAutomationTextPattern::GetSelection.
        Return List[TextRange], a list of `TextRange`, represents the currently selected text in a text-based control.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-getselection
        """
        eleArray = self.pattern.GetSelection()
        if eleArray:
            textRanges = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                textRanges.append(TextRange(textRange=ele))
            return textRanges
        return []

    def GetVisibleRanges(self) -> List[TextRange]:
        """
        Call IUIAutomationTextPattern::GetVisibleRanges.
        Return List[TextRange], a list of `TextRange`, disjoint text ranges from a text-based control
                     where each text range represents a contiguous span of visible text.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-getvisibleranges
        """
        eleArray = self.pattern.GetVisibleRanges()
        if eleArray:
            textRanges = []
            for i in range(eleArray.Length):
                ele = eleArray.GetElement(i)
                textRanges.append(TextRange(textRange=ele))
            return textRanges
        return []

    def RangeFromChild(self, child) -> TextRange:
        """
        Call IUIAutomationTextPattern::RangeFromChild.
        child: `Control` or its subclass.
        Return `TextRange` or None, a text range enclosing a child element such as an image,
            hyperlink, Microsoft Excel spreadsheet, or other embedded object.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-rangefromchild
        """
        textRange = self.pattern.RangeFromChild(Control.Element)
        if textRange:
            return TextRange(textRange=textRange)

    def RangeFromPoint(self, x: int, y: int) -> TextRange:
        """
        Call IUIAutomationTextPattern::RangeFromPoint.
        child: `Control` or its subclass.
        Return `TextRange` or None, the degenerate (empty) text range nearest to the specified screen coordinates.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-rangefrompoint
        """
        textRange = self.pattern.RangeFromPoint(ctypes.wintypes.POINT(x, y))
        if textRange:
            return TextRange(textRange=textRange)


class TextPattern2():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtextpattern2"""
        self.pattern = pattern


class TogglePattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtogglepattern"""
        self.pattern = pattern

    @property
    def ToggleState(self) -> int:
        """
        Property ToggleState.
        Call IUIAutomationTogglePattern::get_CurrentToggleState.
        Return int, a value in class `ToggleState`, the state of the control.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtogglepattern-get_currenttogglestate
        """
        return self.pattern.CurrentToggleState

    def Toggle(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTogglePattern::Toggle.
        Cycle through the toggle states of the control.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtogglepattern-toggle
        """
        ret = self.pattern.Toggle() == S_OK
        time.sleep(waitTime)
        return ret


class TransformPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtransformpattern"""
        self.pattern = pattern

    @property
    def CanMove(self) -> bool:
        """
        Property CanMove.
        Call IUIAutomationTransformPattern::get_CurrentCanMove.
        Return bool, indicates whether the element can be moved.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern-get_currentcanmove
        """
        return bool(self.pattern.CurrentCanMove)

    @property
    def CanResize(self) -> bool:
        """
        Property CanResize.
        Call IUIAutomationTransformPattern::get_CurrentCanResize.
        Return bool, indicates whether the element can be resized.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern-get_currentcanresize
        """
        return bool(self.pattern.CurrentCanResize)

    @property
    def CanRotate(self) -> bool:
        """
        Property CanRotate.
        Call IUIAutomationTransformPattern::get_CurrentCanRotate.
        Return bool, indicates whether the element can be rotated.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern-get_currentcanrotate
        """
        return bool(self.pattern.CurrentCanRotate)

    def Move(self, x: int, y: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTransformPattern::Move.
        Move the UI Automation element.
        x: int.
        y: int.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern-move
        """
        ret = self.pattern.Move(x, y) == S_OK
        time.sleep(waitTime)
        return ret

    def Resize(self, width: int, height: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTransformPattern::Resize.
        Resize the UI Automation element.
        width: int.
        height: int.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern-resize
        """
        ret = self.pattern.Resize(width, height) == S_OK
        time.sleep(waitTime)
        return ret

    def Rotate(self, degrees: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTransformPattern::Rotate.
        Rotates the UI Automation element.
        degrees: int.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern-rotate
        """
        ret = self.pattern.Rotate(degrees) == S_OK
        time.sleep(waitTime)
        return ret


class TransformPattern2():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationtransformpattern2"""
        self.pattern = pattern

    @property
    def CanZoom(self) -> bool:
        """
        Property CanZoom.
        Call IUIAutomationTransformPattern2::get_CurrentCanZoom.
        Return bool, indicates whether the control supports zooming of its viewport.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern2-get_CurrentCanZoom
        """
        return bool(self.pattern.CurrentCanZoom)

    @property
    def ZoomLevel(self) -> float:
        """
        Property ZoomLevel.
        Call IUIAutomationTransformPattern2::get_CurrentZoomLevel.
        Return float, the zoom level of the control's viewport.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern2-get_currentzoomlevel
        """
        return self.pattern.CurrentZoomLevel

    @property
    def ZoomMaximum(self) -> float:
        """
        Property ZoomMaximum.
        Call IUIAutomationTransformPattern2::get_CurrentZoomMaximum.
        Return float, the maximum zoom level of the control's viewport.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern2-get_currentzoommaximum
        """
        return self.pattern.CurrentZoomMaximum

    @property
    def ZoomMinimum(self) -> float:
        """
        Property ZoomMinimum.
        Call IUIAutomationTransformPattern2::get_CurrentZoomMinimum.
        Return float, the minimum zoom level of the control's viewport.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern2-get_currentzoomminimum
        """
        return self.pattern.CurrentZoomMinimum

    def Zoom(self, zoomLevel: float, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTransformPattern2::Zoom.
        Zoom the viewport of the control.
        zoomLevel: float for int.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern2-zoom
        """
        ret = self.pattern.Zoom(zoomLevel) == S_OK
        time.sleep(waitTime)
        return ret

    def ZoomByUnit(self, zoomUnit: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTransformPattern2::ZoomByUnit.
        Zoom the viewport of the control by the specified unit.
        zoomUnit: int, a value in class `ZoomUnit`.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationtransformpattern2-zoombyunit
        """
        ret = self.pattern.ZoomByUnit(zoomUnit) == S_OK
        time.sleep(waitTime)
        return ret


class ValuePattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationvaluepattern"""
        self.pattern = pattern

    @property
    def IsReadOnly(self) -> bool:
        """
        Property IsReadOnly.
        Call IUIAutomationTransformPattern2::IUIAutomationValuePattern::get_CurrentIsReadOnly.
        Return bool, indicates whether the value of the element is read-only.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationvaluepattern-get_currentisreadonly
        """
        return self.pattern.CurrentIsReadOnly

    @property
    def Value(self) -> str:
        """
        Property Value.
        Call IUIAutomationTransformPattern2::IUIAutomationValuePattern::get_CurrentValue.
        Return str, the value of the element.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationvaluepattern-get_currentvalue
        """
        return self.pattern.CurrentValue

    def SetValue(self, value: str, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationTransformPattern2::IUIAutomationValuePattern::SetValue.
        Set the value of the element.
        value: str.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationvaluepattern-setvalue
        """
        ret = self.pattern.SetValue(value) == S_OK
        time.sleep(waitTime)
        return ret


class VirtualizedItemPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationvirtualizeditempattern"""
        self.pattern = pattern

    def Realize(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationVirtualizedItemPattern::Realize.
        Create a full UI Automation element for a virtualized item.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationvirtualizeditempattern-realize
        """
        ret = self.pattern.Realize() == S_OK
        time.sleep(waitTime)
        return ret


class WindowPattern():
    def __init__(self, pattern=None):
        """Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationwindowpattern"""
        self.pattern = pattern

    def Close(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationWindowPattern::Close.
        Close the window.
        waitTime: float.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-close
        """
        ret = self.pattern.Close() == S_OK
        time.sleep(waitTime)
        return ret

    @property
    def CanMaximize(self) -> bool:
        """
        Property CanMaximize.
        Call IUIAutomationWindowPattern::get_CurrentCanMaximize.
        Return bool, indicates whether the window can be maximized.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-get_currentcanmaximize
        """
        return bool(self.pattern.CurrentCanMaximize)

    @property
    def CanMinimize(self) -> bool:
        """
        Property CanMinimize.
        Call IUIAutomationWindowPattern::get_CurrentCanMinimize.
        Return bool, indicates whether the window can be minimized.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-get_currentcanminimize
        """
        return bool(self.pattern.CurrentCanMinimize)

    @property
    def IsModal(self) -> bool:
        """
        Property IsModal.
        Call IUIAutomationWindowPattern::get_CurrentIsModal.
        Return bool, indicates whether the window is modal.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-get_currentismodal
        """
        return bool(self.pattern.CurrentIsModal)

    @property
    def IsTopmost(self) -> bool:
        """
        Property IsTopmost.
        Call IUIAutomationWindowPattern::get_CurrentIsTopmost.
        Return bool, indicates whether the window is the topmost element in the z-order.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-get_currentistopmost
        """
        return bool(self.pattern.CurrentIsTopmost)

    @property
    def WindowInteractionState(self) -> int:
        """
        Property WindowInteractionState.
        Call IUIAutomationWindowPattern::get_CurrentWindowInteractionState.
        Return int, a value in class `WindowInteractionState`,
                    the current state of the window for the purposes of user interaction.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-get_currentwindowinteractionstate
        """
        return self.pattern.CurrentWindowInteractionState

    @property
    def WindowVisualState(self) -> int:
        """
        Property WindowVisualState.
        Call IUIAutomationWindowPattern::get_CurrentWindowVisualState.
        Return int, a value in class `WindowVisualState`,
                    the visual state of the window; that is, whether it is in the normal, maximized, or minimized state.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-get_currentwindowvisualstate
        """
        return self.pattern.CurrentWindowVisualState

    def SetWindowVisualState(self, state: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call IUIAutomationWindowPattern::SetWindowVisualState.
        Minimize, maximize, or restore the window.
        state: int, a value in class `WindowVisualState`.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-setwindowvisualstate
        """
        ret = self.pattern.SetWindowVisualState(state) == S_OK
        time.sleep(waitTime)
        return ret

    def WaitForInputIdle(self, milliseconds: int) -> bool:
        '''
        Call IUIAutomationWindowPattern::WaitForInputIdle.
        Cause the calling code to block for the specified time or
            until the associated process enters an idle state, whichever completes first.
        milliseconds: int.
        Return bool, True if succeed otherwise False.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationwindowpattern-waitforinputidle
        '''
        return self.pattern.WaitForInputIdle(milliseconds) == S_OK


PatternConstructors = {
    PatternId.AnnotationPattern: AnnotationPattern,
    PatternId.CustomNavigationPattern: CustomNavigationPattern,
    PatternId.DockPattern: DockPattern,
    PatternId.DragPattern: DragPattern,
    PatternId.DropTargetPattern: DropTargetPattern,
    PatternId.ExpandCollapsePattern: ExpandCollapsePattern,
    PatternId.GridItemPattern: GridItemPattern,
    PatternId.GridPattern: GridPattern,
    PatternId.InvokePattern: InvokePattern,
    PatternId.ItemContainerPattern: ItemContainerPattern,
    PatternId.LegacyIAccessiblePattern: LegacyIAccessiblePattern,
    PatternId.MultipleViewPattern: MultipleViewPattern,
    PatternId.ObjectModelPattern: ObjectModelPattern,
    PatternId.RangeValuePattern: RangeValuePattern,
    PatternId.ScrollItemPattern: ScrollItemPattern,
    PatternId.ScrollPattern: ScrollPattern,
    PatternId.SelectionItemPattern: SelectionItemPattern,
    PatternId.SelectionPattern: SelectionPattern,
    PatternId.SpreadsheetItemPattern: SpreadsheetItemPattern,
    PatternId.SpreadsheetPattern: SpreadsheetPattern,
    PatternId.StylesPattern: StylesPattern,
    PatternId.SynchronizedInputPattern: SynchronizedInputPattern,
    PatternId.TableItemPattern: TableItemPattern,
    PatternId.TablePattern: TablePattern,
    PatternId.TextChildPattern: TextChildPattern,
    PatternId.TextEditPattern: TextEditPattern,
    PatternId.TextPattern: TextPattern,
    PatternId.TextPattern2: TextPattern2,
    PatternId.TogglePattern: TogglePattern,
    PatternId.TransformPattern: TransformPattern,
    PatternId.TransformPattern2: TransformPattern2,
    PatternId.ValuePattern: ValuePattern,
    PatternId.VirtualizedItemPattern: VirtualizedItemPattern,
    PatternId.WindowPattern: WindowPattern,
}


def CreatePattern(patternId: int, pattern: ctypes.POINTER(comtypes.IUnknown)):
    """Create a concreate pattern by pattern id and pattern(POINTER(IUnknown))."""
    subPattern = pattern.QueryInterface(GetPatternIdInterface(patternId))
    if subPattern:
        return PatternConstructors[patternId](pattern=subPattern)


class Control():
    ValidKeys = set(['ControlType', 'ClassName', 'AutomationId', 'Name', 'SubName', 'RegexName', 'Depth', 'Compare'])
    def __init__(self, searchFromControl: 'Control' = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        """
        searchFromControl: `Control` or its subclass, if it is None, search from root control(Desktop).
        searchDepth: int, max search depth from searchFromControl.
        foundIndex: int, starts with 1, >= 1.
        searchInterval: float, wait searchInterval after every search in self.Refind and self.Exists, the global timeout is TIME_OUT_SECOND.
        element: `ctypes.POINTER(IUIAutomationElement)`, internal use only.
        searchProperties: defines how to search, the following keys can be used:
                            ControlType: int, a value in class `ControlType`.
                            ClassName: str.
                            AutomationId: str.
                            Name: str.
                            SubName: str, a part str in Name.
                            RegexName: str, supports regex using re.match.
                                You can only use one of Name, SubName, RegexName in searchProperties.
                            Depth: int, only search controls in relative depth from searchFromControl, ignore controls in depth(0~Depth-1),
                                if set, searchDepth will be set to Depth too.
                            Compare: Callable[[Control, int], bool], custom compare function(control: Control, depth: int) -> bool.

        `Control` wraps IUIAutomationElement.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nn-uiautomationclient-iuiautomationelement
        """
        self._element = element
        self._elementDirectAssign = True if element else False
        self.searchFromControl = searchFromControl
        self.searchDepth = searchProperties.get('Depth', searchDepth)
        self.searchInterval = searchInterval
        self.foundIndex = foundIndex
        self.searchProperties = searchProperties
        regName = searchProperties.get('RegexName', '')
        self.regexName = re.compile(regName) if regName else None
        self._supportedPatterns = {}

    def __str__(self) -> str:
        rect = self.BoundingRectangle
        return 'ControlType: {0}    ClassName: {1}    AutomationId: {2}    Rect: {3}    Name: {4}    Handle: 0x{5:X}({5})'.format(
            self.ControlTypeName, self.ClassName, self.AutomationId, rect, self.Name, self.NativeWindowHandle)

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.GetRuntimeId() == other.GetRuntimeId()
    
    @property
    def winapi(self):
        if not hasattr(self, '_winapi'):
            self._winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        return self._winapi
    
    @staticmethod
    def CreateControlFromElement(element) -> 'Control':
        """
        Create a concreate `Control` from a com type `IUIAutomationElement`.
        element: `ctypes.POINTER(IUIAutomationElement)`.
        Return a subclass of `Control`, an instance of the control's real type.
        """
        if element:
            controlType = element.CurrentControlType
            if controlType in ControlConstructors:
                return ControlConstructors[controlType](element=element)
            else:
                Logger.WriteLine("element.CurrentControlType returns {}, invalid ControlType!".format(controlType), ConsoleColor.Red)  #rarely happens

    @staticmethod
    def CreateControlFromControl(control: 'Control') -> 'Control':
        """
        Create a concreate `Control` from a control instance, copy it.
        control: `Control` or its subclass.
        Return a subclass of `Control`, an instance of the control's real type.
        For example: if control's ControlType is EditControl, return an EditControl.
        """
        newControl = Control.CreateControlFromElement(control.Element)
        return newControl
    
    def tree(self, max=9999999):
        try:
            return PrintAllControlTree(self, max)
        except Exception as e:
            pass
        # try:
        #     # from anytree import Node, RenderTree
        #     # node = Node(f"[{self.ControlTypeName} 0](\"{self.ClassName}\", \"{self.Name.replace('\n', '')}\", \"{self.runtimeid}\")")
        #     walk = WalkTree(
        #         self, 
        #         getFirstChild=lambda c: c.GetFirstChildControl(),
        #         getNextSibling=lambda c: c.GetNextSiblingControl()
        #     )
        #     nn = '\n'
        #     print(f"[{self.ControlTypeName} 0](\"{self.ClassName}\", \"{self.Name.replace(nn, '')}\", \"{self.runtimeid}\")")
        #     for c, depth in walk:
        #         print('    ' * depth + f"[{c.ControlTypeName} {depth}](\"{c.ClassName}\", \"{c.Name.replace(nn, '')}\", \"{c.runtimeid}\")")
        # except Exception as e:
        #     pass

    @property
    def runtimeid(self):
        content = self.Name
        rect = self.BoundingRectangle
        hash_text = f'({rect.height()},{rect.width()}){content}{self.GetRuntimeId()}'
        return md5(hash_text.encode()).hexdigest()

    def SetSearchFromControl(self, searchFromControl: 'Control') -> None:
        """searchFromControl: `Control` or its subclass"""
        self.searchFromControl = searchFromControl

    def SetSearchDepth(self, searchDepth: int) -> None:
        self.searchDepth = searchDepth

    def AddSearchProperties(self, **searchProperties) -> None:
        """
        Add search properties using `dict.update`.
        searchProperties: dict, same as searchProperties in `Control.__init__`.
        """
        self.searchProperties.update(searchProperties)
        if 'Depth' in searchProperties:
            self.searchDepth = searchProperties['Depth']
        if 'RegexName' in searchProperties:
            regName = searchProperties['RegexName']
            self.regexName = re.compile(regName) if regName else None

    def RemoveSearchProperties(self, **searchProperties) -> None:
        """
        searchProperties: dict, same as searchProperties in `Control.__init__`.
        """
        for key in searchProperties:
            del self.searchProperties[key]
            if key == 'RegexName':
                self.regexName = None

    def GetSearchPropertiesStr(self) -> str:
        strs = ['{}: {}'.format(k, ControlTypeNames[v] if k == 'ControlType' else repr(v)) for k, v in self.searchProperties.items()]
        return '{' + ', '.join(strs) + '}'

    def GetColorfulSearchPropertiesStr(self, keyColor='DarkGreen', valueColor='DarkCyan') -> str:
        """keyColor, valueColor: str, color name in class ConsoleColor"""
        strs = ['<Color={}>{}</Color>: <Color={}>{}</Color>'.format(keyColor if k in Control.ValidKeys else 'DarkYellow', k, valueColor,
                ControlTypeNames[v] if k == 'ControlType' else repr(v)) for k, v in self.searchProperties.items()]
        return '{' + ', '.join(strs) + '}'

    #BuildUpdatedCache
    #CachedAcceleratorKey
    #CachedAccessKey
    #CachedAriaProperties
    #CachedAriaRole
    #CachedAutomationId
    #CachedBoundingRectangle
    #CachedClassName
    #CachedControlType
    #CachedControllerFor
    #CachedCulture
    #CachedDescribedBy
    #CachedFlowsTo
    #CachedFrameworkId
    #CachedHasKeyboardFocus
    #CachedHelpText
    #CachedIsContentElement
    #CachedIsControlElement
    #CachedIsDataValidForForm
    #CachedIsEnabled
    #CachedIsKeyboardFocusable
    #CachedIsOffscreen
    #CachedIsPassword
    #CachedIsRequiredForForm
    #CachedItemStatus
    #CachedItemType
    #CachedLabeledBy
    #CachedLocalizedControlType
    #CachedName
    #CachedNativeWindowHandle
    #CachedOrientation
    #CachedProcessId
    #CachedProviderDescription

    @property
    def AcceleratorKey(self) -> str:
        """
        Property AcceleratorKey.
        Call IUIAutomationElement::get_CurrentAcceleratorKey.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentacceleratorkey
        """
        return self.Element.CurrentAcceleratorKey

    @property
    def AccessKey(self) -> str:
        """
        Property AccessKey.
        Call IUIAutomationElement::get_CurrentAccessKey.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentaccesskey
        """
        return self.Element.CurrentAccessKey

    @property
    def AriaProperties(self) -> str:
        """
        Property AriaProperties.
        Call IUIAutomationElement::get_CurrentAriaProperties.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentariaproperties
        """
        return self.Element.CurrentAriaProperties

    @property
    def AriaRole(self) -> str:
        """
        Property AriaRole.
        Call IUIAutomationElement::get_CurrentAriaRole.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentariarole
        """
        return self.Element.CurrentAriaRole

    @property
    def AutomationId(self) -> str:
        """
        Property AutomationId.
        Call IUIAutomationElement::get_CurrentAutomationId.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentautomationid
        """
        return self.Element.CurrentAutomationId

    @property
    def BoundingRectangle(self) -> Rect:
        """
        Property BoundingRectangle.
        Call IUIAutomationElement::get_CurrentBoundingRectangle.
        Return `Rect`.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentboundingrectangle

        rect = control.BoundingRectangle
        print(rect.left, rect.top, rect.right, rect.bottom, rect.width(), rect.height(), rect.xcenter(), rect.ycenter())
        """
        rect = self.Element.CurrentBoundingRectangle
        return Rect(rect.left, rect.top, rect.right, rect.bottom)
    
    # def ScreenShot(self, savePath: str=None, return_img=False) -> str:
    #     """
    #     Save the control's screenshot to savePath.
    #     savePath: str, the path to save the screenshot.
    #     Return str, the path of the saved screenshot.
    #     """
    #     rect = self.Element.CurrentBoundingRectangle
    #     bbox = (rect.left, rect.top, rect.right, rect.bottom)
    #     img = ImageGrab.grab(bbox=bbox, all_screens=True)
    #     if return_img:
    #         return img
    #     if savePath is None:
    #         savePath = os.path.join(os.getcwd(), 'ControlScreenShot.png')
    #     img.save(savePath)
    #     return savePath

    def ScreenShot(self, savePath: str = None, crop: tuple = (0, 0, 0, 0), crop_percentage: bool = False, return_img=False) -> str:
        """
        Save the control's screenshot to savePath with optional cropping.
        
        :param savePath: str, the path to save the screenshot.
        :param crop: tuple, the amount to crop in (left, top, right, bottom).
        :param crop_percentage: bool, whether the crop values are in percentage.
        :return: str, the path of the saved screenshot.
        """
        if not hasattr(self, 'winapi'):
            self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        rect = self.Element.CurrentBoundingRectangle
        bbox = [rect.left, rect.top, rect.right, rect.bottom]
        
        if crop_percentage:
            width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            crop = (
                int(width * crop[0] / 100),
                int(height * crop[1] / 100),
                int(width * crop[2] / 100),
                int(height * crop[3] / 100)
            )
        
        # Apply cropping
        bbox = (
            bbox[0] + crop[0],
            bbox[1] + crop[1],
            bbox[2] - crop[2],
            bbox[3] - crop[3]
        )
        
        img = self.winapi.capture(bbox)
        if return_img:
            return img
        
        if savePath is None:
            savePath = create_temp_png_path(prefix='uia_screenshot_')
        savePath = os.path.realpath(savePath)
        img.save(savePath)
        return savePath
    
    def Walk(self, includeTop: bool = False, maxDepth: int = 0xFFFFFFFF):
        return WalkControl(self, includeTop, maxDepth)

    @property
    def ClassName(self) -> str:
        """
        Property ClassName.
        Call IUIAutomationElement::get_CurrentClassName.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentclassname
        """
        return self.Element.CurrentClassName

    @property
    def ControlType(self) -> int:
        """
        Property ControlType.
        Return int, a value in class `ControlType`.
        Call IUIAutomationElement::get_CurrentControlType.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentcontroltype
        """
        if hasattr(self, '_controlType'):
            return self._controlType
        self._controlType = self.Element.CurrentControlType
        return self._controlType

    #@property
    #def ControllerFor(self):
        #return self.Element.CurrentControllerFor

    @property
    def Culture(self) -> int:
        """
        Property Culture.
        Call IUIAutomationElement::get_CurrentCulture.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentculture
        """
        return self.Element.CurrentCulture

    #@property
    #def DescribedBy(self):
        #return self.Element.CurrentDescribedBy

    #@property
    #def FlowsTo(self):
        #return self.Element.CurrentFlowsTo

    @property
    def FrameworkId(self) -> str:
        """
        Property FrameworkId.
        Call IUIAutomationElement::get_CurrentFrameworkId.
        Return str, such as Win32, WPF...
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentframeworkid
        """
        return self.Element.CurrentFrameworkId

    @property
    def HasKeyboardFocus(self) -> bool:
        """
        Property HasKeyboardFocus.
        Call IUIAutomationElement::get_CurrentHasKeyboardFocus.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currenthaskeyboardfocus
        """
        return bool(self.Element.CurrentHasKeyboardFocus)

    @property
    def HelpText(self) -> str:
        """
        Property HelpText.
        Call IUIAutomationElement::get_CurrentHelpText.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currenthelptext
        """
        return self.Element.CurrentHelpText

    @property
    def IsContentElement(self) -> bool:
        """
        Property IsContentElement.
        Call IUIAutomationElement::get_CurrentIsContentElement.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentiscontentelement
        """
        return bool(self.Element.CurrentIsContentElement)

    @property
    def IsControlElement(self) -> bool:
        """
        Property IsControlElement.
        Call IUIAutomationElement::get_CurrentIsControlElement.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentiscontrolelement
        """
        return bool(self.Element.CurrentIsControlElement)

    @property
    def IsDataValidForForm(self) -> bool:
        """
        Property IsDataValidForForm.
        Call IUIAutomationElement::get_CurrentIsDataValidForForm.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentisdatavalidforform
        """
        return bool(self.Element.CurrentIsDataValidForForm)

    @property
    def IsEnabled(self) -> bool:
        """
        Property IsEnabled.
        Call IUIAutomationElement::get_CurrentIsEnabled.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentisenabled
        """
        return self.Element.CurrentIsEnabled

    @property
    def IsKeyboardFocusable(self) -> bool:
        """
        Property IsKeyboardFocusable.
        Call IUIAutomationElement::get_CurrentIsKeyboardFocusable.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentiskeyboardfocusable
        """
        return self.Element.CurrentIsKeyboardFocusable

    @property
    def IsOffscreen(self) -> bool:
        """
        Property IsOffscreen.
        Call IUIAutomationElement::get_CurrentIsOffscreen.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentisoffscreen
        """
        return self.Element.CurrentIsOffscreen

    @property
    def IsPassword(self) -> bool:
        """
        Property IsPassword.
        Call IUIAutomationElement::get_CurrentIsPassword.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentispassword
        """
        return self.Element.CurrentIsPassword

    @property
    def IsRequiredForForm(self) -> bool:
        """
        Property IsRequiredForForm.
        Call IUIAutomationElement::get_CurrentIsRequiredForForm.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentisrequiredforform
        """
        return self.Element.CurrentIsRequiredForForm

    @property
    def ItemStatus(self) -> str:
        """
        Property ItemStatus.
        Call IUIAutomationElement::get_CurrentItemStatus.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentitemstatus
        """
        return self.Element.CurrentItemStatus

    @property
    def ItemType(self) -> str:
        """
        Property ItemType.
        Call IUIAutomationElement::get_CurrentItemType.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentitemtype
        """
        return self.Element.CurrentItemType

    #@property
    #def LabeledBy(self):
        #return self.Element.CurrentLabeledBy

    @property
    def LocalizedControlType(self) -> str:
        """
        Property LocalizedControlType.
        Call IUIAutomationElement::get_CurrentLocalizedControlType.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentlocalizedcontroltype
        """
        return self.Element.CurrentLocalizedControlType

    @property
    def Name(self) -> str:
        """
        Property Name.
        Call IUIAutomationElement::get_CurrentName.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentname
        """
        return self.Element.CurrentName or ''   # CurrentName may be None

    @property
    def NativeWindowHandle(self) -> str:
        """
        Property NativeWindowHandle.
        Call IUIAutomationElement::get_CurrentNativeWindowHandle.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentnativewindowhandle
        """
        handle = self.Element.CurrentNativeWindowHandle
        return 0 if handle is None else handle

    @property
    def Orientation(self) -> int:
        """
        Property Orientation.
        Return int, a value in class `OrientationType`.
        Call IUIAutomationElement::get_CurrentOrientation.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentorientation
        """
        return self.Element.CurrentOrientation

    @property
    def ProcessId(self) -> int:
        """
        Property ProcessId.
        Call IUIAutomationElement::get_CurrentProcessId.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentprocessid
        """
        return self.Element.CurrentProcessId

    @property
    def ProviderDescription(self) -> str:
        """
        Property ProviderDescription.
        Call IUIAutomationElement::get_CurrentProviderDescription.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-get_currentproviderdescription
        """
        return self.Element.CurrentProviderDescription

    #FindAll
    def FindAll(
            self,
            find_mode: Literal['All', 'Ancestors', 'Descendants', 'Children', 'Subtree', 'Parent']='All',
            control_type: str=None,
            pointer = None,
            return_pointer: bool=False,
        ) -> List['Control']:
        """
        Call IUIAutomationElement::FindAll.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-findall
        """
        tree_scope = getattr(TreeScope, find_mode)
        if control_type:
            condition = _AutomationClient.instance().IUIAutomation.CreatePropertyCondition(
                PropertyId.ControlTypeProperty,
                getattr(ControlType, control_type)
            )
        else:
            condition = _AutomationClient.instance().IUIAutomation.CreateTrueCondition()
        if pointer is not None:
            result = pointer
        else:
            result = self.Element.FindAll(tree_scope, condition)
        if return_pointer:
            return result
        sub_controls = [
            Control.CreateControlFromElement(result.GetElement(i))
            for i in range(result.Length)
        ]
        return sub_controls
    #FindAllBuildCache
    #FindFirst
    #FindFirstBuildCache
    #GetCachedChildren
    #GetCachedParent
    #GetCachedPattern
    #GetCachedPatternAs
    #GetCachedPropertyValue
    #GetCachedPropertyValueEx

    def GetClickablePoint(self) -> Tuple[int, int, bool]:
        """
        Call IUIAutomationElement::GetClickablePoint.
        Return Tuple[int, int, bool], three items tuple (x, y, gotClickable), such as (20, 10, True)
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-getclickablepoint
        """
        point, gotClickable = self.Element.GetClickablePoint()
        return (point.x, point.y, bool(gotClickable))

    def GetPattern(self, patternId: int):
        """
        Call IUIAutomationElement::GetCurrentPattern.
        Get a new pattern by pattern id if it supports the pattern.
        patternId: int, a value in class `PatternId`.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-getcurrentpattern
        """
        try:
            pattern = self.Element.GetCurrentPattern(patternId)
            if pattern:
                subPattern = CreatePattern(patternId, pattern)
                self._supportedPatterns[patternId] = subPattern
                return subPattern
        except comtypes.COMError as ex:
            pass

    def GetPatternAs(self, patternId: int, riid):
        """
        Call IUIAutomationElement::GetCurrentPatternAs.
        Get a new pattern by pattern id if it supports the pattern, todo.
        patternId: int, a value in class `PatternId`.
        riid: GUID.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-getcurrentpatternas
        """
        return self.Element.GetCurrentPatternAs(patternId, riid)

    def GetPropertyValue(self, propertyId: int) -> Any:
        """
        Call IUIAutomationElement::GetCurrentPropertyValue.
        propertyId: int, a value in class `PropertyId`.
        Return Any, corresponding type according to propertyId.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-getcurrentpropertyvalue
        """
        return self.Element.GetCurrentPropertyValue(propertyId)

    def GetPropertyValueEx(self, propertyId: int, ignoreDefaultValue: int) -> Any:
        """
        Call IUIAutomationElement::GetCurrentPropertyValueEx.
        propertyId: int, a value in class `PropertyId`.
        ignoreDefaultValue: int, 0 or 1.
        Return Any, corresponding type according to propertyId.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-getcurrentpropertyvalueex
        """
        return self.Element.GetCurrentPropertyValueEx(propertyId, ignoreDefaultValue)

    def GetRuntimeId(self) -> List[int]:
        """
        Call IUIAutomationElement::GetRuntimeId.
        Return List[int], a list of int.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-getruntimeid
        """
        return self.Element.GetRuntimeId()

    #QueryInterface
    #Release

    def SetFocus(self) -> bool:
        """
        Call IUIAutomationElement::SetFocus.
        Refer https://docs.microsoft.com/en-us/windows/desktop/api/uiautomationclient/nf-uiautomationclient-iuiautomationelement-setfocus
        """
        try:
            return self.Element.SetFocus() == S_OK
        except comtypes.COMError as ex:
            return False

    @property
    def Element(self):
        """
        Property Element.
        Return `ctypes.POINTER(IUIAutomationElement)`.
        """
        if not self._element:
            self.Refind(maxSearchSeconds=TIME_OUT_SECOND, searchIntervalSeconds=self.searchInterval)
        return self._element

    @property
    def ControlTypeName(self) -> str:
        """
        Property ControlTypeName.
        """
        cls_name = self.__class__.__name__
        if cls_name == 'Control':
            return ControlTypeNames[self.ControlType]
        else:
            return cls_name

    def GetCachedPattern(self, patternId: int, cache: bool):
        """
        Get a pattern by patternId.
        patternId: int, a value in class `PatternId`.
        Return a pattern if it supports the pattern else None.
        cache: bool, if True, store the pattern for later use, if False, get a new pattern by `self.GetPattern`.
        """
        if cache:
            pattern = self._supportedPatterns.get(patternId, None)
            if pattern:
                return pattern
            else:
                pattern = self.GetPattern(patternId)
                if pattern:
                    self._supportedPatterns[patternId] = pattern
                    return pattern
        else:
            pattern = self.GetPattern(patternId)
            if pattern:
                self._supportedPatterns[patternId] = pattern
                return pattern

    def GetLegacyIAccessiblePattern(self) -> LegacyIAccessiblePattern:
        """
        Return `LegacyIAccessiblePattern` if it supports the pattern else None.
        """
        return self.GetPattern(PatternId.LegacyIAccessiblePattern)

    def GetAncestorControl(self, condition: Callable[['Control', int], bool]) -> 'Control':
        """
        Get an ancestor control that matches the condition.
        condition: Callable[[Control, int], bool], function(control: Control, depth: int) -> bool,
                   depth starts with -1 and decreses when search goes up.
        Return `Control` subclass or None.
        """
        ancestor = self
        depth = 0
        while True:
            ancestor = ancestor.GetParentControl()
            depth -= 1
            if ancestor:
                if condition(ancestor, depth):
                    return ancestor
            else:
                break

    def GetParentControl(self) -> 'Control':
        """
        Return `Control` subclass or None.
        """
        ele = _AutomationClient.instance().ViewWalker.GetParentElement(self.Element)
        return Control.CreateControlFromElement(ele)

    def GetFirstChildControl(self) -> 'Control':
        """
        Return `Control` subclass or None.
        """
        ele = _AutomationClient.instance().ViewWalker.GetFirstChildElement(self.Element)
        return Control.CreateControlFromElement(ele)

    def GetLastChildControl(self) -> 'Control':
        """
        Return `Control` subclass or None.
        """
        ele = _AutomationClient.instance().ViewWalker.GetLastChildElement(self.Element)
        return Control.CreateControlFromElement(ele)

    def GetNextSiblingControl(self) -> 'Control':
        """
        Return `Control` subclass or None.
        """
        ele = _AutomationClient.instance().ViewWalker.GetNextSiblingElement(self.Element)
        return Control.CreateControlFromElement(ele)

    def GetPreviousSiblingControl(self) -> 'Control':
        """
        Return `Control` subclass or None.
        """
        ele = _AutomationClient.instance().ViewWalker.GetPreviousSiblingElement(self.Element)
        return Control.CreateControlFromElement(ele)

    def GetSiblingControl(self, condition: Callable[['Control'], bool], forward: bool = True) -> 'Control':
        """
        Get a sibling control that matches the condition.
        forward: bool, if True, only search next siblings, if False, search pervious siblings first, then search next siblings.
        condition: Callable[[Control], bool], function(control: Control) -> bool.
        Return `Control` subclass or None.
        """
        if not forward:
            prev = self
            while True:
                prev = prev.GetPreviousSiblingControl()
                if prev:
                    if condition(prev):
                        return prev
                else:
                    break
        next_ = self
        while True:
            next_ = next_.GetNextSiblingControl()
            if next_:
                if condition(next_):
                    return next_
            else:
                break

    def GetChildControl(self, index: int, control_type: str = None) -> 'Control':
        """
        Get the nth child control.
        index: int, starts with 0.
        control_type: `Control` or its subclass, if not None, only return the nth control that matches the control_type.
        Return `Control` subclass or None.
        """
        children = self.GetChildren()
        if control_type:
            children = [child for child in children if child.ControlTypeName == control_type]
        if index < len(children):
            return children[index]
        else:
            return None
        
    def GetAllProgeny(self, refresh=False) -> List[List['Control']]:
        """
        Get all progeny controls.
        Return List[List[Control]], a list of list of `Control` subclasses.
        """
        if hasattr(self, '_progeny') and not refresh:
            return self._progeny
        all_elements = []

        def find_all_elements(element, depth=0):
            children = element.GetChildren()
            if depth == len(all_elements):
                all_elements.append([])
            all_elements[depth].append(element)
            for child in children:
                find_all_elements(child, depth+1)
            return all_elements
        
        self._progeny = find_all_elements(self)
        return self._progeny
    
    def GetProgenyControl(self, depth: int=1, index: int=0, control_type: str = None, refresh=False) -> 'Control':
        """
        Get the nth control in the mth depth.
        depth: int, starts with 0.
        index: int, starts with 0.
        control_type: `Control` or its subclass, if not None, only return the nth control that matches the control_type.
        Return `Control` subclass or None.
        """
        progeny = self.GetAllProgeny(refresh)
        try:
            controls = progeny[depth]
            if control_type:
                controls = [child for child in controls if child.ControlTypeName == control_type]
            if index < len(controls):
                return controls[index]
        except IndexError:
            return

    def GetChildren(self) -> List['Control']:
        """
        Return List[Control], a list of `Control` subclasses.
        """
        children = []
        child = self.GetFirstChildControl()
        while child:
            children.append(child)
            child = child.GetNextSiblingControl()
        return children

    def _CompareFunction(self, control: 'Control', depth: int) -> bool:
        """
        Define how to search.
        control: `Control` or its subclass.
        depth: int, tree depth from searchFromControl.
        Return bool.
        """
        for key, value in self.searchProperties.items():
            if 'ControlType' == key:
                if value != control.ControlType:
                    return False
            elif 'ClassName' == key:
                if value != control.ClassName:
                    return False
            elif 'AutomationId' == key:
                if value != control.AutomationId:
                    return False
            elif 'Depth' == key:
                if value != depth:
                    return False
            elif 'Name' == key:
                if value != control.Name:
                    return False
            elif 'SubName' == key:
                if value not in control.Name:
                    return False
            elif 'RegexName' == key:
                if not self.regexName.match(control.Name):
                    return False
            elif 'Compare' == key:
                if not value(control, depth):
                    return False
        return True

    def Exists(self, maxSearchSeconds: float = 5, searchIntervalSeconds: float = SEARCH_INTERVAL, printIfNotExist: bool = False) -> bool:
        """
        maxSearchSeconds: float
        searchIntervalSeconds: float
        Find control every searchIntervalSeconds seconds in maxSearchSeconds seconds.
        Return bool, True if find
        """
        if self._element and self._elementDirectAssign:
            #if element is directly assigned, not by searching, just check whether self._element is valid
            #but I can't find an API in UIAutomation that can directly check
            rootElement = GetRootControl().Element
            if self._element == rootElement:
                return True
            else:
                parentElement = _AutomationClient.instance().ViewWalker.GetParentElement(self._element)
                if parentElement:
                    return True
                else:
                    return False
        #find the element
        if len(self.searchProperties) == 0:
            raise LookupError("control's searchProperties must not be empty!")
        self._element = None
        startTime = ProcessTime()
        # Use same timeout(s) parameters for resolve all parents
        prev =  self.searchFromControl
        if prev and not prev._element and not prev.Exists(maxSearchSeconds, searchIntervalSeconds):
            if printIfNotExist or DEBUG_EXIST_DISAPPEAR:
                Logger.ColorfullyLog(self.GetColorfulSearchPropertiesStr() + '<Color=Red> does not exist.</Color>')
            return False
        startTime2 = ProcessTime()
        if DEBUG_SEARCH_TIME:
            startDateTime = datetime.datetime.now()
        while True:
            try:
                control = FindControl(self.searchFromControl, self._CompareFunction, self.searchDepth, False, self.foundIndex)
            except _ctypes.COMError:
                return False
            if control:
                self._element = control.Element
                control._element = 0  # control will be destroyed, but the element needs to be stroed in self._element
                if DEBUG_SEARCH_TIME:
                    Logger.ColorfullyLog('{} TraverseControls: <Color=Cyan>{}</Color>, SearchTime: <Color=Cyan>{:.3f}</Color>s[{} - {}]'.format(
                        self.GetColorfulSearchPropertiesStr(), control.traverseCount, ProcessTime() - startTime2,
                        startDateTime.time(), datetime.datetime.now().time()))
                return True
            else:
                remain = startTime + maxSearchSeconds - ProcessTime()
                if remain > 0:
                    time.sleep(min(remain, searchIntervalSeconds))
                else:
                    if printIfNotExist or DEBUG_EXIST_DISAPPEAR:
                        Logger.ColorfullyLog(self.GetColorfulSearchPropertiesStr() + '<Color=Red> does not exist.</Color>')
                    return False
        

    def Disappears(self, maxSearchSeconds: float = 5, searchIntervalSeconds: float = SEARCH_INTERVAL, printIfNotDisappear: bool = False) -> bool:
        """
        maxSearchSeconds: float
        searchIntervalSeconds: float
        Check if control disappears every searchIntervalSeconds seconds in maxSearchSeconds seconds.
        Return bool, True if control disappears.
        """
        global DEBUG_EXIST_DISAPPEAR
        start = ProcessTime()
        while True:
            temp = DEBUG_EXIST_DISAPPEAR
            DEBUG_EXIST_DISAPPEAR = False  # do not print for Exists
            if not self.Exists(0, 0, False):
                DEBUG_EXIST_DISAPPEAR = temp
                return True
            DEBUG_EXIST_DISAPPEAR = temp
            remain = start + maxSearchSeconds - ProcessTime()
            if remain > 0:
                time.sleep(min(remain, searchIntervalSeconds))
            else:
                if printIfNotDisappear or DEBUG_EXIST_DISAPPEAR:
                    Logger.ColorfullyLog(self.GetColorfulSearchPropertiesStr() + '<Color=Red> does not disappear.</Color>')
                return False

    def Refind(self, maxSearchSeconds: float = TIME_OUT_SECOND, searchIntervalSeconds: float = SEARCH_INTERVAL, raiseException: bool = True) -> bool:
        """
        Refind the control every searchIntervalSeconds seconds in maxSearchSeconds seconds.
        maxSearchSeconds: float.
        searchIntervalSeconds: float.
        raiseException: bool, if True, raise a LookupError if timeout.
        Return bool, True if find.
        """
        if not self.Exists(maxSearchSeconds, searchIntervalSeconds, False if raiseException else DEBUG_EXIST_DISAPPEAR):
            if raiseException:
                # Logger.ColorfullyLog('<Color=Red>Find Control Timeout: </Color>' + self.GetColorfulSearchPropertiesStr())
                raise LookupError('Find Control Timeout: ' + self.GetSearchPropertiesStr())
            else:
                return False
        return True

    def MoveCursorToInnerPos(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, simulateMove: bool = True) -> Tuple[int, int]:
        """
        Move cursor to control's internal position, default to center.
        x: int, if < 0, move to self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, move to self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        simulateMove: bool.
        Return Tuple[int, int], two ints tuple (x, y), the cursor positon relative to screen(0, 0)
            after moving or None if control's width or height is 0.
        """
        rect = self.BoundingRectangle
        if rect.width() == 0 or rect.height() == 0:
            Logger.ColorfullyLog('<Color=Yellow>Can not move cursor</Color>. {}\'s BoundingRectangle is {}. SearchProperties: {}'.format(
                self.ControlTypeName, rect, self.GetColorfulSearchPropertiesStr()))
            return
        if x is None:
            x = rect.left + int(rect.width() * ratioX)
        else:
            x = (rect.left if x >= 0 else rect.right) + x
        if y is None:
            y = rect.top + int(rect.height() * ratioY)
        else:
            y = (rect.top if y >= 0 else rect.bottom) + y
        if simulateMove and MAX_MOVE_SECOND > 0:
            MoveTo(x, y, waitTime=0)
        else:
            SetCursorPos(x, y)
        return x, y

    def MoveCursorToMyCenter(self, simulateMove: bool = True) -> Tuple[int, int]:
        """
        Move cursor to control's center.
        Return Tuple[int, int], two ints tuple (x, y), the cursor positon relative to screen(0, 0) after moving.
        """
        return self.MoveCursorToInnerPos(simulateMove=simulateMove)

    def Click(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, simulateMove: bool = False, waitTime: float = OPERATION_WAIT_TIME, move: bool=False, pos='center', return_pos=True, show_window=False) -> None:
        """
        x: int, if < 0, click self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, click self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        simulateMove: bool, if True, first move cursor to control smoothly.
        waitTime: float.

        Click(), Click(ratioX=0.5, ratioY=0.5): click center.
        Click(10, 10): click left+10, top+10.
        Click(-10, -10): click right-10, bottom-10.
        """
        # if move:
        #     pos = win32api.GetCursorPos()
        #     point = self.MoveCursorToInnerPos(x, y, ratioX, ratioY, simulateMove)
        #     if point:
        #         Click(point[0], point[1], waitTime)
        #     if return_pos:
        #         win32api.SetCursorPos(pos)
        # else:
        #     if not hasattr(self, 'winapi'):
        #         self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        #     self.winapi.click_by_bbox(self.BoundingRectangle, xbias=x, ybias=y, pos=pos, activate=show_window)
        if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        self.winapi.click_by_bbox(self.BoundingRectangle, xbias=x, ybias=y, pos=pos, activate=show_window, move=move)

    def Flash(self, color=0x0000FF):
        """
        color: int, RGB color.
        Flash the control with color.
        """
        rect = self.BoundingRectangle
        if not rect:
            print('Control has no BoundingRectangle.')
            return
        
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        desktop_hwnd = win32gui.GetDesktopWindow()
        if not hasattr(self, 'winapi'):
            self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        self.winapi._overlay.add_rect(left, top, right, bottom).flash()
        # for i in range(3):
        #     desktop_dc = win32gui.GetWindowDC(desktop_hwnd)
        #     brush = win32gui.CreateSolidBrush(color)
        #     rect_tuple = (left, top, right, bottom)
        #     win32gui.FrameRect(desktop_dc, rect_tuple, brush)
        #     time.sleep(0.5)
        #     win32gui.InvalidateRect(desktop_hwnd, rect_tuple, True)
        #     win32gui.ReleaseDC(desktop_hwnd, desktop_dc)
        #     self.Hover()
        #     time.sleep(0.5)

    def Hover(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, simulateMove: bool = True, waitTime: float = OPERATION_WAIT_TIME, move: bool=False) -> None:
        """
        x: int, if < 0, hover self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, hover self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        simulateMove: bool, if True, first move cursor to control smoothly.
        waitTime: float.
        
        Hover(), Hover(ratioX=0.5, ratioY=0.5): hover center.
        Hover(10, 10): hover left+10, top+10.
        Hover(-10, -10): hover right-10, bottom-10.
        """
        if move:
            point = self.MoveCursorToInnerPos(x, y, ratioX, ratioY, simulateMove)
            # if point:
            #     Hover(point[0], point[1], waitTime)
        else:
            if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
            self.winapi.hover_by_bbox(self.BoundingRectangle, xbias=x, ybias=y)

    def MiddleClick(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, simulateMove: bool = True, waitTime: float = OPERATION_WAIT_TIME, move: bool=False, show_window=False) -> None:
        """
        x: int, if < 0, middle click self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, middle click self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        simulateMove: bool, if True, first move cursor to control smoothly.
        waitTime: float.

        MiddleClick(), MiddleClick(ratioX=0.5, ratioY=0.5): middle click center.
        MiddleClick(10, 10): middle click left+10, top+10.
        MiddleClick(-10, -10): middle click right-10, bottom-10.
        """
        if move:
            point = self.MoveCursorToInnerPos(x, y, ratioX, ratioY, simulateMove)
            if point:
                MiddleClick(point[0], point[1], waitTime)
        else:
            if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
            self.winapi.click_by_bbox(self.BoundingRectangle, button='mid', xbias=x, ybias=y, activate=show_window)

    def RightClick(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, simulateMove: bool = True, waitTime: float = OPERATION_WAIT_TIME, move=False, pos='center', show_window=False) -> None:
        """
        x: int, if < 0, right click self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, right click self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        simulateMove: bool, if True, first move cursor to control smoothly.
        waitTime: float.

        RightClick(), RightClick(ratioX=0.5, ratioY=0.5): right click center.
        RightClick(10, 10): right click left+10, top+10.
        RightClick(-10, -10): right click right-10, bottom-10.
        """
        if move:
            point = self.MoveCursorToInnerPos(x, y, ratioX, ratioY, simulateMove)
            if point:
                RightClick(point[0], point[1], waitTime)
        else:
            if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
            self.winapi.click_by_bbox(self.BoundingRectangle, button='right', xbias=x, ybias=y, pos=pos, activate=show_window)

    def DoubleClick(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, simulateMove: bool = True, waitTime: float = OPERATION_WAIT_TIME, move=False, show_window=False) -> None:
        """
        x: int, if < 0, right click self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, right click self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        simulateMove: bool, if True, first move cursor to control smoothly.
        waitTime: float.

        DoubleClick(), DoubleClick(ratioX=0.5, ratioY=0.5): double click center.
        DoubleClick(10, 10): double click left+10, top+10.
        DoubleClick(-10, -10): double click right-10, bottom-10.
        """
        if move:
            x, y = self.MoveCursorToInnerPos(x, y, ratioX, ratioY, simulateMove)
            Click(x, y, GetDoubleClickTime() * 1.0 / 2000)
            Click(x, y, waitTime)
        else:
            if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
            self.winapi.click_by_bbox(self.BoundingRectangle, double_click=True, activate=show_window)

    def ShortcutPaste(self, click=True, move=False) -> None:
        """
        Paste content from clipboard like Ctrl+V.
        click: bool, if True, first click control.
        """
        if click:
            self.Click(move=move, simulateMove=False, return_pos=False)
        if not hasattr(self, 'winapi'):
            self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        self.winapi.shortcut_paste()

    def ShortcutSearch(self, click=True, move=False) -> None:
        """
        Search content from clipboard like Ctrl+F.
        click: bool, if True, first click control.
        """
        if click:
            self.Click(move=move, simulateMove=False, return_pos=False)
        if not hasattr(self, 'winapi'):
            self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        self.winapi.shortcut_search()

    def ShortcutSelectAll(self, click=True, move=False) -> None:
        """
        Select all content like Ctrl+A.
        click: bool, if True, first click control.
        """
        if click:
            self.Click(move=move, simulateMove=False, return_pos=False)
        if not hasattr(self, 'winapi'):
            self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        self.winapi.shortcut_select_all()

    def ShortcutCopy(self, click=True, move=False) -> None:
        """
        Paste content from clipboard like Ctrl+V.
        click: bool, if True, first click control.
        """
        if click:
            self.Click(move=move, simulateMove=False, return_pos=False)
        if not hasattr(self, 'winapi'):
            self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        self.winapi.shortcut_copy()

    def DragDrop(self, x1: int, y1: int, x2: int, y2: int, moveSpeed: float=1, waitTime: float = OPERATION_WAIT_TIME) -> None:
        rect = self.BoundingRectangle
        if rect.width() == 0 or rect.height() == 0:
            Logger.ColorfullyLog('<Color=Yellow>Can not move cursor</Color>. {}\'s BoundingRectangle is {}. SearchProperties: {}'.format(
                self.ControlTypeName, rect, self.GetColorfulSearchPropertiesStr()))
            return
        x1 = (rect.left if x1 >= 0 else rect.right) + x1
        y1 = (rect.top if y1 >= 0 else rect.bottom) + y1
        x2 = (rect.left if x2 >= 0 else rect.right) + x2
        y2 = (rect.top if y2 >= 0 else rect.bottom) + y2
        DragDrop(x1, y1, x2, y2, moveSpeed, waitTime)

    def WheelDown(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, wheelTimes: int = 1, interval: float = 0.05, waitTime: float = OPERATION_WAIT_TIME, api=True) -> None:
        """
        Make control have focus first, move cursor to the specified position and mouse wheel down.
        x: int, if < 0, move x cursor to self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, move y cursor to self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        wheelTimes: int.
        interval: float.
        waitTime: float.
        """
        if api:
            if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
            self.winapi.scroll_wheel(self.BoundingRectangle, wheelTimes*(-120))
        else:
            cursorX, cursorY = GetCursorPos()
            self.SetFocus()
            self.MoveCursorToInnerPos(x, y, ratioX, ratioY, simulateMove=False)
            WheelDown(wheelTimes, interval, waitTime)
            SetCursorPos(cursorX, cursorY)

    def WheelUp(self, x: int = None, y: int = None, ratioX: float = 0.5, ratioY: float = 0.5, wheelTimes: int = 1, interval: float = 0.05, waitTime: float = OPERATION_WAIT_TIME, api=True) -> None:
        """
        Make control have focus first, move cursor to the specified position and mouse wheel up.
        x: int, if < 0, move x cursor to self.BoundingRectangle.right + x, if not None, ignore ratioX.
        y: int, if < 0, move y cursor to self.BoundingRectangle.bottom + y, if not None, ignore ratioY.
        ratioX: float.
        ratioY: float.
        wheelTimes: int.
        interval: float.
        waitTime: float.
        """
        if api:
            if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
            self.winapi.scroll_wheel(self.BoundingRectangle, wheelTimes*120)
        else:
            cursorX, cursorY = GetCursorPos()
            self.SetFocus()
            self.MoveCursorToInnerPos(x, y, ratioX, ratioY, simulateMove=False)
            WheelUp(wheelTimes, interval, waitTime)
            SetCursorPos(cursorX, cursorY)

    def ShowWindow(self, cmdShow: int, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Get a native handle from self or ancestors until valid and call native `ShowWindow` with cmdShow.
        cmdShow: int, a value in in class `SW`.
        waitTime: float.
        Return bool, True if succeed otherwise False.
        """
        handle = self.NativeWindowHandle
        if not handle:
            control = self
            while not handle:
                control = control.GetParentControl()
                handle = control.NativeWindowHandle
        if handle:
            ret = ShowWindow(handle, cmdShow)
            time.sleep(waitTime)
            return ret

    def Show(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call native `ShowWindow(SW.Show)`.
        Return bool, True if succeed otherwise False.
        """
        return self.ShowWindow(SW.Show, waitTime)

    def Hide(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Call native `ShowWindow(SW.Hide)`.
        waitTime: float
        Return bool, True if succeed otherwise False.
        """
        return self.ShowWindow(SW.Hide, waitTime)

    def MoveWindow(self, x: int, y: int, width: int, height: int, repaint: bool = True) -> bool:
        """
        Call native MoveWindow if control has a valid native handle.
        x: int.
        y: int.
        width: int.
        height: int.
        repaint: bool.
        Return bool, True if succeed otherwise False.
        """
        handle = self.NativeWindowHandle
        if handle:
            return MoveWindow(handle, x, y, width, height, int(repaint))
        return False

    def GetWindowText(self) -> str:
        """
        Call native GetWindowText if control has a valid native handle.
        """
        handle = self.NativeWindowHandle
        if handle:
            return GetWindowText(handle)

    def SetWindowText(self, text: str) -> bool:
        """
        Call native SetWindowText if control has a valid native handle.
        """
        handle = self.NativeWindowHandle
        if handle:
            return SetWindowText(handle, text)
        return False

    def SendKey(self, key: int, waitTime: float = OPERATION_WAIT_TIME) -> None:
        """
        Make control have focus first and type a key.
        `self.SetFocus` may not work for some controls, you may need to click it to make it have focus.
        key: int, a key code value in class Keys.
        waitTime: float.
        """
        self.SetFocus()
        SendKey(key, waitTime)

    def Input(self, text: str, waitTime: float = -1) -> None:
        """
        Input text to edit control.
        text: str.
        waitTime: float. If < 0 use the random time between 0.01s and 0.05s per char.
        """
        if not hasattr(self, 'winapi'):
            self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
        self.winapi.input(text, waitTime)

    def Paste(self, text: str):
        pyperclip.copy(text)
        self.ShortcutPaste()

    def SendKeys(self, text: str, interval: float = 0.01, waitTime: float = OPERATION_WAIT_TIME, charMode: bool = True, api=True) -> None:
        """
        Make control have focus first and type keys.
        `self.SetFocus` may not work for some controls, you may need to click it to make it have focus.
        text: str, keys to type, see the docstring of `SendKeys`.
        interval: float, seconds between keys.
        waitTime: float.
        charMode: bool, if False, the text typied is depend on the input method if a input method is on.
        """
        if api:
            if not hasattr(self, 'winapi'):
                self.winapi = Win32(self.GetTopLevelControl().NativeWindowHandle)
            self.winapi.send_keys_shortcut(text)
        else:
            self.SetFocus()
            SendKeys(text, interval, waitTime, charMode)

    def GetPixelColor(self, x: int, y: int) -> int:
        """
        Call native `GetPixelColor` if control has a valid native handle.
        Use `self.ToBitmap` if control doesn't have a valid native handle or you get many pixels.
        x: int, internal x position.
        y: int, internal y position.
        Return int, a color value in bgr.
        r = bgr & 0x0000FF
        g = (bgr & 0x00FF00) >> 8
        b = (bgr & 0xFF0000) >> 16
        """
        handle = self.NativeWindowHandle
        if handle:
            return GetPixelColor(x, y, handle)

    def ToBitmap(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0) -> Bitmap:
        """
        Capture control to a Bitmap object.
        x, y: int, the point in control's internal position(from 0,0).
        width, height: int, image's width and height from x, y, use 0 for entire area.
                       If width(or height) < 0, image size will be control's width(or height) - width(or height).
        """
        bitmap = Bitmap()
        bitmap.FromControl(self, x, y, width, height)
        return bitmap

    def CaptureToImage(self, savePath: str, x: int = 0, y: int = 0, width: int = 0, height: int = 0) -> bool:
        """
        Capture control to a image file.
        savePath: str, should end with .bmp, .jpg, .jpeg, .png, .gif, .tif, .tiff.
        x, y: int, the point in control's internal position(from 0,0).
        width, height: int, image's width and height from x, y, use 0 for entire area.
                       If width(or height) < 0, image size will be control's width(or height) - width(or height).
        Return bool, True if succeed otherwise False.
        """
        bitmap = Bitmap()
        if bitmap.FromControl(self, x, y, width, height):
            return bitmap.ToFile(savePath)
        return False

    def IsTopLevel(self) -> bool:
        """Determine whether current control is top level."""
        handle = self.NativeWindowHandle
        if handle:
            return GetAncestor(handle, GAFlag.Root) == handle
        return False

    def GetTopLevelControl(self) -> 'Control':
        """
        Get the top level control which current control lays.
        If current control is top level, return self.
        If current control is root control, return None.
        Return `PaneControl` or `WindowControl` or None.
        """
        handle = self.NativeWindowHandle
        if handle:
            topHandle = GetAncestor(handle, GAFlag.Root)
            if topHandle:
                if topHandle == handle:
                    return self
                else:
                    return ControlFromHandle(topHandle)
            else:
                #self is root control
                pass
        else:
            control = self
            while True:
                control = control.GetParentControl()
                handle = control.NativeWindowHandle
                if handle:
                    topHandle = GetAncestor(handle, GAFlag.Root)
                    return ControlFromHandle(topHandle)

    def Control(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'Control':
        return Control(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ButtonControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ButtonControl':
        return ButtonControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def CalendarControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'CalendarControl':
        return CalendarControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def CheckBoxControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'CheckBoxControl':
        return CheckBoxControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ComboBoxControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ComboBoxControl':
        return ComboBoxControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def CustomControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'CustomControl':
        return CustomControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def DataGridControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'DataGridControl':
        return DataGridControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def DataItemControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'DataItemControl':
        return DataItemControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def DocumentControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'DocumentControl':
        return DocumentControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def EditControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'EditControl':
        return EditControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def GroupControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'GroupControl':
        return GroupControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def HeaderControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'HeaderControl':
        return HeaderControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def HeaderItemControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'HeaderItemControl':
        return HeaderItemControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def HyperlinkControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'HyperlinkControl':
        return HyperlinkControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ImageControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ImageControl':
        return ImageControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ListControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'listControl':
        return ListControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ListItemControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ListItemControl':
        return ListItemControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def MenuControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'MenuControl':
        return MenuControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def MenuBarControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'MenuBarControl':
        return MenuBarControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def MenuItemControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'MenuItemControl':
        return MenuItemControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def PaneControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'PaneControl':
        return PaneControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ProgressBarControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ProgressBarControl':
        return ProgressBarControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def RadioButtonControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'RadioButtonControl':
        return RadioButtonControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ScrollBarControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ScrollBarControl':
        return ScrollBarControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def SemanticZoomControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'SemanticZoomControl':
        return SemanticZoomControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def SeparatorControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'SeparatorControl':
        return SeparatorControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def SliderControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'SliderControl':
        return SliderControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def SpinnerControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'SpinnerControl':
        return SpinnerControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def SplitButtonControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'SplitButtonControl':
        return SplitButtonControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def StatusBarControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'StatusBarControl':
        return StatusBarControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def TabControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'TabControl':
        return TabControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def TabItemControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'TabItemControl':
        return TabItemControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def TableControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'TableControl':
        return TableControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def TextControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'TextControl':
        return TextControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ThumbControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ThumbControl':
        return ThumbControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def TitleBarControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'TitleBarControl':
        return TitleBarControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ToolBarControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ToolBarControl':
        return ToolBarControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def ToolTipControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'ToolTipControl':
        return ToolTipControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def TreeControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'TreeControl':
        return TreeControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def TreeItemControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'TreeItemControl':
        return TreeItemControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)

    def WindowControl(self, searchDepth=0xFFFFFFFF, searchInterval=SEARCH_INTERVAL, foundIndex=1, element=0, **searchProperties) -> 'WindowControl':
        return WindowControl(searchDepth=searchDepth, searchInterval=searchInterval, foundIndex=foundIndex, element=element, searchFromControl=self, **searchProperties)


class AppBarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.AppBarControl)


class ButtonControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ButtonControl)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetInvokePattern(self) -> InvokePattern:
        """
        Return `InvokePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.InvokePattern)

    def GetTogglePattern(self) -> TogglePattern:
        """
        Return `TogglePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TogglePattern)


class CalendarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.CalendarControl)

    def GetGridPattern(self) -> GridPattern:
        """
        Return `GridPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.GridPattern)

    def GetTablePattern(self) -> TablePattern:
        """
        Return `TablePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.TablePattern)

    def GetScrollPattern(self) -> ScrollPattern:
        """
        Return `ScrollPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollPattern)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)


class CheckBoxControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.CheckBoxControl)

    def GetTogglePattern(self) -> TogglePattern:
        """
        Return `TogglePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.TogglePattern)


class ComboBoxControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ComboBoxControl)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)

    def Select(self, itemName: str = '', condition: Callable[[str], bool] = None, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Show combobox's popup menu and select a item by name.
        itemName: str.
        condition: Callable[[str], bool], function(comboBoxItemName: str) -> bool, if condition is valid, ignore itemName.
        waitTime: float.
        Some comboboxs doesn't support SelectionPattern, here is a workaround.
        This method tries to add selection support.
        It may not work for some comboboxes, such as comboboxes in older Qt version.
        If it doesn't work, you should write your own version Select, or it doesn't support selection at all.
        """
        expandCollapsePattern = self.GetExpandCollapsePattern()
        if expandCollapsePattern:
            expandCollapsePattern.Expand()
        else:
            #Windows Form's ComboBoxControl doesn't support ExpandCollapsePattern
            self.Click(x=-10, ratioY=0.5, simulateMove=False)
        find = False
        if condition:
            listItemControl = self.ListItemControl(Compare=lambda c, d: condition(c.Name))
        else:
            listItemControl = self.ListItemControl(Name=itemName)
        if listItemControl.Exists(1):
            scrollItemPattern = listItemControl.GetScrollItemPattern()
            if scrollItemPattern:
                scrollItemPattern.ScrollIntoView(waitTime=0.1)
            listItemControl.Click(waitTime=waitTime)
            find = True
        else:
            #ComboBox's popup window is a child of root control
            listControl = ListControl(searchDepth= 1)
            if listControl.Exists(1):
                if condition:
                    listItemControl = listControl.ListItemControl(Compare=lambda c, d: condition(c.Name))
                else:
                    listItemControl = listControl.ListItemControl(Name=itemName)
                if listItemControl.Exists(0, 0):
                    scrollItemPattern = listItemControl.GetScrollItemPattern()
                    if scrollItemPattern:
                        scrollItemPattern.ScrollIntoView(waitTime=0.1)
                    listItemControl.Click(waitTime=waitTime)
                    find = True
        if not find:
            Logger.ColorfullyLog('Can\'t find <Color=Cyan>{}</Color> in ComboBoxControl or it does not support selection.'.format(itemName), ConsoleColor.Yellow)
            if expandCollapsePattern:
                expandCollapsePattern.Collapse(waitTime)
            else:
                self.Click(x=-10, ratioY=0.5, simulateMove=False, waitTime=waitTime)
        return find


class CustomControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.CustomControl)


class DataGridControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.DataGridControl)

    def GetGridPattern(self) -> GridPattern:
        """
        Return `GridPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.GridPattern)

    def GetScrollPattern(self) -> ScrollPattern:
        """
        Return `ScrollPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollPattern)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)

    def GetTablePattern(self) -> TablePattern:
        """
        Return `TablePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TablePattern)


class DataItemControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.DataItemControl)

    def GetSelectionItemPattern(self) -> SelectionItemPattern:
        """
        Return `SelectionItemPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionItemPattern)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetGridItemPattern(self) -> GridItemPattern:
        """
        Return `GridItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.GridItemPattern)

    def GetScrollItemPattern(self) -> ScrollItemPattern:
        """
        Return `ScrollItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollItemPattern)

    def GetTableItemPattern(self) -> TableItemPattern:
        """
        Return `TableItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TableItemPattern)

    def GetTogglePattern(self) -> TogglePattern:
        """
        Return `TogglePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TogglePattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class DocumentControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.DocumentControl)

    def GetTextPattern(self) -> TextPattern:
        """
        Return `TextPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.TextPattern)

    def GetScrollPattern(self) -> ScrollPattern:
        """
        Return `ScrollPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollPattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class EditControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.EditControl)

    def GetRangeValuePattern(self) -> RangeValuePattern:
        """
        Return `RangeValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.RangeValuePattern)

    def GetTextPattern(self) -> TextPattern:
        """
        Return `TextPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TextPattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class GroupControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.GroupControl)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)


class HeaderControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.HeaderControl)

    def GetTransformPattern(self) -> TransformPattern:
        """
        Return `TransformPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TransformPattern)


class HeaderItemControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.HeaderItemControl)

    def GetInvokePattern(self) -> InvokePattern:
        """
        Return `InvokePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.InvokePattern)

    def GetTransformPattern(self) -> TransformPattern:
        """
        Return `TransformPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TransformPattern)


class HyperlinkControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.HyperlinkControl)

    def GetInvokePattern(self) -> InvokePattern:
        """
        Return `InvokePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.InvokePattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class ImageControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ImageControl)

    def GetGridItemPattern(self) -> GridItemPattern:
        """
        Return `GridItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.GridItemPattern)

    def GetTableItemPattern(self) -> TableItemPattern:
        """
        Return `TableItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TableItemPattern)


class ListControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ListControl)

    def GetGridPattern(self) -> GridPattern:
        """
        Return `GridPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.GridPattern)

    def GetMultipleViewPattern(self) -> MultipleViewPattern:
        """
        Return `MultipleViewPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.MultipleViewPattern)

    def GetScrollPattern(self) -> ScrollPattern:
        """
        Return `ScrollPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollPattern)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)


class ListItemControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ListItemControl)

    def GetSelectionItemPattern(self) -> SelectionItemPattern:
        """
        Return `SelectionItemPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionItemPattern)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetGridItemPattern(self) -> GridItemPattern:
        """
        Return `GridItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.GridItemPattern)

    def GetInvokePattern(self) -> InvokePattern:
        """
        Return `InvokePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.InvokePattern)

    def GetScrollItemPattern(self) -> ScrollItemPattern:
        """
        Return `ScrollItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollItemPattern)

    def GetTogglePattern(self) -> TogglePattern:
        """
        Return `TogglePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TogglePattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class MenuControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.MenuControl)


class MenuBarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.MenuBarControl)

    def GetDockPattern(self) -> DockPattern:
        """
        Return `DockPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.DockPattern)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetTransformPattern(self) -> TransformPattern:
        """
        Return `TransformPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TransformPattern)


class MenuItemControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.MenuItemControl)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetInvokePattern(self) -> InvokePattern:
        """
        Return `InvokePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.InvokePattern)

    def GetSelectionItemPattern(self) -> SelectionItemPattern:
        """
        Return `SelectionItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionItemPattern)

    def GetTogglePattern(self) -> TogglePattern:
        """
        Return `TogglePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TogglePattern)


class TopLevel():
    """Class TopLevel"""
    def SetTopmost(self, isTopmost: bool = True, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Set top level window topmost.
        isTopmost: bool.
        waitTime: float.
        """
        if self.IsTopLevel():
            ret = SetWindowTopmost(self.NativeWindowHandle, isTopmost)
            time.sleep(waitTime)
            return ret
        return False

    def IsTopmost(self) -> bool:
        if self.IsTopLevel():
            WS_EX_TOPMOST = 0x00000008
            return bool(GetWindowLong(self.NativeWindowHandle, GWL.ExStyle) & WS_EX_TOPMOST)
        return False

    def SwitchToThisWindow(self, waitTime: float = OPERATION_WAIT_TIME) -> None:
        if self.IsTopLevel():
            SwitchToThisWindow(self.NativeWindowHandle)
            time.sleep(waitTime)

    def Maximize(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Set top level window maximize.
        """
        if self.IsTopLevel():
            return self.ShowWindow(SW.ShowMaximized, waitTime)
        return False

    def IsMaximize(self) -> bool:
        if self.IsTopLevel():
            return bool(IsZoomed(self.NativeWindowHandle))
        return False

    def Minimize(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        if self.IsTopLevel():
            return self.ShowWindow(SW.Minimize, waitTime)
        return False

    def IsMinimize(self) -> bool:
        if self.IsTopLevel():
            return bool(IsIconic(self.NativeWindowHandle))
        return False

    def Restore(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """
        Restore window to normal state.
        Similar to SwitchToThisWindow.
        """
        if self.IsTopLevel():
            return self.ShowWindow(SW.Restore, waitTime)
        return False

    def MoveToCenter(self) -> bool:
        """
        Move window to screen center.
        """
        if self.IsTopLevel():
            rect = self.BoundingRectangle
            screenWidth, screenHeight = GetScreenSize()
            x, y = (screenWidth - rect.width()) // 2, (screenHeight - rect.height()) // 2
            if x < 0: x = 0
            if y < 0: y = 0
            return SetWindowPos(self.NativeWindowHandle, SWP.HWND_Top, x, y, 0, 0, SWP.SWP_NoSize)
        return False

    def SetActive(self, waitTime: float = OPERATION_WAIT_TIME) -> bool:
        """Set top level window active."""
        if self.IsTopLevel():
            handle = self.NativeWindowHandle
            if IsIconic(handle):
                ret = ShowWindow(handle, SW.Restore)
            elif not IsWindowVisible(handle):
                ret = ShowWindow(handle, SW.Show)
            ret = SetForegroundWindow(handle)  # may fail if foreground windows's process is not python
            time.sleep(waitTime)
            return ret
        return False


class PaneControl(Control, TopLevel):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.PaneControl)

    def GetDockPattern(self) -> DockPattern:
        """
        Return `DockPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.DockPattern)

    def GetScrollPattern(self) -> ScrollPattern:
        """
        Return `ScrollPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollPattern)

    def GetTransformPattern(self) -> TransformPattern:
        """
        Return `TransformPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TransformPattern)


class ProgressBarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ProgressBarControl)

    def GetRangeValuePattern(self) -> RangeValuePattern:
        """
        Return `RangeValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.RangeValuePattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class RadioButtonControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.RadioButtonControl)

    def GetSelectionItemPattern(self) -> SelectionItemPattern:
        """
        Return `SelectionItemPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionItemPattern)


class ScrollBarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ScrollBarControl)

    def GetRangeValuePattern(self) -> RangeValuePattern:
        """
        Return `RangeValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.RangeValuePattern)


class SemanticZoomControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.SemanticZoomControl)


class SeparatorControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.SeparatorControl)


class SliderControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.SliderControl)

    def GetRangeValuePattern(self) -> RangeValuePattern:
        """
        Return `RangeValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.RangeValuePattern)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class SpinnerControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.SpinnerControl)

    def GetRangeValuePattern(self) -> RangeValuePattern:
        """
        Return `RangeValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.RangeValuePattern)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)

    def GetValuePattern(self) -> ValuePattern:
        """
        Return `ValuePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ValuePattern)


class SplitButtonControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.SplitButtonControl)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetInvokePattern(self) -> InvokePattern:
        """
        Return `InvokePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.InvokePattern)


class StatusBarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.StatusBarControl)

    def GetGridPattern(self) -> GridPattern:
        """
        Return `GridPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.GridPattern)


class TabControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.TabControl)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)

    def GetScrollPattern(self) -> ScrollPattern:
        """
        Return `ScrollPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollPattern)


class TabItemControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.TabItemControl)

    def GetSelectionItemPattern(self) -> SelectionItemPattern:
        """
        Return `SelectionItemPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionItemPattern)


class TableControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.TableControl)

    def GetGridPattern(self) -> GridPattern:
        """
        Return `GridPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.GridPattern)

    def GetGridItemPattern(self) -> GridItemPattern:
        """
        Return `GridItemPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.GridItemPattern)

    def GetTablePattern(self) -> TablePattern:
        """
        Return `TablePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.TablePattern)

    def GetTableItemPattern(self) -> TableItemPattern:
        """
        Return `TableItemPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.TableItemPattern)


class TextControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.TextControl)

    def GetGridItemPattern(self) -> GridItemPattern:
        """
        Return `GridItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.GridItemPattern)

    def GetTableItemPattern(self) -> TableItemPattern:
        """
        Return `TableItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TableItemPattern)

    def GetTextPattern(self) -> TextPattern:
        """
        Return `TextPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TextPattern)


class ThumbControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ThumbControl)

    def GetTransformPattern(self) -> TransformPattern:
        """
        Return `TransformPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.TransformPattern)


class TitleBarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.TitleBarControl)


class ToolBarControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ToolBarControl)

    def GetDockPattern(self) -> DockPattern:
        """
        Return `DockPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.DockPattern)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetTransformPattern(self) -> TransformPattern:
        """
        Return `TransformPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TransformPattern)


class ToolTipControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.ToolTipControl)

    def GetTextPattern(self) -> TextPattern:
        """
        Return `TextPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TextPattern)

    def GetWindowPattern(self) -> WindowPattern:
        """
        Return `WindowPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.WindowPattern)


class TreeControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.TreeControl)

    def GetScrollPattern(self) -> ScrollPattern:
        """
        Return `ScrollPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollPattern)

    def GetSelectionPattern(self) -> SelectionPattern:
        """
        Return `SelectionPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionPattern)


class TreeItemControl(Control):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.TreeItemControl)

    def GetExpandCollapsePattern(self) -> ExpandCollapsePattern:
        """
        Return `ExpandCollapsePattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.ExpandCollapsePattern)

    def GetInvokePattern(self) -> InvokePattern:
        """
        Return `InvokePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.InvokePattern)

    def GetScrollItemPattern(self) -> ScrollItemPattern:
        """
        Return `ScrollItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.ScrollItemPattern)

    def GetSelectionItemPattern(self) -> SelectionItemPattern:
        """
        Return `SelectionItemPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.SelectionItemPattern)

    def GetTogglePattern(self) -> TogglePattern:
        """
        Return `TogglePattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.TogglePattern)


class WindowControl(Control, TopLevel):
    def __init__(self, searchFromControl: Control = None, searchDepth: int = 0xFFFFFFFF, searchInterval: float = SEARCH_INTERVAL, foundIndex: int = 1, element=None, **searchProperties):
        Control.__init__(self, searchFromControl, searchDepth, searchInterval, foundIndex, element, **searchProperties)
        self.AddSearchProperties(ControlType=ControlType.WindowControl)
        self._DockPattern = None
        self._TransformPattern = None

    def GetTransformPattern(self) -> TransformPattern:
        """
        Return `TransformPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.TransformPattern)

    def GetWindowPattern(self) -> WindowPattern:
        """
        Return `WindowPattern` if it supports the pattern else None(Must support according to MSDN).
        """
        return self.GetPattern(PatternId.WindowPattern)

    def GetDockPattern(self) -> DockPattern:
        """
        Return `DockPattern` if it supports the pattern else None(Conditional support according to MSDN).
        """
        return self.GetPattern(PatternId.DockPattern)

    def MetroClose(self, waitTime: float = OPERATION_WAIT_TIME) -> None:
        """
        Only work on Windows 8/8.1, if current window is Metro UI.
        waitTime: float.
        """
        if self.ClassName == METRO_WINDOW_CLASS_NAME:
            screenWidth, screenHeight = GetScreenSize()
            MoveTo(screenWidth // 2, 0, waitTime=0)
            DragDrop(screenWidth // 2, 0, screenWidth // 2, screenHeight, waitTime=waitTime)
        else:
            Logger.WriteLine('Window is not Metro!', ConsoleColor.Yellow)


ControlConstructors = {
    ControlType.AppBarControl: AppBarControl,
    ControlType.ButtonControl: ButtonControl,
    ControlType.CalendarControl: CalendarControl,
    ControlType.CheckBoxControl: CheckBoxControl,
    ControlType.ComboBoxControl: ComboBoxControl,
    ControlType.CustomControl: CustomControl,
    ControlType.DataGridControl: DataGridControl,
    ControlType.DataItemControl: DataItemControl,
    ControlType.DocumentControl: DocumentControl,
    ControlType.EditControl: EditControl,
    ControlType.GroupControl: GroupControl,
    ControlType.HeaderControl: HeaderControl,
    ControlType.HeaderItemControl: HeaderItemControl,
    ControlType.HyperlinkControl: HyperlinkControl,
    ControlType.ImageControl: ImageControl,
    ControlType.ListControl: ListControl,
    ControlType.ListItemControl: ListItemControl,
    ControlType.MenuBarControl: MenuBarControl,
    ControlType.MenuControl: MenuControl,
    ControlType.MenuItemControl: MenuItemControl,
    ControlType.PaneControl: PaneControl,
    ControlType.ProgressBarControl: ProgressBarControl,
    ControlType.RadioButtonControl: RadioButtonControl,
    ControlType.ScrollBarControl: ScrollBarControl,
    ControlType.SemanticZoomControl: SemanticZoomControl,
    ControlType.SeparatorControl: SeparatorControl,
    ControlType.SliderControl: SliderControl,
    ControlType.SpinnerControl: SpinnerControl,
    ControlType.SplitButtonControl: SplitButtonControl,
    ControlType.StatusBarControl: StatusBarControl,
    ControlType.TabControl: TabControl,
    ControlType.TabItemControl: TabItemControl,
    ControlType.TableControl: TableControl,
    ControlType.TextControl: TextControl,
    ControlType.ThumbControl: ThumbControl,
    ControlType.TitleBarControl: TitleBarControl,
    ControlType.ToolBarControl: ToolBarControl,
    ControlType.ToolTipControl: ToolTipControl,
    ControlType.TreeControl: TreeControl,
    ControlType.TreeItemControl: TreeItemControl,
    ControlType.WindowControl: WindowControl,
}


class UIAutomationInitializerInThread:
    def __init__(self, debug: bool = False):
        self.debug = debug
        InitializeUIAutomationInCurrentThread()
        if self.debug:
            th = threading.currentThread()
            print('\ncall InitializeUIAutomationInCurrentThread in {}'.format(th))

    def __del__(self):
        UninitializeUIAutomationInCurrentThread()
        if self.debug:
            th = threading.currentThread()
            print('\ncall UninitializeUIAutomationInCurrentThread in {}'.format(th))


def InitializeUIAutomationInCurrentThread() -> None:
    """
    Initialize UIAutomation in a new thread.
    If you want to use functionalities related to Controls and Patterns in a new thread.
    You must call this function first in the new thread.
    But you can't use use a Control or a Pattern created in a different thread.
    So you can't create a Control or a Pattern in main thread and then pass it to a new thread and use it.
    """
    comtypes.CoInitializeEx()
    SetDpiAwareness(dpiAwarenessPerMonitor=True)


def UninitializeUIAutomationInCurrentThread() -> None:
    """
    Uninitialize UIAutomation in a new thread after calling InitializeUIAutomationInCurrentThread.
    You must call this function when the new thread exits if you have called InitializeUIAutomationInCurrentThread in the same thread.
    """
    comtypes.CoUninitialize()


def SetGlobalSearchTimeout(seconds: float) -> None:
    """
    seconds: float.
    To make this available, you need explicitly import uiautomation:
        from uiautomation import uiautomation as auto
        auto.SetGlobalSearchTimeout(10)
    """
    global TIME_OUT_SECOND
    TIME_OUT_SECOND = seconds


def WaitForExist(control: Control, timeout: float) -> bool:
    """
    Check if control exists in timeout seconds.
    control: `Control` or its subclass.
    timeout: float.
    Return bool.
    """
    return control.Exists(timeout, 1)


def WaitForDisappear(control: Control, timeout: float) -> bool:
    """
    Check if control disappears in timeout seconds.
    control: `Control` or its subclass.
    timeout: float.
    Return bool.
    """
    return control.Disappears(timeout, 1)


def WalkTree(top, getChildren: Callable[[TreeNode], List[TreeNode]] = None,
             getFirstChild: Callable[[TreeNode], TreeNode] = None, getNextSibling: Callable[[TreeNode], TreeNode] = None,
             yieldCondition: Callable[[TreeNode, int], bool] = None, includeTop: bool = False, maxDepth: int = 0xFFFFFFFF):
    """
    Walk a tree not using recursive algorithm.
    top: a tree node.
    getChildren: Callable[[TreeNode], List[TreeNode]], function(treeNode: TreeNode) -> List[TreeNode].
    getNextSibling: Callable[[TreeNode], TreeNode], function(treeNode: TreeNode) -> TreeNode.
    getNextSibling: Callable[[TreeNode], TreeNode], function(treeNode: TreeNode) -> TreeNode.
    yieldCondition: Callable[[TreeNode, int], bool], function(treeNode: TreeNode, depth: int) -> bool.
    includeTop: bool, if True yield top first.
    maxDepth: int, enum depth.

    If getChildren is valid, ignore getFirstChild and getNextSibling,
        yield 3 items tuple: (treeNode, depth, remain children count in current depth).
    If getChildren is not valid, using getFirstChild and getNextSibling,
        yield 2 items tuple: (treeNode, depth).
    If yieldCondition is not None, only yield tree nodes that yieldCondition(treeNode: TreeNode, depth: int)->bool returns True.

    For example:
    def GetDirChildren(dir_):
        if os.path.isdir(dir_):
            return [os.path.join(dir_, it) for it in os.listdir(dir_)]
    for it, depth, leftCount in WalkTree('D:\\', getChildren= GetDirChildren):
        print(it, depth, leftCount)
    """
    if maxDepth <= 0:
        return
    depth = 0
    if getChildren:
        if includeTop:
            if not yieldCondition or yieldCondition(top, 0):
                yield top, 0, 0
        children = getChildren(top)
        childList = [children]
        while depth >= 0:   #or while childList:
            lastItems = childList[-1]
            if lastItems:
                if not yieldCondition or yieldCondition(lastItems[0], depth + 1):
                    yield lastItems[0], depth + 1, len(lastItems) - 1
                if depth + 1 < maxDepth:
                    children = getChildren(lastItems[0])
                    if children:
                        depth += 1
                        childList.append(children)
                del lastItems[0]
            else:
                del childList[depth]
                depth -= 1
    elif getFirstChild and getNextSibling:
        if includeTop:
            if not yieldCondition or yieldCondition(top, 0):
                yield top, 0
        child = getFirstChild(top)
        childList = [child]
        while depth >= 0:  #or while childList:
            lastItem = childList[-1]
            if lastItem:
                if not yieldCondition or yieldCondition(lastItem, depth + 1):
                    yield lastItem, depth + 1
                child = getNextSibling(lastItem)
                childList[depth] = child
                if depth + 1 < maxDepth:
                    child = getFirstChild(lastItem)
                    if child:
                        depth += 1
                        childList.append(child)
            else:
                del childList[depth]
                depth -= 1


def GetRootControl() -> PaneControl:
    """
    Get root control, the Desktop window.
    Return `PaneControl`.
    """
    return Control.CreateControlFromElement(_AutomationClient.instance().IUIAutomation.GetRootElement())


def GetFocusedControl() -> Control:
    """Return `Control` subclass."""
    return Control.CreateControlFromElement(_AutomationClient.instance().IUIAutomation.GetFocusedElement())


def GetForegroundControl() -> Control:
    """Return `Control` subclass."""
    return ControlFromHandle(GetForegroundWindow())
    #another implement
    #focusedControl = GetFocusedControl()
    #parentControl = focusedControl
    #controlList = []
    #while parentControl:
        #controlList.insert(0, parentControl)
        #parentControl = parentControl.GetParentControl()
    #if len(controlList) == 1:
        #parentControl = controlList[0]
    #else:
        #parentControl = controlList[1]
    #return parentControl


def GetConsoleWindow() -> WindowControl:
    """Return `WindowControl` or None, a console window that runs python."""
    return ControlFromHandle(ctypes.windll.kernel32.GetConsoleWindow())


def ControlFromPoint(x: int, y: int) -> Control:
    """
    Call IUIAutomation ElementFromPoint x,y. May return None if mouse is over cmd's title bar icon.
    Return `Control` subclass or None.
    """
    element = _AutomationClient.instance().IUIAutomation.ElementFromPoint(ctypes.wintypes.POINT(x, y))
    return Control.CreateControlFromElement(element)


def ControlFromPoint2(x: int, y: int) -> Control:
    """
    Get a native handle from point x,y and call IUIAutomation.ElementFromHandle.
    Return `Control` subclass.
    """
    return Control.CreateControlFromElement(_AutomationClient.instance().IUIAutomation.ElementFromHandle(WindowFromPoint(x, y)))


def ControlFromCursor() -> Control:
    """
    Call ControlFromPoint with current cursor point.
    Return `Control` subclass.
    """
    x, y = GetCursorPos()
    return ControlFromPoint(x, y)


def ControlFromCursor2() -> Control:
    """
    Call ControlFromPoint2 with current cursor point.
    Return `Control` subclass.
    """
    x, y = GetCursorPos()
    return ControlFromPoint2(x, y)


def ControlFromHandle(handle: int) -> Control:
    """
    Call IUIAutomation.ElementFromHandle with a native handle.
    handle: int, a native window handle.
    Return `Control` subclass or None.
    """
    if handle:
        return Control.CreateControlFromElement(_AutomationClient.instance().IUIAutomation.ElementFromHandle(handle))


def ControlsAreSame(control1: Control, control2: Control) -> bool:
    """
    control1: `Control` or its subclass.
    control2: `Control` or its subclass.
    Return bool, True if control1 and control2 represent the same control otherwise False.
    """
    return bool(_AutomationClient.instance().IUIAutomation.CompareElements(control1.Element, control2.Element))


def WalkControl(control: Control, includeTop: bool = False, maxDepth: int = 0xFFFFFFFF):
    """
    control: `Control` or its subclass.
    includeTop: bool, if True, yield (control, 0) first.
    maxDepth: int, enum depth.
    Yield 2 items tuple (control: Control, depth: int).
    """
    if includeTop:
        yield control, 0
    if maxDepth <= 0:
        return
    depth = 0
    child = control.GetFirstChildControl()
    controlList = [child]
    while depth >= 0:
        lastControl = controlList[-1]
        if lastControl:
            yield lastControl, depth + 1
            child = lastControl.GetNextSiblingControl()
            controlList[depth] = child
            if depth + 1 < maxDepth:
                child = lastControl.GetFirstChildControl()
                if child:
                    depth += 1
                    controlList.append(child)
        else:
            del controlList[depth]
            depth -= 1


def LogControl(control: Control, depth: int = 0, showAllName: bool = True, showPid: bool = False) -> None:
    """
    Print and log control's properties.
    control: `Control` or its subclass.
    depth: int, current depth.
    showAllName: bool, if False, print the first 30 characters of control.Name.
    """
    def getKeyName(theDict, theValue):
        for key in theDict:
            if theValue == theDict[key]:
                return key
    indent = ' ' * depth * 4
    Logger.Write('{0}ControlType: '.format(indent))
    Logger.Write(control.ControlTypeName, ConsoleColor.DarkGreen)
    Logger.Write('    ClassName: ')
    Logger.Write(control.ClassName, ConsoleColor.DarkGreen)
    Logger.Write('    AutomationId: ')
    Logger.Write(control.AutomationId, ConsoleColor.DarkGreen)
    Logger.Write('    Rect: ')
    Logger.Write(control.BoundingRectangle, ConsoleColor.DarkGreen)
    Logger.Write('    Name: ')
    Logger.Write(control.Name, ConsoleColor.DarkGreen, printTruncateLen=0 if showAllName else 30)
    Logger.Write('    Handle: ')
    Logger.Write('0x{0:X}({0})'.format(control.NativeWindowHandle), ConsoleColor.DarkGreen)
    Logger.Write('    Depth: ')
    Logger.Write(depth, ConsoleColor.DarkGreen)
    if showPid:
        Logger.Write('    ProcessId: ')
        Logger.Write(control.ProcessId, ConsoleColor.DarkGreen)
    supportedPatterns = list(filter(lambda t: t[0], ((control.GetPattern(id_), name) for id_, name in PatternIdNames.items())))
    for pt, name in supportedPatterns:
        if isinstance(pt, ValuePattern):
            Logger.Write('    ValuePattern.Value: ')
            Logger.Write(pt.Value, ConsoleColor.DarkGreen, printTruncateLen=0 if showAllName else 30)
        elif isinstance(pt, RangeValuePattern):
            Logger.Write('    RangeValuePattern.Value: ')
            Logger.Write(pt.Value, ConsoleColor.DarkGreen)
        elif isinstance(pt, TogglePattern):
            Logger.Write('    TogglePattern.ToggleState: ')
            Logger.Write('ToggleState.' + getKeyName(ToggleState.__dict__, pt.ToggleState), ConsoleColor.DarkGreen)
        elif isinstance(pt, SelectionItemPattern):
            Logger.Write('    SelectionItemPattern.IsSelected: ')
            Logger.Write(pt.IsSelected, ConsoleColor.DarkGreen)
        elif isinstance(pt, ExpandCollapsePattern):
            Logger.Write('    ExpandCollapsePattern.ExpandCollapseState: ')
            Logger.Write('ExpandCollapseState.' + getKeyName(ExpandCollapseState.__dict__, pt.ExpandCollapseState), ConsoleColor.DarkGreen)
        elif isinstance(pt, ScrollPattern):
            Logger.Write('    ScrollPattern.HorizontalScrollPercent: ')
            Logger.Write(pt.HorizontalScrollPercent, ConsoleColor.DarkGreen)
            Logger.Write('    ScrollPattern.VerticalScrollPercent: ')
            Logger.Write(pt.VerticalScrollPercent, ConsoleColor.DarkGreen)
        elif isinstance(pt, GridPattern):
            Logger.Write('    GridPattern.RowCount: ')
            Logger.Write(pt.RowCount, ConsoleColor.DarkGreen)
            Logger.Write('    GridPattern.ColumnCount: ')
            Logger.Write(pt.ColumnCount, ConsoleColor.DarkGreen)
        elif isinstance(pt, GridItemPattern):
            Logger.Write('    GridItemPattern.Row: ')
            Logger.Write(pt.Column, ConsoleColor.DarkGreen)
            Logger.Write('    GridItemPattern.Column: ')
            Logger.Write(pt.Column, ConsoleColor.DarkGreen)
        elif isinstance(pt, TextPattern):
            # issue 49: CEF Control as DocumentControl have no "TextPattern.Text" property, skip log this part.
            # https://docs.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-get_documentrange
            try:
                Logger.Write('    TextPattern.Text: ')
                Logger.Write(pt.DocumentRange.GetText(30), ConsoleColor.DarkGreen)
            except comtypes.COMError as ex:
                pass
    Logger.Write('    SupportedPattern:')
    for pt, name in supportedPatterns:
        Logger.Write(' ' + name, ConsoleColor.DarkGreen)
    Logger.Write('\n')


def EnumAndLogControl(control: Control, maxDepth: int = 0xFFFFFFFF, showAllName: bool = True, showPid: bool = False, startDepth: int = 0) -> None:
    """
    Print and log control and its descendants' propertyies.
    control: `Control` or its subclass.
    maxDepth: int, enum depth.
    showAllName: bool, if False, print the first 30 characters of control.Name.
    startDepth: int, control's current depth.
    """
    for c, d in WalkControl(control, True, maxDepth):
        LogControl(c, d + startDepth, showAllName, showPid)


def EnumAndLogControlAncestors(control: Control, showAllName: bool = True, showPid: bool = False) -> None:
    """
    Print and log control and its ancestors' propertyies.
    control: `Control` or its subclass.
    showAllName: bool, if False, print the first 30 characters of control.Name.
    """
    lists = []
    while control:
        lists.insert(0, control)
        control = control.GetParentControl()
    for i, control in enumerate(lists):
        LogControl(control, i, showAllName, showPid)


def FindControl(control: Control, compare: Callable[[Control, int], bool], maxDepth: int = 0xFFFFFFFF, findFromSelf: bool = False, foundIndex: int = 1) -> Control:
    """
    control: `Control` or its subclass.
    compare: Callable[[Control, int], bool], function(control: Control, depth: int) -> bool.
    maxDepth: int, enum depth.
    findFromSelf: bool, if False, do not compare self.
    foundIndex: int, starts with 1, >= 1.
    Return `Control` subclass or None if not find.
    """
    foundCount = 0
    if not control:
        control = GetRootControl()
    traverseCount = 0
    for child, depth in WalkControl(control, findFromSelf, maxDepth):
        traverseCount += 1
        if compare(child, depth):
            foundCount += 1
            if foundCount == foundIndex:
                child.traverseCount = traverseCount
                return child


def ShowDesktop(waitTime: float = 1) -> None:
    """Show Desktop by pressing win + d"""
    SendKeys('{Win}d')
    time.sleep(waitTime)
    #another implement
    #paneTray = PaneControl(searchDepth = 1, ClassName = 'Shell_TrayWnd')
    #if paneTray.Exists():
        #WM_COMMAND = 0x111
        #MIN_ALL = 419
        #MIN_ALL_UNDO = 416
        #PostMessage(paneTray.NativeWindowHandle, WM_COMMAND, MIN_ALL, 0)
        #time.sleep(1)


def WaitHotKeyReleased(hotkey: Tuple[int, int]) -> None:
    """hotkey: Tuple[int, int], two ints tuple (modifierKey, key)"""
    mod = {ModifierKey.Alt: Keys.VK_MENU,
           ModifierKey.Control: Keys.VK_CONTROL,
                 ModifierKey.Shift: Keys.VK_SHIFT,
                 ModifierKey.Win: Keys.VK_LWIN
           }
    while True:
        time.sleep(0.05)
        if IsKeyPressed(hotkey[1]):
            continue
        for k, v in mod.items():
            if k & hotkey[0]:
                if IsKeyPressed(v):
                    break
        else:
            break


def RunByHotKey(keyFunctions: Dict[Tuple[int, int], Callable], stopHotKey: Tuple[int, int] = None, exitHotKey: Tuple[int, int] = (ModifierKey.Control, Keys.VK_D), waitHotKeyReleased: bool = True) -> None:
    """
    Bind functions with hotkeys, the function will be run or stopped in another thread when the hotkey is pressed.
    keyFunctions: Dict[Tuple[int, int], Callable], such as {(uiautomation.ModifierKey.Control, uiautomation.Keys.VK_1) : function}
    stopHotKey: hotkey tuple
    exitHotKey: hotkey tuple
    waitHotKeyReleased: bool, if True, hotkey function will be triggered after the hotkey is released

    def main(stopEvent):
        while True:
            if stopEvent.is_set(): # must check stopEvent.is_set() if you want to stop when stop hotkey is pressed
                break
            print(n)
            n += 1
            stopEvent.wait(1)
        print('main exit')

    uiautomation.RunByHotKey({(uiautomation.ModifierKey.Control, uiautomation.Keys.VK_1) : main}
                        , (uiautomation.ModifierKey.Control | uiautomation.ModifierKey.Shift, uiautomation.Keys.VK_2))
    """
    import traceback

    def getModName(theDict, theValue):
        name = ''
        for key in theDict:
            if isinstance(theDict[key], int) and theValue & theDict[key]:
                if name:
                    name += '|'
                name += key
        return name
    def getKeyName(theDict, theValue):
        for key in theDict:
            if theValue == theDict[key]:
                return key
    def releaseAllKey():
        for key, value in Keys.__dict__.items():
            if isinstance(value, int) and key.startswith('VK'):
                if IsKeyPressed(value):
                    ReleaseKey(value)
    def threadFunc(function, stopEvent, hotkey, hotkeyName):
        if waitHotKeyReleased:
            WaitHotKeyReleased(hotkey)
        try:
            function(stopEvent)
        except Exception as ex:
            Logger.ColorfullyWrite('Catch an exception <Color=Red>{}</Color> in thread for hotkey <Color=DarkCyan>{}</Color>\n'.format(
                ex.__class__.__name__, hotkeyName), writeToFile=False)
            print(traceback.format_exc())
        finally:
            releaseAllKey()  #need to release keys if some keys were pressed
            Logger.ColorfullyWrite('{} for function <Color=DarkCyan>{}</Color> exits, hotkey <Color=DarkCyan>{}</Color>\n'.format(
                threading.currentThread(), function.__name__, hotkeyName), ConsoleColor.DarkYellow, writeToFile=False)

    stopHotKeyId = 1
    exitHotKeyId = 2
    hotKeyId = 3
    registed = True
    id2HotKey = {}
    id2Function = {}
    id2Thread = {}
    id2Name = {}
    for hotkey in keyFunctions:
        id2HotKey[hotKeyId] = hotkey
        id2Function[hotKeyId] = keyFunctions[hotkey]
        id2Thread[hotKeyId] = None
        modName = getModName(ModifierKey.__dict__, hotkey[0])
        keyName = getKeyName(Keys.__dict__, hotkey[1])
        id2Name[hotKeyId] = str((modName, keyName))
        if ctypes.windll.user32.RegisterHotKey(0, hotKeyId, hotkey[0], hotkey[1]):
            Logger.ColorfullyWrite('Register hotkey <Color=Cyan>{}</Color> successfully\n'.format((modName, keyName)), writeToFile=False)
        else:
            registed = False
            Logger.ColorfullyWrite('Register hotkey <Color=Cyan>{}</Color> unsuccessfully, maybe it was allready registered by another program\n'.format((modName, keyName)), writeToFile=False)
        hotKeyId += 1
    if stopHotKey and len(stopHotKey) == 2:
        modName = getModName(ModifierKey.__dict__, stopHotKey[0])
        keyName = getKeyName(Keys.__dict__, stopHotKey[1])
        if ctypes.windll.user32.RegisterHotKey(0, stopHotKeyId, stopHotKey[0], stopHotKey[1]):
            Logger.ColorfullyWrite('Register stop hotkey <Color=DarkYellow>{}</Color> successfully\n'.format((modName, keyName)), writeToFile=False)
        else:
            registed = False
            Logger.ColorfullyWrite('Register stop hotkey <Color=DarkYellow>{}</Color> unsuccessfully, maybe it was allready registered by another program\n'.format((modName, keyName)), writeToFile=False)
    if not registed:
        return
    if exitHotKey and len(exitHotKey) == 2:
        modName = getModName(ModifierKey.__dict__, exitHotKey[0])
        keyName = getKeyName(Keys.__dict__, exitHotKey[1])
        if ctypes.windll.user32.RegisterHotKey(0, exitHotKeyId, exitHotKey[0], exitHotKey[1]):
            Logger.ColorfullyWrite('Register exit hotkey <Color=DarkYellow>{}</Color> successfully\n'.format((modName, keyName)), writeToFile=False)
        else:
            Logger.ColorfullyWrite('Register exit hotkey <Color=DarkYellow>{}</Color> unsuccessfully\n'.format((modName, keyName)), writeToFile=False)
    funcThread = None
    livingThreads = []
    stopEvent = threading.Event()
    msg = ctypes.wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), ctypes.c_void_p(0), ctypes.c_uint(0), ctypes.c_uint(0)) != 0:
        if msg.message == 0x0312: # WM_HOTKEY=0x0312
            if msg.wParam in id2HotKey:
                if msg.lParam & 0x0000FFFF == id2HotKey[msg.wParam][0] and msg.lParam >> 16 & 0x0000FFFF == id2HotKey[msg.wParam][1]:
                    Logger.ColorfullyWrite('----------hotkey <Color=Cyan>{}</Color> pressed----------\n'.format(id2Name[msg.wParam]), writeToFile=False)
                    if not id2Thread[msg.wParam]:
                        stopEvent.clear()
                        funcThread = threading.Thread(None, threadFunc, args=(id2Function[msg.wParam], stopEvent, id2HotKey[msg.wParam], id2Name[msg.wParam]))
                        funcThread.start()
                        id2Thread[msg.wParam] = funcThread
                    else:
                        if id2Thread[msg.wParam].is_alive():
                            Logger.WriteLine('There is a {} that is already running for hotkey {}'.format(id2Thread[msg.wParam], id2Name[msg.wParam]), ConsoleColor.Yellow, writeToFile=False)
                        else:
                            stopEvent.clear()
                            funcThread = threading.Thread(None, threadFunc, args=(id2Function[msg.wParam], stopEvent, id2HotKey[msg.wParam], id2Name[msg.wParam]))
                            funcThread.start()
                            id2Thread[msg.wParam] = funcThread
            elif stopHotKeyId == msg.wParam:
                if msg.lParam & 0x0000FFFF == stopHotKey[0] and msg.lParam >> 16 & 0x0000FFFF == stopHotKey[1]:
                    Logger.Write('----------stop hotkey pressed----------\n', ConsoleColor.DarkYellow, writeToFile=False)
                    stopEvent.set()
                    for id_ in id2Thread:
                        if id2Thread[id_]:
                            if id2Thread[id_].is_alive():
                                livingThreads.append((id2Thread[id_], id2Name[id_]))
                            id2Thread[id_] = None
            elif exitHotKeyId == msg.wParam:
                if msg.lParam & 0x0000FFFF == exitHotKey[0] and msg.lParam >> 16 & 0x0000FFFF == exitHotKey[1]:
                    Logger.Write('Exit hotkey pressed. Exit\n', ConsoleColor.DarkYellow, writeToFile=False)
                    stopEvent.set()
                    for id_ in id2Thread:
                        if id2Thread[id_]:
                            if id2Thread[id_].is_alive():
                                livingThreads.append((id2Thread[id_], id2Name[id_]))
                            id2Thread[id_] = None
                    break
    for thread, hotkeyName in livingThreads:
        if thread.is_alive():
            Logger.Write('join {} triggered by hotkey {}\n'.format(thread, hotkeyName), ConsoleColor.DarkYellow, writeToFile=False)
            thread.join(2)
    os._exit(0)


if __name__ == '__main__':

    print('\nUIAutomationCore:----')
    for i in sorted([it for it in dir(_AutomationClient.instance().UIAutomationCore) if not it.startswith('_')]):
        print(i)

    print('\nIUIAutomation:----')
    for i in sorted([it for it in dir(_AutomationClient.instance().IUIAutomation) if not it.startswith('_')]):
        print(i)

    print('\nViewWalker:----')
    for i in sorted([it for it in dir(_AutomationClient.instance().ViewWalker) if not it.startswith('_')]):
        print(i)

    print()
    for ct, ctor in ControlConstructors.items():
        c = ctor()
        print(type(c))

    notepad = WindowControl(searchDepth=1, ClassName='Notepad')
    if not notepad.Exists(0, 0):
        import subprocess
        subprocess.Popen('notepad.exe')
        notepad.Refind()

    print('\n', notepad)
    print('Control:----')
    for i in sorted([it for it in dir(notepad) if not it.startswith('_')]):
        print(i)

    print('\n', notepad.Element)
    print('Control.Element:----')
    for i in sorted([it for it in dir(notepad.Element) if not it.startswith('_')]):
        print(i)

    lp = notepad.GetLegacyIAccessiblePattern()
    print('\n', lp)
    print('Control.LegacyIAccessiblePattern:----')
    for i in sorted([it for it in dir(lp.pattern) if not it.startswith('_')]):
        print(i)

    print('\nControl.Properties:----')
    for k, v in PropertyIdNames.items():
        try:
            value = notepad.GetPropertyValue(k)
            print('GetPropertyValue, {} = {}, type: {}'.format(v, value, type(value)))
        except (KeyError, comtypes.COMError) as ex:
            print('GetPropertyValue, {}, error'.format(v))

    children = notepad.GetChildren()
    print('\n notepad children:----', len(children))
    for c in notepad.GetChildren():
        print(c)

    del lp
    del notepad

    hello = '{Ctrl}{End}{Enter}Hello World! 你好世界！'
    SendKeys(hello)
