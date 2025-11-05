# 数字人模型实现

## 数字人模型实现

### LipReal - Wav2Lip实现

位置: `lipreal.py`

基于Wav2Lip模型的数字人实现。

#### 模型加载
```python
# lipreal.py:58-69
load_model(path) -> Wav2Lip
load_avatar(avatar_id) -> (frame_list, face_list, coord_list)
```

Avatar结构:
```
data/avatars/{avatar_id}/
├── full_imgs/      # 完整帧图像序列
├── face_imgs/      # 裁剪的面部图像序列
└── coords.pkl      # 面部坐标数据
```

#### 推理流程

LipReal类核心方法:
- `init_facerender()`: 初始化面部渲染
- `inference()`: 模型推理，输入mel频谱和面部图像
- `paste_back_frame()`: 将推理结果贴回完整帧

ASR使用: `LipASR` (lipasr.py)

特征提取: Mel频谱 (80维)

模型输入尺寸: 256x256

### MuseReal - MuseTalk实现

位置: `musereal.py`

基于MuseTalk模型的数字人实现。

#### 模型加载
```python
# musereal.py:51-63
load_model() -> (vae, unet, pe, timesteps, audio_processor)
load_avatar(avatar_id) -> (frames, masks, coords, mask_coords, latents)
```

Avatar结构:
```
data/avatars/{avatar_id}/
├── full_imgs/          # 完整帧
├── mask/               # mask图像
├── coords.pkl          # 坐标
├── mask_coords.pkl     # mask坐标
└── latents.pt          # 预计算的latent向量
```

#### 推理流程

核心组件:
- **VAE**: 图像编解码
- **UNet**: 扩散模型推理
- **PE**: 位置编码
- **Audio2Feature**: Whisper音频特征提取

推理过程:
1. Whisper提取音频特征
2. 通过UNet生成latent
3. VAE解码为图像
4. 使用mask和coords贴回完整帧

ASR使用: `MuseASR` (museasr.py)

特征维度: Whisper Tiny模型特征

### LightReal - Ultralight实现

位置: `lightreal.py`

基于Ultralight-Digital-Human的轻量级实现。

#### 模型加载
```python
# lightreal.py:62-85
load_model(opt) -> audio_processor
load_avatar(avatar_id) -> (model, frames, faces, coords)
```

Avatar结构:
```
data/avatars/{avatar_id}/
├── full_imgs/          # 完整帧
├── face_imgs/          # 面部图像
├── coords.pkl          # 坐标
└── ultralight.pth      # 训练好的模型权重
```

#### 推理流程

核心组件:
- **Model(UNet)**: 轻量级UNet模型
- **Audio2Feature**: Hubert音频特征提取

推理过程:
1. Hubert提取音频特征
2. UNet生成面部图像
3. 贴回完整帧

ASR使用: `HubertASR` (hubertasr.py)

特征维度: Hubert特征 (32x32x32)

模型输入尺寸: 160x160
