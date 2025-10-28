---
weight: 5
bookFlatSection: true
title: "五、使用示例"
---

### 1. 基本使用

```python
from wxauto import WeChat

# 初始化微信实例
wx = WeChat()

# 发送消息
wx.SendMsg("你好", who="张三")

# 获取当前聊天窗口消息
msgs = wx.GetAllMessage()
for msg in msgs:
    print(f"消息内容: {msg.content}, 消息类型: {msg.type}")
```

### 2. 监听消息

```python
from wxauto import WeChat
from wxauto.msgs import FriendMessage
import time

wx = WeChat()

# 消息处理函数
def on_message(msg, chat):
    # 示例1：将消息记录到本地文件
    with open('msgs.txt', 'a', encoding='utf-8') as f:
        f.write(msg.content + '\n')

    # 示例2：自动下载图片和视频
    if msg.type in ('image', 'video'):
        print(msg.download())

    # 示例3：自动回复收到
    if isinstance(msg, FriendMessage):
        msg.quote('收到')

    ...# 其他处理逻辑，配合Message类的各种方法，可以实现各种功能

# 添加监听，监听到的消息用on_message函数进行处理
wx.AddListenChat(nickname="张三", callback=on_message)

# 保持程序运行
wx.KeepRunning()
```

```python
# ... 程序运行一段时间后 ...

# 移除监听
wx.RemoveListenChat(nickname="张三")
```

### 3. 处理好友申请

```python
from wxauto import WeChat

wx = WeChat()

# 获取新的好友申请
newfriends = wx.GetNewFriends(acceptable=True)

# 处理好友申请
tags = ['同学', '技术群']
for friend in newfriends:
    remark = f'备注_{friend.name}'
    friend.accept(remark=remark, tags=tags)  # 接受好友请求，并设置备注和标签
```

### 4. 使用打字机模式发送消息

```python
from wxauto import WeChat

wx = WeChat()

# 普通文本发送
wx.SendTypingText("你好，这是一条测试消息", who="张三")

# 使用@功能和换行
wx.SendTypingText("各位好：\n{@张三} 请负责前端部分\n{@李四} 请负责后端部分", who="项目群")
```

### 5. 获取多个微信客户端/登录窗口

#### 5.1 获取多个微信客户端
```python
from wxauto import get_wx_clients

# 获取所有微信客户端
clients = get_wx_clients()
for client in clients:
    print(f"微信客户端: {client}")
```

#### 5.2 获取多个登录窗口

```python
from wxauto import get_wx_logins

# 获取所有微信客户端
login_windows = get_wx_logins()

# 关闭所有登录窗口
for login_window in login_windows:
    login_window.close()  # 关闭
```

### 6. 自动登录

```python
from wxauto import LoginWnd

wxpath = "D:/path/to/WeChat.exe"

# 创建登录窗口
loginwnd = LoginWnd(wxpath)

# 登录微信
loginwnd.login()
```

### 7. 获取登录二维码

```python
from wxauto import LoginWnd

wxpath = "D:/path/to/WeChat.exe"

# 创建登录窗口
loginwnd = LoginWnd(wxpath)

# 获取登录二维码图片路径
qrcode_path = loginwnd.get_qrcode()
print(qrcode)
```

### 8. 合并转发消息

```python
from wxauto import WeChat
from wxauto.msgs import HumanMessage

wx = WeChat()

# 打开指定聊天窗口
wx.ChatWith("工作群")

# 获取消息列表
msgs = wx.GetAllMessage()

# 多选最后五条消息
n = 0
for msg in msgs[::-1]:
    if n >= 5:
        break
    if isinstance(msg, HumanMessage):
        n += 1
        msg.multi_select()

# 执行合并转发
targets = [
    '张三',
    '李四
]
wx.MergeForward(targets)
```

### 9. 创建群聊

```python
from wxauto import WeChat

wx = WeChat()

# 以“张三”聊天窗口，添加“李四”，形成群聊
wx.AddGroupMembers(group='张三', members=['李四'])

# 简单等待
time.sleep(3)

# 修改群名
wx.ManageGroup(name='这是新群名')
```