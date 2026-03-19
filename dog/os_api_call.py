#!/usr/bin/env python3
# encoding: utf-8

import rospy
import time
import math
import threading
from puppy_control.srv import SetRunActionName
# from std_srvs.srv import Trigger, Empty, SetBool
from std_srvs.srv import *
from puppy_control.msg import Velocity, Pose, Gait
from std_msgs.msg import String
from large_models.srv import SetString

class FunctionCall:
    def __init__(self, name):
        # 初始化 ROS 节点
        rospy.init_node(name)

        # 初始化变量
        self.action = []
        self.llm_result = ''
        self.running = True
        self.result = ''

        # 创建话题发布者
        self.pose_publisher = rospy.Publisher('puppy_control/pose', Pose, queue_size=10)
        self.gait_publisher = rospy.Publisher('puppy_control/gait', Gait, queue_size=10)
        self.velocity_publisher = rospy.Publisher('puppy_control/velocity', Velocity, queue_size=10)
        
        # 设置步态
        self.set_gait()

        # 创建服务代理
        self.cli = rospy.ServiceProxy('/puppy_control/go_home', Empty)

        rospy.Subscriber('/color', String, self._call_back)
        self.run_action_group_srv = rospy.ServiceProxy('puppy_control/runActionGroup', SetRunActionName)

        # kick_ball 客户端
        self.enter_client_kick_ball = rospy.ServiceProxy('kick_ball_demo/enter', Trigger)
        self.start_client_kick_ball = rospy.ServiceProxy('kick_ball_demo/enable_running', SetBool)
        self.set_target_client_kick_ball = rospy.ServiceProxy('kick_ball_demo/set_color_target', SetString)

        # visual_patrol 客户端
        self.enter_client_visual_patrol = rospy.ServiceProxy('visual_patrol_demo/enter', Trigger)
        self.start_client_visual_patrol = rospy.ServiceProxy('visual_patrol_demo/enable_running', SetBool)
        self.set_target_client_visual_patrol = rospy.ServiceProxy('visual_patrol_demo/set_color_target', SetString)
        
        time.sleep(10)
        # 初始化进程
        self.init_process()

        # 创建初始化完成的服务
        rospy.Service('~init_finish', Trigger, self.get_node_state)
        rospy.loginfo('\033[1;32m%s\033[0m' % 'start')

        self.task_service = rospy.Service('/task', SetString, self._call_back)

    def init_process(self):
        # 调用回家服务，并播放起始音频
        self.cli()

    def get_node_state(self, request):
        # 返回节点状态的服务回调
        response = Trigger()
        response.success = True
        return response

    def set_move(self, x=0.00, y=0.0, yaw_rate=0.0):
        # 发布移动指令
        velocity_msg = Velocity(x=x, y=y, yaw_rate=yaw_rate)
        self.velocity_publisher.publish(velocity_msg)

    def set_gait(self, overlap_time=0.15, swing_time=0.2, clearance_time=0.0, z_clearance=5.0):
        # 设置步态参数并发布
        self.gait_publisher.publish(Gait(overlap_time=overlap_time, swing_time=swing_time, clearance_time=clearance_time, z_clearance=z_clearance))

    def _call_back(self, msg):
        color = msg.data
        if color == 'red' or color == 'green' or color == 'blue':
            print("finding ...")
            reponse = self.enter_client_kick_ball()
            print(reponse)
            self.set_target_client_kick_ball(color)
            response = self.start_client_kick_ball(True)
            print(response)
            response = TriggerResponse()
            response.success = True
            response.message = color
            return [True, 'color']
        else:
            print("wrong input")
            response = TriggerResponse()
            response.success = False
            response.message = color
            return [False, 'color']
    
def main():
    # 主函数
    node = FunctionCall('my_function_call')
    try:
        rospy.spin()  # 持续运行节点
    except rospy.ROSInterruptException:
        print('shutdown')
    finally:
        rospy.signal_shutdown('Node shutdown')  # 清理节点

if __name__ == "__main__":
    main()

    
