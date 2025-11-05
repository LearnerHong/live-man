# WebRTC模块

## 架构概览

```
前端 (client.js)
    ↓ SDP Offer
app.py (/offer API)
    ↓
webrtc.py (PlayerStreamTrack)
    ↓
BaseReal.render()
    ↓ 音视频帧
WebRTC 传输 → 浏览器播放
```

## 后端实现 (webrtc.py)

### PlayerStreamTrack

媒体流轨道类，管理音频/视频流输出。

位置: `webrtc.py:48-152`

```python
class PlayerStreamTrack(MediaStreamTrack):
    kind: 'audio' | 'video'
    _queue: asyncio.Queue     # 帧队列
    _timestamp: int           # 当前时间戳
    _start: float            # 开始时间
```

#### 时间同步参数

```python
# webrtc.py:30-35
AUDIO_PTIME = 0.020        # 音频: 20ms间隔
VIDEO_PTIME = 0.040        # 视频: 40ms间隔 (25fps)

SAMPLE_RATE = 16000        # 音频采样率
VIDEO_CLOCK_RATE = 90000   # 视频时钟频率 (RTP标准)
VIDEO_TIME_BASE = fractions.Fraction(1, VIDEO_CLOCK_RATE)
```

**采样数计算**:
```python
# 音频: 20ms @ 16kHz
SAMPLES_PER_FRAME = int(AUDIO_PTIME * SAMPLE_RATE)  # 320 samples

# 视频: 40ms @ 90kHz
samples = int(VIDEO_PTIME * VIDEO_CLOCK_RATE)  # 3600 ticks
```

#### next_timestamp()

计算下一帧时间戳并控制发送速率。

位置: `webrtc.py:68-108`

```python
async def next_timestamp(self) -> Tuple[int, float]:
    if self._timestamp is None:
        self._start = time.time()
        self._timestamp = 0

    if hasattr(self, "_throttle_playback"):
        # 节流模式: 等待到真实时间
        elapsed_time = time.time() - self._start
        samples = self._timestamp + samples_per_frame
        wait = (samples / sample_rate) - elapsed_time
        await asyncio.sleep(wait)
    else:
        # 非节流模式: 短暂等待避免CPU占用
        await asyncio.sleep(0.001)

    # 更新时间戳
    self._timestamp += samples_per_frame
    return self._timestamp, time_base
```

**节流模式**:
- `_throttle_playback=True`: 严格按帧率发送（避免网络拥塞）
- `_throttle_playback=False`: 尽快发送（低延迟，依赖网络缓冲）

#### recv()

异步获取下一帧，设置 PTS 和 time_base。

位置: `webrtc.py:110-146`

```python
async def recv(self):
    # 1. 从队列获取帧
    frame = await self._queue.get()
    if frame is None:
        self._ended = True
        raise MediaStreamError

    # 2. 计算时间戳
    timestamp, time_base = await self.next_timestamp()

    # 3. 设置帧属性
    frame.pts = timestamp
    frame.time_base = time_base

    return frame
```

**队列管理**:
```python
# 放入帧 (from BaseReal)
await audio_track._queue.put(audio_frame)

# 结束信号
await audio_track._queue.put(None)  # 触发 MediaStreamError
```

### HumanPlayer

数字人播放器，连接 BaseReal 和 WebRTC 轨道。

位置: `webrtc.py:163-231`

```python
class HumanPlayer:
    __audio: PlayerStreamTrack     # 音频轨道
    __video: PlayerStreamTrack     # 视频轨道
    __container: BaseReal          # 关联的数字人实例
    __ended: threading.Event       # 结束事件

    def __init__(self, container: BaseReal, opt):
        self.__container = container
        self.__audio = PlayerStreamTrack(
            self.__container, kind="audio", opt=opt)
        self.__video = PlayerStreamTrack(
            self.__container, kind="video", opt=opt)
```

#### 工作线程

启动 worker 线程调用 `BaseReal.render()`:

位置: `webrtc.py:203-214`

```python
def player_worker_thread(quit_event, loop, container,
                        audio_track, video_track):
    container.render(quit_event)

    # 发送结束信号
    asyncio.run_coroutine_threadsafe(
        audio_track._queue.put(None), loop)
    asyncio.run_coroutine_threadsafe(
        video_track._queue.put(None), loop)
```

