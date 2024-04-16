from openai import OpenAI
from wxauto import *
import time

def receive_message(w,type,robot_array):
	msgs = w.GetListenMessage()
	for chat in msgs:
		msg = msgs.get(chat)   # 获取消息内容
		for i in range(1,len(msg)):
			print(len(msg))
			print(type)
			print(msg[i][0])
			print(msg[i][1])
			if msg[i][0]=='SYS' or msg[i][0]=='Self':
				continue
			elif type==1 and '@lzc' in msg[i][1] :
				num=0
				answer=robot_array[num].kobe_talk(change_mes(msg[i][1]))
			elif type==0 :
				num=get_number(msg[i][0])
				print(num)
				answer=robot_array[num].kobe_talk(msg[i][1])
			else:
				continue
			chat.SendMsg(answer)

def change_mes(message):
	message_1 = message.replace("@lzc", "")
	return message_1

def get_number(name):
	global listen_list_human
	for i in range(0,len(listen_list_human)):
		if name==listen_list_human[i]:
			return i

class Robot:
	def __init__(self,name,type,role,client,pretrained):
		self.name = name
		self.type = type
		self.role = role
		self.client = client
		self.mes_history = self.prepare(role,pretrained)

	def _read_(self, role):
		with open(role, 'r', encoding='utf-8') as file:
			return file.readlines()

	def prepare(self, role_path,pretrained_path):
		role = self._read_(role_path)
		pretrain = self._read_(pretrained_path)
		pre = [{"role": "system", "content":role[0]}]
		for i in range(0,len(pretrain)):
			if(i % 2 == 1):
				pre.append( {"role": "user", "content": pretrain[i]})
			else:
				pre.append( {"role": "assistant", "content": pretrain[i]})
		return pre

				
	def kobe_talk(self,question):
		self.mes_history.append({"role": "user", "content": question})	
		completion = self.client.chat.completions.create(
		model="gpt-4-turbo-preview",
		messages=self.mes_history
		)
		answer=completion.choices[0].message.content
		self.mes_history.append( {"role": "assistant", "content": answer})
		return answer


#wx = WeChat()
wx2 = WeChat()

listen_list_human = [
    'lzcc'
]
listen_list_group = [
    '健身群'
]

role='role/kobe.txt'
pretrained='pretrained/kobe_1.txt'


client = OpenAI()
robot_human_array=[]
robot_group_array=[]
"""for i in range(0,len(listen_list_human)):
	wx.AddListenChat(who=listen_list_human[i], savepic=False)  # 添加监听对象并且不自动保存新消息图片
	robot=Robot(listen_list_human[i],0,role,client,pretrained)#role表示角色
	robot_human_array.append(robot)"""
for i in range(0,len(listen_list_group)):
	wx2.AddListenChat(who=listen_list_group[i], savepic=False)  
	robot=Robot(listen_list_group[i],1,role,client,pretrained)
	robot_group_array.append(robot)

wait = 10
while True:
	#receive_message(wx,0,robot_human_array)
	receive_message(wx2,1,robot_group_array)
	time.sleep(wait)
