# 项目架构

## 整体架构

LiveTalking-V2 是实时交互流式数字人系统，基于 Python 3.10、PyTorch 2.5.0 和 CUDA 12.4 构建。

### 技术栈

- **深度学习框架**: PyTorch 2.5.0
- **Web 服务**: Flask + aiohttp (异步HTTP)
- **实时通信**: WebRTC (aiortc)
- **视频处理**: OpenCV, av (PyAV)
- **音频处理**: soundfile, resampy
- **进程管理**: torch.multiprocessing

### 系统分层

```
┌─────────────────────────────────────────────────────┐
│                  Web/Client Layer                   │
│    (WebRTC Client, HTTP API, Dashboard UI)        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│              Application Entry Layer                │
│         app.py - Flask/aiohttp Server              │
│  (Session管理, WebRTC连接, HTTP路由)               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│             Real-time Processing Layer              │
│  basereal.py - 基类                                 │
│  ├── LipReal (Wav2Lip)                             │
│  ├── MuseReal (MuseTalk)                           │
│  └── LightReal (Ultralight)                        │
└─────────────────────────────────────────────────────┘
         ↓                  ↓                 ↓
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  TTS Layer   │   │  ASR Layer   │   │ Model Layer  │
│  ttsreal.py  │   │ baseasr.py   │   │ 推理模型     │
│  (9种TTS)    │   │ (4种ASR)     │   │ VAE/UNet等   │
└──────────────┘   └──────────────┘   └──────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│           Communication/Transport Layer             │
│    webrtc.py - 媒体流传输                           │
│    (Audio/Video Track, 帧同步)                      │
└─────────────────────────────────────────────────────┘
```

## 核心目录结构

```
LiveTalking-V2/
├── app.py                  # 应用入口、WebRTC服务器
├── basereal.py             # 实时处理基类
├── baseasr.py              # ASR基类
├── ttsreal.py              # TTS实现（9种服务）
├── webrtc.py               # WebRTC媒体流处理
├── llm.py                  # LLM集成
│
├── lipreal.py              # Wav2Lip数字人实现
├── lipasr.py               # Wav2Lip ASR
├── musereal.py             # MuseTalk数字人实现
├── museasr.py              # MuseTalk ASR
├── lightreal.py            # Ultralight数字人实现
├── hubertasr.py            # Hubert ASR
│
├── wav2lip/                # Wav2Lip模型代码
│   ├── models/             # 模型定义
│   ├── audio.py            # 音频处理
│   └── genavatar.py        # Avatar生成
│
├── musetalk/               # MuseTalk模型代码
│   ├── models/             # VAE/UNet/SyncNet
│   ├── utils/              # 工具函数
│   └── whisper/            # Whisper特征提取
│
├── ultralight/             # Ultralight模型代码
│   ├── unet.py             # UNet模型
│   └── audio2feature.py    # 音频特征提取
│
├── web/                    # Web客户端
│   ├── dashboard.html      # 控制台
│   ├── webrtcapi.html      # WebRTC客户端
│   └── *.js                # 客户端脚本
│
├── data/                   # 数据目录
│   └── avatars/            # Avatar数据
│       └── {avatar_id}/    # 每个avatar独立目录
│           ├── full_imgs/  # 完整帧图像
│           ├── face_imgs/  # 面部图像
│           ├── coords.pkl  # 坐标数据
│           └── ...
│
└── models/                 # 模型权重
    └── wav2lip.pth
```

## 核心组件关系

### 1. Session 管理

```python
# app.py:53-56
nerfreals: Dict[int, BaseReal] = {}  # sessionid -> BaseReal实例
```

每个WebRTC连接对应一个session，通过随机6位数字标识。

### 2. 数字人实例化流程

```
app.py:offer()
  → build_nerfreal(sessionid)
    → 根据opt.model选择: LipReal/MuseReal/LightReal
      → 继承自BaseReal
```

参考: app.py:68-82

### 3. 媒体处理流程

```
HumanPlayer (webrtc.py:163)
  → PlayerStreamTrack (audio/video)
    → BaseReal.process_frames()
      → 推理queue → 视频帧合成 → WebRTC输出
```

参考: webrtc.py:154-231

## 数据流向

```
文本输入 → TTS → 音频chunk(16kHz, 20ms)
                    ↓
         ASR特征提取 → feat_queue
                    ↓
         数字人模型推理 → res_frame_queue
                    ↓
         帧合成(paste_back) → WebRTC Track
                    ↓
              客户端播放
```

## 并发处理

### 多Session支持

- 每个session独立BaseReal实例
- 显存不随并发数增加（共享模型权重）
- 通过`opt.max_session`控制最大并发数

### 进程/线程模型

- **主进程**: Flask服务器、WebRTC连接管理
- **子进程**: ASR特征提取进程（multiprocessing）
- **线程**:
  - TTS处理线程
  - 推理线程
  - 帧处理线程（process_frames）
  - WebRTC媒体线程

参考: basereal.py 中的Queue和mp.Queue使用

## 扩展点

### 添加新数字人模型

1. 继承`BaseReal`类（basereal.py:70）
2. 实现`render()`方法
3. 在app.py中注册模型加载逻辑
4. 实现对应的ASR子类

### 添加新TTS服务

1. 继承`BaseTTS`类（ttsreal.py:54）
2. 实现`txt_to_audio()`方法
3. 在BaseReal.__init__中注册

### 添加新传输方式

当前支持: webrtc, rtcpush, virtualcam

实现方式参考: basereal.py:300-401 (process_frames方法)

## 性能优化

### 模型预热

启动时执行warm_up避免首次推理卡顿:
- app.py:369 (MuseTalk)
- app.py:375 (Wav2Lip)
- app.py:381 (Ultralight)

### 批处理推理

通过`opt.batch_size`控制批次大小，平衡延迟和吞吐。

### 显存管理

模型权重在进程间共享，各session只维护独立的处理队列和状态。
