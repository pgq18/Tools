# Robot-Arm-Tools

机器人臂数据采集、远程控制与 VLA 推理测试工具集。支持 SO101 单臂和 Alicia D 双臂机器人，提供 WebSocket 服务器、动作分块推理、Human-in-the-Loop 测试及数据集处理等功能。

## 项目结构

```
Tools/
├── src/                        # 核心源码
│   ├── main.py                 # 机器人控制主程序（支持 RTC 模式）
│   ├── so101_robot_server.py   # SO101 WebSocket 服务器
│   ├── hil_test.py             # Human-in-the-Loop 测试
│   ├── dataset_process.py      # 数据集处理工具
│   └── get_idle_action.py      # 获取机械臂空闲位姿
├── openpi_client/              # 推理客户端库
│   ├── base_policy.py          # 策略基类（抽象接口）
│   ├── action_chunk_broker.py  # 动作分块代理（标准模式 + RTC 模式）
│   ├── websocket_client_policy.py  # WebSocket 策略客户端
│   ├── websocket_policy_server.py  # WebSocket 策略服务器
│   ├── image_tools.py          # 图像预处理工具
│   ├── msgpack_numpy.py        # msgpack + numpy 序列化
│   └── runtime/                # 通用运行时框架
│       ├── runtime.py          # Runtime 主循环（Agent-Environment 编排）
│       ├── agent.py            # Agent 抽象基类
│       ├── environment.py      # Environment 抽象基类
│       ├── subscriber.py       # 事件订阅者基类
│       └── agents/
│           └── policy_agent.py # 基于 Policy 的 Agent 实现
├── calibration/                # 机器人、遥操作器及数据集标定配置
├── lerobot/                    # lerobot 相关配置
├── asserts/                    # 静态资源
└── *.sh                        # 各场景启动脚本
```

## 功能模块

### 1. 机器人控制（`src/main.py`）

统一的机器人控制入口，支持 SO101 单臂和 Alicia D 双臂：

- **标准推理模式**：通过 WebSocket 连接远程 VLA 推理服务，按 action chunk 逐步执行
- **RTC（Real-Time Action Chunking）模式**：后台线程异步推理，重叠计算与执行，降低延迟
- **视频录制**：可选录制 up 相机画面为 MP4
- **键盘交互**：`s` 启停机器人，`q` 退出

### 2. SO101 WebSocket 服务器（`src/so101_robot_server.py`）

将 SO101 机器人能力通过网络暴露，支持分布式部署：

| API 方法 | 功能 |
|----------|------|
| `get_observation` | 获取关节状态 + 相机图像 |
| `send_action` | 发送关节位置指令 |
| `reset` | 复位到空闲位姿 |
| `get_metadata` | 获取服务器元信息 |

支持 `--mock` 模式无需硬件即可测试。

### 3. 动作分块代理（`openpi_client/action_chunk_broker.py`）

封装推理策略，逐步返回动作：

- **标准模式**：耗尽当前 chunk 后再请求新推理
- **RTC 模式**：在执行第 `s` 步时启动后台推理，第 `s+d` 步时无缝切换结果，消除推理等待延迟

### 4. 推理通信（`openpi_client/`）

- `websocket_client_policy.py`：同步 WebSocket 客户端，连接远端策略服务
- `websocket_policy_server.py`：WebSocket 策略服务端，加载策略并响应推理请求
- `base_policy.py`：策略抽象基类，定义 `infer` / `reset` 接口
- 使用 msgpack + numpy 高效序列化，适合图像等大数据传输

### 5. 运行时框架（`openpi_client/runtime/`）

通用的 Agent-Environment 编排框架：

- `Runtime`：驱动 Agent 与 Environment 交互主循环
- `Agent` / `Environment`：抽象基类，解耦决策与感知
- `Subscriber`：事件回调机制（用于日志、可视化等）

### 6. Human-in-the-Loop 测试（`src/hil_test.py`）

在线强化学习人工干预测试：

- **自主模式**：Follower 由模型控制，Leader 跟踪 Follower
- **干预模式**：Leader 控制 Follower，记录干预数据

### 7. 数据集处理（`src/dataset_process.py`）

基于 lerobot 的数据集处理工具：

- 查看数据集信息
- 可视化 episode 动作轨迹
- 删除指定 episode
- 时间偏移测量与校准
- 交互式命令行界面

### 8. 空闲位姿获取（`src/get_idle_action.py`）

手动将 Alicia D 机械臂移动到期望位置，实时读取关节值作为 idle_action。

## 启动脚本

### SO101 机器人

| 脚本 | 用途 |
|------|------|
| `so101_server.sh` | 启动 SO101 WebSocket 服务器，用于分布式远程控制 |
| `so101_teleoperate.sh` | SO101 遥操作模式，leader-follower 实时控制 |
| `so101_record.sh` | SO101 数据集采集（leader-follower 模式） |
| `so101_test.sh` | SO101 与 VLA 推理服务端通信测试 |

### Alicia D 双臂机器人

| 脚本 | 用途 |
|------|------|
| `bi_alicia_d_test.sh` | 双臂 Alicia D 与 VLA 推理服务端通信测试 |
| `bi_alicia_d_record.sh` | 双臂 Alicia D 数据集采集（leader-follower 模式） |
| `bi_alicia_d_get_idle.sh` | 获取空闲动作状态 |
| `single_alicia_d_record.sh` | 单臂 Alicia D 数据集采集（leader-follower 模式） |

### HIL 测试

| 脚本 | 用途 |
|------|------|
| `hil_test.sh` | Human-in-the-Loop 测试，连接远程服务器进行干预记录 |
| `hil_test_debug.sh` | HIL 调试模式，本地运行（支持 idle/cyclic 动作） |

### 数据处理

| 脚本 | 用途 |
|------|------|
| `dataset_process.sh` | 数据集处理工具（删除 episode、可视化、时间偏移校准等） |

## 常用命令

查找设备串口：
```bash
lerobot-find-port
```
