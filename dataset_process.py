#!/home/pengguanqi/miniconda3/envs/tools-lerobot/bin/python
"""
数据集处理工具

基于 lerobot 库的数据集处理脚本，提供以下功能：
1. 读取并显示数据集信息
2. 可视化 episode 的动作轨迹
3. 删除指定 episodes 并保存为新数据集
4. 时间偏移测量和调节
5. 交互式命令行界面

Usage:
    # 显示数据集信息
    python dataset_process.py --dataset-path /path/to/dataset --info

    # 可视化单个 episode
    python dataset_process.py --dataset-path /path/to/dataset --visualize --episode 0

    # 删除指定 episodes
    python dataset_process.py --dataset-path /path/to/dataset --delete-episodes 0,1 --output /path/to/output

    # 测量时间偏移
    python dataset_process.py --dataset-path /path/to/dataset --measure-offset --episode 0

    # 应用时间偏移
    python dataset_process.py --dataset-path /path/to/dataset --apply-offset --video-offset observation.images.wrist:0.1 --output /path/to/output

    # 进入交互模式
    python dataset_process.py --dataset-path /path/to/dataset --interactive
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 配置 logging 以显示进度信息
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

# 从本地 lerobot 源码导入
sys.path.insert(0, str(Path(__file__).parent / "lerobot" / "src"))

from lerobot.datasets.dataset_tools import delete_episodes
from lerobot.datasets.lerobot_dataset import LeRobotDataset


# ============================================================================
# 数据集加载和信息显示
# ============================================================================

def load_dataset(dataset_path: str, episodes: Optional[list] = None, tolerance_s: float = 0.1) -> LeRobotDataset:
    """
    加载 LeRobot 数据集

    Args:
        dataset_path: 数据集路径
        episodes: 要加载的 episode 索引列表，None 表示加载全部
        tolerance_s: 时间戳容差（秒），默认 0.1s，用于处理偏移后的数据集

    Returns:
        LeRobotDataset 实例
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"数据集路径不存在: {dataset_path}")

    # 使用路径名称作为 repo_id
    repo_id = path.name

    kwargs = {"repo_id": repo_id, "root": path, "tolerance_s": tolerance_s}
    if episodes is not None:
        kwargs["episodes"] = episodes

    dataset = LeRobotDataset(**kwargs)
    return dataset


def print_dataset_info(dataset: LeRobotDataset):
    """
    打印数据集基本信息

    Args:
        dataset: LeRobotDataset 实例
    """
    print("\n" + "=" * 60)
    print("数据集信息")
    print("=" * 60)
    print(f"Repo ID:        {dataset.repo_id}")
    print(f"路径:           {dataset.root}")
    print(f"Robot 类型:     {dataset.meta.robot_type}")
    print(f"FPS:            {dataset.meta.fps}")
    print(f"总 Episodes:    {dataset.meta.total_episodes}")
    print(f"总帧数:         {dataset.meta.total_frames}")
    print(f"总任务数:       {dataset.meta.total_tasks}")
    print(f"代码版本:       {dataset.meta._version}")
    print(f"\n特征列表:")
    for name, feat in dataset.meta.features.items():
        if feat["dtype"] == "video":
            print(f"  - {name}: video {feat['shape']} (camera)")
        else:
            print(f"  - {name}: {feat['dtype']} {feat['shape']}")

    if dataset.meta.video_keys:
        print(f"\n摄像头:         {', '.join(dataset.meta.video_keys)}")

    if hasattr(dataset.meta, "tasks") and dataset.meta.tasks is not None:
        print(f"\n任务列表:")
        for task_name, row in dataset.meta.tasks.iterrows():
            print(f"  - Task {row['task_index']}: {task_name}")

    # 显示 episode 统计
    print(f"\nEpisode 统计:")
    episodes_data = dataset.meta.episodes
    if episodes_data is not None and len(episodes_data) > 0:
        # episodes 是 HuggingFace Dataset，获取 length 和 episode_index
        lengths = list(episodes_data["length"])
        episode_indices = list(episodes_data["episode_index"])

        min_len = min(lengths)
        max_len = max(lengths)
        avg_len = sum(lengths) / len(lengths)

        # 找到最短和最长的 episodes
        min_ep_indices = [episode_indices[i] for i, l in enumerate(lengths) if l == min_len]
        max_ep_indices = [episode_indices[i] for i, l in enumerate(lengths) if l == max_len]

        print(f"  - 最短长度:    {min_len} 帧 (Episode {min_ep_indices})")
        print(f"  - 最长长度:    {max_len} 帧 (Episode {max_ep_indices})")
        print(f"  - 平均长度:    {avg_len:.1f} 帧")
        print(f"  - 总时长:      {sum(lengths) / dataset.meta.fps:.1f} 秒")

    print("=" * 60 + "\n")


# ============================================================================
# 可视化功能
# ============================================================================

