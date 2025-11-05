# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 相关文档

## 快速启动

### 基础启动命令

**Wav2Lip 模型**
```bash
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
```

**MuseTalk 模型（高质量）：**
```bash
python app.py --transport webrtc --model musetalk --avatar_id avator_1 --batch_size 16
```

**Ultralight 模型：**
```bash
python app.py --transport webrtc --model ultralight --avatar_id <avatar_id>
```

**自定义 TTS：**
```bash
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 \
  --tts gpt-sovits --TTS_SERVER http://127.0.0.1:9880 --REF_FILE reference.wav
```

### 访问地址
- 对话主页: `http://<serverip>:8010/index.html`

## 核心架构速览

```
app.py (Web服务层)
├─ WebRTC 连接管理
├─ Session 管理 (nerfreals: Dict[sessionid, BaseReal])
└─ HTTP API (/offer, /human, /record 等)
    ↓
BaseReal (抽象基类 - basereal.py)
├─ TTS 模块 (ttsreal.py)
├─ ASR 模块 (baseasr.py)
└─ 音视频缓冲队列
    ↓
具体实现 (musereal.py / lipreal.py / lightreal.py)
    ↓
WebRTC 传输层 (webrtc.py)
```

**数据流**: 文本 → LLM → TTS → ASR → 模型推理 → WebRTC推送  
详见: [docs/guides/dataflow.md](./docs/guides/dataflow.md)

### 开发流程
1、当完成代码修改后，请手动执行以下命令：
```bash
git add <文件名> # 添加修改的文件
git commit -m "feat: 具体修改内容" # 提交（使用清晰的提交信息）
git push # 推送到远程
```

**提交规范：**
- 提交信息清晰描述修改内容
- 大功能修改时同步更新 `docs/` 目录
- 修改 API 时更新 API 文档