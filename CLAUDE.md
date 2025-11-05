# GUIDE FOR AI CODE ANALYSIS

This file provides guidance to ai code agent when working with code in this repository.

## 项目介绍

这个项目是一个基于WebRTC的实时交互流式数字人系统，主要用于实现数字人对话功能。

最终是要实现的一个信贷智能客服系统，用户可以与数字人进行对话，数字人会根据用户的问题给出回答。

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

1、当完成代码修改后，请自动执行以下命令：
```bash
git add <文件名> # 添加修改的文件
git commit -m "feat: 具体修改内容" # 提交（使用清晰的提交信息）
git push # 推送到远程
```

**提交规范：**
- 提交信息清晰描述修改内容
- 大功能修改时同步更新 `docs/` 目录
- 修改 API 时更新 API 文档

## 当然任务

1. 当前我们最核心优化的是 index.html 页面的UI和交互。