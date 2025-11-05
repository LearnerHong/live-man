# WebRTC模块

## WebRTC模块

位置: `webrtc.py`

### PlayerStreamTrack

媒体流轨道类，管理音频/视频流输出。

```python
# webrtc.py:48-152
class PlayerStreamTrack(MediaStreamTrack):
    kind: 'audio' | 'video'
    _queue: asyncio.Queue     # 帧队列
    _timestamp: int           # 当前时间戳
```

#### 时间同步

音频: 20ms间隔 (16000 sample_rate)
```python
AUDIO_PTIME = 0.020
SAMPLE_RATE = 16000
```

视频: 40ms间隔 (25fps)
```python
VIDEO_PTIME = 0.040
VIDEO_CLOCK_RATE = 90000
```

位置: webrtc.py:30-35

#### next_timestamp()
计算下一帧时间戳并控制发送速率。

位置: webrtc.py:68-108

#### recv()
异步获取下一帧，设置PTS和time_base。

位置: webrtc.py:110-146

### HumanPlayer

数字人播放器，连接BaseReal和WebRTC轨道。

```python
# webrtc.py:163-231
class HumanPlayer:
    __audio: PlayerStreamTrack
    __video: PlayerStreamTrack
    __container: BaseReal      # 关联的数字人实例
```

#### 工作线程

启动worker线程调用`BaseReal.render()`:
```python
# webrtc.py:203-214
player_worker_thread(
    quit_event, loop, container,
    audio_track, video_track
)
```

#### 事件通知

支持事件回调机制:
```python
# webrtc.py:181-182
def notify(self, eventpoint):
    self.__container.notify(eventpoint)
```
