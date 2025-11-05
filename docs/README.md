# LiveTalking-V2 技术文档

实时交互流式数字人系统技术文档，面向AI代码分析。

## 文档目录

### 📐 architecture/ - 架构设计
- **[overview.md](./architecture/overview.md)** - 项目整体架构
  - 系统分层设计和技术栈
  - 核心目录结构
  - Session管理和并发模型
  - 扩展点和性能优化

### 🔧 core/ - 核心模块
- **[basereal.md](./core/basereal.md)** - BaseReal基类
  - 核心API和属性
  - 音频流处理
  - 自定义视频支持
  - 录制功能

- **[models.md](./core/models.md)** - 数字人模型
  - LipReal (Wav2Lip) 实现
  - MuseReal (MuseTalk) 实现
  - LightReal (Ultralight) 实现
  - Avatar数据结构

- **[tts.md](./core/tts.md)** - TTS服务
  - BaseTTS基类
  - 9种TTS服务实现
  - 事件同步机制

- **[asr.md](./core/asr.md)** - ASR处理
  - BaseASR基类
  - 滑动窗口机制
  - 特征提取实现

- **[webrtc.md](./core/webrtc.md)** - WebRTC通信
  - PlayerStreamTrack实现
  - 时间同步机制
  - HumanPlayer播放器

- **[llm.md](./core/llm.md)** - LLM集成
  - 对话流程
  - 流式输出处理

### 🌐 api/ - API接口
- **[http-api.md](./api/http-api.md)** - HTTP API规范
  - WebRTC连接接口
  - 交互和控制接口
  - 客户端集成示例

### 📖 guides/ - 使用指南
- **[dataflow.md](./guides/dataflow.md)** - 数据流与处理
  - 完整数据流图
  - 文本/音频输入流程
  - 推理和输出流程
  - 延迟分析和优化

- **[configuration.md](./guides/configuration.md)** - 配置参数
  - 命令行参数详解
  - 环境变量配置
  - 运行示例
  - 故障排查

## 快速导航

### 按使用场景

#### 🚀 快速开始
1. [configuration.md](./guides/configuration.md) - 运行配置
2. [http-api.md](./api/http-api.md) - API使用

#### 🏗️ 理解架构
1. [architecture/overview.md](./architecture/overview.md) - 整体架构
2. [guides/dataflow.md](./guides/dataflow.md) - 数据流向
3. [core/](./core/) - 核心模块详情

#### 🔌 客户端集成
1. [http-api.md](./api/http-api.md) - API接口
2. [webrtc.md](./core/webrtc.md) - WebRTC实现