def extract_and_save_episode_videos(
    dataset: LeRobotDataset,
    episode_index: int,
    output_dir: str,
    fps: int = 30
):
    """
    提取并保存 episode 的视频（使用 PyAV 支持 AV1 编码）

    Args:
        dataset: LeRobotDataset 实例
        episode_index: episode 索引
        output_dir: 输出目录
        fps: 输出视频帧率
    """
    import av

    ep_info = dataset.meta.episodes[episode_index]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_videos = []

    for video_key in dataset.meta.video_keys:
        # 获取视频文件路径
        chunk_idx = ep_info[f"videos/{video_key}/chunk_index"]
        file_idx = ep_info[f"videos/{video_key}/file_index"]
        from_ts = ep_info[f"videos/{video_key}/from_timestamp"]
        to_ts = ep_info[f"videos/{video_key}/to_timestamp"]

        video_path = dataset.root / dataset.meta.video_path.format(
            video_key=video_key,
            chunk_index=chunk_idx,
            file_index=file_idx
        )

        if not video_path.exists():
            print(f"  警告: 视频文件不存在: {video_path}")
            continue

        # 使用 PyAV 打开视频（支持 AV1 编码）
        try:
            container = av.open(str(video_path))
            stream = container.streams.video[0]
            stream.codec_context.thread_type = "AUTO"

            width = stream.width
            height = stream.height

            # 输出视频路径
            safe_key = video_key.replace("/", "_").replace(".", "_")
            out_video_path = output_path / f"episode_{episode_index}_{safe_key}.mp4"

            # 使用 PyAV 创建输出视频（H.264 编码，更兼容）
            out_container = av.open(str(out_video_path), mode="w")
            out_stream = out_container.add_stream("libx264", rate=fps)
            out_stream.width = width
            out_stream.height = height
            out_stream.pix_fmt = "yuv420p"
            out_stream.options = {"crf": "23"}

            # 尝试跳转到起始时间（使用秒为单位）
            if from_ts > 0:
                try:
                    container.seek(from_ts, stream=stream)
                except Exception:
                    pass

            # 读取并写入帧
            frame_count = 0
            for frame in container.decode(video=0):
                frame_time = float(frame.time)

                # 跳过早于起始时间的帧
                if frame_time < from_ts - 0.1:
                    continue
                # 超过结束时间则停止
                if frame_time >= to_ts:
                    break

                # 转换为 RGB 格式并写入
                img = frame.to_ndarray(format="rgb24")
                out_frame = av.VideoFrame.from_ndarray(img, format="rgb24")
                out_frame.pict_type = frame.pict_type
                for packet in out_stream.encode(out_frame):
                    out_container.mux(packet)
                frame_count += 1

            # 刷新编码器
            for packet in out_stream.encode():
                out_container.mux(packet)

            container.close()
            out_container.close()

            saved_videos.append((video_key, str(out_video_path), frame_count))
            print(f"  已保存视频: {out_video_path} ({frame_count} 帧)")

        except Exception as e:
            print(f"  警告: 处理视频失败 {video_path}: {e}")
            continue

    return saved_videos


