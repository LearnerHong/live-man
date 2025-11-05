# LLM模块

## LLM模块

位置: `llm.py`

### llm_response(message, nerfreal)

集成OpenAI兼容API进行对话。

配置:
- 环境变量: `DASHSCOPE_API_KEY`
- 默认模型: qwen-plus

流程:
1. 流式调用LLM API
2. 按标点符号切分回复
3. 每个片段通过`nerfreal.put_msg_txt()`发送到TTS
4. 实现边生成边播报

位置: llm.py:6-48

标点分割: `,.!;:，。！？：；`
