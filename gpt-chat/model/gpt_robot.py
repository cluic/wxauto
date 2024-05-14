from openai import OpenAI
from wxauto import *

class Robot:
	def __init__(self,human_group_info,client,model):
		self.human_group_info = human_group_info
		self.model = model	
		self.client = client#获取openai实例
		self.mes_history = self.prepare(human_group_info['role_file'],human_group_info['pretrained_file'])
		self.condition = human_group_info['condition']
		self.condition_type = human_group_info['condition_type']

	def _read_(self, role):
		with open(role, 'r', encoding='utf-8') as file:
			return file.readlines()

	#通过插入角色预设和多段提前对话，达到预训练的效果
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
	
	#输入问题，输出答案
	def generate_answer(self,question):	
		self.mes_history.append({"role": "user", "content": question})	
		completion = self.client.chat.completions.create(
		model=self.model,
		messages=self.mes_history
		)#导入历史对话，使得GPT拥有历史记忆
		answer=completion.choices[0].message.content
		self.mes_history.append( {"role": "assistant", "content": answer})
		return answer

	#判断是否需要去掉关键词并执行操作
	def change_mes(self,message):
		if self.condition_type==1:
			message_modify = message.replace(self.condition, "")
			return message_modify
		else:
			return message

	#获取用户对应机器人的的编号
	def get_number(name):
		global listen_list_human
		for i in range(0,len(listen_list_human)):
			if name==listen_list_human[i]:
				return i

	def chat(self,msgs):#与机器人实现聊天
		chat_target = None
		for chat in msgs:#找到相应的聊天窗口
			if chat.who == self.human_group_info['name']:
				chat_target = chat
				break
		if chat_target is None:
			return
		msg = msgs.get(chat_target)   # 获取消息内容
		for i in range(1,len(msg)):
			#打印消息内容，用于调试
			print(msg[i][0])
			print(msg[i][1])

			if msg[i][0]=='SYS' or msg[i][0]=='Self':#如果检测到接收到自己的信息和系统信息如撤回，则跳过
				continue
			elif self.condition in msg[i][1] :
				messaage = self.change_mes(msg[i][1])#选择是否去掉关键词
				answer=self.generate_answer(messaage)#生成答案
			else:
				continue
			chat.SendMsg(answer)
