from wxauto import *
import time
# 获取当前微信客户端
wx = WeChat()
# 获取会话列表
wx.GetSessionList()
msg = ['man','haha','what can i say','manba out']
who = '健身群'
wx.SendMsg(msg[0], who)
i=1
while(1):#每二十四分钟循环发送科比语录
    time.sleep(24*60)
    wx.SendMsg(msg[i], who)
    i=(i+1)%len(msg)

