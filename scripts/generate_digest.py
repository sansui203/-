#!/usr/bin/env python3
"""
AI 资讯聚合器 - 热加载版本
每个数据源独立运行，失败不影响其他
"""

import os
import json
import requests
import feedparser
from datetime import datetime, timedelta
from pathlib import Path


class AIDigestGenerator:
    def __init__(self):
        self.siliconflow_key = os.environ.get("SILICONFLOW_API_KEY")
        self.youtube_key = os.environ.get("YOUTUBE_API_KEY")
        self.twitter_key = os.environ.get("TWITTER_API_KEY")
        self.rapidapi_key = os.environ.get("RAPIDAPI_KEY")
        
        self.model = os.environ.get("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3")
        
        self.today = datetime.now()
        self.today_str = self.today.strftime("%Y-%m-%d")
        self.yesterday = self.today - timedelta(days=1)
        
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        self.all_items = []
        
        # 打印 API 状态
        print("📋 API 状态:")
        print(f"  - 硅基流动: {'✅' if self.siliconflow_key else '❌ 未配置'}")
        print(f"  - YouTube: {'✅' if self.youtube_key else '⚠️ 跳过'}")
        print(f"  - Twitter: {'✅' if self.twitter_key else '⚠️ 跳过'}")
        print(f"  - TikTok: {'✅' if self.rapidapi_key else '⚠️ 跳过'}")

    def safe_fetch(self, name, func):
        """安全执行数据获取，失败不影响其他"""
        try:
            func()
        except Exception as e:
            print(f"  ❌ {name} 失败: {e}")

    # ==================== RSS（无需 API）====================
    
    def fetch_rss(self):
        """获取 RSS 新闻"""
        print("\n📰 RSS 新闻...")
        
        sources = [
            ("https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/spotlight/artificial-intelligence/rss.xml", "纽约时报"),
            ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch"),
            ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "The Verge"),
        ]
        
        for url, name in sources:
            try:
                feed = feedparser.parse(url)
                count = 0
                for entry in feed.entries[:10]:
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub:
                        dt = datetime(*pub[:6])
                        if dt > self.yesterday:
                            self.all_items.append({
                                "标题": entry.get("title", ""),
                                "内容": entry.get("summary", "")[:200],
                                "日期": dt.isoformat(),
                                "来源": name,
                                "板块": "新闻",
                                "链接": entry.get("link", "")
                            })
                            count += 1
                print(f"  ✅ {name}: {count} 条")
            except Exception as e:
                print(f"  ❌ {name}: {e}")

    # ==================== YouTube 博主（RSS，无需 API）====================
    
    def fetch_youtube_rss(self):
        """获取 YouTube 博主更新"""
        print("\n📺 YouTube 博主...")
        
        channels = [
            "UCNJ1Ymd5yFuUPtn21xtRbbw",
            "UChpleBmo18P08aKCIgti38g", 
            "UCPjNBjflYl0-HQtUvOx0Ibw"
        ]
        
        for cid in channels:
            try:
                feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
                name = feed.feed.get("author", "YouTube")
                count = 0
                for entry in feed.entries[:3]:
                    pub = entry.get("published_parsed")
                    if pub:
                        dt = datetime(*pub[:6])
                        if dt > self.yesterday:
                            self.all_items.append({
                                "标题": entry.get("title", ""),
                                "内容": "",
                                "日期": dt.isoformat(),
                                "来源": name,
                                "板块": "油管博主",
                                "链接": entry.get("link", "")
                            })
                            count += 1
                print(f"  ✅ {name}: {count} 条")
            except Exception as e:
                print(f"  ❌ 频道 {cid[:8]}: {e}")

    # ==================== YouTube 热门（需要 API）====================
    
    def fetch_youtube_trending(self):
        """获取 YouTube 热门视频"""
        if not self.youtube_key:
            return
        
        print("\n🔥 YouTube 热门...")
        
        try:
            # 搜索
            r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
                "key": self.youtube_key,
                "part": "snippet",
                "q": "AI",
                "order": "relevance",
                "maxResults": 10,
                "regionCode": "US",
                "type": "video",
                "publishedAfter": self.yesterday.isoformat() + "Z"
            }, timeout=30)
            data = r.json()
            
            if "items" not in data:
                print(f"  ❌ {data.get('error', {}).get('message', '错误')}")
                return
            
            ids = [i["id"]["videoId"] for i in data["items"]]
            
            # 统计
            r2 = requests.get("https://www.googleapis.com/youtube/v3/videos", params={
                "key": self.youtube_key,
                "part": "statistics",
                "id": ",".join(ids)
            }, timeout=30)
            stats = {i["id"]: i["statistics"] for i in r2.json().get("items", [])}
            
            count = 0
            for item in data["items"]:
                vid = item["id"]["videoId"]
                views = int(stats.get(vid, {}).get("viewCount", 0))
                if views > 200000:
                    self.all_items.append({
                        "标题": item["snippet"]["title"],
                        "内容": item["snippet"]["description"][:150],
                        "日期": item["snippet"]["publishTime"],
                        "来源": "YouTube",
                        "板块": "YouTube热点",
                        "链接": f"https://youtube.com/watch?v={vid}"
                    })
                    count += 1
            print(f"  ✅ {count} 条 (播放量>20万)")
        except Exception as e:
            print(f"  ❌ {e}")

    # ==================== Twitter（需要 API）====================
    
    def fetch_twitter(self):
        """获取 Twitter 热门"""
        if not self.twitter_key:
            return
        
        print("\n🐦 Twitter 热门...")
        
        try:
            r = requests.get("https://api.twitterapi.io/twitter/tweet/advanced_search",
                headers={"x-api-key": self.twitter_key},
                params={"query": "AI", "queryType": "Top"},
                timeout=30)
            data = r.json()
            
            count = 0
            for t in data.get("tweets", []):
                views = t.get("viewCount", 0)
                heat = t.get("likeCount", 0) + t.get("retweetCount", 0) * 2
                if views > 10000 and heat > 1000:
                    self.all_items.append({
                        "标题": t.get("text", "")[:100],
                        "内容": t.get("text", ""),
                        "日期": t.get("createdAt", ""),
                        "来源": "Twitter",
                        "板块": "Twitter热点",
                        "链接": t.get("url", "")
                    })
                    count += 1
            print(f"  ✅ {count} 条")
        except Exception as e:
            print(f"  ❌ {e}")

    def fetch_twitter_accounts(self):
        """获取明星公司动态"""
        if not self.twitter_key:
            return
        
        print("\n🌟 明星公司动态...")
        
        for user in ["OpenAI", "GoogleDeepMind", "GoogleAIStudio"]:
            try:
                r = requests.get("https://api.twitterapi.io/twitter/user/last_tweets",
                    headers={"x-api-key": self.twitter_key},
                    params={"userName": user},
                    timeout=30)
                data = r.json()
                
                count = 0
                for t in data.get("data", {}).get("tweets", [])[:5]:
                    text = t.get("text", "")
                    if t.get("retweeted_tweet"):
                        text = f"(转发) {t['retweeted_tweet'].get('text', '')}"
                    self.all_items.append({
                        "标题": text[:100],
                        "内容": text,
                        "日期": t.get("createdAt", ""),
                        "来源": user,
                        "板块": "明星公司动态",
                        "链接": t.get("url", "")
                    })
                    count += 1
                print(f"  ✅ @{user}: {count} 条")
            except Exception as e:
                print(f"  ❌ @{user}: {e}")

    # ==================== TikTok（需要 API）====================
    
    def fetch_tiktok(self):
        """获取 TikTok 热门"""
        if not self.rapidapi_key:
            return
        
        print("\n🎵 TikTok 热门...")
        
        try:
            r = requests.get("https://tiktok-api23.p.rapidapi.com/api/search/general",
                headers={
                    "x-rapidapi-key": self.rapidapi_key,
                    "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
                },
                params={"keyword": "AI", "cursor": "0"},
                timeout=30)
            data = r.json()
            
            count = 0
            for item in data.get("data", []):
                d = item.get("item", {})
                plays = d.get("stats", {}).get("playCount", 0)
                followers = d.get("authorStats", {}).get("followerCount", 1)
                
                if plays > 100000 and plays / followers > 3:
                    ts = d.get("createTime", 0)
                    if ts and datetime.fromtimestamp(ts) > self.today - timedelta(days=14):
                        author = d.get("author", {})
                        self.all_items.append({
                            "标题": d.get("desc", "")[:100],
                            "内容": d.get("desc", ""),
                            "日期": datetime.fromtimestamp(ts).isoformat(),
                            "来源": "TikTok",
                            "板块": "TikTok热点",
                            "链接": f"https://tiktok.com/@{author.get('uniqueId', '')}/video/{d.get('id', '')}"
                        })
                        count += 1
            print(f"  ✅ {count} 条")
        except Exception as e:
            print(f"  ❌ {e}")

    # ==================== GitHub（无需 API）====================
    
    def fetch_github_trending(self):
        """获取 GitHub Trending（多个备用方案）"""
        print("\n⭐ GitHub Trending...")
        
        periods = [
            ("daily", "今日热门"),
            ("weekly", "本周热门")
        ]
        
        for period, label in periods:
            count = 0
            
            # 方案1: 尝试多个 Trending API
            # GitHub Search API 备用方案：查询最近活跃的高星项目
            if period == "daily":
                # 今日：最近 1 天更新的项目，star > 1000
                date_range = self.yesterday.strftime('%Y-%m-%d')
                stars_req = "1000"
                search_field = "pushed"  # 使用 pushed（最近更新）而不是 created
            else:
                # 本周：最近 7 天更新的项目，star > 500
                date_range = (self.today - timedelta(days=7)).strftime('%Y-%m-%d')
                stars_req = "500"
                search_field = "pushed"
            
            apis = [
                f"https://api.gitterapp.com/repositories?since={period}",
                f"https://gh-trending-api.herokuapp.com/repositories?since={period}",
                f"https://api.github.com/search/repositories?q=stars:>{stars_req}+{search_field}:>{date_range}&sort=stars&order=desc&per_page=10",
            ]
            
            for api_url in apis:
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    r = requests.get(api_url, headers=headers, timeout=30)
                    if r.status_code != 200:
                        print(f"      ⚠️ {api_url[:50]}... -> HTTP {r.status_code}")
                        continue
                    
                    data = r.json()
                    
                    # GitHub Search API 返回格式不同
                    if "items" in data:
                        repos = data["items"]
                    else:
                        repos = data if isinstance(data, list) else []
                    
                    if not repos:
                        print(f"      ⚠️ {api_url[:50]}... -> 返回空数据")
                        continue
                    
                    for repo in repos[:10]:
                        # 兼容多种 API 返回格式
                        if "full_name" in repo:  # GitHub Search API
                            author, name = repo["full_name"].split("/") if "/" in repo["full_name"] else ("", repo["full_name"])
                        else:  # Trending API
                            author = repo.get("author", "") or repo.get("username", "")
                            name = repo.get("name", "") or repo.get("reponame", "")
                        
                        if not author or not name:
                            continue
                            
                        desc = repo.get("description", "") or ""
                        lang = repo.get("language", "") or repo.get("programmingLanguage", "") or "Unknown"
                        
                        # 星标数
                        stars = (
                            repo.get("stars") or 
                            repo.get("totalStars") or 
                            repo.get("stargazers_count") or 
                            0
                        )
                        stars_today = repo.get("starsSince", 0) or repo.get("starsToday", 0)
                        
                        self.all_items.append({
                            "标题": f"{author}/{name}",
                            "内容": desc[:200] if desc else f"{lang} 项目",
                            "日期": self.today.isoformat(),
                            "来源": f"GitHub {label}",
                            "板块": f"GitHub{label}",
                            "链接": repo.get("url") or repo.get("html_url") or f"https://github.com/{author}/{name}",
                            "额外": f"⭐ {stars:,} | 🔥 +{stars_today:,} | 💻 {lang}" if stars_today else f"⭐ {stars:,} | 💻 {lang}"
                        })
                        count += 1
                    
                    if count > 0:
                        print(f"  ✅ {label}: {count} 条（使用 {api_url.split('/')[2]}）")
                        break  # 成功就不尝试下一个 API
                        
                except Exception as e:
                    print(f"      ❌ {api_url[:50]}... -> {type(e).__name__}: {str(e)[:100]}")
                    continue
            
            if count == 0:
                print(f"  ⚠️ {label}: 所有 API 均失败")

    # ==================== HuggingFace（无需 API）====================
    
    def fetch_huggingface_trending(self):
        """获取 HuggingFace 热门模型（已验证可用）"""
        print("\n🤗 HuggingFace Trending...")
        
        try:
            # 使用 HuggingFace 官方 API（实测可用）
            r = requests.get(
                "https://huggingface.co/api/models",
                params={"limit": 10},  # 按 trendingScore 默认排序
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30
            )
            
            if r.status_code != 200:
                print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")
                return
                
            models = r.json()
            if not isinstance(models, list):
                print(f"  ❌ 返回格式错误")
                return
            
            count = 0
            for model in models[:10]:
                if not isinstance(model, dict):
                    continue
                    
                model_id = model.get("id", "")
                if not model_id:
                    continue
                    
                downloads = model.get("downloads", 0) or 0
                likes = model.get("likes", 0) or 0
                trending = model.get("trendingScore", 0) or 0
                
                # 获取标签和任务类型
                tags = model.get("tags", [])
                task = next((t for t in tags if not t.startswith(("license:", "region:", "arxiv:"))), "模型")
                
                self.all_items.append({
                    "标题": model_id,
                    "内容": f"{task} | 热度: {trending}",
                    "日期": self.today.isoformat(),
                    "来源": "HuggingFace",
                    "板块": "HuggingFace热门",
                    "链接": f"https://huggingface.co/{model_id}",
                    "额外": f"📥 {downloads:,} 下载 | ❤️ {likes} 点赞 | 🔥 热度 {trending}"
                })
                count += 1
            
            print(f"  ✅ {count} 条")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")
    
    # ==================== ModelScope（无需 API）====================
    
    def fetch_modelscope_trending(self):
        """获取 ModelScope 热门模型（API 已验证失效，暂时跳过）"""
        print("\n🔮 ModelScope Trending...")
        print("  ⚠️ ModelScope API 已废弃（实测 404），跳过此数据源")
        # 注：经实测 https://modelscope.cn/api/v1/models 返回 404
        # ModelScope 可能需要认证或 API 已迁移
        return

    def _fetch_modelscope_old(self):
        """旧的 ModelScope 获取代码（已废弃，保留作参考）"""
        for url, params in [("https://modelscope.cn/api/v1/models", {"PageSize": 10})]:
            try:
                r = requests.get(
                    url, 
                    params=params, 
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": "https://modelscope.cn/"
                    },
                    timeout=30
                )
                
                if r.status_code != 200:
                    print(f"      ⚠️ {url.split('/')[2]} -> HTTP {r.status_code}")
                    continue
                
                data = r.json()
                
                # 尝试多种数据结构
                models_data = (
                    data.get("Data") or 
                    data.get("data") or 
                    data.get("models") or 
                    []
                )
                
                if not models_data or not isinstance(models_data, list):
                    print(f"      ⚠️ {url.split('/')[2]} -> 返回数据格式错误或为空")
                    continue
                
                count = 0
                for model in models_data[:8]:
                    if not isinstance(model, dict):
                        continue
                    
                    # 多种字段名尝试
                    model_name = (
                        model.get("Path") or 
                        model.get("Name") or 
                        model.get("Id") or 
                        model.get("ModelId") or
                        ""
                    )
                    
                    if not model_name:
                        continue
                    
                    desc = model.get("ChineseDescription") or model.get("Description", "")
                    if desc and isinstance(desc, str):
                        desc = desc[:150]
                    else:
                        desc = "ModelScope 热门模型"
                    
                    downloads = model.get("Downloads", 0) or model.get("DownloadCount", 0) or 0
                    
                    self.all_items.append({
                        "标题": model_name,
                        "内容": desc,
                        "日期": self.today.isoformat(),
                        "来源": "ModelScope",
                        "板块": "ModelScope热门",
                        "链接": f"https://modelscope.cn/models/{model_name}",
                        "额外": f"📥 {downloads:,} 下载"
                    })
                    count += 1
                
                if count > 0:
                    print(f"  ✅ {count} 条（使用 {url.split('/')[2]}）")
                    return  # 成功就退出
                    
            except Exception as e:
                print(f"      ❌ {url.split('/')[2]} -> {type(e).__name__}: {str(e)[:100]}")
                continue
        
        print("  ⚠️ 所有接口均失败（ModelScope 可能需要登录或在国外访问受限）")

    # ==================== GitHub AI Agent/MCP/Skills 热门（无需 API）====================
    
    def fetch_github_agents(self):
        """获取 GitHub 热门 AI Agent 项目"""
        print("\n🤖 GitHub AI Agent 热门项目...")
        
        try:
            # 搜索 AI agent 相关的热门仓库
            # 使用更简单的查询格式，避免 URL 编码问题
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": "ai agent llm autonomous stars:>1000",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30
            )
            
            if r.status_code != 200:
                print(f"  ❌ HTTP {r.status_code}")
                return
            
            data = r.json()
            repos = data.get("items", [])
            
            count = 0
            for repo in repos[:10]:
                full_name = repo.get("full_name", "")
                if not full_name:
                    continue
                
                self.all_items.append({
                    "标题": full_name,
                    "内容": (repo.get("description") or "AI Agent 项目")[:200],
                    "日期": self.today.isoformat(),
                    "来源": "GitHub AI Agent",
                    "板块": "AI Agent热门",
                    "链接": repo.get("html_url", f"https://github.com/{full_name}"),
                    "额外": f"⭐ {repo.get('stargazers_count', 0):,} | 💻 {repo.get('language', 'Unknown')}"
                })
                count += 1
            
            print(f"  ✅ {count} 条")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")
    
    def fetch_github_mcp_tools(self):
        """获取 Smithery.ai 热门 MCP 工具"""
        print("\n🔧 Smithery.ai MCP 工具热门...")
        
        try:
            # 使用 Smithery.ai 官方 API 获取热门 MCP servers
            r = requests.get(
                "https://registry.smithery.ai/servers?limit=10",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30
            )
            
            if r.status_code != 200:
                print(f"  ❌ HTTP {r.status_code}")
                return
            
            data = r.json()
            servers = data.get("servers", [])
            
            count = 0
            for server in servers[:10]:
                name = server.get("displayName", "") or server.get("qualifiedName", "")
                if not name:
                    continue
                
                use_count = server.get("useCount", 0)
                desc = server.get("description", "MCP Server")
                
                self.all_items.append({
                    "标题": name,
                    "内容": desc[:200] if desc else "MCP 工具",
                    "日期": self.today.isoformat(),
                    "来源": "Smithery.ai",
                    "板块": "MCP工具热门",
                    "链接": server.get("homepage", f"https://smithery.ai/server/{server.get('qualifiedName', '')}"),
                    "额外": f"🔥 {use_count:,} 使用次数 | {'✅ 官方验证' if server.get('verified') else ''}"
                })
                count += 1
            
            print(f"  ✅ {count} 条")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")
    
    def fetch_github_ai_skills(self):
        """获取热门 AI Skills（优先 Smithery API，备用 skillsmp.com 和 GitHub）"""
        print("\n🎯 热门 AI Skills...")
        
        count = 0
        smithery_key = os.environ.get("SMITHERY_API_KEY")
        
        # 方案1: Smithery API（需要 API Key）
        if smithery_key:
            try:
                r = requests.get(
                    "https://registry.smithery.ai/skills",
                    params={"limit": 10},
                    headers={
                        "Authorization": f"Bearer {smithery_key}",
                        "User-Agent": "Mozilla/5.0"
                    },
                    timeout=30
                )
                
                if r.status_code == 200:
                    data = r.json()
                    skills = data.get("skills", []) if isinstance(data, dict) else data
                    
                    for skill in skills[:10]:
                        name = skill.get("displayName", "") or skill.get("name", "") or skill.get("qualifiedName", "")
                        if not name:
                            continue
                        
                        use_count = skill.get("useCount", 0)
                        desc = skill.get("description", "AI Skill")
                        
                        self.all_items.append({
                            "标题": name,
                            "内容": desc[:200] if desc else "AI Skill",
                            "日期": self.today.isoformat(),
                            "来源": "Smithery Skills",
                            "板块": "AI Skills热门",
                            "链接": skill.get("homepage", f"https://smithery.ai/skill/{skill.get('qualifiedName', '')}"),
                            "额外": f"🔥 {use_count:,} 使用次数 | {'✅ 官方验证' if skill.get('verified') else ''}"
                        })
                        count += 1
                    
                    if count > 0:
                        print(f"  ✅ {count} 条（来自 Smithery API）")
                        return
                else:
                    print(f"  ⚠️ Smithery API HTTP {r.status_code}，尝试备用方案")
            except Exception as e:
                print(f"  ⚠️ Smithery API 失败: {type(e).__name__}，尝试备用方案")
        else:
            print("  ⚠️ 未配置 SMITHERY_API_KEY，尝试备用方案")
        
        # 方案2: 尝试 skillsmp.com（GitHub Actions 环境应可访问）
        try:
            r = requests.get(
                "https://skillsmp.com/api/skills",
                params={"limit": 10, "sort": "popular"},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                },
                timeout=30
            )
            
            if r.status_code == 200:
                data = r.json()
                skills = data if isinstance(data, list) else data.get("skills", []) or data.get("data", [])
                
                for skill in skills[:10]:
                    name = skill.get("name", "") or skill.get("title", "")
                    if not name:
                        continue
                    
                    self.all_items.append({
                        "标题": name,
                        "内容": (skill.get("description") or "AI Skill")[:200],
                        "日期": self.today.isoformat(),
                        "来源": "SkillsMP",
                        "板块": "AI Skills热门",
                        "链接": skill.get("url") or skill.get("link") or f"https://skillsmp.com/skill/{skill.get('id', '')}",
                        "额外": f"🔥 {skill.get('downloads', 0) or skill.get('uses', 0):,} 使用"
                    })
                    count += 1
                
                if count > 0:
                    print(f"  ✅ {count} 条（来自 skillsmp.com）")
                    return
            else:
                print(f"  ⚠️ skillsmp.com HTTP {r.status_code}，尝试 GitHub 备用方案")
        except Exception as e:
            print(f"  ⚠️ skillsmp.com 失败: {type(e).__name__}，尝试 GitHub 备用方案")
        
        # 方案2: GitHub 备用 - 搜索 agent skills 相关项目
        try:
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": "awesome-chatgpt-prompts awesome-prompts prompt-engineering stars:>1000",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30
            )
            
            if r.status_code != 200:
                print(f"  ❌ GitHub 备用也失败: HTTP {r.status_code}")
                return
            
            data = r.json()
            repos = data.get("items", [])
            
            for repo in repos[:10]:
                full_name = repo.get("full_name", "")
                if not full_name:
                    continue
                
                self.all_items.append({
                    "标题": full_name,
                    "内容": (repo.get("description") or "AI Skills 项目")[:200],
                    "日期": self.today.isoformat(),
                    "来源": "GitHub Skills",
                    "板块": "AI Skills热门",
                    "链接": repo.get("html_url", f"https://github.com/{full_name}"),
                    "额外": f"⭐ {repo.get('stargazers_count', 0):,} | 💻 {repo.get('language', 'Unknown')}"
                })
                count += 1
            
            print(f"  ✅ {count} 条（来自 GitHub 备用）")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")

    # ==================== AI 处理 ====================
    
    def clean_json(self, text):
        """清洗并提取有效的 JSON"""
        import re
        text = text.strip()
        
        # 1. 移除 Markdown 代码块
        if "```" in text:
            pattern = r"```(?:json|JSON)?\s*([\s\S]*?)\s*```"
            match = re.search(pattern, text)
            if match:
                text = match.group(1).strip()
                
        # 2. 尝试直接解析
        try:
            return json.loads(text)
        except:
            pass
    
        # 3. 修复常见错误
        # 移除对象/数组末尾的逗号
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        
        # 尝试解析
        try:
            return json.loads(text)
        except:
            pass
            
        # 4. 提取第一个有效的 JSON 对象/数组（寻找匹配的括号）
        stack = []
        start_index = -1
        
        for i, char in enumerate(text):
            if char == '{' or char == '[':
                if not stack:
                    start_index = i
                stack.append(char)
            elif char == '}' or char == ']':
                if stack:
                    last = stack[-1]
                    if (char == '}' and last == '{') or (char == ']' and last == '['):
                        stack.pop()
                        if not stack:
                            # 找到一个完整的块
                            candidate = text[start_index:i+1]
                            try:
                                return json.loads(candidate)
                            except:
                                pass
        return None

    def ai_process(self):
        """AI 翻译和摘要（分批处理）"""
        if not self.siliconflow_key:
            error_msg = "❌ 未配置 SILICONFLOW_API_KEY，无法进行 AI 处理"
            print(f"\n{error_msg}")
            
            # 保存错误信息（限制5条）
            fallback = {
                "date": self.today_str,
                "error": error_msg,
                "categories": {"原始数据": self.all_items[:5]},
                "analysis": {
                    "summary": "⚠️ 未配置 API Key，请在 GitHub Secrets 中添加 SILICONFLOW_API_KEY（显示前5条）",
                    "trends": []
                }
            }
            (self.data_dir / "latest.json").write_text(
                json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
            return fallback
        
        if not self.all_items:
            print("\n⚠️ 没有数据")
            return None
        
        print(f"\n🤖 AI 处理 ({self.model})...")
        
        try:
            # 1. 预处理：按分类分组并限制数量（减少输入 token）
            # 每个分类最多取前15条发给 AI 筛选
            grouped = {}
            for item in self.all_items:
                cat = item.get("板块", "其他")
                if cat not in grouped:
                    grouped[cat] = []
                if len(grouped[cat]) < 15:
                    grouped[cat].append(item)
            
            filtered_items = []
            for items in grouped.values():
                filtered_items.extend(items)
                
            print(f"  无需处理的数据: {len(self.all_items) - len(filtered_items)} 条 (每类限制15条输入)")
            
            # 2. 分批处理
            print(f"  无需处理的数据: {len(self.all_items) - len(filtered_items)} 条 (每类限制15条输入)")
            
            # 2. 分批处理
            BATCH_SIZE = 15  # 降低 Batch Size 防止截断
            batches = [filtered_items[i:i + BATCH_SIZE] for i in range(0, len(filtered_items), BATCH_SIZE)]
            
            final_categories = {}
            final_analysis = {"summary": "今日 AI 摘要", "trends": []}
            
            from openai import OpenAI
            client = OpenAI(
                api_key=self.siliconflow_key,
                base_url="https://api.siliconflow.cn/v1"
            )

            for i, batch in enumerate(batches):
                print(f"  🔄 处理批次 {i+1}/{len(batches)} ({len(batch)} 条)...")
                
                prompt = f"""You are a JSON formatter. Process the following AI news data and return ONLY valid JSON.

Input data:
{json.dumps(batch, ensure_ascii=False)}

Requirements:
1. Translate English to Chinese
2. Summarize content to 60-80 Chinese characters
3. Group by category
4. Keep "额外" field
5. JSON Output ONLY.

Output Format:
{{"categories":{{"CategoryName":[{{ "标题":"...", "内容":"...", "链接":"...", "日期":"...", "来源":"...", "额外":"..." }}]}}, "analysis":{{"summary":"...", "trends":["..."]}}}}
"""

                try:
                    resp = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a JSON formatter. Return valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=8192,
                        temperature=0.1
                    )
                    
                    content = resp.choices[0].message.content.strip()
                    
                    # 使用增强的 JSON 解析
                    batch_result = self.clean_json(content)
                    
                    if not batch_result:
                        print(f"  ❌ 批次 {i+1} 解析彻底失败，原始内容预览: {content[:100]}...")
                        continue

                    # 合并结果
                    if batch_result:
                        # 合并分类
                        cats = batch_result.get("categories", {})
                        for cat_name, items in cats.items():
                            if cat_name not in final_categories:
                                final_categories[cat_name] = []
                            final_categories[cat_name].extend(items)
                        
                        # 仅使用第一批的分析结果（通常包含新闻）
                        if i == 0 and "analysis" in batch_result:
                            final_analysis = batch_result["analysis"]
                            
                except Exception as e:
                    print(f"  ❌ 批次 {i+1} 请求失败: {e}")

            # 3. 最终组装
            result = {
                "date": self.today_str,
                "categories": final_categories,
                "analysis": final_analysis
            }
            
            # 再次确保每类不超过10条
            total = 0
            for cat in result["categories"]:
                result["categories"][cat] = result["categories"][cat][:10]
                total += len(result["categories"][cat])
            
            # 保存
            (self.data_dir / f"digest_{self.today_str}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (self.data_dir / "latest.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            
            total = sum(len(v) for v in result.get("categories", {}).values())
            print(f"  ✅ 完成，共 {total} 条（每分类最多10条）")
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"AI 处理失败: {str(e)}\n{traceback.format_exc()}"
            print(f"  ❌ {error_msg}")
            
            # 失败时保存原始数据，并附带错误信息（限制5条）
            fallback = {
                "date": self.today_str,
                "error": error_msg,
                "categories": {"原始数据": self.all_items[:5]},
                "analysis": {
                    "summary": f"⚠️ AI 处理失败，显示原始数据（前5条）。错误：{str(e)}",
                    "trends": []
                }
            }
            (self.data_dir / "latest.json").write_text(
                json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
            return fallback

    def run(self):
        print("=" * 50)
        print(f"🚀 AI 资讯聚合器 - {self.today_str}")
        print("=" * 50)
        
        # 数据采集（每个独立，失败不影响其他）
        self.safe_fetch("RSS", self.fetch_rss)
        self.safe_fetch("YouTube博主", self.fetch_youtube_rss)
        self.safe_fetch("YouTube热门", self.fetch_youtube_trending)
        self.safe_fetch("Twitter热门", self.fetch_twitter)
        self.safe_fetch("Twitter账号", self.fetch_twitter_accounts)
        self.safe_fetch("TikTok", self.fetch_tiktok)
        self.safe_fetch("GitHub热门", self.fetch_github_trending)
        self.safe_fetch("AI Agent热门", self.fetch_github_agents)
        self.safe_fetch("MCP工具热门", self.fetch_github_mcp_tools)
        self.safe_fetch("AI Skills热门", self.fetch_github_ai_skills)
        self.safe_fetch("HuggingFace", self.fetch_huggingface_trending)
        self.safe_fetch("ModelScope", self.fetch_modelscope_trending)
        
        print(f"\n📦 共采集 {len(self.all_items)} 条")
        
        # AI 处理
        result = self.ai_process()
        
        print("\n" + "=" * 50)
        print("✨ 完成!")
        return result


if __name__ == "__main__":
    AIDigestGenerator().run()
