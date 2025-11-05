# 配置参数

## 命令行参数

所有参数在 app.py:318-350 定义。

### 基础参数

#### --fps
音频采样FPS，固定值。

- 类型: int
- 默认: 50
- 说明: 必须为50，对应20ms音频帧
- 位置: app.py:321

#### -l, -m, -r
滑动窗口配置，控制ASR处理的上下文。

- `-l`: 左窗口大小（单位: 20ms）
  - 类型: int
  - 默认: 10
  - 说明: 左侧上下文帧数

- `-m`: 中间窗口大小（单位: 20ms）
  - 类型: int
  - 默认: 8
  - 说明: 实际推理的帧数

- `-r`: 右窗口大小（单位: 20ms）
  - 类型: int
  - 默认: 10
  - 说明: 右侧上下文帧数

- 位置: app.py:323-325

总窗口: `l + m + r` = 28帧 = 560ms

#### --W, --H
GUI窗口尺寸（用于非WebRTC模式）。

- 类型: int
- 默认: 450x450
- 位置: app.py:327-328

### 数字人配置

#### --model
数字人模型类型。

- 类型: str
- 默认: 'musetalk'
- 可选值: 'musetalk', 'wav2lip', 'ultralight'
- 位置: app.py:344

#### --avatar_id
Avatar数据目录名。

- 类型: str
- 默认: 'avator_1'
- 说明: 对应 `data/avatars/{avatar_id}`
- 位置: app.py:331

#### --batch_size
推理批次大小。

- 类型: int
- 默认: 16
- 说明: 批量推理的帧数
- 建议:
  - 3060: 8
  - 3080Ti/3090: 16
  - 4090: 32
- 位置: app.py:333

#### --customvideo_config
自定义动作视频配置文件。

- 类型: str
- 默认: ''
- 格式: JSON文件路径
- 示例: `data/custom_config.json`
- 位置: app.py:335

配置文件格式:
```json
[
  {
    "audiotype": 2,
    "imgpath": "data/custom/video1/imgs",
    "audiopath": "data/custom/video1/audio.wav"
  }
]
```

### TTS配置

#### --tts
TTS服务类型。

- 类型: str
- 默认: 'edgetts'
- 可选值:
  - 'edgetts': 微软Edge TTS
  - 'xtts': Coqui XTTS
  - 'gpt-sovits': GPT-SoVITS
  - 'cosyvoice': CosyVoice
  - 'fishtts': Fish TTS
  - 'tencent': 腾讯云TTS
  - 'doubao': 字节豆包TTS
  - 'indextts2': IndexTTS2
  - 'azuretts': Azure TTS
- 位置: app.py:337

#### --REF_FILE
参考文件或语音模型ID。

- 类型: str
- 默认: "zh-CN-YunxiaNeural" (EdgeTTS语音ID)
- 说明:
  - EdgeTTS: 语音模型ID
  - XTTS/GPT-SoVITS/CosyVoice: 参考音频文件路径
  - FishTTS: reference_id
  - Tencent/Doubao: voice_type (整数字符串)
  - AzureTTS: 语音模型名称
- 位置: app.py:338

#### --REF_TEXT
参考文本（用于声音克隆）。

- 类型: str
- 默认: None
- 说明: GPT-SoVITS/CosyVoice需要
- 位置: app.py:339

#### --TTS_SERVER
TTS服务器地址。

- 类型: str
- 默认: 'http://127.0.0.1:9880'
- 说明: 本地TTS服务的HTTP地址
- 位置: app.py:340

### 传输配置

#### --transport
传输方式。

- 类型: str
- 默认: 'rtcpush'
- 可选值:
  - 'webrtc': WebRTC点对点
  - 'rtcpush': RTC推流
  - 'virtualcam': 虚拟摄像头
- 位置: app.py:346

#### --push_url
推流URL（用于rtcpush模式）。

- 类型: str
- 默认: 'http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream'
- 说明: SRS服务器的WHIP端点
- 位置: app.py:347

### 服务器配置

#### --max_session
最大并发会话数。

- 类型: int
- 默认: 1
- 说明: 限制同时连接的WebRTC会话数
- 位置: app.py:349

#### --listenport
HTTP服务监听端口。

- 类型: int
- 默认: 8010
- 位置: app.py:350

## 环境变量

### LLM配置

#### DASHSCOPE_API_KEY
阿里云DashScope API密钥（用于LLM对话）。

- 用途: llm.py:11
- 获取: https://dashscope.aliyun.com/

### TTS服务配置

#### TENCENT_APPID, TENCENT_SECRET_KEY, TENCENT_SECRET_ID
腾讯云TTS凭证。

- 用途: ttsreal.py:413-415
- 获取: https://cloud.tencent.com/

#### DOUBAO_APPID, DOUBAO_TOKEN
字节豆包TTS凭证。

- 用途: ttsreal.py:537-538
- 获取: https://www.volcengine.com/

#### AZURE_SPEECH_KEY, AZURE_TTS_REGION
微软Azure TTS凭证。

- 用途: ttsreal.py:936-937
- 获取: https://azure.microsoft.com/

### Hugging Face镜像

#### HF_ENDPOINT
Hugging Face镜像地址。

- 默认: https://huggingface.co
- 国内镜像: https://hf-mirror.com
- 设置方式:
  ```bash
  export HF_ENDPOINT=https://hf-mirror.com
  ```

## 配置文件

### data/custom_config.json
自定义视频配置。

格式:
```json
[
  {
    "audiotype": 2,           // 状态ID (>1)
    "imgpath": "path/to/imgs", // 图像序列目录
    "audiopath": "path/to/audio.wav" // 音频文件
  }
]
```

使用:
```bash
python app.py --customvideo_config data/custom_config.json
```

