#!/usr/bin/env python3
# encoding: utf-8

import rospy
from std_msgs.msg import Int32, String
from large_models.srv import SetString
import time
import signal
import sys

from wsgiref.simple_server import make_server
from flask import Flask, request, Response, jsonify
from threading import Thread
from puppy_control.msg import Velocity, Pose, Gait
import math
app = Flask(__name__)
httpd = None

thread = Thread(target=lambda: rospy.init_node('agent_input', disable_signals=True))
thread.start()
thread.join()
asr_pub = rospy.Publisher('vocal_detect/asr_result', String, queue_size=1)
start_task = rospy.ServiceProxy('/task', SetString)

PP = rospy.get_param('/puppy_control/PuppyPose')
PuppyPose_LookDown_30deg = PP['LookDown_30deg'].copy()
PuppyPose_Unload = PP['Unload'].copy()
PuppyPose_Stand = PP['Stand'].copy()
PuppyPosePub = rospy.Publisher('/puppy_control/pose', Pose, queue_size=1)
PuppyVelocityPub = rospy.Publisher('/puppy_control/velocity', Velocity, queue_size=1)

def asr_input_pub(prompt):
    asr_msg = String()
    asr_msg.data = prompt
    asr_pub.publish(asr_msg)
    print("============================== MSG SENT ==============================")

def unload():
    # PuppyPosePub.publish(stance_x=PuppyPose_LookDown_30deg['stance_x'], stance_y=PuppyPose_LookDown_30deg['stance_y'], x_shift=PuppyPose_LookDown_30deg['x_shift']
    #         ,height=PuppyPose_LookDown_30deg['height'], roll=PuppyPose_LookDown_30deg['roll'], pitch=PuppyPose_LookDown_30deg['pitch'], yaw=PuppyPose_LookDown_30deg['yaw'], run_time = 500)
    PuppyPosePub.publish(stance_x=PuppyPose_Unload['stance_x'], stance_y=PuppyPose_Unload['stance_y'], x_shift=PuppyPose_Unload['x_shift']
            ,height=PuppyPose_Unload['height'], roll=PuppyPose_Unload['roll'], pitch=PuppyPose_Unload['pitch'], yaw=PuppyPose_Unload['yaw'], run_time = 500)
    time.sleep(3)
    PuppyPosePub.publish(stance_x=PuppyPose_Stand['stance_x'], stance_y=PuppyPose_Stand['stance_y'], x_shift=PuppyPose_Stand['x_shift']
            ,height=PuppyPose_Stand['height'], roll=PuppyPose_Stand['roll'], pitch=PuppyPose_Stand['pitch'], yaw=PuppyPose_Stand['yaw'], run_time = 500)
    
def forward(duration):
    PuppyVelocityPub.publish(x=10, y=0, yaw_rate = math.radians(0))
    time.sleep(duration)
    PuppyVelocityPub.publish(x=0, y=0, yaw_rate = math.radians(0))

def turn(direstion, duration):
    if direstion == "left":
        PuppyVelocityPub.publish(x=0, y=0, yaw_rate = math.radians(12))
        time.sleep(duration)
    elif direstion == "right":
        PuppyVelocityPub.publish(x=0, y=0, yaw_rate = math.radians(-12))
        time.sleep(duration)
    PuppyVelocityPub.publish(x=0, y=0, yaw_rate = math.radians(0))

@app.route('/puppy/api/action', methods=['POST'])
def action():
    print(f'action++, from={ request.form}, json={ request.json} ')
    content_type=request.headers['Content-Type']
    if 'from-data' in content_type:
        print('action, from-data++')
    elif 'application/json' in content_type:
        print(f'action, application/json++, {request.json}')
        action_text = request.json["action"]['text']
        print(f'action, action_text={action_text}')
        try:
            if("unload" in action_text):
                unload()
                # asr_input_pub(action_text)
                return jsonify({
                            "status": "success",
                            "message": "successfully move to red"
                        }), 200
            elif("forward" in action_text):
                duration = request.json["duration"]
                forward(duration)
                return jsonify({
                            "status": "success",
                            "message": "successfully move forward for 3s"
                        }), 200
            elif("turn" in action_text):
                duration = request.json["duration"]
                direstion = request.json["direstion"]
                turn(direstion, duration)
                return jsonify({
                            "status": "success",
                            "message": "successfully turn for 3s"
                        }), 200
            else:
                return jsonify({
                    "status": "failure",
                    "message": "invalid input"
                }), 500
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Service call failed: {str(e)}"
            }), 500


    elif 'text/plain' in content_type:
        print('action, text/plain++')

    return "已成功启动"

@app.route('/puppy/api/navigate', methods=['POST'])
def navigate():
    print(f'action++, from={request.form}, json={request.json} ')
    content_type=request.headers['Content-Type']
    if 'from-data' in content_type:
        print('action, from-data++')
    elif 'application/json' in content_type:
        print(f'action, application/json++, {request.json}')
        action_text = request.json["action"]['text']
        print(f'action, action_text={action_text}')
        try:
            if action_text == "green":
                start_task("green")
                return jsonify({
                    "status": "success",
                    "message": "successfully move to green"
                }), 200
            elif action_text == "blue":
                start_task("blue")
                return jsonify({
                    "status": "success",
                    "message": "successfully move to blue"
                }), 200
            elif action_text == "red":
                start_task("red")
                return jsonify({
                    "status": "success",
                    "message": "successfully move to red"
                }), 200
            else:
                return jsonify({
                    "status": "failure",
                    "message": "invalid input"
                }), 500
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Service call failed: {str(e)}"
            }), 500
    elif 'text/plain' in content_type:
        print('action, text/plain++')

    return jsonify({
                "status": "success",
                "message": "已成功启动"
            }), 200

def signal_handler(sig, frame):
    print('收到SIGINT信号，正在关闭服务器...')
    if httpd:
        httpd.shutdown()
    rospy.signal_shutdown("收到关闭信号")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    host='0.0.0.0'
    port=8789
    httpd = make_server(host, port, app)
    print(f"Servie {host}:{port} running...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("服务器已关闭")
        pass