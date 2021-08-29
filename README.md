# wxauto
[![Wechat](https://img.shields.io/badge/%E5%BE%AE%E4%BF%A1-3.3.5-07c160)](https://weixin.qq.com/cgi-bin/readtemplate?ang=zh_CN&t=page/faq/win/335/index&faq=win_335)
[![Python](https://img.shields.io/badge/Python-3.6|3.7|3.8|3.9-blue)](https://www.python.org/)
[![Python](https://img.shields.io/badge/BBS-FishC-007c7c)](https://fishc.com.cn/thread-200904-1-1.html)

Windows版本微信客户端自动化，可实现简单的发送、接收微信消息，开发中

开发过程使用的微信版本：3.3.5

部分版本的微信可能由于UI界面不同从而无法使用，截至2021-08-16最新版本可用

## 示例
```python
from wxauto import WeChat

# 获取当前微信客户端
wx = WeChat()

# 获取会话列表
wx.GetSessionList()

# 输出当前聊天窗口聊天消息
msgs = wx.GetAllMessage
for msg in msgs:
    print('%s : %s'%(msg[0], msg[1]))
## 获取更多聊天记录
wx.LoadMoreMessage()
msgs = wx.GetAllMessage
for msg in msgs:
    print('%s : %s'%(msg[0], msg[1]))

# 向某人发送消息（以`文件传输助手`为例）
msg = '你好~'
who = '文件传输助手'
wx.ChatWith(who)  # 打开`文件传输助手`聊天窗口
wx.SendMsg(msg)  # 向`文件传输助手`发送消息：你好~

# 向某人发送文件（以`文件传输助手`为例，发送三个不同类型文件）
file1 = 'D:/test/wxauto.py'
file2 = 'D:/test/pic.png'
file3 = 'D:/test/files.rar'
who = '文件传输助手'
wx.ChatWith(who)  # 打开`文件传输助手`聊天窗口
wx.SendFiles(file1, file2, file3)  # 向`文件传输助手`发送上述三个文件
```

## 注意事项
目前还在开发中，测试案例较少，使用过程中可能遇到各种Bug

如果遇到问题或者有新的想法，希望您可以通过邮件联系我进行改进：tikic@qq.com

## 最后
如果对您有帮助，希望可以帮忙点个Star，非常非常感谢！
