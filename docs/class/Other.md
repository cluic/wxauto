---
weight: 6
bookFlatSection: true
title: "其他类（方法）"
---

### WxResponse

该类用于该项目多个方法的返回值

```python
# 这里假设result为某个方法的WxResponse类型返回值
result: WxResponse = ...

# 判断是否成功
if result:
    data = result['data'] # 成功，获取返回数据，大多数情况下为None
else:
    print(result['message'])  # 该方法调用失败，打印错误信息
```

### WxParam

该类用于该项目的一些参数，在获取`WeChat`实例前，可以通过修改该类的属性来修改默认参数

| 属性                | 类型   |  默认值  | 描述                                                                                     |
| ------------------- | ------ | -------- | ---------------------------------------------------------------------------------------- |
| ENABLE_FILE_LOGGER  | bool   | True     | 是否启用日志文件                                                                         |
| DEFAULT_SAVE_PATH   | str    | ./wxauto | 下载文件/图片默认保存路径 |
| MESSAGE_HASH        | bool   | False    | 是否启用消息哈希值用于辅助判断消息，开启后会稍微影响性能                               |
| DEFAULT_MESSAGE_XBIAS | int    | 51       | 头像到消息X偏移量，用于消息定位，点击消息等操作                                       |
| FORCE_MESSAGE_XBIAS  | bool   | True    | 是否强制重新自动获取X偏移量，如果设置为True，则每次启动都会重新获取，系统设置了分辨率缩放时开启    |
| LISTEN_INTERVAL     | int    | 1        | 监听消息时间间隔，单位秒                                                                 |
| LISTENER_EXCUTOR_WORKERS | int    | 4        | 监听执行器线程池大小，根据自身需求和设备性能设置                                       |
| SEARCH_CHAT_TIMEOUT | int    | 5        | 搜索聊天对象超时时间，单位秒                                                             |
| NOTE_LOAD_TIMEOUT | int    | 30        | 微信笔记加载超时时间，单位秒                                                            |


示例：

```python
from wxauto import WxParam

# 设置8个监听线程
WxParam.LISTENER_EXCUTOR_WORKERS = 8
...
```


### NewFriendElement

![NewFriendElement](/images/new_friend_element.png)

| 属性     | 类型   | 描述（以上图为例）       |
| -------- | ------ | --------------- |
| name     | str    | 对方名（诸葛孔明）  |
| msg     | str    | 申请信息（wxauto）  |
| acceptable | bool    | 是否可接受（True）  |

#### accept

**同意添加好友**

参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| remark | str | None | 备注 |
| tags | list | None | 标签 |
| permission | str  | '朋友圈' | 朋友圈权限，可选值：'全部'、'仅聊天' |

#### delete

**删除好友申请**

参数：无

#### reply

**回复好友申请**

参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| text | str | 必填 | 回复信息 |

#### get_account

**获取申请添加的好友的账号信息**


参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| wait | int | 5 | 等待时间 |

返回值：str

### LoginWnd


该类用于微信登录、获取二维码等操作

```python
from wxauto import LoginWnd

wxlogin = LoginWnd(app_path="...")
```

![LoginWnd](/images/login_wnd.png)

参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| app_path | str | None | 微信客户端路径 |


属性：无

#### login

**登录微信**

参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| timeout | int | 10 | 登录超时时间 |

返回值：[`WxResponse`](#wxresponse)

#### get_qrcode

**获取二维码**

参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| path | str | None | 二维码图片的保存路径，None即本地目录下的wxauto_qrcode文件夹 |

返回值：str，二维码图片的路径

#### reopen

**重新打开微信**，为了避免各种弹窗影响操作，建议调用该方法后再执行login或get_qrcode

参数：无

返回值：无

#### open

**启动微信**，建议在初始化的时候传入app_path参数，否则可能会启动失败

参数：无

返回值：无

### WeChatImage

```python
from wxauto.ui.component import WeChatImage

imgwnd = WeChatImage()
```

微信图片/视频**窗口**类，用于处理微信图片或图片窗口的各种操作

![wxauto_image_wnd](/images/wxauto_image_wnd.png)

#### ocr

**识别图片中的文字**，仅支持图片，不支持视频

参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| wait | int | 10 | 隐性等待时间 |

返回值：str，识别到的文字

#### save

**保存图片/视频**

参数：

| 参数名 | 类型 |  默认值 | 说明 |
| :--- | :--- | :--- |:--- |
| dir_path | str | None | 保存的目录路径，None即本地路径下自动生成 |
| timeout | int | 10 | 保存超时时间 |

返回值：Path，保存的文件路径

#### close

**关闭图片/视频窗口**

参数：无

返回值：无

### WeChatDialog

微信对话框对象，用于处理微信对话框的各种操作

![wxauto_dialog_wnd](/images/wechatdialog.png)

#### select_option

**选择对话框中的选项**，如“确定”、“取消”等

参数：无

返回值：[WxResponse](#wxresponse)对象

#### get_all_text

**获取对话框中所有的文字内容**

参数：无

返回值：str

#### close

**关闭对话框**

参数：无

返回值：无

### get_wx_clients

**获取所有已登录的微信3.9客户端**

```python
from wxauto import get_wx_clients

# 获取所有微信客户端
clients = get_wx_clients()
for client in clients:
    print(f"微信客户端: {client}")
```

返回值：List[[WeChat](/docs/class/wechat)]

> [!Warning]
> **wxauto项目不支持一切违反官方用户协议的操作，<font color='red'>不建议</font>、<font color='red'>不支持</font>、<font color='red'>不提供</font>微信多开的方法或行为。**
> 但是如果你**自行使用**其他方法多开微信，wxauto不承担由你自行多开的行为导致的风险，也不保证所有功能的正常调用。

### get_wx_logins

```python
from wxauto import get_wx_logins

# 获取所有微信客户端
login_windows = get_wx_logins()

# 关闭所有登录窗口
for login_window in login_windows:
    login_window.close()  # 关闭
```

返回值：List[[LoginWnd](#loginwnd)]


> [!Warning]
> **wxauto项目不支持一切违反官方用户协议的操作，<font color='red'>不建议</font>、<font color='red'>不支持</font>、<font color='red'>不提供</font>微信多开的方法或行为。**
> 但是如果你**自行使用**其他方法多开微信，wxauto不承担由你自行多开的行为导致的风险，也不保证所有功能的正常调用。