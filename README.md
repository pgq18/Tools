# Tools

A collection of robotics and AI tools, including tools for multiple robot platforms and LLM-related functionalities.

## Directory Structure

```
Tools/
├── LLM-Tools/        # AI voice and LLM tools
├── Go2-Tools/        # Unitree Go2 robot dog tools
├── PuppyPi-Demo/     # PuppyPi robot dog demo
├── TonyPi-Demo/      # TonyPi robot demo
├── Wheeltec-Tools/   # Wheeltec mobile robot tools
└── Robot-Arm-Tools/  # Robot arm control tools
```

## Module Description

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

## Installation

```bash
git clone https://github.com/pgq18/Tools.git
```

For detailed usage, please refer to the README files in each subdirectory.
