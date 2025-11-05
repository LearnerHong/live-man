import time
import os
import re
from basereal import BaseReal
from logger import logger

def clean_markdown(text):
    """清理 Markdown 格式标记，使文本适合 TTS 朗读"""
    if not text:
        return ""

    # 移除粗体标记 **text** 或 __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)

    # 移除斜体标记 *text* 或 _text_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)

    # 移除标题标记 ## text
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

    # 移除代码块标记 ```code```
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)

    # 移除链接标记 [text](url)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

    # 移除引用标记 > text
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # 移除列表标记
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # 移除水平分割线
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)

    return text.strip()

def llm_response(message,nerfreal:BaseReal):
    start = time.perf_counter()
    from openai import OpenAI
    client = OpenAI(
        # 如果您没有配置环境变量，请在此处用您的API Key进行替换
        api_key=os.getenv("DEEPSEEK_API_KEY", "sk-ffcd082bff2c475e851666c0d156fd44"),
        # 填写DeepSeek API的base_url
        base_url="https://api.deepseek.com",
    )
    end = time.perf_counter()
    logger.info(f"llm Time init: {end-start}s")
    completion = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{'role': 'system', 'content': 'You are a helpful assistant.'},
                  {'role': 'user', 'content': message}],
        stream=True,
        # 通过以下设置，在流式输出的最后一行展示token使用信息
        stream_options={"include_usage": True}
    )
    result=""
    full_response = ""  # 用于保存完整回复
    first = True
    for chunk in completion:
        if len(chunk.choices)>0:
            #print(chunk.choices[0].delta.content)
            if first:
                end = time.perf_counter()
                logger.info(f"llm Time to first chunk: {end-start}s")
                first = False
            msg = chunk.choices[0].delta.content
            full_response += msg  # 累积完整回复
            lastpos=0
            #msglist = re.split('[,.!;:，。！?]',msg)
            for i, char in enumerate(msg):
                if char in ",.!;:，。！？：；" :
                    result = result+msg[lastpos:i+1]
                    lastpos = i+1
                    if len(result)>10:
                        # 清理 Markdown 格式后再发送给 TTS
                        clean_result = clean_markdown(result)
                        logger.info(clean_result)
                        nerfreal.put_msg_txt(clean_result)
                        result=""
            result = result+msg[lastpos:]
    end = time.perf_counter()
    logger.info(f"llm Time to last chunk: {end-start}s")
    # 清理剩余文本的 Markdown 格式
    if result:
        clean_result = clean_markdown(result)
        nerfreal.put_msg_txt(clean_result)
    return full_response  # 返回完整回复（保留 Markdown 格式，用于前端显示）    