#!/usr/bin/env python3
import math
import socketio
import requests

import rclpy
from rclpy.node import Node
from rclpy.time import Time

from tf2_ros import Buffer, TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException


SERVER_URL = "http://192.168.3.17:5555"  # 换成你的 Flask 服务器 IP
FLASK_SERVER_URL = "http://localhost:5000"  # Flask 服务器地址
ROBOT_ID   = "dog2"                     # 这台机器人的 ID
MAP_FRAME  = "map"                     # slam_toolbox 的地图坐标系
BASE_FRAME = "base_link"               # 机器人底盘坐标系

class TfPoseSender(Node):
    def __init__(self):
        super().__init__("dog_tf_sender")

        # SocketIO 客户端
        self.sio = socketio.Client()
        try:
            self.sio.connect(SERVER_URL)
            self.get_logger().info(f"Connected to Flask server at {SERVER_URL}")
        except Exception as e:
            self.get_logger().error(f"Failed to connect to server: {e}")

        # TF2 Buffer + Listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # 定时器，10Hz 查询一次 TF 然后发送
        self.timer = self.create_timer(0.1, self.timer_cb)

    def timer_cb(self):
        try:
            # 查 TF: map -> base_link
            t = self.tf_buffer.lookup_transform(
                MAP_FRAME,
                BASE_FRAME,
                Time()               # 最新可用时间
            )
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().warn(f"Could not get transform {MAP_FRAME}->{BASE_FRAME}: {e}")
            return

        x = t.transform.translation.x
        y = t.transform.translation.y
        q = t.transform.rotation

        # 从四元数算 yaw（绕 z 轴）
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )

        # SocketIO 发送数据
        socketio_data = {
            "id": ROBOT_ID,
            "x": x,
            "y": y,
            "angle": yaw
        }
        print(socketio_data)
        try:
            self.sio.emit("update_robot_position", socketio_data)
        except Exception as e:
            self.get_logger().warn(f"SocketIO emit failed: {e}")

        # 同时发送到 Flask 服务器
        try:
            flask_data = {
                "x": x,
                "y": y,
                "yaw": yaw
            }
            response = requests.post(f"{FLASK_SERVER_URL}/position", json=flask_data)
            if response.status_code != 200:
                self.get_logger().warn(f"Failed to send position to Flask server: {response.status_code}")
        except Exception as e:
            self.get_logger().warn(f"Failed to send position to Flask server: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = TfPoseSender()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
    try:
        node.sio.disconnect()
    except Exception:
        pass

if __name__ == "__main__":
    main()