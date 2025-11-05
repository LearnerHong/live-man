# 数据流与处理流程

## 整体数据流

```
用户输入
   ↓
┌─────────────────────────────────────────┐
│          输入层 (app.py)                │
│  文本 → /human                          │
│  音频 → /humanaudio                     │
└─────────────────────────────────────────┘
   ↓                        ↓
文本路径                    音频路径
   ↓                        ↓
[TTS层]                  [ASR层]
   ↓                        ↓
音频chunk(16kHz,20ms) ← ← ← ┘
   ↓
[特征提取]
   ↓
特征queue (feat_queue)
   ↓
[数字人模型推理]
   ↓
推理结果queue (res_frame_queue)
   ↓
[帧合成处理]
   ↓
WebRTC Track输出
   ↓
客户端播放
```

## 详细处理流程

### 1. 文本输入流程

#### 1.1 Echo模式

```
客户端 POST /human {type:"echo", text:"你好"}
         ↓
  app.py:153 nerfreals[sessionid].put_msg_txt(text)
         ↓
  BaseReal.put_msg_txt() → self.tts.put_msg_txt()
         ↓
  BaseTTS.msgqueue.put((text, datainfo))
         ↓
  TTS处理线程: process_tts()
         ↓
  txt_to_audio() 调用TTS API
         ↓
  音频流 → 切分为20ms chunks
         ↓
  parent.put_audio_frame(chunk, eventpoint)
         ↓
  BaseASR.queue.put((chunk, eventpoint))
```

位置:
- app.py:153
- basereal.py:111-112
- ttsreal.py:71-73, 79-86

#### 1.2 Chat模式

```
客户端 POST /human {type:"chat", text:"天气如何"}
         ↓
  app.py:155 异步调用llm_response()
         ↓
  llm.py:17 调用LLM API (流式)
         ↓
  按标点切分回复文本
         ↓
  nerfreal.put_msg_txt(分片)
         ↓
  进入TTS流程 (同Echo)
```

位置:
- app.py:155
- llm.py:6-48

### 2. 音频输入流程

```
客户端 POST /humanaudio {file: audio.wav}
         ↓
  app.py:202 nerfreals[sessionid].put_audio_file(bytes)
         ↓
  BaseReal.put_audio_file()
    → soundfile读取
    → 重采样到16kHz
    → 切分为20ms chunks
         ↓
  BaseReal.put_audio_frame(chunk) for each chunk
         ↓
  BaseASR.put_audio_frame(chunk, datainfo)
         ↓
  BaseASR.queue.put((chunk, datainfo))
```

位置:
- app.py:195-217
- basereal.py:117-141

### 3. ASR特征提取流程

#### 3.1 滑动窗口机制

```
音频帧序列: [f0, f1, f2, f3, f4, ...]
窗口配置: -l 10 -m 8 -r 10

当前窗口: [f0...f9] [f10...f17] [f18...f27]
            ↑左窗     ↑中间窗      ↑右窗

推理使用: 左窗 + 中间窗 + 右窗 = 28帧
输出对应: 中间窗的8帧

滑动步进: 8帧 (中间窗大小)
```

#### 3.2 特征提取子进程

以MuseASR为例:

```
主进程:
  BaseASR.queue.get() → 获取音频chunk
       ↓
  填充滑动窗口 self.frames[]
       ↓
  窗口满后 → self.input_queue.put(窗口数据)

子进程 (render_process):
  input_queue.get() → 获取窗口数据
       ↓
  Whisper特征提取 audio_processor.audio2feat()
       ↓
  feat_queue.put(特征) → 发送到主进程
       ↓
  output_queue.put(音频帧) → 输出音频
```

位置: museasr.py

其他ASR实现类似:
- LipASR: 提取Mel频谱
- HubertASR: 提取Hubert特征

### 4. 模型推理流程

#### 4.1 批处理推理

以MuseReal为例:

