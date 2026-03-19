# Tools

This repository contains multiple robotics and AI tools, each with its own branch.

## Branch List

| Branch | Description |
|--------|-------------|
| [feature/llm-tools](https://github.com/pgq18/Tools/tree/feature/llm-tools) | AI voice recognition and iFLYTEK Spark LLM integration |
| [feature/go2-tools](https://github.com/pgq18/Tools/tree/feature/go2-tools) | Unitree Go2 robot dog camera and client tools |
| [feature/puppypi-demo](https://github.com/pgq18/Tools/tree/feature/puppypi-demo) | PuppyPi robot dog navigation and action control demo |
| [feature/tonypi-demo](https://github.com/pgq18/Tools/tree/feature/tonypi-demo) | TonyPi robot kick ball demo |
| [feature/wheeltec-tools](https://github.com/pgq18/Tools/tree/feature/wheeltec-tools) | Wheeltec mobile robot ROS TF pose publishing |
| [feature/robot-arm-tools](https://github.com/pgq18/Tools/tree/feature/robot-arm-tools) | LeRobot-based robot arm control tools |

## Usage

Checkout a specific tool branch:

```bash
# Clone a single tool
git clone -b feature/llm-tools https://github.com/pgq18/Tools.git

# Or switch in an existing repository
git checkout feature/llm-tools
```

## Tool Overview

### LLM-Tools
- **ASR**: iFLYTEK Speech Recognition
- **LLM**: iFLYTEK Spark Large Language Model

### Go2-Tools
- Front camera image capture and WebSocket video streaming
- ROS TF pose publishing

### PuppyPi-Demo
- Flask API client testing
- Navigation and action control interfaces

### TonyPi-Demo
- Ball kicking demo
- Test client

### Wheeltec-Tools
- ROS TF-based pose publishing tools

### Robot-Arm-Tools
- LeRobot-based robot arm control (SO100, SO101, Koch, etc.)
- WebSocket client for remote policy server (OpenPI)
- Keyboard control and video recording support
- Rerun visualization integration