def visualize_episode(
    dataset: LeRobotDataset,
    episode_index: int,
    save_path: Optional[str] = None,
    save_video: bool = False,
    video_output_dir: Optional[str] = None
):
    """
    可视化单个 episode 的动作轨迹，可选保存视频

    Args:
        dataset: LeRobotDataset 实例
        episode_index: 要可视化的 episode 索引
        save_path: 保存图像的路径，None 则显示
        save_video: 是否保存视频
        video_output_dir: 视频输出目录，None 则使用 save_path 同目录
    """
    if episode_index >= dataset.meta.total_episodes:
        print(f"错误: episode {episode_index} 不存在 (总共有 {dataset.meta.total_episodes} 个 episodes)")
        return

    print(f"正在可视化 Episode {episode_index}...")

    # 获取 episode 的帧范围
    ep_info = dataset.meta.episodes[episode_index]
    start_idx = ep_info["dataset_from_index"]
    end_idx = ep_info["dataset_to_index"]

    # 获取 episode 的所有帧
    episode_data = []
    for idx in range(start_idx, end_idx):
        frame = dataset[idx]
        episode_data.append(frame)

    print(f"  Episode 长度: {len(episode_data)} 帧")

    # 保存视频（如果需要）
    if save_video:
        if video_output_dir is None:
            if save_path:
                video_output_dir = str(Path(save_path).parent)
            else:
                video_output_dir = f"/tmp/episode_{episode_index}_videos"
        print(f"  正在提取视频...")
        extract_and_save_episode_videos(dataset, episode_index, video_output_dir, fps=dataset.meta.fps)

    # 提取动作数据
    actions = np.array([frame["action"].numpy() for frame in episode_data])
    timestamps = np.array([frame["timestamp"].item() for frame in episode_data])

    # 关节名称
    joint_names = dataset.meta.features["action"]["names"]

    # 创建图表
    fig, axes = plt.subplots(len(joint_names), 1, figsize=(12, 2.5 * len(joint_names)))
    if len(joint_names) == 1:
        axes = [axes]

    for i, (ax, name) in enumerate(zip(axes, joint_names)):
        ax.plot(timestamps, actions[:, i], linewidth=2)
        ax.set_ylabel(f"{name}\n(度)", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(timestamps[0], timestamps[-1])

    axes[-1].set_xlabel("时间 (秒)", fontsize=11)
    fig.suptitle(f"Episode {episode_index} - 动作轨迹", fontsize=14, fontweight="bold")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  图表已保存到: {save_path}")
    else:
        plt.show()

    plt.close()


def visualize_episodes_comparison(dataset: LeRobotDataset, episode_indices: list,
                                   save_path: Optional[str] = None):
    """
    对比可视化多个 episodes 的动作轨迹

    Args:
        dataset: LeRobotDataset 实例
        episode_indices: 要对比的 episode 索引列表
        save_path: 保存图像的路径，None 则显示
    """
    print(f"正在对比可视化 Episodes {episode_indices}...")

    joint_names = dataset.meta.features["action"]["names"]

    # 为每个 episode 收集数据
    episodes_data = []
    for ep_idx in episode_indices:
        if ep_idx >= dataset.meta.total_episodes:
            print(f"  警告: episode {ep_idx} 不存在，跳过")
            continue

        ep_info = dataset.meta.episodes[ep_idx]
        start_idx = ep_info["dataset_from_index"]
        end_idx = ep_info["dataset_to_index"]

        actions = []
        for idx in range(start_idx, end_idx):
            frame = dataset[idx]
            actions.append(frame["action"].numpy())

        episodes_data.append(np.array(actions))

    if not episodes_data:
        print("错误: 没有有效的 episode 数据")
        return

    # 创建图表
    fig, axes = plt.subplots(len(joint_names), 1, figsize=(12, 2.5 * len(joint_names)))
    if len(joint_names) == 1:
        axes = [axes]

    colors = plt.cm.tab10(np.linspace(0, 1, len(episode_indices)))

    for i, (ax, name) in enumerate(zip(axes, joint_names)):
        for j, (ep_idx, actions) in enumerate(zip(episode_indices, episodes_data)):
            frames = np.arange(len(actions))
            ax.plot(frames, actions[:, i], linewidth=2,
                   color=colors[j], label=f"Ep {ep_idx}", alpha=0.8)
        ax.set_ylabel(f"{name}\n(度)", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=9)

    axes[-1].set_xlabel("帧索引", fontsize=11)
    fig.suptitle(f"Episodes 对比 - {episode_indices}", fontsize=14, fontweight="bold")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  图表已保存到: {save_path}")
    else:
        plt.show()

    plt.close()


def plot_state_distribution(dataset: LeRobotDataset, episode_indices: Optional[list] = None,
                            save_path: Optional[str] = None):
    """
    绘制状态数据的分布图（箱线图）

    Args:
        dataset: LeRobotDataset 实例
        episode_indices: 要分析的 episode 索引列表，None 表示全部
        save_path: 保存图像的路径，None 则显示
    """
    print(f"正在绘制状态分布图...")

    joint_names = dataset.meta.features["observation.state"]["names"]

    # 收集状态数据
    all_states = []
    if episode_indices is None:
        episode_indices = range(min(10, dataset.meta.total_episodes))

    for ep_idx in episode_indices:
        if ep_idx >= dataset.meta.total_episodes:
            continue

        ep_info = dataset.meta.episodes[ep_idx]
        start_idx = ep_info["dataset_from_index"]
        end_idx = ep_info["dataset_to_index"]

        for idx in range(start_idx, end_idx):
            frame = dataset[idx]
            all_states.append(frame["observation.state"].numpy())

    all_states = np.array(all_states)
    print(f"  收集了 {len(all_states)} 帧的状态数据")

    # 创建箱线图
    _, ax = plt.subplots(figsize=(12, 6))

    data_to_plot = [all_states[:, i] for i in range(len(joint_names))]
    bp = ax.boxplot(data_to_plot, labels=[name.replace(".pos", "") for name in joint_names],
                    patch_artist=True, showmeans=True)

    # 美化
    for patch in bp["boxes"]:
        patch.set_facecolor("lightblue")
        patch.set_alpha(0.7)

    ax.set_ylabel("关节位置 (度)", fontsize=11)
    ax.set_xlabel("关节名称", fontsize=11)
    ax.set_title("状态数据分布 (箱线图)", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  图表已保存到: {save_path}")
    else:
        plt.show()

    plt.close()


# ============================================================================
# 删除 Episodes 功能
# ============================================================================

def delete_selected_episodes(dataset: LeRobotDataset, episode_indices: list,
                             output_path: str, output_repo_id: Optional[str] = None):
    """
    删除指定 episodes 并保存为新数据集

    Args:
        dataset: LeRobotDataset 实例
        episode_indices: 要删除的 episode 索引列表
        output_path: 输出路径
        output_repo_id: 输出数据集的 repo_id，None 则自动生成
    """
    if not episode_indices:
        print("错误: 没有指定要删除的 episodes")
        return

    # 验证索引
    invalid = [i for i in episode_indices if i >= dataset.meta.total_episodes]
    if invalid:
        print(f"错误: 无效的 episode 索引: {invalid}")
        print(f"       数据集共有 {dataset.meta.total_episodes} 个 episodes (0-{dataset.meta.total_episodes-1})")
        return

    print(f"正在删除 {len(episode_indices)} 个 episodes: {episode_indices}")
    print(f"  原数据集: {dataset.meta.total_episodes} episodes, {dataset.meta.total_frames} frames")
    print(f"  输出路径: {output_path}")
    print(f"\n注意: 处理视频文件可能需要几分钟，请耐心等待...")
    print("-" * 50)

    # 如果未指定 repo_id，使用输出目录名
    if output_repo_id is None:
        output_repo_id = Path(output_path).name

    # 删除 episodes
    new_dataset = delete_episodes(
        dataset,
        episode_indices=episode_indices,
        output_dir=output_path,
        repo_id=output_repo_id
    )

    print(f"  新数据集: {new_dataset.meta.total_episodes} episodes, {new_dataset.meta.total_frames} frames")
    print(f"  保存位置: {new_dataset.root}")
    print("完成!")


# ============================================================================
# 时间偏移测量和调节工具
# ============================================================================

def interactive_offset_measurement(
    dataset: LeRobotDataset,
    episode_index: int,
    initial_offsets: Optional[dict] = None
) -> dict:
    """
    交互式时间偏移测量工具

    同时显示视频帧和动作曲线，让用户手动调整偏移直到对齐

    Args:
        dataset: LeRobotDataset 实例
        episode_index: 要分析的 episode 索引
        initial_offsets: 初始偏移量 {video_key: offset_seconds}

    Returns:
        测量得到的偏移量字典
    """
    import av

    if episode_index >= dataset.meta.total_episodes:
        print(f"错误: episode {episode_index} 不存在")
        return {}

    ep_info = dataset.meta.episodes[episode_index]
    start_idx = ep_info["dataset_from_index"]
    end_idx = ep_info["dataset_to_index"]
    num_frames = end_idx - start_idx

    # 初始化偏移量
    video_keys = dataset.meta.video_keys
    offsets = initial_offsets.copy() if initial_offsets else {k: 0.0 for k in video_keys}
    selected_camera_idx = 0

    # 加载 episode 的动作数据
    print(f"正在加载 Episode {episode_index} 的数据...")
    actions = []
    timestamps = []
    for idx in range(start_idx, end_idx):
        frame = dataset[idx]
        actions.append(frame["action"].numpy())
        timestamps.append(frame["timestamp"].item())
    actions = np.array(actions)
    timestamps = np.array(timestamps)

    # 加载视频帧
    print(f"正在加载视频帧...")
    video_frames = {k: [] for k in video_keys}
    for video_key in video_keys:
        chunk_idx = ep_info[f"videos/{video_key}/chunk_index"]
        file_idx = ep_info[f"videos/{video_key}/file_index"]
        video_path = dataset.root / dataset.meta.video_path.format(
            video_key=video_key, chunk_index=chunk_idx, file_index=file_idx
        )
        if video_path.exists():
            container = av.open(str(video_path))
            stream = container.streams.video[0]
            from_ts = ep_info[f"videos/{video_key}/from_timestamp"]
            to_ts = ep_info[f"videos/{video_key}/to_timestamp"]

            for frame in container.decode(video=0):
                if frame.time < from_ts:
                    continue
                if frame.time >= to_ts:
                    break
                img = frame.to_ndarray(format="rgb24")
                video_frames[video_key].append(img)
            container.close()

    print(f"已加载 {num_frames} 帧数据和视频")
    print("\n" + "=" * 60)
    print("交互式偏移测量工具")
    print("=" * 60)
    print("操作说明:")
    print("  ←/→  : 前/后移动一帧")
    print("  ↑/↓  : 增加/减少当前摄像头的偏移 (0.01秒)")
    print("  [/]  : 减少/增加偏移 (0.1秒)")
    print("  1/2  : 选择摄像头 1 或 2")
    print("  r    : 重置当前摄像头偏移为 0")
    print("  p    : 打印当前偏移配置")
    print("  s    : 保存偏移配置并退出")
    print("  q    : 退出不保存")
    print("=" * 60 + "\n")

    current_frame = 0

    def get_shifted_frame(video_key: str, frame_idx: int, offset: float):
        """获取应用偏移后的视频帧"""
        fps = dataset.meta.fps
        shifted_idx = frame_idx - int(offset * fps)
        shifted_idx = max(0, min(shifted_idx, len(video_frames[video_key]) - 1))
        return video_frames[video_key][shifted_idx]

    # 创建图表
    plt.ion()
    fig = plt.figure(figsize=(14, 10))

    # 视频显示区域
    video_axes = []
    for i in range(len(video_keys)):
        ax = fig.add_subplot(2, len(video_keys) + 1, i + 1)
        video_axes.append(ax)

    # 动作曲线显示区域
    action_ax = fig.add_subplot(2, 1, 2)

    def update_display():
        # 清除旧内容
        for ax in video_axes:
            ax.clear()
        action_ax.clear()

        # 显示视频帧
        for i, (key, ax) in enumerate(zip(video_keys, video_axes)):
            if video_frames[key]:
                frame = get_shifted_frame(key, current_frame, offsets[key])
                ax.imshow(frame)
                marker = " *" if i == selected_camera_idx else ""
                ax.set_title(f"{key}\nOffset: {offsets[key]:+.3f}s{marker}", fontsize=10)
            ax.axis("off")

        # 显示动作曲线，标记当前帧
        joint_names = dataset.meta.features["action"]["names"]
        colors = plt.cm.tab10(np.linspace(0, 1, len(joint_names)))

        for j, name in enumerate(joint_names):
            action_ax.plot(timestamps, actions[:, j], label=name, color=colors[j], alpha=0.7)

        # 标记当前帧位置
        action_ax.axvline(x=timestamps[current_frame], color="red", linewidth=2, label="Current Frame")

        # 标记偏移后的视频帧位置
        for key in video_keys:
            shifted_time = timestamps[current_frame] + offsets[key]
            if 0 <= shifted_time <= timestamps[-1]:
                action_ax.axvline(x=shifted_time, color="green", linewidth=1, linestyle="--", alpha=0.5)

        action_ax.set_xlabel("Time (s)")
        action_ax.set_ylabel("Joint Position (deg)")
        action_ax.set_title(f"Episode {episode_index} - Frame {current_frame}/{num_frames-1}")
        action_ax.legend(loc="upper right", fontsize=8)
        action_ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.canvas.draw()

    def on_key(event):
        nonlocal current_frame, selected_camera_idx

        if event.key == "right":
            current_frame = min(current_frame + 1, num_frames - 1)
        elif event.key == "left":
            current_frame = max(current_frame - 1, 0)
        elif event.key == "up":
            offsets[video_keys[selected_camera_idx]] += 0.01
        elif event.key == "down":
            offsets[video_keys[selected_camera_idx]] -= 0.01
        elif event.key == "]":
            offsets[video_keys[selected_camera_idx]] += 0.1
        elif event.key == "[":
            offsets[video_keys[selected_camera_idx]] -= 0.1
        elif event.key == "1" and len(video_keys) > 0:
            selected_camera_idx = 0
        elif event.key == "2" and len(video_keys) > 1:
            selected_camera_idx = 1
        elif event.key == "r":
            offsets[video_keys[selected_camera_idx]] = 0.0
        elif event.key == "p":
            print("\n当前偏移配置:")
            for k, v in offsets.items():
                print(f"  {k}: {v:+.3f}s")
        elif event.key == "s":
            print("\n保存偏移配置:")
            for k, v in offsets.items():
                print(f"  {k}: {v:+.3f}s")
            plt.close(fig)
            return "save"
        elif event.key == "q":
            plt.close(fig)
            return "quit"

        update_display()
        return None

    fig.canvas.mpl_connect("key_press_event", on_key)
    update_display()
    plt.show(block=True)

    return offsets


def generate_offset_comparison_grid(
    dataset: LeRobotDataset,
    episode_index: int,
    video_key: str,
    frame_indices: list,
    offsets: list,
    output_path: str
):
    """
    生成不同偏移值的对比网格图

    Args:
        dataset: LeRobotDataset 实例
        episode_index: episode 索引
        video_key: 视频键名
        frame_indices: 要显示的帧索引列表
        offsets: 偏移值列表 (秒)
        output_path: 输出图片路径
    """
    import av

    ep_info = dataset.meta.episodes[episode_index]
    start_idx = ep_info["dataset_from_index"]

    # 加载视频帧
    chunk_idx = ep_info[f"videos/{video_key}/chunk_index"]
    file_idx = ep_info[f"videos/{video_key}/file_index"]
    video_path = dataset.root / dataset.meta.video_path.format(
        video_key=video_key, chunk_index=chunk_idx, file_index=file_idx
    )

    all_frames = []
    container = av.open(str(video_path))
    from_ts = ep_info[f"videos/{video_key}/from_timestamp"]
    to_ts = ep_info[f"videos/{video_key}/to_timestamp"]

    for frame in container.decode(video=0):
        if frame.time < from_ts:
            continue
        if frame.time >= to_ts:
            break
        all_frames.append(frame.to_ndarray(format="rgb24"))
    container.close()

    fps = dataset.meta.fps

    # 创建网格图
    n_rows = len(offsets)
    n_cols = len(frame_indices)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3 * n_cols, 3 * n_rows))

    if n_rows == 1:
        axes = [axes]
    if n_cols == 1:
        axes = [[ax] for ax in axes]

    for row, offset in enumerate(offsets):
        for col, frame_idx in enumerate(frame_indices):
            ax = axes[row][col]
            shifted_idx = frame_idx - int(offset * fps)
            shifted_idx = max(0, min(shifted_idx, len(all_frames) - 1))

            ax.imshow(all_frames[shifted_idx])
            ax.axis("off")

            if col == 0:
                ax.set_ylabel(f"Offset: {offset:+.2f}s", fontsize=10)
            if row == 0:
                ax.set_title(f"Frame {frame_idx}", fontsize=10)

    plt.suptitle(f"Episode {episode_index} - {video_key} - Offset Comparison", fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"对比图已保存到: {output_path}")


