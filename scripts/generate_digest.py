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
                f"https://api.github.com/search/repositories?q=stars:>{stars_req}+{search_field}:>{date_range}&sort=stars&order=desc&per_page=8",
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
                    
                    for repo in repos[:8]:
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
            for model in models[:8]:
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

    # ==================== AI 处理 ====================
    
    def ai_process(self):
        """AI 翻译和摘要"""
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
        
        prompt = f"""You are a JSON formatter. Process the following AI news data and return ONLY valid JSON, no extra text.

Input data:
{json.dumps(self.all_items[:100], ensure_ascii=False)}

Requirements:
1. Translate English to Chinese
2. Summarize long content to 60-80 Chinese characters
3. Group by category
4. Keep "额外" field (stars, downloads, etc.)
5. **IMPORTANT: Each category should have AT MOST 5 items (select the most important/popular ones)**

Output format (ONLY this JSON, nothing else):
{{"date":"{self.today_str}","categories":{{"新闻":[],"明星公司动态":[],"油管博主":[],"YouTube热点":[],"Twitter热点":[],"TikTok热点":[],"GitHub今日热门":[],"GitHub本周热门":[],"HuggingFace热门":[]}},"analysis":{{"summary":"今日摘要","trends":["趋势1","趋势2"]}}}}

CRITICAL: Return ONLY the JSON object, no markdown, no code blocks, no explanations. Maximum 5 items per category."""

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.siliconflow_key,
                base_url="https://api.siliconflow.cn/v1"
            )
            
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a JSON formatter. Always return valid JSON only, no extra text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=8000,
                temperature=0.1  # 降低温度使输出更稳定
            )
            
            content = resp.choices[0].message.content.strip()
            
            # 多种方式提取 JSON
            result = None
            errors = []
            
            # 方法1: 直接解析
            try:
                result = json.loads(content)
            except Exception as e1:
                errors.append(f"直接解析失败: {e1}")
                
                # 方法2: 移除 markdown 代码块
                try:
                    if "```" in content:
                        content = content.split("```")[1]
                        content = content.replace("json", "").replace("JSON", "").strip()
                    result = json.loads(content)
                except Exception as e2:
                    errors.append(f"移除代码块后失败: {e2}")
                    
                    # 方法3: 提取第一个 { 到最后一个 }
                    try:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        if start >= 0 and end > start:
                            content = content[start:end]
                        result = json.loads(content)
                    except Exception as e3:
                        errors.append(f"提取括号后失败: {e3}")
                        
                        # 保存原始内容以便调试
                        debug_file = self.data_dir / f"debug_response_{self.today_str}.txt"
                        debug_file.write_text(f"原始返回:\n{resp.choices[0].message.content}\n\n错误:\n" + "\n".join(errors), encoding="utf-8")
                        raise Exception(f"所有JSON解析方法均失败。详见 {debug_file}")
            
            if not result:
                raise Exception("无法解析 AI 返回的 JSON")
            
            # 确保每个分类最多5条
            categories = result.get("categories", {})
            for category_name, items in categories.items():
                if isinstance(items, list) and len(items) > 5:
                    categories[category_name] = items[:5]
            
            # 保存
            (self.data_dir / f"digest_{self.today_str}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (self.data_dir / "latest.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            
            total = sum(len(v) for v in result.get("categories", {}).values())
            print(f"  ✅ 完成，共 {total} 条（每分类最多5条）")
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