```
主循环 (render):
  batch_frames = []
  for i in range(batch_size):
      feat = asr.get_next_feat(block=True)
      batch_frames.append(feat)

  # 批量推理
  input_queue.put(batch_frames)

推理子进程 (inference_process):
  batch = input_queue.get()
       ↓
  whisper_chunks = torch.cat(batch)
       ↓
  latent_batch = pe(whisper_chunks)
       ↓
  for each frame in batch:
      audio_feat = latent_batch[i]
      video_feat = latents[frame_idx]

      # UNet推理
      latent = unet(video_feat, timesteps, audio_feat)

      # VAE解码
      frame = vae.decode(latent)

      output_queue.put((frame, frame_idx, audio_frames))
```

位置: musereal.py

#### 4.2 输出格式

推理输出到`res_frame_queue`:
```python
(
  res_frame,     # 推理生成的面部图像
  idx,           # 帧索引
  audio_frames   # 对应的音频帧列表
)
```

audio_frames格式:
```python
[
  (frame, type, eventpoint),
  ...
]
```

### 5. 帧合成流程

```
process_frames线程:
  res_frame, idx, audio_frames = res_frame_queue.get()
       ↓
  判断是否说话:
    if audio_frames全为静音 (type!=0):
        # 使用静音帧
        if 有自定义视频:
            frame = custom_img_cycle[idx]
        else:
            frame = frame_list_cycle[idx]
    else:
        # 合成说话帧
        frame = paste_back_frame(res_frame, idx)
       ↓
  添加水印: cv2.putText("LiveTalking", ...)
       ↓
  输出视频帧:
    new_frame = VideoFrame.from_ndarray(frame)
    video_track._queue.put((new_frame, None))
       ↓
  输出音频帧 (对应的audio_frames):
    for audio_frame in audio_frames:
        frame_s16 = (frame * 32767).astype(np.int16)
        audio_track._queue.put((frame_s16, eventpoint))
```

位置: basereal.py:300-401

### 6. WebRTC输出流程

#### 6.1 视频轨道

```
PlayerStreamTrack (video):
  recv() 被WebRTC调用
       ↓
  frame, eventpoint = await _queue.get()
       ↓
  pts, time_base = await next_timestamp()
    # pts根据VIDEO_PTIME (40ms) 递增
    # 控制发送速率25fps
       ↓
  frame.pts = pts
  frame.time_base = time_base
       ↓
  return frame
```

位置: webrtc.py:110-146

#### 6.2 音频轨道

```
PlayerStreamTrack (audio):
  recv() 被WebRTC调用
       ↓
  frame, eventpoint = await _queue.get()
       ↓
  if eventpoint:
      _player.notify(eventpoint)  # 触发事件
       ↓
  pts, time_base = await next_timestamp()
    # pts根据AUDIO_PTIME (20ms) 递增
       ↓
  frame.pts = pts
  frame.time_base = time_base
       ↓
  return frame
```

位置: webrtc.py:110-146

## 时序图

### 完整交互时序

```
Client          app.py         TTS        ASR       Model      WebRTC
  |               |             |          |          |          |
  |--POST /human->|             |          |          |          |
  |               |--put_txt--->|          |          |          |
  |               |             |          |          |          |
  |               |             |-TTS API->|          |          |
  |               |             |          |          |          |
  |               |             |--chunk-->|          |          |
  |               |             |          |--feat--->|          |
  |               |             |          |          |--推理--->|
  |               |             |          |          |          |
  |               |             |          |<--result-|          |
  |               |             |          |          |          |
  |<-------------------------------------------video frame------|
  |<-------------------------------------------audio frame------|
```

## 延迟分析

### TTS延迟

EdgeTTS示例:
```
POST请求 → TTS API → 首chunk返回 → 开始播放
   ↓          ↓           ↓
  0ms      50-200ms    100-500ms
```

位置: ttsreal.py中各TTS实现的日志

### 推理延迟

关键指标:
- `inferfps`: GPU推理帧率
- `finalfps`: 最终输出帧率

实时要求: 两者均 ≥ 25fps

批处理权衡:
- `batch_size`越大: 吞吐量高，延迟高
- `batch_size`越小: 延迟低，GPU利用率低

推荐配置:
- 3060: batch_size=8
- 3080Ti+: batch_size=16

