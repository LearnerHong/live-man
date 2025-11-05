# ASR模块

## ASR模块

位置: `baseasr.py` 及各子类实现

### BaseASR基类

```python
# baseasr.py:28-88
class BaseASR:
    def __init__(self, opt, parent: BaseReal)
    def put_audio_frame(audio_chunk, datainfo)  # 接收音频
    def get_audio_frame()         # 获取音频帧
    def get_audio_out()           # 获取输出音频
    def get_next_feat()           # 获取特征(从feat_queue)
    def warm_up()                 # 预热
    def run_step()                # 特征提取步骤(子类实现)
```

### 滑动窗口机制

```python
# baseasr.py:42-45
self.stride_left_size = opt.l   # 左窗口大小
self.stride_right_size = opt.r  # 右窗口大小
```

用于平滑处理和上下文感知，默认配置: `-l 10 -m 8 -r 10`

### 音频数据类型

`get_audio_frame()` 返回: `(frame, type, eventpoint)`
- `type = 0`: 正常语音
- `type = 1`: 静音
- `type > 1`: 自定义音频类型

位置: baseasr.py:56-70

### ASR实现

#### 1. LipASR (Wav2Lip)
位置: `lipasr.py`

特征: Mel频谱
- 提取80维Mel频谱
- 帧窗口: 16帧 (对应16个20ms chunk)

#### 2. MuseASR (MuseTalk)
位置: `museasr.py`

特征: Whisper特征
- 使用Whisper Tiny模型
- 特征缓存和批处理

#### 3. HubertASR (Ultralight)
位置: `hubertasr.py`

特征: Hubert特征
- 使用HuBERT模型提取语音特征
- 输出形状: (32, 32, 32)
