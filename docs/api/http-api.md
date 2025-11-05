# API接口文档

## 服务器配置

默认监听: `0.0.0.0:8010`

CORS: 允许所有域名跨域访问

## WebRTC相关接口

### POST /offer

建立WebRTC连接。

位置: app.py:85-142

#### 请求

```json
{
  "sdp": "v=0\r\no=...",  // SDP描述
  "type": "offer"          // 固定为"offer"
}
```

#### 响应

成功 (200):
```json
{
  "sdp": "v=0\r\no=...",   // 服务端SDP
  "type": "answer",         // 固定为"answer"
  "sessionid": 123456      // 6位session ID
}
```

失败:
```json
{
  "code": -1,
  "msg": "reach max session"  // 达到最大并发数
}
```

#### 处理流程

1. 生成随机6位sessionid
2. 创建BaseReal实例（根据opt.model）
3. 建立RTCPeerConnection
4. 添加音频/视频轨道
5. 设置H264/VP8编解码器优先级
6. 创建answer并返回

#### 连接状态回调

```python
# app.py:108-118
@pc.on("connectionstatechange")
async def on_connectionstatechange():
    # "failed" 或 "closed" 时清理资源
    del nerfreals[sessionid]
```

## 交互接口

### POST /human

发送文本消息给数字人。

位置: app.py:144-171

#### 请求

```json
{
  "sessionid": 123456,     // 会话ID
  "type": "echo",          // "echo" 或 "chat"
  "text": "你好",          // 文本内容
  "interrupt": false       // 可选，是否中断当前说话
}
```

#### 响应

```json
{
  "code": 0,
  "msg": "ok"
}
```

#### type字段说明

- `"echo"`: 直接TTS播报文本
- `"chat"`: 通过LLM生成回复后播报

#### interrupt字段

设置为`true`时调用`flush_talk()`中断当前说话。

### POST /interrupt_talk

主动中断数字人当前说话。

位置: app.py:173-193

#### 请求

```json
{
  "sessionid": 123456
}
```

#### 响应

```json
{
  "code": 0,
  "msg": "ok"
}
```

### POST /humanaudio

上传音频文件给数字人处理。

位置: app.py:195-217

#### 请求

Content-Type: `multipart/form-data`

表单字段:
- `sessionid`: 会话ID (整数)
- `file`: 音频文件 (支持多种格式，自动重采样到16kHz)

#### 响应

```json
{
  "code": 0,
  "msg": "ok"
}
```

#### 处理流程

1. 读取音频文件字节
2. 调用`put_audio_file()`
3. 自动切分为20ms chunks
4. 进入ASR处理流程

## 状态管理接口

### POST /set_audiotype

切换数字人自定义状态/视频。

位置: app.py:219-239

#### 请求

```json
{
  "sessionid": 123456,
  "audiotype": 2,         // 自定义状态ID
  "reinit": true          // 是否重置播放进度
}
```

#### 响应

```json
{
  "code": 0,
  "msg": "ok"
}
```

#### audiotype说明

- `0`: 默认状态（推理帧）
- `1`: 静音状态
- `>1`: 自定义视频状态（需在配置中定义）

### POST /is_speaking

查询数字人是否正在说话。

位置: app.py:266-275

#### 请求

```json
{
  "sessionid": 123456
}
```

#### 响应

```json
{
  "code": 0,
  "data": true  // true表示正在说话，false表示静音
}
```

## 录制接口

### POST /record

控制视频录制。

位置: app.py:241-264

#### 开始录制

```json
{
  "sessionid": 123456,
  "type": "start_record"
}
```

#### 停止录制

```json
{
  "sessionid": 123456,
  "type": "end_record"
}
```

#### 响应

```json
{
  "code": 0,
  "msg": "ok"
}
```

#### 输出文件

录制完成后生成: `data/record.mp4`

临时文件:
- `temp{sessionid}.mp4`: 视频流
- `temp{sessionid}.aac`: 音频流

## 静态文件服务

### GET /

静态文件根目录: `web/`

位置: app.py:404

#### 主要页面

- `/dashboard.html`: WebRTC集成控制台（推荐）
- `/webrtcapi.html`: WebRTC客户端
- `/rtcpushapi.html`: RTC推流客户端
- `/echoapi.html`: RTMP客户端

## RTMP推流模式

### 配置

```bash
python app.py --transport rtmp --push_url rtmp://localhost/live/livestream
```

### 流程

启动时自动调用`run()`函数建立连接:

位置: app.py:292-312

不需要客户端调用/offer接口，服务端主动推流。

## 错误处理

所有接口异常统一返回格式:

```json
{
  "code": -1,
  "msg": "error message"
}
```

位置: app.py中各接口的except块

## 客户端示例

### WebRTC连接流程

```javascript
// 1. 创建RTCPeerConnection
const pc = new RTCPeerConnection();

// 2. 添加本地轨道（如果需要）
// pc.addTrack(...)

// 3. 创建offer
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);

// 4. 发送offer到服务端
const response = await fetch('/offer', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    sdp: pc.localDescription.sdp,
    type: pc.localDescription.type
  })
});

const answer = await response.json();
const sessionid = answer.sessionid;

// 5. 设置远端描述
await pc.setRemoteDescription(
  new RTCSessionDescription({
    sdp: answer.sdp,
    type: answer.type
  })
);

// 6. 接收远端轨道
pc.ontrack = (event) => {
  if (event.track.kind === 'video') {
    videoElement.srcObject = event.streams[0];
  }
  if (event.track.kind === 'audio') {
    audioElement.srcObject = event.streams[0];
  }
};
```

参考: web/webrtcapi.html

### 发送文本

```javascript
await fetch('/human', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    sessionid: sessionid,
    type: 'echo',
    text: '你好',
    interrupt: false
  })
});
```

### 上传音频

```javascript
const formData = new FormData();
formData.append('sessionid', sessionid);
formData.append('file', audioBlob, 'audio.wav');

await fetch('/humanaudio', {
  method: 'POST',
  body: formData
});
```

## 性能监控

### 后端日志指标

- `inferfps`: GPU推理帧率
- `finalfps`: 最终推流帧率

两者均需 ≥25 才能保证实时性。

位置: 各Real类实现中的日志输出

### 客户端监控

WebRTC统计:
```javascript
const stats = await pc.getStats();
// 分析jitter、packetsLost、framesDecoded等
```

## 安全考虑

### 并发限制

```python
# app.py:349
parser.add_argument('--max_session', type=int, default=1)
```

超过限制返回错误，防止资源耗尽。

### Session隔离

每个sessionid对应独立的BaseReal实例，session间完全隔离。

### 文件上传大小

```python
# app.py:395
appasync = web.Application(client_max_size=1024**2*100)
```

最大上传100MB。

## 扩展API

### 自定义事件通知

BaseReal.notify()方法可被重写实现自定义事件处理:

```python
# basereal.py:168-169
def notify(self, eventpoint):
    logger.info("notify:%s", eventpoint)
```

eventpoint包含:
- `status`: 'start' / 'end'
- `text`: 当前文本
- 其他自定义字段

### Webhook支持

可在notify()中实现HTTP回调:
```python
def notify(self, eventpoint):
    if eventpoint.get('status') == 'start':
        requests.post(webhook_url, json=eventpoint)
```

## API版本

当前版本: v1 (隐含)

接口路径可能在未来版本添加`/v1/`前缀。