### 端到端延迟

```
文本输入 → TTS首包 → 特征提取 → 推理 → 输出
   0ms      200ms      20ms       40ms    0ms

总延迟: ~260ms (TTS主导)
```

音频输入延迟更低（跳过TTS）:
```
音频 → 特征提取 → 推理 → 输出
0ms     20ms      40ms    0ms

总延迟: ~60ms
```

## 队列管理

### 队列大小配置

```python
# baseasr.py:45
self.feat_queue = mp.Queue(2)  # 特征队列: 最多2个batch

# webrtc.py:57
self._queue = asyncio.Queue()  # WebRTC队列: 无限制
```

### 队列清空（打断）

```
/interrupt_talk 或 /human {interrupt:true}
         ↓
  flush_talk()
         ↓
  self.tts.msgqueue.queue.clear()   # 清空待TTS文本
  self.asr.queue.queue.clear()       # 清空待处理音频
```

位置: basereal.py:143-145

## 同步机制

### 音视频同步

通过PTS (Presentation Timestamp) 实现:

音频:
```python
pts = timestamp_index * 320  # 320 samples per 20ms
time_base = 1/16000
```

视频:
```python
pts = timestamp_index * 3600  # 90000Hz * 0.04s
time_base = 1/90000
```

位置: webrtc.py:68-108

### 帧速率控制

```python
# webrtc.py:77-80
wait = self._start + self.current_frame_count * VIDEO_PTIME - time.time()
if wait > 0:
    await asyncio.sleep(wait)
```

确保精确25fps输出。

## 性能优化点

### 1. 模型权重共享

多session共享同一模型权重:
```python
# app.py:54-56
model = None    # 全局模型
avatar = None   # 全局avatar数据

# app.py:367-381
model = load_model()        # 启动时加载一次
avatar = load_avatar()
```

### 2. 批处理推理

收集batch_size个帧后批量推理:
```python
# musereal.py 推理循环
for _ in range(batch_size):
    feat = asr.get_next_feat()
    batch_feats.append(feat)

# 批量推理
results = model(batch_feats)
```

### 3. 预计算数据

#### MuseTalk latents
Avatar生成时预计算VAE编码:
```python
# data/avatars/{id}/latents.pt
input_latent_list_cycle = torch.load(latents_path)
```

跳过运行时VAE编码，节省推理时间。

### 4. 异步处理

关键操作使用异步:
```python
# app.py:100
nerfreal = await asyncio.get_event_loop().run_in_executor(
    None, build_nerfreal, sessionid
)
```

避免阻塞主事件循环。

### 5. 多进程特征提取

ASR特征提取在独立进程:
```python
# museasr.py
self.process = mp.Process(target=self.render_process)
self.process.start()
```

避免GIL限制，充分利用多核CPU。

## 错误处理

### 推理队列阻塞

```python
# musereal.py
try:
    res_frame, idx, audio_frame = self.res_frame_queue.get(
        block=True, timeout=1
    )
except queue.Empty:
    continue  # 跳过该帧
```

### TTS失败

```python
# ttsreal.py:101-103
if self.input_stream.getbuffer().nbytes <= 0:
    logger.error('edgetts err!!!!!')
    return  # 放弃该句
```

### WebRTC连接断开

```python
# app.py:108-118
@pc.on("connectionstatechange")
async def on_connectionstatechange():
    if pc.connectionState in ["failed", "closed"]:
        del nerfreals[sessionid]  # 清理资源
        gc.collect()
```

## 调试工具

### 队列状态监控

```python
logger.info(f"queue size: {self.queue.qsize()}")
logger.info(f"feat_queue size: {self.feat_queue.qsize()}")
```

### 帧率统计

```python
# webrtc.py:142-144
if self.framecount == 100:
    logger.info(f"avg fps: {self.framecount/self.totaltime:.4f}")
```

### 延迟测试

在关键路径添加时间戳:
```python
t0 = time.perf_counter()
# ... 处理 ...
logger.info(f"elapsed: {time.perf_counter()-t0:.4f}s")
```

参考: ttsreal.py和llm.py中的延迟日志