**线程模型**:
```
主线程 (asyncio)
    ├─ WebRTC 事件循环
    └─ HTTP API 处理

Worker 线程
    └─ BaseReal.render() → 生成音视频帧
```

#### 事件通知

支持事件回调机制:

位置: `webrtc.py:181-182`

```python
def notify(self, eventpoint):
    self.__container.notify(eventpoint)
```

用于传递 TTS 事件、ASR 事件等。

## 前端实现 (client.js)

### WebRTC 连接流程

位置: `web/client.js:45-130`

```javascript
// 1. 创建 RTCPeerConnection
function start() {
    var config = {
        sdpSemantics: 'unified-plan'
    };

    // 可选: 使用 STUN 服务器
    if (document.getElementById('use-stun').checked) {
        config.iceServers = [
            { urls: ['stun:stun.l.google.com:19302'] }
        ];
    }

    pc = new RTCPeerConnection(config);

    // 2. 添加媒体接收器
    pc.addTransceiver('audio', { direction: 'recvonly' });
    pc.addTransceiver('video', { direction: 'recvonly' });

    // 3. 监听媒体轨道
    pc.ontrack = function(evt) {
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
        }
    };

    // 4. 创建 SDP Offer
    pc.createOffer().then(function(offer) {
        return pc.setLocalDescription(offer);
    }).then(function() {
        // 5. 发送 Offer 到服务器
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: pc.localDescription.sdp,
                type: pc.localDescription.type,
                video_transform: 'none'
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then(function(response) {
        return response.json();
    }).then(function(answer) {
        // 6. 设置 SDP Answer
        return pc.setRemoteDescription(answer);
    });
}
```

### SDP 交换流程

```
客户端                          服务器
  |                              |
  | 1. createOffer()             |
  |-------------------------------->
  |    sdp: v=0...              |
  |    type: "offer"            |
  |                              |
  |                              | 2. 创建 RTCPeerConnection
  |                              | 3. setRemoteDescription(offer)
  |                              | 4. createAnswer()
  |                              |
  |    sdp: v=0...              |
  |    type: "answer"           |
  |<--------------------------------
  |                              |
  | 5. setRemoteDescription()   |
  |                              |
  | 6. ICE 候选交换             |
  |<------------------------------->
  |                              |
  | 7. 媒体流传输               |
  |<================================
```

### ICE 候选处理

```javascript
// webrtc.py:259-286
pc.on("iceconnectionstatechange", async () => {
    if (pc.iceConnectionState === "failed") {
        await pc.setLocalDescription(await pc.createOffer({ iceRestart: true }));
    }
});
```

**ICE 状态转换**:
```
new → checking → connected → completed
                    ↓ (失败)
                  failed → (ICE restart)
```

## STUN/TURN 服务器

### STUN (Session Traversal Utilities for NAT)

**作用**: 发现客户端的公网 IP 和端口，用于 NAT 穿透。

**配置** (client.js:50-52):
```javascript
config.iceServers = [
    { urls: ['stun:stun.l.google.com:19302'] }
];
```

**工作流程**:
```
1. 客户端 → STUN服务器: Binding Request
   "我的公网地址是什么？"

2. STUN服务器 → 客户端: Binding Response
   "你的公网地址是 203.0.113.5:54321"

3. 客户端将公网地址添加到 ICE 候选列表

4. 双方交换 ICE 候选，尝试建立连接
```

**NAT 类型与穿透**:

| NAT 类型 | STUN 是否有效 | 说明 |
|---------|-------------|------|
| Full Cone | ✅ | 任何外部主机可访问，STUN 足够 |
| Restricted Cone | ✅ | 限制源 IP，STUN 足够 |
| Port Restricted Cone | ✅ | 限制源 IP 和端口，STUN 足够 |
| Symmetric | ❌ | 每个目标不同端口，需要 TURN |

### TURN (Traversal Using Relays around NAT)

**作用**: 当 STUN 无法穿透时，作为中继服务器转发数据。

**配置示例**:
```javascript
config.iceServers = [
    {
        urls: ['stun:stun.example.com:3478']
    },
    {
        urls: ['turn:turn.example.com:3478'],
        username: 'user',
        credential: 'password'
    }
];
```

