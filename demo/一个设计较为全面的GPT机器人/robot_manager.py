from robot import Robot
import json
import os


class RobotManager:
    def __init__(self, wechat):
        self.robots = []
        self.wechat = wechat
        self.config_file = "json/robots.json"
        self.robots_config = self.load_config()
        self.load_robots()

    # 保存配置到本地文件
    def save_config(self, robots):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(robots, f, ensure_ascii=False, indent=4)

    # 加载本地配置
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 如果文件不存在，创建文件并设置一个默认机器人
            default_robot = [
                {
                    "name": "DefaultRobot",
                    "persona": "友好型机器人",
                }
            ]
            self.save_config(default_robot)
            return default_robot

    # 添加机器人配置
    def add_robot_config(self, name, persona, targets):
        self.robots_config.append({
            "name": name,
            "persona": persona,
        })
        self.save_config(self.robots_config)

    # 删除机器人配置
    def delete_robot_config(self, name):
        robots_config = [robot for robot in self.robots_config if robot["name"] != name]
        self.save_config(robots_config)

    # 获取机器人配置
    def get_robot_config(self, name):
        robots = self.load_config()
        for robot in robots:
            if robot["name"] == name:
                return robot
        return None

    def create_robot(self, name, persona, wechat):
        robot = Robot(name, persona, wechat)
        self.robots.append(robot)
        self.add_robot_config(name, persona, wechat)
        self.save_config(self.robots_config)
        return robot

    # 从配置文件加载并创建机器人
    def load_robots(self):
        for robot_config in self.robots_config:
            name = robot_config["name"]
            persona = robot_config["persona"]
            robot = Robot(name, persona, self.wechat)
            self.robots.append(robot)

        # 处理消息

    def handle_message(self, message, nickname):
        # 查找空闲的机器人
        for robot in self.robots:
            if not robot.running:
                robot.start()
                robot.send_message_async(message, nickname)
                return

        # 如果没有空闲的机器人，选择第一个机器人处理消息
        if self.robots:
            first_robot = self.robots[0]
            if not first_robot.running:
                first_robot.start()
            first_robot.send_message_async(message, nickname)

