# TTS模块

位置: `ttsreal.py` (723行)

## 架构设计

### 插件化架构

```python
BaseTTS (ttsreal.py:53-90)
├── EdgeTTS (93-155)
├── FishTTS (157-231)
├── SovitsTTS (233-327)
├── CosyVoiceTTS (330-393)
├── TencentTTS (401-517)
├── DoubaoTTS (522-647)
├── XTTS (650-723)
├── IndexTTS2 (663-849)
└── AzureTTS (930-985)
```

所有TTS实现继承 `BaseTTS`，提供统一接口。上层代码 (`basereal.py`) 通过接口调用，无需关心具体实现。

### 初始化流程

```python
# basereal.py:77-90
if opt.tts == "edgetts":
    self.tts = EdgeTTS(opt, self)
elif opt.tts == "gpt-sovits":
    self.tts = SovitsTTS(opt, self)
# ... 其他实现
```

## BaseTTS 基类

```python
# ttsreal.py:53-90
class BaseTTS:
    def __init__(self, opt, parent: BaseReal):
        self.opt = opt
        self.parent = parent
        self.fps = opt.fps                    # 默认50 (20ms per frame)
        self.sample_rate = 16000              # 标准采样率
        self.chunk = self.sample_rate // self.fps  # 320 samples/frame
        self.msgqueue = Queue()               # 文本消息队列
        self.state = State.RUNNING

    def put_msg_txt(self, msg: str, eventpoint=None):
        """将文本消息放入队列"""
        if len(msg) > 0:
            self.msgqueue.put((msg, eventpoint))

    def render(self, quit_event):
        """启动后台线程处理TTS"""
        process_thread = Thread(target=self.process_tts,
                               args=(quit_event,))
        process_thread.start()

    def process_tts(self, quit_event):
        """后台线程持续处理队列中的文本"""
        while not quit_event.is_set():
            try:
                msg = self.msgqueue.get(block=True, timeout=1)
                self.state = State.RUNNING
            except queue.Empty:
                continue
            self.txt_to_audio(msg)  # 调用子类实现

    def txt_to_audio(self, msg):
        """子类必须实现的方法"""
        raise NotImplementedError

    def flush_talk(self):
        """清空队列并暂停"""
        self.msgqueue.queue.clear()
        self.state = State.PAUSE
```

### 关键属性

- `fps`: 帧率，默认50 (20ms/帧)
- `sample_rate`: 输出采样率，统一16000 Hz
- `chunk`: 每帧样本数，计算公式 `16000 / 50 = 320`
- `msgqueue`: `Queue` 对象，存储待合成文本
- `state`: `State.RUNNING` 或 `State.PAUSE`

## 工作流程

### 完整调用链

```
app.py:315 (/human API)
    ↓ params['text']
nerfreals[sessionid].put_msg_txt(text)
    ↓
basereal.py:107
    ↓ self.tts.put_msg_txt(msg, eventpoint)
ttsreal.py:83
    ↓ self.msgqueue.put((msg, eventpoint))
后台线程 (ttsreal.py:88-96)
    ↓ msg = self.msgqueue.get()
txt_to_audio(msg) - 具体TTS实现
    ↓ 生成音频流
self.parent.put_audio_frame(chunk, eventpoint)
    ↓
basereal.py:163-186
    ↓ 转换为 int16 PCM
self.asr.put_audio_frame(audio_chunk, eventpoint)
    ↓
ASR模块处理 → 唇形同步
```

### 数据流转

```
文本 (str)
    ↓
TTS API (Edge/GPT-SoVITS/...)
    ↓
原始音频流 (WAV/OGG/PCM, 不同采样率)
    ↓
numpy.ndarray (float32)
    ↓
重采样 → 16000 Hz
    ↓
分帧 → 320 samples/frame (20ms)
    ↓
int16 PCM (-32768 ~ 32767)
    ↓
WebRTC → 前端播放
```

## TTS 实现细节

### 1. EdgeTTS (微软Edge)

**位置**: ttsreal.py:93-155

**实现方式**:
- 使用 `edge_tts` 库异步调用
- 返回完整 WAV 文件

