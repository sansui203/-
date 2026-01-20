# AI 资讯日报自动化系统

基于 GitHub Actions + 硅基流动 AI，完全按照 n8n 工作流实现的自动化资讯聚合系统。

## 数据源

| 来源 | 说明 | 筛选条件 |
|-----|------|---------|
| RSS | 纽约时报、TechCrunch、The Verge | 24小时内 |
| YouTube 博主 | 3个订阅频道 | 24小时内 |
| YouTube 热门 | 搜索 "AI" | 播放量 > 20万 |
| Twitter/X 热帖 | 搜索 "AI" | 浏览量 > 1万，热度 > 1000 |
| Twitter/X 账号 | OpenAI, GoogleDeepMind, GoogleAIStudio | 24小时内 |
| TikTok | 搜索 "AI" | 爆款算法筛选 |

## 需要配置的 API

在 GitHub 仓库的 `Settings → Secrets and variables → Actions` 中添加：

### Secrets（必填）

| Secret 名称 | 获取地址 | 说明 |
|------------|---------|------|
| `SILICONFLOW_API_KEY` | https://cloud.siliconflow.cn/ | 硅基流动 API Key |
| `YOUTUBE_API_KEY` | https://console.cloud.google.com/ | YouTube Data API |
| `TWITTER_API_KEY` | https://twitterapi.io/ | Twitter 数据 |
| `RAPIDAPI_KEY` | https://rapidapi.com/ | TikTok（可选） |

### Variables（可选）

| Variable 名称 | 默认值 | 说明 |
|--------------|-------|------|
| `SILICONFLOW_MODEL` | `deepseek-ai/DeepSeek-V3` | 模型选择 |

**可用模型**：
- `deepseek-ai/DeepSeek-V3`（默认，推荐）
- `deepseek-ai/DeepSeek-R1`
- `Qwen/Qwen2.5-72B-Instruct`
- `THUDM/glm-4-9b-chat`

### 获取 API Key

#### 1. 硅基流动 SiliconFlow
1. 访问 https://cloud.siliconflow.cn/
2. 注册/登录
3. 进入「API 密钥」页面
4. 创建新密钥，复制 `sk-...` 格式的 Key

#### 2. YouTube Data API
1. 访问 https://console.cloud.google.com/
2. 创建项目
3. 启用 "YouTube Data API v3"
4. 创建 API 密钥

#### 3. Twitter API (twitterapi.io)
1. 访问 https://twitterapi.io/
2. 注册获取 API Key

#### 4. TikTok API (RapidAPI)
1. 访问 https://rapidapi.com/tikwm-tikwm-default/api/tiktok-api23
2. 订阅 API
3. 复制 `X-RapidAPI-Key`

## 部署步骤

1. **Fork 本仓库**

2. **配置 Secrets**
   - Settings → Secrets and variables → Actions
   - 添加上述 API Key

3. **启用 GitHub Pages**
   - Settings → Pages
   - Source 选择 "GitHub Actions"

4. **运行**
   - Actions → AI 资讯日报 → Run workflow
   - 或等待每天北京时间 8:00 自动运行

5. **查看结果**
   - 访问 `https://你的用户名.github.io/仓库名/`

## 文件结构

```
├── .github/workflows/daily-ai-digest.yml  # 自动化配置
├── scripts/
│   ├── generate_digest.py                 # 数据采集 + AI 处理
│   └── generate_html.py                   # 网页生成
├── data/                                  # 数据存储
├── docs/                                  # 网页目录
└── requirements.txt                       # Python 依赖
```

## 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export SILICONFLOW_API_KEY="sk-..."
export YOUTUBE_API_KEY="..."
export TWITTER_API_KEY="..."
export RAPIDAPI_KEY="..."

# 可选：指定模型
export SILICONFLOW_MODEL="deepseek-ai/DeepSeek-V3"

# 运行
python scripts/generate_digest.py
python scripts/generate_html.py

# 预览
cd docs && python -m http.server 8000
```

## 成本估算

- 硅基流动: DeepSeek-V3 约 ¥0.5/天
- YouTube API: 免费（10,000 次/天）
- Twitter API: 按 twitterapi.io 定价
- TikTok API: 按 RapidAPI 定价
- GitHub: 免费
