#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time

class KickBallClient:
    def __init__(self, base_url='http://192.168.3.143:5000'):
        self.base_url = base_url
        self.api_endpoint = f"{base_url}/tonypi/api/kick_ball"
    
    def start_kick_ball(self):
        """
        发送开始踢球命令
        """
        try:
            response = requests.post(self.api_endpoint, data={'command': 'start'})
            if response.status_code == 200:
                print("成功发送开始踢球命令")
                return True
            else:
                print(f"发送开始命令失败，状态码: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"请求出错: {e}")
            return False
    
    def stop_kick_ball(self):
        """
        发送停止踢球命令
        """
        try:
            response = requests.post(self.api_endpoint, data={'command': 'stop'})
            if response.status_code == 200:
                print("成功发送停止踢球命令")
                return True
            else:
                print(f"发送停止命令失败，状态码: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"请求出错: {e}")
            return False

def main():
    # 创建客户端实例
    client = KickBallClient('http://192.168.3.50:5000')
    
    print("TonyPi 踢球程序客户端")
    print("=" * 30)
    
    while True:
        print("\n请选择操作:")
        print("1. 开始踢球")
        print("2. 停止踢球")
        print("3. 退出")
        
        choice = input("请输入选项 (1-3): ").strip()
        
        if choice == '1':
            client.start_kick_ball()
        elif choice == '2':
            client.stop_kick_ball()
        elif choice == '3':
            print("退出程序")
            break
        else:
            print("无效选项，请重新输入")

if __name__ == '__main__':
    main()