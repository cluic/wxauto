# wxauto
Windows版本微信客户端自动化，可实现简单的发送、接收微信消息，开发中

开发过程使用的微信版本：3.3.5.34

部分版本的微信可能由于UI界面不同从而无法使用，截至2021-08-16最新版本可用

## 示例
```python
# 获取当前微信客户端
wx = Wechat()

# 获取会话列表
wx.GetSessionList()

# 获取当前聊天窗口聊天消息
wx.GetAllMessage()

# 向某人(王哥)发送消息
msg = '你好~'
who = '王哥'
wx.ChatWith(who)  # 打开王哥聊天窗口
wx.SendMsg(msg)  # 向王哥发送消息：你好~
```