**关键代码**:
```python
def txt_to_audio(self, msg):
    text, textevent = msg
    voicename = self.opt.REF_FILE  # "zh-CN-YunxiaNeural"

    # 异步获取音频
    asyncio.new_event_loop().run_until_complete(
        self.__main(voicename, text))

    # 解析WAV文件
    self.input_stream.seek(0)
    stream = self.__create_bytes_stream(self.input_stream)

    # 重采样到16kHz
    stream = resampy.resample(x=stream, sr_orig=sample_rate,
                             sr_new=self.sample_rate)

    # 分帧输出
    streamlen = stream.shape[0]
    idx = 0
    while streamlen >= self.chunk:
        eventpoint = None
        if idx == 0:
            eventpoint = {'status':'start', 'text':text,
                         'msgevent':textevent}
        elif streamlen < self.chunk:
            eventpoint = {'status':'end', 'text':text,
                         'msgevent':textevent}

        self.parent.put_audio_frame(
            stream[idx:idx+self.chunk], eventpoint)
        idx += self.chunk
```

**配置参数**:
```bash
--tts edgetts
--REF_FILE "zh-CN-YunxiaNeural"  # 音色ID
```

**特点**:
- 免费，无需API密钥
- 支持多语言
- 非流式，需等待完整音频生成
- 采样率不固定 (通常 16kHz 或 24kHz)

### 2. FishTTS

**位置**: ttsreal.py:157-231

**实现方式**:
- HTTP POST 流式请求
- 返回 WAV 格式音频流

**关键代码**:
```python
def fish_speech(self, text, reffile, reftext, language, server_url):
    req = {
        'text': text,
        'reference_id': reffile,
        'format': 'wav',
        'streaming': True,
        'use_memory_cache': 'on'
    }
    res = requests.post(f"{server_url}/v1/tts", json=req,
                       stream=True)

    # 流式返回音频块 (44100Hz, 20ms per chunk)
    for chunk in res.iter_content(chunk_size=17640):
        yield chunk
```

**音频处理**:
```python
# 原始采样率: 44100 Hz
# chunk_size: 17640 bytes = 8820 samples = 200ms @ 44100Hz
stream = resampy.resample(x=stream, sr_orig=44100,
                         sr_new=16000)
```

**配置参数**:
```bash
--tts fishtts
--TTS_SERVER http://127.0.0.1:9880
--REF_FILE "reference_id"  # Fish TTS的reference_id
```

### 3. SovitsTTS (GPT-SoVITS)

**位置**: ttsreal.py:233-327

**实现方式**:
- HTTP POST 流式请求
- 支持声音克隆 (参考音频 + 参考文本)
- 返回 OGG 格式音频流

**关键代码**:
```python
def gpt_sovits(self, text, reffile, reftext, language, server_url):
    req = {
        'text': text,
        'text_lang': language,        # 'zh'/'en'
        'ref_audio_path': reffile,    # 参考音频路径
        'prompt_text': reftext,       # 参考文本
        'prompt_lang': language,
        'media_type': 'ogg',
        'streaming_mode': True
    }
    res = requests.post(f"{server_url}/tts", json=req, stream=True)

    for chunk in res.iter_content(chunk_size=None):
        yield chunk
```

**配置参数**:
```bash
--tts gpt-sovits
--TTS_SERVER http://127.0.0.1:9880
--REF_FILE data/reference.wav    # 参考音频
--REF_TEXT "这是参考文本内容"
```

**特点**:
- 本地部署
- 零样本声音克隆
- 流式输出
- 需要 3-10s 参考音频

### 4. CosyVoiceTTS

**位置**: ttsreal.py:330-393

**实现方式**:
- HTTP GET 请求 + 文件上传
- 零样本声音克隆
- 返回 24kHz PCM 音频流

**关键代码**:
```python
def cosy_voice(self, text, reffile, reftext, language, server_url):
    payload = {
        'tts_text': text,
        'prompt_text': reftext
    }
    files = [('prompt_wav', ('prompt_wav',
             open(reffile, 'rb'), 'application/octet-stream'))]

    res = requests.request("GET",
        f"{server_url}/inference_zero_shot",
        data=payload, files=files, stream=True)

    # 24kHz, 20ms per chunk
    for chunk in res.iter_content(chunk_size=9600):
        yield chunk
```

**音频处理**:
```python
# 原始采样率: 24000 Hz
# chunk_size: 9600 bytes = 4800 samples = 200ms @ 24kHz
stream = resampy.resample(x=stream, sr_orig=24000,
                         sr_new=16000)
```

