# TTS模块

## TTS模块

位置: `ttsreal.py`

### BaseTTS基类

```python
# ttsreal.py:54-91
class BaseTTS:
    def __init__(self, opt, parent: BaseReal)
    def flush_talk()              # 中断当前TTS
    def put_msg_txt(msg, datainfo) # 添加文本到队列
    def process_tts(quit_event)    # TTS处理循环
    def txt_to_audio(msg)          # 文本转音频(子类实现)
```

### TTS服务实现

#### 1. EdgeTTS
微软Edge浏览器TTS服务，免费无需API密钥。

位置: ttsreal.py:94-158

配置:
- `REF_FILE`: 语音模型ID (如 zh-CN-YunxiaNeural)

#### 2. GPT-SoVITS
开源TTS，支持声音克隆。

位置: ttsreal.py:238-334

配置:
- `TTS_SERVER`: 服务地址
- `REF_FILE`: 参考音频路径
- `REF_TEXT`: 参考文本

#### 3. XTTS
Coqui XTTS，支持多语言声音克隆。

位置: ttsreal.py:852-927

配置:
- `TTS_SERVER`: 服务地址
- `REF_FILE`: 参考音频路径

#### 4. CosyVoice
阿里巴巴CosyVoice TTS。

位置: ttsreal.py:337-402

配置:
- `TTS_SERVER`: 服务地址
- `REF_FILE`: 参考音频路径
- `REF_TEXT`: 参考文本

#### 5. FishTTS
Fish Audio TTS服务。

位置: ttsreal.py:160-235

配置:
- `TTS_SERVER`: 服务地址
- `REF_FILE`: reference_id

#### 6. TencentTTS
腾讯云语音合成服务。

位置: ttsreal.py:410-528

配置:
- 环境变量: `TENCENT_APPID`, `TENCENT_SECRET_KEY`, `TENCENT_SECRET_ID`
- `REF_FILE`: voice_type (整数ID)

#### 7. DoubaoTTS (火山引擎)
字节跳动豆包TTS服务。

位置: ttsreal.py:533-660

配置:
- 环境变量: `DOUBAO_APPID`, `DOUBAO_TOKEN`
- `REF_FILE`: voice_type

#### 8. IndexTTS2
IndexTTS2 Gradio服务。

位置: ttsreal.py:663-849

特性:
- 支持长文本自动分句
- 情感控制
- 支持情感参考音频

配置:
- `TTS_SERVER`: Gradio服务地址
- `REF_FILE`: 参考音频路径

#### 9. AzureTTS
微软Azure语音服务。

位置: ttsreal.py:930-985

配置:
- 环境变量: `AZURE_SPEECH_KEY`, `AZURE_TTS_REGION`
- `REF_FILE`: 语音模型名称 (如 zh-CN-XiaoxiaoMultilingualNeural)

### TTS处理流程

```
文本消息 → msgqueue
           ↓
    process_tts线程
           ↓
    txt_to_audio() → TTS API调用
           ↓
    音频流chunk (16kHz PCM)
           ↓
    parent.put_audio_frame() → ASR队列
```

### 事件同步

TTS支持事件标记:
```python
eventpoint = {
    'status': 'start',  # or 'end'
    'text': text,
    ...custom_fields
}
```

事件随音频帧传递，用于字幕同步等功能。
