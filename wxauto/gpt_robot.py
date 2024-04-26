from openai import OpenAI
from wxauto import *

def receive_message(w,type,robot_array,condition,condition_type):
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
			elif type==1 and condition in msg[i][1] :
				num=0
				answer=robot_array[num].talk(change_mes(msg[i][1],condition,condition_type))
			elif type==0 :
				num=get_number(msg[i][0])
				print(num)
				answer=robot_array[num].talk(msg[i][1])
			else:
				continue
			chat.SendMsg(answer)

def change_mes(message,condition,condition_type):
    if condition_type==1:
        message_1 = message.replace(condition, "")
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

				
	def talk(self,question):
		self.mes_history.append({"role": "user", "content": question})	
		completion = self.client.chat.completions.create(
		model="gpt-4-turbo-preview",
		messages=self.mes_history
		)
		answer=completion.choices[0].message.content
		self.mes_history.append( {"role": "assistant", "content": answer})
		return answer


