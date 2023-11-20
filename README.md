# wxauto  (适用PC微信3.9.8.15版本）

### 2023-11-20重写wxauto，欢迎指出bug

Windows版本微信客户端自动化，可实现简单的发送、接收微信消息、保存聊天图片

[点此获取后台调用版本](https://github.com/cluic/wxautoapi)

|  环境  | 版本 |
| :----: | :--: |
|   OS   | [![Windows](https://img.shields.io/badge/Windows-10\|11-white?logo=windows&logoColor=white)](https://www.microsoft.com/)  |
|  微信  | [![Wechat](https://img.shields.io/badge/%E5%BE%AE%E4%BF%A1-3.9.8.X-07c160?logo=wechat&logoColor=white)](https://weixin.qq.com/cgi-bin/readtemplate?ang=zh_CN&t=page/faq/win/335/index&faq=win_335)  |
| Python | [![Python](https://img.shields.io/badge/Python-3.X-blue?logo=python&logoColor=white)](https://www.python.org/)   |


### 部分版本的微信可能由于UI界面不同从而无法使用，截至2023-11-20最新版本可用

[![Star History Chart](https://api.star-history.com/svg?repos=cluic/wxauto&type=Date)](https://star-history.com/#cluic/wxauto)

## 示例
<font color=red>**请先登录PC微信客户端**</font>
```python
from wxauto import *


# 获取当前微信客户端
wx = WeChat()


# 获取会话列表
wx.GetSessionList()

# 向某人发送消息（以`文件传输助手`为例）
msg = '你好~'
who = '文件传输助手'
wx.SendMsg(msg, who)  # 向`文件传输助手`发送消息：你好~


# 向某人发送文件（以`文件传输助手`为例，发送三个不同类型文件）
files = [
    'D:/test/wxauto.py',
    'D:/test/pic.png',
    'D:/test/files.rar'
]
who = '文件传输助手'
wx.SendFiles(filepath=files, who=who)  # 向`文件传输助手`发送上述三个文件


# 下载当前聊天窗口的聊天记录及图片
msgs = wx.GetAllMessage(savepic=True)   # 获取聊天记录，及自动下载图片
```
## 注意事项
目前还在开发中，测试案例较少，使用过程中可能遇到各种Bug

如果遇到问题或者有新的想法，希望您可以通过以下两种方式联系我进行改进：
- [点击前往此页面留下您的问题](https://github.com/cluic/wxauto/issues/new/choose)
- 邮箱：tikic@qq.com
- 微信：
- ![微信](https://github.com/cluic/wxauto/blob/WeChat3.9.8/utils/wxqrcode.png)


## 最后
如果对您有帮助，希望可以帮忙点个Star，如果您正在使用这个项目，可以将右上角的 Unwatch 点为 Watching，以便在我更新或修复某些 Bug 后即使收到反馈，感谢您的支持，非常感谢！

## 免责声明
代码仅供交流学习使用，请勿用于非法用途和商业用途！如因此产生任何法律纠纷，均与作者无关！

## 支持
非常感谢您对该项目的支持

![支付宝](https://github.com/cluic/wxauto/blob/WeChat3.9.8/utils/alipay.png)&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;
![微信](https://github.com/cluic/wxauto/blob/WeChat3.9.8/utils/wxpay.png)