**配置参数**:
```bash
--tts cosyvoice
--TTS_SERVER http://127.0.0.1:8000
--REF_FILE data/voice.wav
--REF_TEXT "参考文本"
```

### 5. TencentTTS (腾讯云)

**位置**: ttsreal.py:401-517

**实现方式**:
- HTTP POST 请求
- HMAC-SHA1 签名认证
- 流式返回 16kHz PCM

**关键代码**:
```python
def tencent_voice(self, text, reffile, reftext, language, server_url):
    timestamp = int(time.time())
    params = {
        'Action': 'TextToStreamAudio',
        'AppId': int(self.appid),
        'SecretId': self.secret_id,
        'Text': text,
        'VoiceType': self.voice_type,  # 整数音色ID
        'Codec': 'pcm',
        'SampleRate': 16000,
        'Timestamp': timestamp,
        'Expired': timestamp + 86400
    }

    # 生成签名
    signature = self.__gen_signature(params)
    params['Signature'] = signature

    res = requests.post(url, headers=headers,
                       data=json.dumps(params), stream=True)

    for chunk in res.iter_content(chunk_size=None):
        yield chunk
```

**签名算法**:
```python
def __gen_signature(self, params):
    # 1. 参数排序
    # 2. 构造签名原文: POSTtts.tencentcloudapi.com/?key1=val1&key2=val2
    # 3. HMAC-SHA1(secret_key, 签名原文)
    # 4. Base64编码
    hmac_code = hmac.new(
        secret_key.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha1).digest()
    return base64.b64encode(hmac_code).decode('utf-8')
```

**配置参数**:
```bash
export TENCENT_APPID="xxx"
export TENCENT_SECRET_KEY="xxx"
export TENCENT_SECRET_ID="xxx"

--tts tencent
--REF_FILE "1001"  # 音色ID (整数字符串)
```

**特点**:
- 商用服务，需付费
- 直接输出 16kHz PCM，无需重采样
- 需要签名认证
- 流式输出

### 6. DoubaoTTS (字节豆包)

**位置**: ttsreal.py:522-647

**实现方式**:
- WebSocket 连接 (wss)
- gzip 压缩传输
- 二进制协议

**关键代码**:
```python
async def doubao_voice(self, text):
    api_url = f"wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    header = {
        "Authorization": f"Bearer; {self.access_token}",
        "Resource-Id": self.appid
    }

    # 构造请求
    request_json = {
        "app": {"appid": self.appid, "token": self.access_token},
        "user": {"uid": "388808087185088"},
        "audio": {
            "voice_type": self.voice_type,
            "encoding": "pcm",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
            "emotion": "happy"
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "query"
        }
    }

    # gzip压缩
    request_json_bytes = json.dumps(request_json).encode('utf-8')
    compressed_bytes = gzip.compress(request_json_bytes)

    # 构造二进制消息 (4字节header)
    async with websockets.connect(api_url, extra_headers=header) as ws:
        await ws.send(full_client_request)

        while True:
            res = await ws.recv()
            # 解析二进制协议
            message_type = res[1] >> 4
            if message_type == 0xb:  # audio-only
                payload = res[header_size*4:]
                yield payload
```

**二进制协议**:
```
Byte 0: 协议版本 (0x10 = version 1)
Byte 1: message_type << 4 | message_serialization
    - 0xb: audio-only
    - 0xf: frontend-type
Byte 2-3: 预留
Byte 4-7: header_size (大端序)
Byte 8+: payload
```

**配置参数**:
```bash
export DOUBAO_APPID="xxx"
export DOUBAO_TOKEN="xxx"

--tts doubao
--REF_FILE "zh_male_1"  # 音色ID
```

**特点**:
- WebSocket 异步通信
- gzip 压缩，节省带宽
- 低延迟
- 直接输出 16kHz PCM

### 7. XTTS (Coqui XTTS)

**位置**: ttsreal.py:650-723

**实现方式**:
- HTTP POST 流式请求
- 支持多语言声音克隆
- 返回 24kHz PCM 音频流

**关键代码**:
```python
def xtts(self, text, speaker, language, server_url):
    speaker["text"] = text
    speaker["language"] = language
    speaker["stream_chunk_size"] = "20"  # 20ms

    res = requests.post(f"{server_url}/tts_stream",
                       json=speaker, stream=True)

    # 24kHz, 20ms per chunk
    for chunk in res.iter_content(chunk_size=9600):
        yield chunk
```

