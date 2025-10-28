当前目录`docs`为文档目录，请自行参考相应文档文件

## 快速开始

### 获取微信实例

```python
from wxauto import WeChat

# 初始化微信实例
wx = WeChat()
```

### 发送消息

```python
# 发送消息
wx.SendMsg("你好", who="文件传输助手")
```

### 获取当前聊天窗口消息

```python
# 获取当前聊天窗口消息
msgs = wx.GetAllMessage()

for msg in msgs:
    print('==' * 30)
    print(f"{msg.sender}: {msg.content}")
```

> [!TIP] Success
> ✅ 恭喜，你已经成功进行了自动化操作，接下来你可以继续探索更多功能。