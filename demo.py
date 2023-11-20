from wxauto import WeChat

wx = WeChat()

# 发送消息
who = '文件传输助手'
for i in range(3):
    wx.SendMsg(f'wxauto测试{i+1}', who)
    
# 发送文件
who = '文件传输助手'
files = [
    r"D:\文件\test1.txt",
    r"D:\文件\test2.txt",
    r"D:\文件\test3.txt"
]
wx.SendFiles(files)
    

# 获取消息，并自动保存聊天图片
who = 'xxx'
wx.ChatWith(who)
msgs = wx.GetAllMessage(savepic=True)