**配置参数**:
```bash
--tts xtts
--TTS_SERVER http://127.0.0.1:8000
--REF_FILE data/reference.wav
```

**特点**:
- 开源方案
- 支持 17 种语言
- 零样本声音克隆
- 需要 6s+ 参考音频

### 8. IndexTTS2

**位置**: ttsreal.py:663-849

**实现方式**:
- Gradio API 调用
- 支持长文本自动分句
- 情感控制

**特点**:
- 自动分句处理长文本
- 支持情感参考音频
- 情感强度控制
- 需要 Gradio 服务

### 9. AzureTTS (微软Azure)

**位置**: ttsreal.py:930-985

**实现方式**:
- Azure Cognitive Services SDK
- 高质量语音合成

**配置参数**:
```bash
export AZURE_SPEECH_KEY="xxx"
export AZURE_TTS_REGION="eastus"

--tts azuretts
--REF_FILE "zh-CN-XiaoxiaoMultilingualNeural"
```

## 音频处理标准化

### 采样率统一

所有 TTS 输出最终转换为 **16000 Hz**：

```python
# ttsreal.py - 不同TTS的重采样

# EdgeTTS (自动检测原始采样率)
stream = resampy.resample(x=stream, sr_orig=sample_rate,
                         sr_new=16000)

# FishTTS (44100 Hz)
stream = resampy.resample(x=stream, sr_orig=44100,
                         sr_new=16000)

# CosyVoice (24000 Hz)
stream = resampy.resample(x=stream, sr_orig=24000,
                         sr_new=16000)

# XTTS (24000 Hz)
stream = resampy.resample(x=stream, sr_orig=24000,
                         sr_new=16000)

# TencentTTS/DoubaoTTS (16000 Hz)
# 无需重采样
```

### 分帧处理

所有音频按 **20ms/帧** (320 samples @ 16kHz) 切分：

```python
# ttsreal.py - 通用分帧逻辑
self.chunk = self.sample_rate // self.fps  # 16000 / 50 = 320

idx = 0
while streamlen >= self.chunk:
    self.parent.put_audio_frame(stream[idx:idx+self.chunk], eventpoint)
    idx += self.chunk
    streamlen -= self.chunk
```

**为什么是 20ms？**
- WebRTC 标准帧长度 (Opus codec)
- 平衡延迟和带宽效率
- 唇形同步的最小时间粒度

### 数据格式转换

```python
# TTS输出 → basereal.py:163-186

# 1. TTS模块输出: numpy.ndarray (float32, -1.0 ~ 1.0)
audio_chunk = stream[idx:idx+self.chunk]  # shape: (320,)

# 2. basereal.py 转换为 int16 PCM
audio_chunk = (audio_chunk * 32767).astype(np.int16)

# 3. 传递给 ASR 和 WebRTC
self.audioplayer.put_audio_frame(audio_chunk)
self.asr.put_audio_frame(audio_chunk, eventpoint)
```

**格式标准**:
- 采样率: 16000 Hz
- 通道数: 1 (单声道)
- 样本格式: int16 PCM
- 取值范围: -32768 ~ 32767

## 事件同步机制

### eventpoint 结构

```python
eventpoint = {
    'status': 'start',      # 'start' | 'end'
    'text': '你好世界',
    'msgevent': textevent,  # 原始事件对象
    # ... 其他自定义字段
}
```

### 事件传递链

```python
# ttsreal.py - TTS生成第一帧和最后一帧
idx = 0
while streamlen >= self.chunk:
    eventpoint = None
    if idx == 0:
        # 第一帧: 标记开始
        eventpoint = {'status':'start', 'text':text,
                     'msgevent':textevent}
    elif streamlen < self.chunk:
        # 最后一帧: 标记结束
        eventpoint = {'status':'end', 'text':text,
                     'msgevent':textevent}

    self.parent.put_audio_frame(stream[idx:idx+self.chunk],
                               eventpoint)
    idx += self.chunk
```

