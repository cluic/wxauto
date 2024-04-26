from openai import OpenAI
from wxauto import *
from wxauto import gpt_robot
import time

wx = WeChat()

#创建一个人/群聊列表,人和群需要分开
listen_list_group = [
    '健身群'
]
robot_group_array=[]#机器人列表
role='role/kobe.txt'#角色文件路径
pretrained='pretrained/kobe_1.txt'#预先对话的文件路径
condition='@lzc'#触发回复的条件为信息@lzc
condition_type=1#需要把该信息过滤后传输给gpt,0表示无需过滤

client = OpenAI()
# 为每个群聊/人设计一个机器人,role为角色,pretrain是自己定义的预先对话
for i in range(0,len(listen_list_group)):
	wx.AddListenChat(who=listen_list_group[i], savepic=False)  
	robot=gpt_robot.Robot(listen_list_group[i],1,role,client,pretrained)
	robot_group_array.append(robot)

wait = 10#设置接收时间间隔,若设置太短容易使程序频繁拉取信息的过程中漏掉某些信息

while True:
	gpt_robot.receive_message(wx,1,robot_group_array,condition,condition_type)#receive_message函数的type,0代表私聊,1代表群聊
	time.sleep(wait)