def apply_time_offsets(
    dataset: LeRobotDataset,
    output_path: str,
    video_offsets: dict[str, float],
    data_offset: float = 0.0
):
    """
    应用时间偏移到数据集，创建新数据集（裁剪对不上的数据）

    偏移含义：
    - 正偏移 (+) = 视频/数据比基准晚到达
    - 负偏移 (-) = 视频/数据比基准早到达

    裁剪策略：
    - 正偏移：裁掉开头部分（因为视频/数据滞后，开头没有对应帧）
    - 负偏移：裁掉结尾部分（因为视频/数据超前，结尾没有对应帧）

    Args:
        dataset: 源数据集
        output_path: 输出路径
        video_offsets: 视频偏移 {video_key: offset_seconds}
        data_offset: 数据偏移 (秒)
    """
    import pyarrow.parquet as pq
    import pyarrow as pa
    import shutil

    print(f"正在应用时间偏移（裁剪模式）...")
    print(f"  数据偏移: {data_offset}s")
    for k, v in video_offsets.items():
        print(f"  {k}: {v}s")

    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    fps = dataset.meta.fps

    # 计算最大偏移量（用于确定需要裁剪多少帧）
    all_offsets = list(video_offsets.values()) + [data_offset]
    max_offset = max(all_offsets) if all_offsets else 0
    min_offset = min(all_offsets) if all_offsets else 0

    # 计算需要裁剪的帧数
    trim_start_frames = max(0, int(max_offset * fps))  # 正偏移需要裁掉开头
    trim_end_frames = max(0, int(-min_offset * fps))   # 负偏移需要裁掉结尾

    print(f"  将裁剪开头 {trim_start_frames} 帧，结尾 {trim_end_frames} 帧")

    # 1. 复制 meta/info.json
    shutil.copytree(dataset.root / "meta", output_dir / "meta", dirs_exist_ok=True)

    # 2. 复制 videos 目录 (不需要重新编码)
    if (dataset.root / "videos").exists():
        shutil.copytree(dataset.root / "videos", output_dir / "videos", dirs_exist_ok=True)

    # 3. 处理 data 目录 - 裁剪并重索引
    total_frames_removed = 0
    episode_length_changes = {}

    for data_file in sorted((dataset.root / "data").rglob("*.parquet")):
        relative_path = data_file.relative_to(dataset.root / "data")
        output_file = output_dir / "data" / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)

        df = pq.read_table(data_file).to_pandas()

        # 按 episode 分组处理
        new_dfs = []
        for ep_idx in df["episode_index"].unique():
            ep_df = df[df["episode_index"] == ep_idx].copy()
            original_length = len(ep_df)

            # 裁剪开头和结尾
            if trim_start_frames > 0 or trim_end_frames > 0:
                start = trim_start_frames
                end = len(ep_df) - trim_end_frames
                if end <= start:
                    print(f"  警告: Episode {ep_idx} 裁剪后为空，跳过")
                    total_frames_removed += original_length
                    continue
                ep_df = ep_df.iloc[start:end].copy()

            # 重置帧索引
            ep_df["frame_index"] = range(len(ep_df))
            ep_df["timestamp"] = ep_df["frame_index"] / fps

            new_dfs.append(ep_df)

            length_change = original_length - len(ep_df)
            if length_change > 0:
                episode_length_changes[ep_idx] = length_change
                total_frames_removed += length_change

        if new_dfs:
            new_df = pd.concat(new_dfs, ignore_index=True)
            # 重新计算全局索引
            new_df["index"] = range(len(new_df))
            pq.write_table(pa.Table.from_pandas(new_df), output_file)
        else:
            # 创建空文件
            empty_df = df.iloc[0:0]
            pq.write_table(pa.Table.from_pandas(empty_df), output_file)

    # 4. 更新 episodes 元数据
    for ep_file in sorted((output_dir / "meta" / "episodes").rglob("*.parquet")):
        df = pq.read_table(ep_file).to_pandas()

        # 更新长度
        for ep_idx in df["episode_index"].unique():
            if ep_idx in episode_length_changes:
                orig_length = df.loc[df["episode_index"] == ep_idx, "length"].values[0]
                df.loc[df["episode_index"] == ep_idx, "length"] = orig_length - episode_length_changes[ep_idx]

        # 更新视频时间戳
        for video_key, offset in video_offsets.items():
            from_col = f"videos/{video_key}/from_timestamp"
            to_col = f"videos/{video_key}/to_timestamp"

            if from_col in df.columns and to_col in df.columns:
                # 视频偏移是反向的：如果视频比动作晚，需要减少时间戳
                df[from_col] = (df[from_col] - offset).clip(lower=0)
                df[to_col] = (df[to_col] - offset).clip(lower=0)

        pq.write_table(pa.Table.from_pandas(df), ep_file)

    # 5. 更新 info.json 中的总帧数
    import json
    info_path = output_dir / "meta" / "info.json"
    with open(info_path) as f:
        info = json.load(f)
    info["total_frames"] = info["total_frames"] - total_frames_removed
    with open(info_path, "w") as f:
        json.dump(info, f, indent=4)

    print(f"\n裁剪统计:")
    print(f"  总共删除帧数: {total_frames_removed}")
    print(f"  受影响的 episodes: {len(episode_length_changes)}")
    print(f"\n新数据集已保存到: {output_dir}")
    print("完成!")


