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

class FrontCamera():
    def __init__(self, networkInterface="eth0"):
        self.lib = cdll.LoadLibrary("/home/unitree/go2_camera/front_camera/build/libfront_camera.so")
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

async def send_video_stream(websocket, path):
    print("客户端已连接")
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
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_forever()