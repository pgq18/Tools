import os
from flask import Flask, render_template, jsonify, request, url_for
from openai import OpenAI
import io
import base64
import time
from threading import Thread
import numpy as np
from dataclasses import dataclass

@dataclass
class ImageWithPose:
    """图像和位置信息的数据结构"""
    image: np.ndarray
    position: dict
    theta: float = 0.0
    timestamp: float = 0.0

class VLModel():
    def __init__(self, model_name="qwen2.5-vl-7b-instruct", debug=False):
        self.model_name = model_name
        self.debug = debug
        if not debug:
            self.client = OpenAI(
                # api_key=os.getenv("DASHSCOPE_API_KEY"),
                api_key="sk-7edd1e29b5694d1bad48cdbdb5ecaddc",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

    def invoke(self, message):
        completion = self.client.chat.completions.create(
            # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            model=self.model_name,
            messages=message,
            max_tokens=512,
            temperature=0.2
        )
        return completion.choices[0].message

class PerceptionNode():
    def __init__(self, memory_ip="localhost", memory_port=5000, debug=False):
        self.memory_url = f"http://{memory_ip}:{memory_port}"
        self.debug = debug
        self.prompt = "Based on the video, briefly describe the key elements in this scene. " + \
            "Focus only on three aspects: 1) Environment (indoor/outdoor, general setting), " + \
            "2) Key objects (people, animals, notable items), and 3) Key events/activities. " + \
            "Keep your response concise and under 80 words. Output format: " + \
            "[Environment: ...] [Key objects: ...] [Key events: ...]"
        self.use_every_nth_image = 15
        self.caption_image_count = 6
        self.caption_interval = 3.0
        self._init_vlm_model()

        # 状态变量
        self.images_with_poses = []  # 带位置信息的图像缓冲区
        self.image_counter = 0
        self.running = False

        self.buffer = {"position": {"x": 0, "y": 0, "yaw": 0}, "image": None}
        self.images = []

    def _init_vlm_model(self):
        self.vlm_model = VLModel(debug=self.debug)

    def _caption_with_vlm(self, images_str):
        """使用线上VLM生成图像描述"""
        try:
            # 构建消息内容
            content = [{"role": "system", "content": self.prompt}]
            # 添加图像（转换为base64）
            for img_str in images_str:
                content.append({
                    "role": "user",
                    "content": [{
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_str}",
                            "detail": "low"
                        }
                    }]
                })
            # 调用VLM
            message = content
            if not self.debug:
                response = self.vlm_model.invoke(message)
                return response.content
            else:
                return "VLM response: " + "test response"
        except Exception as e:
            print(f"❌ 线上VLM调用失败: {e}")
            return f"VLM error: {str(e)}"
        
    def _send_message(self, caption, pose):
        """发送消息给MemoryNode"""
        url = f"{self.memory_url}"
        headers = {"Content-Type": "application/json"}
        data = {
            "caption": caption,
            "pose": {
                "x": pose["x"],
                "y": pose["y"],
                "yaw": pose["yaw"]
            },
            "timestamp": 0.0
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                print("✅ 消息已发送")
            else:
                print()
        except Exception as e:
            print(f"❌ 发送消息失败: {e}")
        
    def start_processing_loop(self):
        """启动处理循环"""
        self.running = True
        thread = Thread(target=self.processing_loop, daemon=True)
        thread.start()
        self.processing_loop_thread = thread
        print("✅ 处理循环已启动")

    def stop_processing_loop(self):
        """停止处理循环"""
        self.running = False
        if self.processing_loop_thread:
            self.processing_loop_thread.join()
            self.processing_loop_thread = None
        print("✅ 处理循环已停止")

    def processing_loop(self):
        last_process = time.perf_counter()
        print("开始图像采集和记忆处理循环...")
        while self.running:
            dt = time.perf_counter() - last_process
            if dt < self.caption_interval:
                time.sleep(0.1)  # 短暂休眠，避免忙等待
                continue
            try:
                # 由于我们是主动调用API而不是接收高频消息，每次都尝试采集图像
                print("正在采集图像和位置信息...")
                if self.buffer["image"] is None:
                    print("⚠️ 跳过处理：无法获取图像")
                    continue
                image_with_pose = ImageWithPose(
                    image=self.buffer["image"],
                    position=self.buffer["position"],
                    theta=0.0,
                    timestamp=time.time()
                )
                self.images_with_poses.append(image_with_pose)
                if len(self.images_with_poses) > self.caption_image_count:
                    self.images_with_poses = self.images_with_poses[1:]
                print("✅ 图像已添加到缓冲区")
                self.image_counter += 1
                # 检查是否可以生成描述
                if len(self.images_with_poses) >= self.caption_image_count:
                    # 生成描述
                    images = [iwp.image for iwp in self.images_with_poses]
                    caption = self._caption_with_vlm(images)
                    # 使用最新图像的位置信息
                    latest_image_with_pose = self.images_with_poses[-1]
                    print(f"位置信息: {latest_image_with_pose.position}")
                    print(f"✅ 使用 {len(images)} 张图像生成描述")
                    print(f"描述内容: {caption}")
                    self._send_message(caption, latest_image_with_pose.position)
            except Exception as e:
                print(f"❌ 处理失败: {e}")

            last_process = time.perf_counter()

    def set_position(self, position):
        self.buffer["position"] = position

    def set_image(self, image):
        self.buffer["image"] = image
