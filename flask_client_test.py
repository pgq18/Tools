import requests
import json

base_url = "http://192.168.3.155:8789/puppy/api"

def test_navigate_api():
    """
    测试 /puppy/api/navigate 接口
    """
    url = base_url + "/navigate"
    
    # 测试不同的导航指令
    test_cases = [
        # {"action": {"text": "green"}},
        {"action": {"text": "blue"}},
        # {"action": {"text": "red"}},
        # {"action": {"text": "unknown"}}
    ]
    
    headers = {
        "Content-Type": "application/json"
    }
    
    for data in test_cases:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        print(f"Navigate API - Request: {data}")
        print(f"Navigate API - Response: {response.text}")
        print(f"Status Code: {response.status_code}")
        print("-" * 40)

def test_action_api():
    """
    测试 /puppy/api/action 接口
    """
    url = base_url + "/action"
    
    # 测试不同的导航指令
    test_cases = [
        # {"action": {"text": "unload"}},
        # {"action": {"text": "forward"}, "duration": 3},
        {"action": {"text": "turn"}, "direstion": "right", "duration": 6.5},
        # {"action": {"text": "forward"}, "duration": 3},
        # {"action": {"text": "turn"}, "direstion": "left", "duration": 3},
        # {"action": {"text": "forward"}, "duration": 3},
        # {"action": {"text": "turn"}, "direstion": "right", "duration": 12.5},
        # {"action": {"text": "forward"}, "duration": 3},
        # {"action": {"text": "turn"}, "direstion": "right", "duration": 3},
        # {"action": {"text": "forward"}, "duration": 3},
        # {"action": {"text": "turn"}, "direstion": "left", "duration": 3},
        # {"action": {"text": "forward"}, "duration": 3},
        # {"action": {"text": "unknown"}}
    ]
    
    headers = {
        "Content-Type": "application/json"
    }
    
    for data in test_cases:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        print(f"Action API - Request: {data}")
        print(f"Action API - Response: {response.text}")
        print(f"Status Code: {response.status_code}")
        print("-" * 40)

if __name__ == "__main__":
    print("开始测试 Flask API...")
    print("确保 Flask 服务器已在运行...")
    print("=" * 50)
    
    # 测试 navigate 接口
    # print("2. 测试 Navigate API:")
    # test_navigate_api()

    # 测试 action 接口
    print("3. 测试 Action API:")
    test_action_api()
    
    print("\n测试完成!")