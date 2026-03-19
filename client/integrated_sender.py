#!/usr/bin/env python3
import os
import sys
if os.geteuid() != 0:
    os.execvp("sudo", ["sudo"] + ["python3"] + sys.argv)
from ctypes import *
import numpy as np
import cv2
import asyncio
import websockets
import base64
import json
from threading import Thread
from flask import Flask, render_template, jsonify, request, url_for
from perception_node import PerceptionNode
import argparse
import math
import socketio
import time

SERVER_URL = "http://192.168.3.8:5555"  # 换成你的 Flask 服务器 IP
ROBOT_ID   = "dog2"                     # 这台机器人的 ID
MAP_FRAME  = "map"                     # slam_toolbox 的地图坐标系
BASE_FRAME = "base_link"               # 机器人底盘坐标系

parser = argparse.ArgumentParser()
parser.add_argument("--remembr", action="store_true", help="remembr")
args = parser.parse_args()

pn = PerceptionNode(debug=False)

if args.remembr:
    pn.start_processing_loop()

# 创建 Flask 应用用于接收位置信息
app = Flask(__name__)

@app.route('/position', methods=['POST'])
def receive_position():
    try:
        data = request.get_json()
        x = data.get('x', 0)
        y = data.get('y', 0)
        yaw = data.get('yaw', 0)
        
        position = {"x": x, "y": y, "yaw": yaw}
        pn.set_position(position)
        
        return jsonify({"status": "success", "message": "Position updated"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
@app.route('/perception/stop', methods=['POST'])
def stop_processing_loop():
    try:
        pn.stop_processing_loop()
        return jsonify({"status": "success", "message": "Perception processing loop stopped"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
@app.route('/perception/start', methods=['POST'])
def start_processing_loop():
    try:
        pn.start_processing_loop()
        return jsonify({"status": "success", "message": "Perception processing loop started"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

def start_flask_server():
    app.run(host='0.0.0.0', port=5000, threaded=True)

class FrontCamera():
    def __init__(self, networkInterface="eth0"):
        self.lib = cdll.LoadLibrary("/home/unitree/Desktop/Test/Go2-Tools/front_camera/build/libfront_camera.so")
        self.lib.init_camera.argtypes = [c_char_p]
        self.lib.init_camera.restype = c_void_p
        self.client = self.lib.init_camera(networkInterface.encode('utf-8'))
        self.img_buffer = np.zeros(dtype=np.uint8, shape=(400000,1))

    def capture(self):
        res = self.lib.capture_img(c_void_p(self.client), self.img_buffer.ctypes.data_as(POINTER(c_ubyte)))
        if res == -1:
            return None
        else:
            img = cv2.imdecode(self.img_buffer[:res], cv2.IMREAD_COLOR)
            return img

def camera_loop():
    cap = FrontCamera()
    try:
        while True:
            frame = cap.capture()
            if frame is None:
                break

            # print(frame.shape) # (1080, 1920, 3)
                
            # 调整帧大小
            frame = cv2.resize(frame, (640, 360))
            
            # 编码为JPEG格式
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            
            # 转换为base64字符串
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            pn.set_image(jpg_as_text)
    except Exception as e:
        print(f"抓取图像时出错: {e}")
    finally:
        del cap  # 删除cap对象，因为FrontCamera没有release方法

# async def send_video_stream(websocket, path):
async def send_video_stream(websocket):
    print("客户端已连接")
    cap = FrontCamera()
    try:
        while True:

            jpg_as_text = pn.buffer["image"]
            
            # 创建JSON消息
            message = json.dumps({
                'image': jpg_as_text
            })
            
            # 发送消息
            await websocket.send(message)
            
            # 控制帧率
            await asyncio.sleep(0.03)  # 约30 FPS
            
    except websockets.exceptions.ConnectionClosed:
        print("客户端断开连接")
    except Exception as e:
        print(f"发送视频时出错: {e}")
    finally:
        del cap  # 删除cap对象，因为FrontCamera没有release方法

async def main():
    # 启动WebSocket服务器
    start_server = websockets.serve(send_video_stream, "0.0.0.0", 8765)
    print("WebSocket服务器已在端口8765上启动")
    await start_server


if __name__ == '__main__':
    # 启动Flask服务器线程
    flask_thread = Thread(target=start_flask_server, daemon=True)
    flask_thread.start()
    
    camera_thread = Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_forever()