#### ⚡ 性能优化
1. [architecture/overview.md](./architecture/overview.md#性能优化) - 优化策略
2. [guides/dataflow.md](./guides/dataflow.md#延迟分析) - 延迟优化
3. [configuration.md](./guides/configuration.md#性能调优) - 参数调优

#### 🔧 功能扩展
1. [architecture/overview.md](./architecture/overview.md#扩展点) - 扩展点说明
2. [core/basereal.md](./core/basereal.md) - 基类API
3. [core/tts.md](./core/tts.md) - 添加TTS服务
4. [core/models.md](./core/models.md) - 添加数字人模型

#### 🐛 问题调试
1. [guides/dataflow.md](./guides/dataflow.md#错误处理) - 错误处理
2. [configuration.md](./guides/configuration.md#故障排查) - 故障排查

### 按模块查找

| 模块 | 文档位置 |
|------|----------|
| 应用入口 (app.py) | [architecture/overview.md](./architecture/overview.md) |
| BaseReal基类 | [core/basereal.md](./core/basereal.md) |
| 数字人模型 | [core/models.md](./core/models.md) |
| TTS服务 | [core/tts.md](./core/tts.md) |
| ASR处理 | [core/asr.md](./core/asr.md) |
| WebRTC通信 | [core/webrtc.md](./core/webrtc.md) |
| LLM集成 | [core/llm.md](./core/llm.md) |
| API接口 | [api/http-api.md](./api/http-api.md) |
| 数据流 | [guides/dataflow.md](./guides/dataflow.md) |
| 配置参数 | [guides/configuration.md](./guides/configuration.md) |

### 按文件查找

| 源代码文件 | 相关文档 |
|-----------|----------|
| app.py | [architecture/overview.md](./architecture/overview.md), [api/http-api.md](./api/http-api.md) |
| basereal.py | [core/basereal.md](./core/basereal.md), [guides/dataflow.md](./guides/dataflow.md) |
| lipreal.py<br>musereal.py<br>lightreal.py | [core/models.md](./core/models.md) |
| ttsreal.py | [core/tts.md](./core/tts.md) |
| baseasr.py<br>lipasr.py<br>museasr.py<br>hubertasr.py | [core/asr.md](./core/asr.md) |
| webrtc.py | [core/webrtc.md](./core/webrtc.md) |
| llm.py | [core/llm.md](./core/llm.md) |

## 核心概念速查

### Session
每个WebRTC连接对应一个独立session（6位随机数字标识），维护独立的BaseReal实例。

详见: [architecture/overview.md](./architecture/overview.md#session-管理)

### Avatar
数字人形象数据，包含图像序列、坐标、latent等预处理数据。

详见: [core/models.md](./core/models.md#avatar数据结构)

### 滑动窗口
ASR处理的上下文机制，配置为左-中-右三段（默认10-8-10）。

详见: [core/asr.md](./core/asr.md#滑动窗口机制)

### 批处理推理
收集batch_size个帧后批量推理，平衡延迟和吞吐。

详见: [guides/dataflow.md](./guides/dataflow.md#批处理推理)

### 事件同步
eventpoint机制实现音频帧与业务事件同步。

详见: [core/tts.md](./core/tts.md#事件同步)

## 代码位置索引

### 核心类定义
- `BaseReal`: basereal.py:70 → [core/basereal.md](./core/basereal.md)
- `BaseTTS`: ttsreal.py:54 → [core/tts.md](./core/tts.md)
- `BaseASR`: baseasr.py:28 → [core/asr.md](./core/asr.md)
- `LipReal`: lipreal.py → [core/models.md](./core/models.md#lipreal)
- `MuseReal`: musereal.py → [core/models.md](./core/models.md#musereal)
- `LightReal`: lightreal.py → [core/models.md](./core/models.md#lightreal)
- `HumanPlayer`: webrtc.py:163 → [core/webrtc.md](./core/webrtc.md#humanplayer)

### 关键函数
- `offer()`: app.py:85 → [api/http-api.md](./api/http-api.md#post-offer)
- `human()`: app.py:144 → [api/http-api.md](./api/http-api.md#post-human)
- `process_frames()`: basereal.py:300 → [core/basereal.md](./core/basereal.md#process_frames)
- `llm_response()`: llm.py:6 → [core/llm.md](./core/llm.md)

## 技术要点

### 实时性保证
- 音频: 20ms帧处理
- 视频: 25fps输出
- 批处理优化
- 异步架构

详见: [guides/dataflow.md](./guides/dataflow.md#延迟分析)

### 多并发支持
- Session隔离
- 模型权重共享
- 显存优化

详见: [architecture/overview.md](./architecture/overview.md#并发处理)

### 模型支持
- Wav2Lip (256x256)
- MuseTalk (VAE+UNet)
- Ultralight (轻量级)

详见: [core/models.md](./core/models.md)

### TTS服务
9种TTS服务，从免费到商业化。

详见: [core/tts.md](./core/tts.md)

### 传输方式
- WebRTC: 低延迟P2P
- RTCPush: 推流到SRS
- VirtualCam: 虚拟摄像头

详见: [configuration.md](./guides/configuration.md#传输配置)

## 性能指标

### 推理性能参考
| 模型 | GPU | FPS |
|------|-----|-----|
| Wav2Lip | 3060 | 60 |
| Wav2Lip | 3080Ti | 120 |
| MuseTalk | 3080Ti | 42 |
| MuseTalk | 4090 | 72 |

### 延迟指标
- TTS首包: 100-500ms
- 推理: 40ms/frame
- 端到端: ~260ms

详见: [guides/dataflow.md](./guides/dataflow.md#延迟分析)

## 依赖技术栈

```
Python 3.10+
├── PyTorch 2.5.0 (CUDA 12.4)
├── Flask / aiohttp
├── aiortc (WebRTC)
├── OpenCV
├── soundfile / resampy
└── transformers
```

## 开发建议

### 添加新数字人模型
参考: [core/models.md](./core/models.md) + [architecture/overview.md](./architecture/overview.md#添加新数字人模型)

### 添加新TTS服务
参考: [core/tts.md](./core/tts.md#basetts基类) + [architecture/overview.md](./architecture/overview.md#添加新tts服务)

### 性能优化
参考: [configuration.md](./guides/configuration.md#性能调优) + [guides/dataflow.md](./guides/dataflow.md#性能优化点)

## 项目信息

- 仓库: https://github.com/lipku/LiveTalking
- 许可证: Apache 2.0
- Python: 3.10+
- CUDA: 12.4 (推荐)

## 文档更新

文档基于代码分析生成，与代码库同步更新。

**另见**: 项目根目录的 [CLAUDE.md](../CLAUDE.md) 获取完整项目指引。