# ============================================================================
# 交互式模式
# ============================================================================

def interactive_mode(dataset: LeRobotDataset):
    """
    交互式命令行界面

    Args:
        dataset: LeRobotDataset 实例
    """
    print("\n" + "=" * 60)
    print("交互式数据集处理工具")
    print("=" * 60)
    print("可用命令:")
    print("  info              - 显示数据集信息")
    print("  list [episodes]   - 列出 episodes (可选指定范围，如 'list 0:10')")
    print("  viz <ep_idx> [--video] - 可视化单个 episode (--video 同时保存视频)")
    print("  compare <idx1,idx2,...> - 对比多个 episodes")
    print("  dist [episodes]   - 显示状态分布图")
    print("  delete <idx1,idx2,...> - 删除指定 episodes")
    print("  help              - 显示帮助")
    print("  quit / exit       - 退出")
    print("=" * 60 + "\n")

    current_episodes = None  # 当前选中的 episodes

    while True:
        try:
            cmd_input = input(">>> ").strip()
            if not cmd_input:
                continue

            parts = cmd_input.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            if cmd in ["quit", "exit", "q"]:
                print("再见!")
                break

            elif cmd == "help":
                print("\n可用命令:")
                print("  info              - 显示数据集信息")
                print("  list [episodes]   - 列出 episodes (可选指定范围，如 'list 0:10')")
                print("  viz <ep_idx> [--video] - 可视化单个 episode (--video 同时保存视频)")
                print("  compare <idx1,idx2,...> - 对比多个 episodes")
                print("  dist [episodes]   - 显示状态分布图")
                print("  delete <idx1,idx2,...> - 删除指定 episodes")
                print("  help              - 显示帮助")
                print("  quit / exit       - 退出")

            elif cmd == "info":
                print_dataset_info(dataset)

            elif cmd == "list":
                if args:
                    # 解析范围
                    range_str = args[0]
                    if ":" in range_str:
                        start, end = map(int, range_str.split(":"))
                        current_episodes = list(range(start, min(end, dataset.meta.total_episodes)))
                    else:
                        current_episodes = [int(args[0])]
                else:
                    current_episodes = list(range(min(20, dataset.meta.total_episodes)))

                print(f"\nEpisodes 列表 (显示 {len(current_episodes)} 个):")
                for ep_idx in current_episodes[:20]:
                    ep_info = dataset.meta.episodes[ep_idx]
                    print(f"  Episode {ep_idx}: {ep_info['length']} 帧, 任务 {ep_info['episode_index']}")

            elif cmd == "viz":
                if not args:
                    print("用法: viz <episode_index> [--video]")
                    continue
                ep_idx = int(args[0])
                save_video = "--video" in args
                video_dir = f"/tmp/episode_{ep_idx}_videos" if save_video else None
                visualize_episode(dataset, ep_idx, save_video=save_video, video_output_dir=video_dir)

            elif cmd == "compare":
                if not args:
                    print("用法: compare <idx1,idx2,...>")
                    continue
                indices = [int(x) for x in args[0].split(",")]
                visualize_episodes_comparison(dataset, indices)

            elif cmd == "dist":
                episodes = current_episodes if current_episodes else None
                plot_state_distribution(dataset, episodes)

            elif cmd == "delete":
                if not args:
                    print("用法: delete <idx1,idx2,...>")
                    continue
                indices = [int(x) for x in args[0].split(",")]

                output_path = input("  输出路径 (默认: ~/Datasets/<dataset>_filtered): ").strip()
                if not output_path:
                    output_path = str(Path(dataset.root).parent / f"{dataset.repo_id}_filtered")

                delete_selected_episodes(dataset, indices, output_path)

            else:
                print(f"未知命令: {cmd} (输入 'help' 查看可用命令)")

        except KeyboardInterrupt:
            print("\n使用 'quit' 或 'exit' 退出")
        except Exception as e:
            print(f"错误: {e}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="LeRobot 数据集处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 显示数据集信息
  python dataset_process.py --dataset-path /path/to/dataset --info

  # 可视化单个 episode
  python dataset_process.py --dataset-path /path/to/dataset --visualize --episode 0

  # 对比多个 episodes
  python dataset_process.py --dataset-path /path/to/dataset --compare --episodes 0,1,2

  # 显示状态分布
  python dataset_process.py --dataset-path /path/to/dataset --distribution

  # 删除指定 episodes
  python dataset_process.py --dataset-path /path/to/dataset --delete-episodes 0,1 --output /path/to/output

  # 测量时间偏移 (交互式)
  python dataset_process.py --dataset-path /path/to/dataset --measure-offset --episode 0

  # 应用时间偏移
  python dataset_process.py --dataset-path /path/to/dataset --apply-offset --video-offset observation.images.wrist:0.1 --output /path/to/output

  # 生成偏移对比图
  python dataset_process.py --dataset-path /path/to/dataset --generate-comparison --episode 0 --output /tmp/comparison.png

  # 进入交互模式
  python dataset_process.py --dataset-path /path/to/dataset --interactive
        """
    )

    parser.add_argument("--dataset-path", type=str, required=True,
                        help="数据集路径")
    parser.add_argument("--info", action="store_true",
                        help="显示数据集信息")
    parser.add_argument("--visualize", action="store_true",
                        help="可视化模式")
    parser.add_argument("--episode", type=int, default=0,
                        help="要可视化的 episode 索引")
    parser.add_argument("--compare", action="store_true",
                        help="对比多个 episodes")
    parser.add_argument("--episodes", type=str,
                        help="逗号分隔的 episode 索引列表，如 '0,1,2'")
    parser.add_argument("--distribution", action="store_true",
                        help="显示状态分布图")
    parser.add_argument("--delete-episodes", type=str,
                        help="要删除的 episodes，逗号分隔，如 '0,1,5'")
    parser.add_argument("--output", type=str,
                        help="输出路径（用于删除操作）")
    parser.add_argument("--interactive", action="store_true",
                        help="进入交互模式")
    parser.add_argument("--save", type=str,
                        help="保存可视化图表到指定路径")
    parser.add_argument("--save-video", action="store_true",
                        help="保存 episode 视频到图表同目录")
    parser.add_argument("--video-output", type=str,
                        help="视频输出目录（默认与图表同目录）")

    # 时间偏移测量和应用相关参数
    parser.add_argument("--measure-offset", action="store_true",
                        help="进入交互式时间偏移测量模式")
    parser.add_argument("--apply-offset", action="store_true",
                        help="应用时间偏移到数据集")
    parser.add_argument("--offset-config", type=str,
                        help="偏移配置文件路径 (YAML/JSON)")
    parser.add_argument("--video-offset", type=str, action="append",
                        metavar="KEY:OFFSET",
                        help="视频偏移，格式: video_key:offset_seconds (可多次指定)")
    parser.add_argument("--data-offset", type=float, default=0.0,
                        help="数据偏移 (秒)")
    parser.add_argument("--generate-comparison", action="store_true",
                        help="生成偏移对比网格图")
    parser.add_argument("--frames", type=str,
                        help="要对比的帧索引列表，逗号分隔，如 '0,50,100'")
    parser.add_argument("--offsets", type=str,
                        help="要对比的偏移值列表，逗号分隔，如 '-0.1,0,0.1'")
    parser.add_argument("--tolerance", type=float, default=0.1,
                        help="时间戳容差 (秒)，默认 0.1s，用于处理偏移后的数据集")

    args = parser.parse_args()

    # 加载数据集
    try:
        dataset = load_dataset(args.dataset_path, tolerance_s=args.tolerance)
        print(f"成功加载数据集: {dataset.repo_id}")
    except Exception as e:
        print(f"加载数据集失败: {e}")
        sys.exit(1)

    # 执行相应操作
    if args.info:
        print_dataset_info(dataset)

    elif args.visualize:
        if args.episodes:
            # 多个 episodes 对比
            indices = [int(x.strip()) for x in args.episodes.split(",")]
            if len(indices) == 1:
                visualize_episode(dataset, indices[0], args.save,
                                  save_video=args.save_video,
                                  video_output_dir=args.video_output)
            else:
                visualize_episodes_comparison(dataset, indices, args.save)
        else:
            visualize_episode(dataset, args.episode, args.save,
                              save_video=args.save_video,
                              video_output_dir=args.video_output)

    elif args.compare:
        if not args.episodes:
            print("错误: --compare 需要 --episodes 参数")
            sys.exit(1)
        indices = [int(x.strip()) for x in args.episodes.split(",")]
        visualize_episodes_comparison(dataset, indices, args.save)

    elif args.distribution:
        plot_state_distribution(dataset, save_path=args.save)

    elif args.delete_episodes:
        if not args.output:
            print("错误: --delete-episodes 需要 --output 参数")
            sys.exit(1)
        indices = [int(x.strip()) for x in args.delete_episodes.split(",")]
        delete_selected_episodes(dataset, indices, args.output)

    elif args.measure_offset:
        # 交互式偏移测量
        offsets = interactive_offset_measurement(dataset, args.episode)
        if offsets:
            # 保存配置文件
            config_path = args.offset_config or f"/tmp/offset_config_{dataset.repo_id}.yaml"
            import yaml
            config = {
                "dataset": dataset.repo_id,
                "video_offsets": offsets,
                "data_offset": 0.0
            }
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            print(f"\n偏移配置已保存到: {config_path}")

    elif args.apply_offset:
        # 应用偏移到数据集
        if not args.output:
            print("错误: --apply-offset 需要 --output 参数")
            sys.exit(1)

        # 解析偏移配置
        video_offsets = {}
        data_offset = args.data_offset

        if args.offset_config:
            # 从配置文件加载
            import yaml
            with open(args.offset_config) as f:
                config = yaml.safe_load(f)
            video_offsets = config.get("video_offsets", {})
            data_offset = config.get("data_offset", 0.0)
        elif args.video_offset:
            # 从命令行参数解析
            for item in args.video_offset:
                key, offset = item.rsplit(":", 1)
                video_offsets[key] = float(offset)

        if not video_offsets and data_offset == 0:
            print("警告: 没有指定任何偏移量")

        apply_time_offsets(dataset, args.output, video_offsets, data_offset)

    elif args.generate_comparison:
        # 生成偏移对比图
        if not args.output:
            args.output = "/tmp/offset_comparison.png"

        video_key = dataset.meta.video_keys[0] if dataset.meta.video_keys else None
        if not video_key:
            print("错误: 数据集没有视频")
            sys.exit(1)

        # 默认对比几个帧和几个偏移值
        frame_indices = [0, 10, 20, 30]
        offsets = [-0.2, -0.1, 0.0, 0.1, 0.2]

        if args.video_offset:
            offsets = [float(item.rsplit(":", 1)[1]) for item in args.video_offset]

        generate_offset_comparison_grid(
            dataset, args.episode, video_key, frame_indices, offsets, args.output
        )

    elif args.interactive:
        interactive_mode(dataset)

    else:
        # 默认显示信息
        print_dataset_info(dataset)
        print("\n提示: 使用 --help 查看所有选项，或使用 --interactive 进入交互模式")


if __name__ == "__main__":
    main()
