# Robot-Arm-Tools

机器人臂数据采集与测试工具集。

## 脚本说明

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
