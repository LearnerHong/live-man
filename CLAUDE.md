# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 相关文档
- **[docs/](./docs/)** - Markdown格式技术文档（适合AI分析和开发查阅）
  - [docs/README.md](./docs/README.md) - 文档总索引
  - [docs/architecture/](./docs/architecture/) - 架构设计
  - [docs/core/](./docs/core/) - 核心模块详细说明
  - [docs/api/](./docs/api/) - API接口规范
  - [docs/guides/](./docs/guides/) - 使用指南

- **[docs-site/](./docs-site/)** - HTML交互式文档站点（适合人工浏览）
  - 响应式设计 + 深色模式
  - 交互式导航 + 实时搜索
  - 代码高亮 + 一键复制
  - 📌 **[立即查看](./docs-site/index.html)**


## 项目概述

LiveTalking-V2 是实时交互流式数字人系统，通过 WebRTC 实现低延迟音视频同步对话。支持多种数字人模型（musetalk、wav2lip、ultralight）和多种 TTS 引擎。

**架构详情**: [docs/architecture/overview.md](./docs/architecture/overview.md)

### 启动服务

**基础启动（wav2lip 模型）：**
```bash
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
```

**Musetalk 模型：**
```bash
python app.py --transport webrtc --model musetalk --avatar_id avator_1 --batch_size 16
```

**Ultralight 模型：**
```bash
python app.py --transport webrtc --model ultralight --avatar_id <avatar_id>
```

**自定义 TTS 引擎：**
```bash
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 \
  --tts gpt-sovits --TTS_SERVER http://127.0.0.1:9880 --REF_FILE reference.wav
```

**虚拟摄像头输出：**
```bash
python app.py --transport virtualcam --model wav2lip --avatar_id wav2lip256_avatar1
```

### 访问地址
- WebRTC 集成前端: `http://<serverip>:8010/dashboard.html`
- API 测试页面: `http://<serverip>:8010/webrtcapi.html`

## 核心架构

**完整架构文档**: [docs/architecture/overview.md](./docs/architecture/overview.md)

### 系统分层结构

```
app.py (aiohttp Web 服务层)
├─ WebRTC 连接管理 (aiortc)
├─ 会话管理 (nerfreals: Dict[sessionid, BaseReal])
└─ HTTP API 端点 (/offer, /human, /record 等)
    ↓
BaseReal (抽象基类 - basereal.py)
├─ TTS 模块 (ttsreal.py)
├─ ASR 模块 (baseasr.py)
└─ 音视频缓冲队列
    ↓
具体实现类
├─ MuseReal (musereal.py) - musetalk 模型
├─ LipReal (lipreal.py) - wav2lip 模型
└─ LightReal (lightreal.py) - ultralight 模型
    ↓
WebRTC 传输层 (webrtc.py)
└─ HumanPlayer → PlayerStreamTrack (音频/视频轨道)
```

### 会话生命周期

**1. 创建会话（app.py:85-142）：**
```
前端 WebRTC offer → POST /offer
  ↓
生成随机 6 位 sessionid (app.py:97)
  ↓
异步执行 build_nerfreal(sessionid) (app.py:100)
  ↓
创建 RTCPeerConnection，绑定音视频轨道 (app.py:105-122)
  ↓
返回 SDP answer + sessionid
```

**2. 对话推理流程：**
```
用户输入 → POST /human {type:'chat', text, sessionid}
  ↓
llm.py:llm_response() 流式生成回复
  ↓
按标点符号分句 (llm.py:38)
  ↓
BaseReal.put_msg_txt() → TTS 队列
  ↓
TTS 引擎合成音频 (ttsreal.py)
  ↓
ASR 提取音频特征 (baseasr.py)
  ↓
数字人模型推理口型 (MuseReal/LipReal/LightReal)
  ↓
WebRTC 推送音视频帧 (webrtc.py)
```

**3. 销毁会话（app.py:108-118）：**
- 监听 `pc.connectionState`
- 状态为 `failed` 或 `closed` 时删除 `nerfreals[sessionid]`
- 执行 `gc.collect()` 释放显存

### 数字人模型对比

**详细实现文档**: [docs/core/models.md](./docs/core/models.md)

| 模型 | 实现文件 | GPU 要求 | FPS (3080Ti) | 特点 |
|------|----------|----------|--------------|------|
| wav2lip | lipreal.py | RTX 3060+ | 120 | 256分辨率，低显存 |
| musetalk | musereal.py | RTX 3080Ti+ | 42 | 高质量口型同步 |
| ultralight | lightreal.py | - | - | 轻量级模型 |

**共同实现要求：**
- 继承 `BaseReal` 抽象基类 ([docs/core/basereal.md](./docs/core/basereal.md))
- 实现 `render(quit_event, loop, audio_track, video_track)` 方法
- 提供 `load_model()`, `load_avatar()`, `warm_up()` 函数

### TTS 引擎架构

**详细TTS文档**: [docs/core/tts.md](./docs/core/tts.md)