**数据流对比**:
```
# 直连 (STUN)
客户端A ←--直接连接--→ 客户端B

# 中继 (TURN)
客户端A → TURN服务器 → 客户端B
```

**成本**:
- STUN: 免费公共服务，仅用于连接建立
- TURN: 需要自建或付费，中继所有媒体流量（带宽成本高）

### 公共 STUN 服务器

```javascript
// Google
stun:stun.l.google.com:19302
stun:stun1.l.google.com:19302
stun:stun2.l.google.com:19302

// Mozilla
stun:stun.services.mozilla.com:3478

// Twilio
stun:global.stun.twilio.com:3478
```

## 后端 API (app.py)

### /offer 端点

位置: `app.py:121-236`

```python
@app.route('/offer', methods=['POST'])
async def offer():
    params = await request.get_json()

    # 1. 解析客户端 SDP
    offer = RTCSessionDescription(sdp=params['sdp'],
                                  type=params['type'])

    # 2. 创建 RTCPeerConnection
    pc = RTCPeerConnection()
    pcs.add(pc)

    # 3. 创建 HumanPlayer
    player = HumanPlayer(
        container=nerfreal,  # BaseReal 实例
        opt=opt
    )

    # 4. 添加媒体轨道
    pc.addTrack(player.audio)
    pc.addTrack(player.video)

    # 5. 设置远程描述
    await pc.setRemoteDescription(offer)

    # 6. 创建 Answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # 7. 返回 SDP Answer
    return jsonify({
        'sdp': pc.localDescription.sdp,
        'type': pc.localDescription.type
    })
```

### Session 管理

位置: `app.py:78-95`

```python
# 全局变量
pcs = set()                           # RTCPeerConnection 集合
nerfreals: Dict[int, BaseReal] = {}   # sessionid → BaseReal 映射

# 连接关闭处理
@pc.on("connectionstatechange")
async def on_connectionstatechange():
    if pc.connectionState == "failed":
        await pc.close()
        pcs.discard(pc)
```

## 媒体流处理

### 音频流

**参数**:
- 采样率: 16000 Hz
- 通道数: 1 (单声道)
- 格式: int16 PCM
- 帧大小: 320 samples (20ms)

**代码路径**:
```python
# basereal.py:163-186
def put_audio_frame(self, audio_chunk):
    audio_chunk = (audio_chunk * 32767).astype(np.int16)

    # 放入队列
    self.audioplayer.put_audio_frame(audio_chunk)
```

**队列流转**:
```
TTS → BaseReal.put_audio_frame()
        ↓
    AudioPlayer.put_audio_frame()
        ↓
    PlayerStreamTrack._queue
        ↓
    WebRTC 传输
```

### 视频流

**参数**:
- 帧率: 25 fps (40ms/帧)
- 格式: YUV420p
- 分辨率: 由模型决定 (如 512x512)

**代码路径**:
```python
# musereal.py / lipreal.py
def get_video_frame(self):
    # 渲染数字人
    frame = self.render_frame()

    # 转换为 av.VideoFrame
    video_frame = av.VideoFrame.from_ndarray(
        frame, format='rgb24')

    return video_frame
```

**编码**:
- WebRTC 自动使用 VP8/VP9 或 H.264 编码
- 由 aiortc 库处理

## 性能优化

### 延迟优化

**总延迟构成**:
```
TTS 生成: 100-300ms
    ↓
音频编码: 5-10ms
    ↓
网络传输: 20-100ms (取决于网络)
    ↓
解码播放: 10-30ms
---
总计: 135-440ms
```

**优化措施**:
1. 使用流式 TTS (非 EdgeTTS)
2. 禁用节流模式 (`_throttle_playback=False`)
3. 减少队列深度
4. 使用本地 STUN/TURN 服务器

### 带宽优化

**音频**:
```
16kHz, 16bit, 单声道
= 16000 * 2 bytes/s = 32 KB/s = 256 kbps (未压缩)
Opus 编码后: 约 32 kbps
```

