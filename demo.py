from wxauto import WeChat

wx = WeChat()

# 发送消息
who = '文件传输助手'
for i in range(3):
    wx.SendMsg(f'wxauto测试{i+1}', who)
    
# 获取当前聊天页面（文件传输助手）消息，并自动保存聊天图片
msgs = wx.GetAllMessage(savepic=True)
for msg in msgs:
    print(f"{msg[0]}: {msg[1]}")


print('wxauto测试完成！')