**所有 TTS 继承 `BaseTTS` (ttsreal.py:54)：**
- `put_msg_txt(msg, datainfo)`: 文本加入队列
- `txt_to_audio(msg)`: 合成音频并调用 `parent.put_audio_frame()`
- `flush_talk()`: 打断播报，清空队列

**支持的 TTS 引擎：**
- EdgeTTS (ttsreal.py:94): 微软 Edge TTS，免费
- SovitsTTS: GPT-SoVITS 声音克隆
- XTTS, CosyVoiceTTS, FishTTS
- TencentTTS, DoubaoTTS, IndexTTS2, AzureTTS

### ASR 实现

**详细ASR文档**: [docs/core/asr.md](./docs/core/asr.md)

- **MuseASR** (museasr.py): 基于 Whisper，用于 musetalk
- **LipASR** (lipasr.py): 用于 wav2lip
- **HubertASR** (hubertasr.py): 基于 Hubert 模型

**核心接口：**
- `put_audio_frame(audio_chunk)`: 接收 16kHz 20ms PCM 音频
- `run_step()`: 提取音频特征并触发口型推理

### WebRTC 传输机制 (webrtc.py)

**详细WebRTC文档**: [docs/core/webrtc.md](./docs/core/webrtc.md)

**关键参数：**
- 视频: 25fps (VIDEO_PTIME=0.04s), 时钟频率 90kHz
- 音频: 16kHz 采样率, 20ms 分包 (AUDIO_PTIME=0.02s)
- 编码器优先级: H264 > VP8 > rtx (app.py:124-128)

**PlayerStreamTrack 实现：**
- `recv()`: 从队列取音视频帧，设置 pts/time_base
- `next_timestamp()`: 控制发送时序，确保音视频同步
- 每 100 帧统计实际 fps (webrtc.py:142-145)

## API 端点

**完整API文档**: [docs/api/http-api.md](./docs/api/http-api.md)

| 端点 | 方法 | 功能 | 关键参数 |
|------|------|------|----------|
| `/offer` | POST | WebRTC 握手 | {sdp, type} |
| `/human` | POST | 文本对话 | {text, type:'chat'/'echo', interrupt, sessionid} |
| `/humanaudio` | POST | 音频文件输入 | {file, sessionid} |
| `/record` | POST | 录制控制 | {type:'start_record'/'end_record', sessionid} |
| `/interrupt_talk` | POST | 打断播报 | {sessionid} |
| `/is_speaking` | POST | 查询播报状态 | {sessionid} |
| `/set_audiotype` | POST | 切换 Avatar 状态 | {audiotype, reinit, sessionid} |

## 命令行参数

**完整配置文档**: [docs/guides/configuration.md](./docs/guides/configuration.md)

### 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | musetalk | 数字人模型: wav2lip/musetalk/ultralight |
| `--avatar_id` | avator_1 | Avatar 目录名（在 data/avatars/ 下）|
| `--batch_size` | 16 | 推理批次大小 |
| `--tts` | edgetts | TTS 引擎类型 |
| `--REF_FILE` | zh-CN-YunxiaNeural | EdgeTTS 模型 ID 或参考音频 |
| `--TTS_SERVER` | http://127.0.0.1:9880 | 外部 TTS 服务地址 |
| `--transport` | rtcpush | 传输方式: webrtc/rtcpush/virtualcam |
| `--listenport` | 8010 | Web 服务端口 |
| `--max_session` | 1 | 最大并发会话数 |

### 音频处理参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--fps` | 50 | 音频帧率（固定 50，对应 20ms）|
| `-l` | 10 | 滑动窗口左侧长度 |
| `-m` | 8 | 滑动窗口中间长度 |
| `-r` | 10 | 滑动窗口右侧长度 |

### 视频参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--W` | 450 | GUI 宽度 |
| `--H` | 450 | GUI 高度 |

### 自定义视频编排

| 参数 | 说明 |
|------|------|
| `--customvideo_config` | 自定义动作 JSON 配置文件路径 |

JSON 格式示例：
```json
[
  {
    "audiotype": "idle",
    "imgpath": "./data/custom/idle/imgs",
    "audiopath": "./data/custom/idle/audio.wav"
  }
]
```

## Avatar 数据结构

