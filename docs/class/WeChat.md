---
weight: 1
bookFlatSection: true
title: "WeChat类"
---


## WeChat 类方法


### 初始化参数

| 参数     | 类型 | 默认值 | 描述                             |
| -------- | ---- | ------ | -------------------------------- |
| nickname | str  | None   | 微信昵称，用于定位特定的微信窗口 |
| debug    | bool | False  | 是否开启调试模式                 |

```python
from wxauto import WeChat

wx = WeChat()
```

### 保持程序运行 KeepRunning

由于wxauto使用守护线程来监听消息，当程序仅用于监听模式时，主线程会退出，因此需要调用此方法来保持程序运行

```python
from wxauto import WeChat

wx = WeChat()
wx.AddListenChat('张三', callback=lambda msg, chat: ...)

# 保持程序运行，确保正常监听
wx.KeepRunning()
```

### 获取当前会话列表 GetSession

```python
sessions = wx.GetSession()
for session in sessions:
    print(session.info)
```

**返回值**：

- 类型：List[[SessionElement](/docs/class/other/#sessionelement)]
- 描述：当前会话列表

### 发送链接卡片 SendUrlCard

```python
wx.SendUrlCard(url="https://example.com", friends="张三", timeout=10)
```

**参数**：

| 参数    | 类型                  | 默认值 | 描述                                   |
| ------- | --------------------- | ------ | -------------------------------------- |
| url     | str                   | 必填   | 链接地址                               |
| friends | Union[str, List[str]] | None   | 发送对象，可以是单个用户名或用户名列表 |
| message | str | None   | 附加消息，默认不发送 |
| timeout | int                   | 10     | 等待时间（秒）                         |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：发送结果

### 打开聊天窗口 ChatWith

```python
wx.ChatWith(who="张三", exact=False)
```

**参数**：

| 参数  | 类型 | 默认值 | 描述                   |
| ----- | ---- | ------ | ---------------------- |
| who   | str  | 必填   | 要聊天的对象           |
| exact | bool | False  | 搜索好友时是否精确匹配 |

**返回值**：无

### 获取子窗口实例 GetSubWindow

```python
chat = wx.GetSubWindow(nickname="张三")
```

**参数**：

| 参数     | 类型 | 默认值 | 描述                 |
| -------- | ---- | ------ | -------------------- |
| nickname | str  | 必填   | 要获取的子窗口的昵称 |

**返回值**：

- 类型：[`Chat`](/docs/class/Chat)
- 描述：子窗口实例

### 获取所有子窗口实例 GetAllSubWindow

```python
chats = wx.GetAllSubWindow()
```

**返回值**：

- 类型：List[[`Chat`](/docs/class/Chat)]
- 描述：所有子窗口实例的列表

### 添加监听聊天窗口 AddListenChat

```python
def on_message(msg, chat):
    print(f"收到来自 {chat} 的消息: {msg.content}")

wx.AddListenChat(nickname="张三", callback=on_message)
```

**参数**：

| 参数     | 类型                                              | 默认值 | 描述                                                       |
| -------- | ------------------------------------------------- | ------ | ---------------------------------------------------------- |
| nickname | str                                               | 必填   | 要监听的聊天对象                                           |
| callback | Callable[[[Message](/docs/class/message/), [Chat](/docs/class/chat/)], None] | 必填   | 回调函数，参数为([Message](/docs/class/message/)对象, [Chat](/docs/class/chat/)对象) |

**返回值**：

- 成功时：
  - 类型：[Chat](/docs/class/chat/)
  - 描述：该监的听子窗口实例

- 失败时：
  - 类型：[`WxResponse`](/docs/class/other/#wxresponse)
  - 描述：执行结果，成功时包含监听名称

### 移除监听聊天 RemoveListenChat

```python
wx.RemoveListenChat(nickname="张三")
```

**参数**：

| 参数     | 类型 | 默认值 | 描述                 |
| -------- | ---- | ------ | -------------------- |
| nickname | str  | 必填   | 要移除的监听聊天对象 |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：执行结果

### 开始监听 StartListening

```python
wx.StartListening()
```

**参数**：无

**返回值**：无

### 停止监听 StopListening

```python
wx.StopListening()
```

**参数**：

| 参数     | 类型 | 默认值 | 描述                 |
| -------- | ---- | ------ | -------------------- |
| remove | bool  | True   | 是否移出所有子窗口 |

**返回值**：无

### 进入朋友圈 Moments

```python
moments = wx.Moments(timeout=3)
```

**参数**：

| 参数    | 类型 | 默认值 | 描述           |
| ------- | ---- | ------ | -------------- |
| timeout | int  | 3      | 等待时间（秒） |

**返回值**：

- 类型：[`MomentsWnd`](/docs/class/moment)
- 描述：朋友圈窗口实例

### 获取下一个新消息 GetNextNewMessage

```python
messages = wx.GetNextNewMessage(filter_mute=False)
```

**参数**：

| 参数        | 类型 | 默认值 | 描述                 |
| ----------- | ---- | ------ | -------------------- |
| filter_mute | bool | False  | 是否过滤掉免打扰消息 |

**返回值**：

- 类型：Dict[str, List[[Message](/docs/class/message/)]
- 描述：消息列表，键为聊天名称，值为消息列表
- 示例：
    ```python
    {'chat_name': 'wxauto交流',
      'chat_type': 'group',
      'msg': [
          <wxauto - TimeMessage(2025年5月2...) at 0x227379555d0>,
          <wxauto - FriendImageMessage([图片]) at 0x2273795ca10>,
          <wxauto - FriendTextMessage(/[微笑]) at 0x22737967c50>,
          <wxauto - FriendTextMessage(你点击发送会自动...) at 0x227366c4f50>, 
          ...
        ]
    }
    ```

### 获取好友列表 GetFriendDetails

```python
# 获取前10个好友详情信息
messages = wx.GetFriendDetails(n=10)
```

**参数**：

| 参数        | 类型 | 默认值 | 描述                 |
| ----------- | ---- | ------ | -------------------- |
|        n    | int  | None   | 获取前n个好友详情信息 |
| tag         | str  | None   | 从指定拼音首字母开始 |
| timeout     | int  | 0xFFFFF | 获取超时时间（秒） |

**返回值**：

- 类型：List[dict]
- 描述：好友详情信息列表

> [!warning]
> 1. 该方法运行时间较长，约0.5~1秒一个好友的速度，好友多的话可将n设置为一个较小的值，先测试一下
> 2. 如果遇到企业微信的好友且为已离职状态，可能导致微信卡死，需重启（此为微信客户端BUG）
> 3. 该方法未经过大量测试，可能存在未知问题，如有问题请微信群内反馈


### 获取新的好友申请列表 GetNewFriends


```python
newfriends = wx.GetNewFriends(acceptable=True)
```

**参数**：

| 参数       | 类型 | 默认值 | 描述                       |
| ---------- | ---- | ------ | -------------------------- |
| acceptable | bool | True   | 是否过滤掉已接受的好友申请 |

**返回值**：

- 类型：List[[`NewFriendElement`](/docs/class/other/#newfriendelement)]
- 描述：新的好友申请列表

**示例**：

```python
newfriends = wx.GetNewFriends(acceptable=True)
tags = ['标签1', '标签2']
for friend in newfriends:
    remark = f'备注{friend.name}'
    friend.accept(remark=remark, tags=tags)  # 接受好友请求，并设置备注和标签
```

### 添加新的好友 AddNewFriend

```python
wx.AddNewFriend(keywords="张三", addmsg="我是小明", remark="老张", tags=["同学"], permission="朋友圈", timeout=5)
```

**参数**：

| 参数       | 类型                        | 默认值   | 描述                                     |
| ---------- | --------------------------- | -------- | ---------------------------------------- |
| keywords   | str                         | 必填     | 搜索关键词，可以是昵称、微信号、手机号等 |
| addmsg     | str                         | None     | 添加好友时的附加消息                     |
| remark     | str                         | None     | 添加好友后的备注                         |
| tags       | List[str]                   | None     | 添加好友后的标签                         |
| permission | Literal['朋友圈', '仅聊天'] | '朋友圈' | 添加好友后的权限                         |
| timeout    | int                         | 5        | 搜索好友的超时时间（秒）                 |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：添加好友的结果

### 获取最近群聊名称列表 GetAllRecentGroups

```python
groups = wx.GetAllRecentGroups()
if groups:
    print(groups)
else:
    print('获取失败')
```

**返回值**：

- 类型：WxResponse | List[str]: 失败时返回WxResponse，成功时返回所有最近群聊列表

### 切换到聊天页面 SwitchToChat

```python
wx.SwitchToChat()
```

**返回值**：无

### 切换到联系人页面 SwitchToContact

```python
wx.SwitchToContact()
```

**返回值**：无


### 是否在线 IsOnline

```python
wx.IsOnline()
```

**返回值**：

- 类型：bool

### 获取我的信息 GetMyInfo

获取自己的微信号等信息

```python
wx.GetMyInfo()
```

**返回值**：

- 类型：Dict[str, str]

### 获取通讯录群聊列表 GetContactGroups

获取通讯录中的群聊列表

```python
wx.GetContactGroups()
```

**参数**：

> [!NOTE]
> 自动化操作个体差异较大，根据实际情况调整以下参数，速度不合适可能导致漏掉部分群聊

| 参数  | 类型    | 默认值   | 描述     |
| ------ | -------- | -------- | ----- |
| speed  | int   | 1     | 滚动速度 |
| interval | float    | 0.1     |  滚动时间间隔  |

**返回值**：

- 类型：List[str]