**视频**:
```
512x512, 25fps, RGB24
= 512 * 512 * 3 * 25 = 19.66 MB/s (未压缩)
VP8 编码后: 约 500-1500 kbps (取决于质量)
```

**总带宽**: 约 0.5-2 Mbps

### 队列管理

```python
# webrtc.py:110-146
async def recv(self):
    frame = await self._queue.get()

    # 限制队列深度，避免延迟累积
    if self._queue.qsize() > MAX_QUEUE_SIZE:
        # 丢弃旧帧
        await self._queue.get()
```

## 故障排查

### 连接失败

**症状**: ICE 连接状态为 `failed`

**原因**:
1. 防火墙阻止 UDP 端口
2. Symmetric NAT 无法穿透
3. STUN 服务器不可达

**解决**:
1. 检查防火墙设置
2. 配置 TURN 服务器
3. 使用企业级 TURN 服务 (如 Twilio, Agora)

### 音视频不同步

**症状**: 嘴型与声音对不上

**原因**:
1. 时间戳计算错误
2. 帧率不匹配
3. 队列堆积

**解决**:
```python
# 检查时间戳
print(f"Audio PTS: {audio_frame.pts}, time_base: {audio_frame.time_base}")
print(f"Video PTS: {video_frame.pts}, time_base: {video_frame.time_base}")

# 确保帧率一致
assert AUDIO_PTIME == 0.020
assert VIDEO_PTIME == 0.040
```

### 延迟过高

**症状**: 说话后 1-2 秒才有反应

**排查**:
```javascript
// 浏览器控制台
console.log('ICE 状态:', pc.iceConnectionState);
console.log('连接状态:', pc.connectionState);

// 查看统计
pc.getStats().then(stats => {
    stats.forEach(report => {
        if (report.type === 'inbound-rtp' && report.kind === 'audio') {
            console.log('音频延迟:', report.jitter);
        }
    });
});
```

**优化**:
1. 使用本地 STUN 服务器
2. 减少 TTS 延迟（使用豆包/腾讯云）
3. 启用硬件加速

### 卡顿和丢帧

**症状**: 视频播放不流畅

**原因**:
1. 网络抖动
2. CPU 占用过高
3. 队列溢出

**解决**:
```python
# 监控队列深度
if audio_track._queue.qsize() > 10:
    print("WARNING: 音频队列堆积!")

# 限制渲染帧率
time.sleep(0.04)  # 25fps
```

## 安全性

### HTTPS 要求

WebRTC 的 `getUserMedia` (麦克风/摄像头) 必须在安全上下文中使用：

- ✅ `https://example.com`
- ✅ `http://localhost`
- ✅ `http://127.0.0.1`
- ❌ `http://192.168.1.x` (非 localhost 的 HTTP)

**生产环境配置**:
```bash
# 使用 Nginx 代理
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8010;
    }
}
```

### CORS 配置

位置: `app.py:97-103`

```python
@app.after_request
async def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    return response
```

生产环境应限制 Origin：
```python
response.headers.add('Access-Control-Allow-Origin', 'https://yourdomain.com')
```

## 配置示例

### 局域网测试

```javascript
// client.js
var config = {
    sdpSemantics: 'unified-plan'
    // 不配置 iceServers
};
```

### 公网部署

```javascript
// client.js
var config = {
    sdpSemantics: 'unified-plan',
    iceServers: [
        {
            urls: ['stun:stun.l.google.com:19302']
        },
        {
            urls: ['turn:your-turn-server.com:3478'],
            username: 'your-username',
            credential: 'your-password'
        }
    ]
};
```

### 企业网络

```javascript
// 使用企业内部 STUN/TURN
var config = {
    sdpSemantics: 'unified-plan',
    iceServers: [
        {
            urls: [
                'stun:stun.company.internal:3478',
                'turn:turn.company.internal:3478'
            ],
            username: 'employee',
            credential: 'secret'
        }
    ],
    iceTransportPolicy: 'relay'  // 强制使用 TURN 中继
};
```

## 参考资料

- WebRTC 规范: https://www.w3.org/TR/webrtc/
- aiortc 文档: https://aiortc.readthedocs.io/
- STUN/TURN 协议: RFC 5389, RFC 5766
- SDP 格式: RFC 4566
- ICE 协议: RFC 8445