**详细Avatar文档**: [docs/core/models.md](./docs/core/models.md#avatar数据结构)

### wav2lip Avatar (data/avatars/wav2lip256_avatar1/)
```
full_imgs/          # 全身图像序列
face_imgs/          # 人脸裁剪图像
coords.pkl          # 人脸坐标信息 (pickle)
```

### musetalk Avatar (data/avatars/avator_1/)
```
full_imgs/          # 全身图像序列
coords.pkl          # 人脸坐标
latents.pt          # VAE 编码的潜在向量
mask/               # 面部遮罩图像
mask_coords.pkl     # 遮罩坐标
avator_info.json    # Avatar 元信息
```

### 生成 Avatar
- **wav2lip**: 运行 `wav2lip/genavatar.py`
- **musetalk**: 运行 `genavatar_musetalk.py`

## LLM 集成 (llm.py)

**详细LLM文档**: [docs/core/llm.md](./docs/core/llm.md)

**默认配置：**
- 使用 OpenAI SDK 兼容 DashScope API（通义千问）
- 环境变量: `DASHSCOPE_API_KEY`
- base_url: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- model: `qwen-plus`

**流式输出机制：**
- 按标点符号分句: `,.!;:，。！？：；` (llm.py:38)
- 每句累积 >10 字符时立即发送 TTS (llm.py:41-43)

**替换其他 LLM：**
修改 llm.py:9-14 的 `api_key`, `base_url`, `model` 参数即可接入任何 OpenAI 兼容 API。

## 性能监控与优化

**完整数据流文档**: [docs/guides/dataflow.md](./docs/guides/dataflow.md)

### 关键日志指标

- **inferfps**: GPU 推理帧率（需 ≥25 保证实时）
- **finalfps**: 最终推流帧率（需 ≥25 保证流畅）
- **actual avg final fps**: webrtc.py:143 统计的实际发送帧率

### 性能瓶颈定位

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| inferfps ≥25 但 finalfps <25 | CPU 性能不足（H264 编码瓶颈）| 降低分辨率或升级 CPU |
| inferfps <25 | GPU 性能不足或 batch_size 过大 | 调整 batch_size 或升级 GPU |
| 首次推理卡顿 | 模型未预热 | warm_up() 已自动执行（wav2lip/musetalk）|

### 性能调优建议

1. **调整 batch_size**: 越大显存占用越高，但推理效率越高
2. **监控 GPU 利用率**: `nvidia-smi` 或 `watch -n 1 nvidia-smi`
3. **并发限制**: 显存受限，每个会话独占一份模型显存

## 录制功能 (basereal.py:171-219)

**实现机制：**
- 使用 FFmpeg 管道录制音视频
- 视频: rawvideo (bgr24) → h264 → MP4 (25fps)
- 音频: s16le PCM (16kHz) → AAC
- 输出文件: `temp{sessionid}.mp4` 和 `temp{sessionid}.aac`

**合并音视频：**
```bash
ffmpeg -i temp0.mp4 -i temp0.aac -c copy output.mp4
```

## 常见开发任务

### 添加新 TTS 引擎

**详细指南**: [docs/core/tts.md](./docs/core/tts.md) + [docs/architecture/overview.md](./docs/architecture/overview.md#添加新tts服务)

1. 在 ttsreal.py 继承 `BaseTTS` 类
2. 实现 `txt_to_audio(msg)` 方法
3. 在 basereal.py:77-94 添加初始化逻辑
4. 更新 app.py:337 的 `--tts` 参数帮助文本

### 添加新数字人模型

**详细指南**: [docs/core/models.md](./docs/core/models.md) + [docs/architecture/overview.md](./docs/architecture/overview.md#添加新数字人模型)

1. 继承 `BaseReal` 创建实现类（如 `NewReal`）
2. 实现 `load_model()`, `load_avatar()`, `warm_up()` 函数
3. 实现 `render(quit_event, loop, audio_track, video_track)` 方法
4. 在 app.py:68-82 的 `build_nerfreal()` 添加分支
5. 在 app.py:364-381 添加启动时的模型加载逻辑

### 调试 WebRTC 连接问题

1. 检查 STUN 服务器可达性（app.py:104 使用 `stun:stun.miwifi.com:3478`）
2. 客户端启用 "使用STUN服务器" 选项（web/dashboard.html:342）
3. 查看浏览器控制台 WebRTC 日志
4. 确认防火墙开放 UDP 端口
5. 测试本地网络: `http://localhost:8010/dashboard.html`

### 替换 LLM

修改 llm.py:9-14:
```python
client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.example.com/v1",
)
# 修改 model 参数
completion = client.chat.completions.create(
    model="your-model-name",
    ...
)
```

## 项目结构说明

### 核心文件

- `app.py`: aiohttp Web 服务入口，WebRTC 连接管理
- `basereal.py`: 数字人抽象基类，定义核心接口
- `webrtc.py`: WebRTC 音视频轨道实现
- `llm.py`: LLM 对话接口（通义千问）
- `ttsreal.py`: TTS 引擎抽象类及所有实现
- `baseasr.py`: ASR 抽象基类

### 模型实现

- `musereal.py`: musetalk 模型实现
- `lipreal.py`: wav2lip 模型实现
- `lightreal.py`: ultralight 模型实现
- `museasr.py`, `lipasr.py`, `hubertasr.py`: ASR 实现

### Web 前端

- `web/dashboard.html`: WebRTC 集成前端界面
- `web/client.js`: WebRTC 客户端逻辑
- `web/srs.sdk.js`: SRS WebRTC SDK

### 模型目录

- `musetalk/`: musetalk 模型代码
- `wav2lip/`: wav2lip 模型代码
- `ultralight/`: ultralight 模型代码


## 修改之后

1. 请手动 
* git add <文件名>
* git commit -m "修改说明"
* git push