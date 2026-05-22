@echo off
REM SO101 Robot Control Server
REM Run on the machine connected to SO101 robot
REM
REM Usage:
REM   Real robot:  so101_server.bat
REM   Mock mode:   set MOCK_ROBOT=true && so101_server.bat

if not defined MOCK_ROBOT set MOCK_ROBOT=false

REM Server configuration
if not defined ROBOT_PORT set ROBOT_PORT=8001
if not defined ROBOT_HOST set ROBOT_HOST=0.0.0.0

REM Mock mode flag
set MOCK_FLAG=
if /i "%MOCK_ROBOT%"=="true" (
    set MOCK_FLAG=--mock
    echo Running in MOCK mode (no real robot)
)

set CAMERA_WRIST_INDEX=1

REM Set default values for camera/env vars BEFORE the if block
REM (CMD expands %%VAR%% at parse time inside if blocks, so they must be set outside)
if not defined SERIAL_PORT set SERIAL_PORT=COM3
if not defined CAMERA_UP_INDEX set CAMERA_UP_INDEX=045322072659
if not defined ROBOT_ID set ROBOT_ID=my_awesome_follower_arm

if "%MOCK_FLAG%"=="" (
    REM Real robot configuration
    python src/so101_robot_server.py ^
        --robot.type=so101_follower ^
        --robot.port=%SERIAL_PORT% ^
        --robot.id=%ROBOT_ID% ^
        --robot.cameras="{wrist: {type: opencv, index_or_path: %CAMERA_WRIST_INDEX%, width: 640, height: 480, fps: 30}, up: {type: intelrealsense, serial_number_or_name: %CAMERA_UP_INDEX%, width: 640, height: 480, fps: 30}}" ^
        --port %ROBOT_PORT% ^
        --host %ROBOT_HOST% ^
        --robot_type so101
) else (
    REM Mock mode - no hardware, no lerobot dependency
    python src/so101_robot_server.py ^
        --port %ROBOT_PORT% ^
        --host %ROBOT_HOST% ^
        --robot_type so101 ^
        %MOCK_FLAG%
)