```python
# basereal.py:163-186 - 传递给ASR
def put_audio_frame(self, audio_chunk, eventpoint=None):
    audio_chunk = (audio_chunk * 32767).astype(np.int16)

    self.speaking = True
    self.audioplayer.put_audio_frame(audio_chunk)

    # 同步给ASR模块
    self.asr.put_audio_frame(audio_chunk, eventpoint)
```

### 事件用途

- **唇形同步**: ASR模块检测 `status='start'` 时激活嘴部动画
- **字幕显示**: 前端根据事件显示文本
- **状态管理**: 追踪 TTS 播放进度
- **日志记录**: 记录对话轮次

## 队列管理

### 消息队列

```python
# ttsreal.py:71
self.msgqueue = Queue()  # 线程安全队列

# 添加消息
def put_msg_txt(self, msg: str, eventpoint=None):
    if len(msg) > 0:
        self.msgqueue.put((msg, eventpoint))

# 获取消息 (阻塞)
msg = self.msgqueue.get(block=True, timeout=1)
```

### 中断机制

```python
# ttsreal.py:78-80
def flush_talk(self):
    """清空队列并暂停TTS"""
    self.msgqueue.queue.clear()
    self.state = State.PAUSE
```

**使用场景**:
- 用户打断对话 (`app.py:/interrupt API`)
- 切换对话模式
- 紧急消息插队

### 状态控制

```python
class State(Enum):
    RUNNING = 0  # 正常处理
    PAUSE = 1    # 暂停状态

# basereal.py 调用
self.tts.flush_talk()  # 暂停并清空
```

## 配置参数汇总

### 命令行参数

```python
# app.py:419-422
parser.add_argument('--tts', type=str, default='edgetts',
                    choices=['edgetts', 'gpt-sovits', 'xtts',
                            'cosyvoice', 'fishtts', 'tencent',
                            'doubao', 'azuretts'])
parser.add_argument('--REF_FILE', type=str,
                    default="zh-CN-YunxiaNeural")
parser.add_argument('--REF_TEXT', type=str, default=None)
parser.add_argument('--TTS_SERVER', type=str,
                    default='http://127.0.0.1:9880')
```

### 环境变量

```bash
# 腾讯云TTS
TENCENT_APPID
TENCENT_SECRET_KEY
TENCENT_SECRET_ID

# 字节豆包TTS
DOUBAO_APPID
DOUBAO_TOKEN

# Azure TTS
AZURE_SPEECH_KEY
AZURE_TTS_REGION
```

### TTS选择矩阵

| TTS | 部署方式 | 需要API密钥 | 声音克隆 | 流式输出 | 延迟 | 适用场景 |
|-----|---------|------------|---------|---------|-----|---------|
| EdgeTTS | 云服务 | ❌ | ❌ | ❌ | 200ms | 快速原型、中文对话 |
| GPT-SoVITS | 本地 | ❌ | ✅ | ✅ | 150ms | 自定义音色、隐私保护 |
| CosyVoice | 本地 | ❌ | ✅ | ✅ | 180ms | 零样本克隆 |
| FishTTS | 云/本地 | ✅ | ✅ | ✅ | 120ms | 高质量语音 |
| XTTS | 本地 | ❌ | ✅ | ✅ | 200ms | 多语言支持 |
| TencentTTS | 云服务 | ✅ | ❌ | ✅ | 100ms | 商用场景、稳定性 |
| DoubaoTTS | 云服务 | ✅ | ❌ | ✅ | 80ms | 低延迟对话 |
| AzureTTS | 云服务 | ✅ | ❌ | ✅ | 100ms | 企业级应用 |

## 性能分析

### 延迟构成

```
文本到音频播放的总延迟:

1. TTS生成延迟
   - EdgeTTS: 150-250ms (非流式，需等待完整音频)
   - GPT-SoVITS: 100-200ms (流式，首字延迟)
   - DoubaoTTS: 50-100ms (WebSocket, 最低延迟)

2. 网络传输延迟
   - 本地服务: 5-10ms
   - 云服务: 20-80ms (取决于地理位置)

3. 音频处理延迟
   - 重采样: 1-3ms (resampy)
   - 分帧: <1ms

4. WebRTC传输延迟
   - 编码: 5-10ms (Opus)
   - 传输: 20-50ms (取决于网络)

总延迟: 100-400ms
```

### chunk_size 计算

不同TTS的 `chunk_size` 设计：

