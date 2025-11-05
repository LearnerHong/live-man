# BaseReal - 实时处理基类

## BaseReal - 实时处理基类

位置: `basereal.py`

所有数字人实现的基类，负责:
- TTS服务管理
- 音频流处理
- 自定义视频循环
- 视频录制
- 帧处理和输出

### 关键属性

```python
# basereal.py:71-109
self.opt                      # 配置选项
self.sample_rate = 16000      # 采样率
self.chunk = 320              # 每帧样本数 (20ms)
self.tts                      # TTS实例
self.speaking                 # 是否正在说话
self.recording                # 是否正在录制
self.curr_state               # 当前状态
self.custom_img_cycle         # 自定义视频帧
self.custom_audio_cycle       # 自定义音频
```

### 核心方法

#### put_msg_txt(msg, datainfo)
将文本消息发送到TTS队列进行语音合成。
位置: basereal.py:111-112

#### put_audio_frame(audio_chunk, datainfo)
接收16kHz 20ms PCM音频chunk，发送到ASR处理。
位置: basereal.py:114-115

#### put_audio_file(filebyte, datainfo)
接收完整音频文件字节流，自动切分为20ms chunk。
位置: basereal.py:117-125

#### flush_talk()
中断当前说话，清空TTS和ASR队列。
位置: basereal.py:143-145

#### process_frames(quit_event, loop, audio_track, video_track)
核心帧处理循环，从res_frame_queue获取推理结果，合成最终视频帧并输出。

处理流程:
1. 从`res_frame_queue`获取推理结果
2. 判断是否说话（audio_frames类型）
3. 说话: 调用paste_back_frame合成
4. 静音: 使用frame_list_cycle或自定义视频
5. 添加水印
6. 输出到WebRTC/虚拟摄像头

位置: basereal.py:300-401

#### 录制相关
- `start_recording()`: 启动FFmpeg子进程录制视频和音频
- `stop_recording()`: 停止录制并合并音视频
- `record_video_data()`: 写入视频帧
- `record_audio_data()`: 写入音频帧

位置: basereal.py:171-272

### 自定义视频支持

通过`opt.customopt`配置自定义动作视频:
```python
# basereal.py:150-159
{
  'audiotype': int,      # 状态ID
  'imgpath': str,        # 图像序列路径
  'audiopath': str       # 音频文件路径
}
```

切换状态: `set_custom_state(audiotype, reinit)`