切换状态:
```
POST /set_audiotype {
  "sessionid": 123456,
  "audiotype": 2,
  "reinit": true
}
```

### Avatar配置

#### avator_info.json (可选)
Avatar元信息，位于 `data/avatars/{avatar_id}/avator_info.json`

```json
{
  "avatar_id": "avator_1",
  "video_path": "source.mp4",
  "bbox_shift": 5
}
```

## 运行示例

### 基础运行

Wav2Lip + EdgeTTS + WebRTC:
```bash
python app.py \
  --model wav2lip \
  --avatar_id wav2lip256_avatar1 \
  --transport webrtc \
  --tts edgetts \
  --REF_FILE zh-CN-YunxiaNeural
```

### MuseTalk + GPT-SoVITS

```bash
python app.py \
  --model musetalk \
  --avatar_id musetalk_avatar1 \
  --batch_size 16 \
  --tts gpt-sovits \
  --REF_FILE data/reference.wav \
  --REF_TEXT "这是参考文本" \
  --TTS_SERVER http://localhost:9880
```

### Ultralight + IndexTTS2

```bash
export DASHSCOPE_API_KEY="your_api_key"

python app.py \
  --model ultralight \
  --avatar_id ultralight_avatar1 \
  --batch_size 8 \
  --tts indextts2 \
  --REF_FILE data/reference.wav \
  --TTS_SERVER http://localhost:7860
```

### 虚拟摄像头输出

```bash
python app.py \
  --model wav2lip \
  --avatar_id wav2lip256_avatar1 \
  --transport virtualcam \
  --tts edgetts
```

### 多并发

```bash
python app.py \
  --model musetalk \
  --avatar_id musetalk_avatar1 \
  --max_session 4 \
  --batch_size 8
```

### 自定义动作

```bash
python app.py \
  --model wav2lip \
  --avatar_id wav2lip256_avatar1 \
  --customvideo_config data/custom_config.json
```

## 性能调优

### GPU显存优化

降低batch_size:
```bash
python app.py --batch_size 4  # 低显存
```

### CPU性能优化

调整滑动窗口:
```bash
python app.py -l 5 -m 4 -r 5  # 减少延迟
```

### 网络优化

端口配置:
- TCP: 8010 (HTTP服务)
- UDP: 1-65536 (WebRTC)

防火墙:
```bash
# Ubuntu
sudo ufw allow 8010/tcp
sudo ufw allow 1:65536/udp

# 阿里云/腾讯云
# 在安全组添加规则
```

## 模型路径

### Wav2Lip
```
models/wav2lip.pth
```

### MuseTalk
```
musetalk/models/
├── musetalk/
│   ├── pytorch_model.bin
│   ├── musetalk.json
│   └── ...
├── sd-vae-ft-mse/
│   └── diffusion_pytorch_model.bin
└── whisper/
    └── tiny.pt

models/whisper/tiny.pt  # Whisper模型
```

### Ultralight
```
data/avatars/{avatar_id}/ultralight.pth  # 每个avatar独立
```

### dwpose (MuseTalk依赖)
```
musetalk/utils/dwpose/
└── dw-ll_ucoco_384.pth
```

## 日志配置

### 日志级别

修改 logger.py:
```python
import logging

# 全局配置
logging.basicConfig(level=logging.INFO)  # 改为 DEBUG 查看详细日志
```

### 性能日志

关键指标:
```
inferfps: GPU推理帧率
finalfps: 最终输出帧率
```

查看方式:
```bash
python app.py | grep "fps"
```

### TTS延迟日志

```
Time to make POST: XX.XXs
Time to first chunk: XX.XXs
```

### LLM延迟日志

```
llm Time init: XX.XXs
llm Time to first chunk: XX.XXs
llm Time to last chunk: XX.XXs
```

## Docker配置

### Docker运行

```bash
docker run --gpus all -it --network=host --rm \
  registry.cn-zhangjiakou.aliyuncs.com/codewithgpu3/lipku-livetalking:toza2irpHZ
```

### 自定义Dockerfile

基于 Dockerfile:
```dockerfile
FROM nvidia/cuda:12.4.0-cudnn-devel-ubuntu22.04

# 安装依赖
RUN apt-get update && apt-get install -y \
    python3.10 python3-pip git ffmpeg

# 安装Python包
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
COPY . /app
WORKDIR /app

# 运行
CMD ["python3", "app.py", "--model", "wav2lip", "--avatar_id", "wav2lip256_avatar1"]
```

## 故障排查

### 端口冲突

修改监听端口:
```bash
python app.py --listenport 8080
```

### CUDA版本不匹配

安装对应版本PyTorch:
```bash
# 检查CUDA版本
nvidia-smi

# 安装对应PyTorch
# https://pytorch.org/get-started/previous-versions/
```

### TTS服务连接失败

检查服务状态:
```bash
curl http://127.0.0.1:9880/health
```

### Avatar加载失败

检查文件完整性:
```bash
ls data/avatars/{avatar_id}/
# 应包含: full_imgs/, coords.pkl等
```

### WebRTC连接失败

1. 检查防火墙
2. 检查STUN服务器可达性
3. 使用dashboard.html测试连接

## 默认配置总览

```python
{
  'fps': 50,
  'l': 10, 'm': 8, 'r': 10,
  'W': 450, 'H': 450,
  'avatar_id': 'avator_1',
  'batch_size': 16,
  'customvideo_config': '',
  'tts': 'edgetts',
  'REF_FILE': 'zh-CN-YunxiaNeural',
  'REF_TEXT': None,
  'TTS_SERVER': 'http://127.0.0.1:9880',
  'model': 'musetalk',
  'transport': 'rtcpush',
  'push_url': 'http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream',
  'max_session': 1,
  'listenport': 8010
}
```

位置: app.py:318-350