```python
# FishTTS - 44100 Hz
chunk_size = 17640 bytes
samples = 17640 / 2 = 8820 samples  # int16 = 2 bytes
duration = 8820 / 44100 = 200ms

# CosyVoice/XTTS - 24000 Hz
chunk_size = 9600 bytes
samples = 9600 / 2 = 4800 samples
duration = 4800 / 24000 = 200ms

# TencentTTS/DoubaoTTS - 16000 Hz
chunk_size = 6400 bytes
samples = 6400 / 2 = 3200 samples
duration = 3200 / 16000 = 200ms
```

统一目标：**200ms 音频块**，减少网络请求次数。

### 内存占用

单个音频帧 (20ms @ 16kHz):
```
320 samples × 4 bytes (float32) = 1.28 KB
转换后: 320 samples × 2 bytes (int16) = 640 bytes
```

1秒音频内存占用:
```
float32: 16000 × 4 = 64 KB
int16:   16000 × 2 = 32 KB
```

## 扩展新TTS

### 实现步骤

1. 继承 `BaseTTS` 类
2. 实现 `txt_to_audio(msg)` 方法
3. 返回 16kHz, float32 音频流
4. 按 320 samples/帧输出

### 实现模板

```python
# ttsreal.py
class NewTTS(BaseTTS):
    def __init__(self, opt, parent):
        super().__init__(opt, parent)
        # 初始化TTS特定参数
        self.api_key = os.getenv('NEW_TTS_API_KEY')

    def txt_to_audio(self, msg):
        text, textevent = msg

        # 1. 调用TTS API
        audio_stream = self._call_tts_api(text)

        # 2. 转换为 numpy 数组 (float32)
        stream = np.frombuffer(audio_stream, dtype=np.int16)
        stream = stream.astype(np.float32) / 32767.0

        # 3. 重采样到 16kHz (如果需要)
        if original_sample_rate != 16000:
            stream = resampy.resample(
                x=stream,
                sr_orig=original_sample_rate,
                sr_new=16000
            )

        # 4. 分帧输出
        idx = 0
        streamlen = stream.shape[0]
        while streamlen >= self.chunk:
            eventpoint = None
            if idx == 0:
                eventpoint = {'status':'start', 'text':text,
                             'msgevent':textevent}
            elif streamlen < self.chunk:
                eventpoint = {'status':'end', 'text':text,
                             'msgevent':textevent}

            self.parent.put_audio_frame(
                stream[idx:idx+self.chunk], eventpoint)
            idx += self.chunk
            streamlen -= self.chunk

    def _call_tts_api(self, text):
        # 实现具体的TTS API调用
        pass
```

### 注册到系统

```python
# basereal.py:77-90
if opt.tts == "newtts":
    self.tts = NewTTS(opt, self)
```

```python
# app.py:419
parser.add_argument('--tts', type=str, default='edgetts',
                    choices=[..., 'newtts'])
```

## 故障排查

### 常见问题

**1. TTS无声音输出**
- 检查 `self.msgqueue` 是否为空
- 确认 `process_tts` 线程是否运行
- 验证 TTS API 返回状态

**2. 音频卡顿**
- 检查采样率转换是否正确
- 确认 chunk_size 计算
- 监控队列堆积情况

**3. 延迟过高**
- 使用流式TTS (非 EdgeTTS)
- 减少网络往返 (本地部署)
- 优化 chunk_size (200ms vs 20ms)

**4. 音质问题**
- 检查重采样质量 (resampy vs scipy)
- 确认 int16 转换范围 (-32768 ~ 32767)
- 验证原始音频质量

### 调试日志

```python
# 添加日志输出
import logging

def txt_to_audio(self, msg):
    text, textevent = msg
    logging.info(f"TTS processing: {text[:50]}...")

    start_time = time.time()
    # ... TTS处理 ...

    elapsed = time.time() - start_time
    logging.info(f"TTS latency: {elapsed*1000:.1f}ms")
```

## 参考资料

- Edge TTS: https://github.com/rany2/edge-tts
- GPT-SoVITS: https://github.com/RVC-Boss/GPT-SoVITS
- CosyVoice: https://github.com/FunAudioLLM/CosyVoice
- XTTS: https://github.com/coqui-ai/TTS
- 腾讯云TTS文档: https://cloud.tencent.com/document/product/1073
- 豆包TTS文档: https://www.volcengine.com/docs/6561/79820
