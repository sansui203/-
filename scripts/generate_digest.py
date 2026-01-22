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
                "maxResults": 50,
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
        """获取 GitHub Trending（使用第三方 API）"""
        print("\n⭐ GitHub Trending...")
        
        periods = [
            ("daily", "今日热门"),
            ("weekly", "本周热门")
        ]
        
        for period, label in periods:
            try:
                # 使用 GitHub Trending API
                r = requests.get(
                    f"https://api.gitterapp.com/repositories?since={period}",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=30
                )
                repos = r.json()
                
                count = 0
                for repo in repos[:15]:
                    author = repo.get("author", "")
                    name = repo.get("name", "")
                    desc = repo.get("description", "")
                    lang = repo.get("language", "Unknown")
                    stars = repo.get("stars", 0)
                    stars_today = repo.get("starsSince", 0)
                    
                    self.all_items.append({
                        "标题": f"{author}/{name}",
                        "内容": desc[:200],
                        "日期": self.today.isoformat(),
                        "来源": f"GitHub {label}",
                        "板块": f"GitHub{label}",
                        "链接": repo.get("url", f"https://github.com/{author}/{name}"),
                        "额外": f"⭐ {stars:,} | 🔥 {period} +{stars_today:,} | 💻 {lang}"
                    })
                    count += 1
                
                print(f"  ✅ {label}: {count} 条")
            except Exception as e:
                print(f"  ❌ {label}: {e}")

    # ==================== HuggingFace（无需 API）====================
    
    def fetch_huggingface_trending(self):
        """获取 HuggingFace 热门模型"""
        print("\n🤗 HuggingFace Trending...")
        
        try:
            # 使用 HuggingFace API
            r = requests.get(
                "https://huggingface.co/api/models",
                params={
                    "sort": "trending",
                    "direction": -1,
                    "limit": 20
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30
            )
            models = r.json()
            
            count = 0
            for model in models[:15]:
                model_id = model.get("id", "")
                if not model_id:
                    continue
                    
                downloads = model.get("downloads", 0)
                likes = model.get("likes", 0)
                
                self.all_items.append({
                    "标题": model_id,
                    "内容": model.get("description", "")[:150] or f"Pipeline: {model.get('pipeline_tag', 'N/A')}",
                    "日期": self.today.isoformat(),
                    "来源": "HuggingFace",
                    "板块": "HuggingFace热门",
                    "链接": f"https://huggingface.co/{model_id}",
                    "额外": f"📥 {downloads:,} 下载 | ❤️ {likes} 点赞"
                })
                count += 1
            
            print(f"  ✅ {count} 条")
        except Exception as e:
            print(f"  ❌ {e}")
    
    # ==================== ModelScope（无需 API）====================
    
    def fetch_modelscope_trending(self):
        """获取 ModelScope 热门模型"""
        print("\n🔮 ModelScope Trending...")
        
        try:
            # ModelScope API (多试几个接口)
            endpoints = [
                ("https://www.modelscope.cn/api/v1/models", {"PageNumber": 1, "PageSize": 20, "SortBy": "gmtDownload7d"}),
                ("https://modelscope.cn/api/v1/models", {"PageNumber": 1, "PageSize": 20})
            ]
            
            for url, params in endpoints:
                try:
                    r = requests.get(url, params=params, 
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=30)
                    data = r.json()
                    
                    models_data = data.get("Data", []) or data.get("data", [])
                    if not models_data:
                        continue
                    
                    count = 0
                    for model in models_data[:15]:
                        model_name = model.get("Path") or model.get("Name") or model.get("Id", "")
                        if not model_name:
                            continue
                            
                        desc = model.get("ChineseDescription") or model.get("Description", "")
                        downloads = model.get("Downloads", 0) or model.get("DownloadCount", 0)
                        
                        self.all_items.append({
                            "标题": model_name,
                            "内容": desc[:150] if desc else "ModelScope 热门模型",
                            "日期": self.today.isoformat(),
                            "来源": "ModelScope",
                            "板块": "ModelScope热门",
                            "链接": f"https://modelscope.cn/models/{model_name}",
                            "额外": f"📥 {downloads:,} 下载"
                        })
                        count += 1
                    
                    print(f"  ✅ {count} 条")
                    return  # 成功就退出
                    
                except Exception as e:
                    continue
            
            print("  ⚠️ 所有接口均失败")
            
        except Exception as e:
            print(f"  ❌ {e}")

    # ==================== AI 处理 ====================
    
    def ai_process(self):
        """AI 翻译和摘要"""
        if not self.siliconflow_key:
            error_msg = "❌ 未配置 SILICONFLOW_API_KEY，无法进行 AI 处理"
            print(f"\n{error_msg}")
            
            # 保存错误信息
            fallback = {
                "date": self.today_str,
                "error": error_msg,
                "categories": {"原始数据": self.all_items},
                "analysis": {
                    "summary": "⚠️ 未配置 API Key，请在 GitHub Secrets 中添加 SILICONFLOW_API_KEY",
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
        
        prompt = f"""处理以下AI资讯，输出JSON：

{json.dumps(self.all_items[:100], ensure_ascii=False)}

要求：
1. 英文翻译成中文
2. 长内容生成60-80字摘要  
3. 按板块分组
4. 保留"额外"字段（星标、下载量等数据）

输出格式：
{{"date":"{self.today_str}","categories":{{"新闻":[],"明星公司动态":[],"油管博主":[],"YouTube热点":[],"Twitter热点":[],"TikTok热点":[],"GitHub今日热门":[],"GitHub本周热门":[],"HuggingFace热门":[],"ModelScope热门":[]}},"analysis":{{"summary":"今日摘要","trends":["趋势1","趋势2"]}}}}

只输出JSON。"""

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.siliconflow_key,
                base_url="https://api.siliconflow.cn/v1"
            )
            
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000
            )
            
            content = resp.choices[0].message.content
            if "```" in content:
                content = content.split("```")[1].replace("json", "").strip()
            
            result = json.loads(content)
            
            # 保存
            (self.data_dir / f"digest_{self.today_str}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (self.data_dir / "latest.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            
            total = sum(len(v) for v in result.get("categories", {}).values())
            print(f"  ✅ 完成，共 {total} 条")
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"AI 处理失败: {str(e)}\n{traceback.format_exc()}"
            print(f"  ❌ {error_msg}")
            
            # 失败时保存原始数据，并附带错误信息
            fallback = {
                "date": self.today_str,
                "error": error_msg,
                "categories": {"原始数据": self.all_items},
                "analysis": {
                    "summary": f"⚠️ AI 处理失败，显示原始数据。错误：{str(e)}",
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
