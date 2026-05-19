import json
import urllib.request
import urllib.error
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0'
BASE_URL = 'aihot.virxact.com'
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'public', 'data.json')

# ========== 国内 RSS 源配置 ==========
RSS_FEEDS = [
    {'name': '少数派', 'url': 'https://sspai.com/feed', 'category': 'tip'},
    {'name': '量子位', 'url': 'https://www.qbitai.com/feed', 'category': 'industry'},
    {'name': '36氪', 'url': 'https://36kr.com/feed', 'category': 'industry'},
    {'name': '极客公园', 'url': 'http://www.geekpark.net/rss', 'category': 'industry'},
    {'name': 'InfoQ中文', 'url': 'https://www.infoq.cn/feed', 'category': 'tip'},
    # 机器之心 RSS 需要额外认证，暂时跳过
    # {'name': '机器之心', 'url': 'https://www.jiqizhixin.com/rss', 'category': 'industry'},
]

# ========== B站 UP 主配置 ==========
# 注意：B站 API 有风控限制，可能需要 cookie 或更完整的 headers
# 当前仅预留结构，抓取可能不稳定
BILIBILI_UPS = [
    {'name': '秋芝2046', 'mid': '385670211'},
]

# ========== 筛选配置 ==========

BLOCKED_KEYWORDS = [
    '死亡', '致死', '自杀', '犯罪', '黑客', '投毒', '漏洞', '攻击', '窃取',
    '诉讼', '起诉', '官司', '被告', '原告', '赔偿', '判决', '宣判',
    '裁员', '失业', '造假', '欺诈', '骗局', '泄露', '隐私泄露',
    '事故', '灾难', '危机', '崩溃', '暴跌', '崩盘'
]

TECH_KEYWORDS = [
    '基准测试', 'benchmark', '权重', '参数', '架构', '骨干网络',
    '训练方案', '强化学习', '蒸馏', '梯度', '损失函数', '推理速度',
    '注意力机制', 'transformer', 'token', '微调', 'fine-tuning',
    'npm', 'git', '代码库', 'sdk', 'cli', 'api', '编程接口',
    '论文', 'arxiv', '技术报告深度', '模型结构', '量化',
    '多任务模型', '视觉语言模型', '原生多模态'
]

INTEREST_TAGS = {
    'creative': {
        'emoji': '🎨', 'label': '创意', 'desc': 'AI做图/视频/音乐',
        'keywords': ['视频', '图像', '图片', '绘画', '画图', '设计', '音乐', '音频', 'sora', 'midjourney', 'runway', 'pika', 'suno', 'flux', '动画', '摄影', '摄像', '剪辑', '生成图', '文生图', '文生视频', '配音', '音效', '3d', '渲染', '视觉']
    },
    'app': {
        'emoji': '💻', 'label': '应用', 'desc': 'AI做工具/网站/智能体',
        'keywords': ['应用', 'app', '工具', '平台', '软件', '智能体', 'agent', '小程序', '网站', '建站', '无代码', '低代码', 'cursor', 'claude code', '产品', '上线', '发布', 'v0', 'replit']
    },
    'writing': {
        'emoji': '✍️', 'label': '文案', 'desc': 'AI写作/内容创作',
        'keywords': ['写作', '文案', '内容', '自媒体', '笔记', '文档', '文章', '博客', '脚本', '小说', '故事', '营销', '稿件', '剧本', ' prompt', '提示词']
    },
    'education': {
        'emoji': '🎓', 'label': '教育', 'desc': 'AI学习/教学',
        'keywords': ['教育', '学习', '教学', '课程', '辅导', '学生', '老师', '学校', '知识', '培训', '考试', '教材', '学堂', 'tutor', '导师']
    },
    'productivity': {
        'emoji': '🏢', 'label': '提效', 'desc': 'AI办公/效率',
        'keywords': ['办公', '效率', 'ppt', 'excel', '表格', '文档', '会议', '自动化', '工作流', '邮件', '日程', '管理', '协作', 'copilot', 'notion', 'gamma', '幻灯片', '汇报', '整理']
    }
}


def fetch_json(path):
    url = f'https://{BASE_URL}{path}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode('utf-8'))


def fetch_rss(url):
    """抓取 RSS feed，返回 XML 字符串"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml,application/xml,text/xml,*/*',
        })
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  ⚠️ RSS 抓取失败: {url} - {e}')
        return None


def parse_rss_items(xml_content, source_name, category):
    """解析 RSS XML，转换为统一格式的 item 列表"""
    items = []
    if not xml_content:
        return items
    try:
        # RSS 内容可能包含非法 XML 字符，需要清理
        # 简单处理：替换一些常见的问题字符
        xml_content = xml_content.replace('\x00', '').replace('\x01', '').replace('\x0b', '').replace('\x0c', '')
        root = ET.fromstring(xml_content)
        # 找到 channel/item
        channel = root.find('channel')
        if channel is None:
            # 可能是 atom 格式
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            for entry in entries:
                title_el = entry.find('atom:title', ns)
                link_el = entry.find('atom:link', ns)
                summary_el = entry.find('atom:summary', ns)
                content_el = entry.find('atom:content', ns)
                published_el = entry.find('atom:published', ns)
                updated_el = entry.find('atom:updated', ns)

                title = title_el.text if title_el is not None else ''
                link = link_el.get('href') if link_el is not None else ''
                summary = ''
                if summary_el is not None and summary_el.text:
                    summary = summary_el.text
                elif content_el is not None and content_el.text:
                    # 清理 HTML 标签，只取前 300 字
                    summary = content_el.text[:300]
                pub_date = published_el.text if published_el is not None else (updated_el.text if updated_el is not None else '')

                if not title or not link:
                    continue

                items.append({
                    'id': f'rss_{hash(link) & 0xFFFFFFFF}',
                    'title': title.strip(),
                    'title_en': None,
                    'url': link,
                    'source': source_name,
                    'publishedAt': _normalize_rss_date(pub_date),
                    'summary': summary.strip() if summary else title.strip(),
                    'category': category,
                })
            return items

        rss_items = channel.findall('item')
        for item in rss_items[:20]:  # 每个源最多取 20 条
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            content_el = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
            pub_date_el = item.find('pubDate')

            title = title_el.text if title_el is not None else ''
            link = link_el.text if link_el is not None else ''
            summary = ''
            if content_el is not None and content_el.text:
                summary = content_el.text[:300]
            elif desc_el is not None and desc_el.text:
                summary = desc_el.text[:300]
            pub_date = pub_date_el.text if pub_date_el is not None else ''

            if not title or not link:
                continue

            items.append({
                'id': f'rss_{hash(link) & 0xFFFFFFFF}',
                'title': title.strip(),
                'title_en': None,
                'url': link,
                'source': source_name,
                'publishedAt': _normalize_rss_date(pub_date),
                'summary': summary.strip() if summary else title.strip(),
                'category': category,
            })
    except Exception as e:
        print(f'  ⚠️ RSS 解析失败 ({source_name}): {e}')
    return items


def _normalize_rss_date(date_str):
    """将各种 RSS 日期格式统一为 ISO 格式"""
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        # 尝试解析常见格式
        # RFC 2822: Fri, 15 May 2026 14:54:44 +0800
        # 或 2026-05-15T14:54:44+08:00
        # 或 2026-05-15 14:54:44
        date_str = date_str.strip()
        for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.astimezone(timezone.utc).isoformat()
            except ValueError:
                continue
        # 如果都失败了，尝试提取日期部分
        if len(date_str) >= 10:
            return date_str[:10] + 'T00:00:00+00:00'
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()


def fetch_bilibili_videos(mid, pn=1, ps=10):
    """
    抓取 B 站 UP 主视频列表
    注意：B 站 API 有风控限制（-799 请求过于频繁），此功能可能不稳定
    如需稳定使用，可能需要配置 cookie 或使用代理
    """
    items = []
    try:
        url = f'https://api.bilibili.com/x/space/arc/search?mid={mid}&pn={pn}&ps={ps}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'https://space.bilibili.com/{mid}',
        })
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode('utf-8'))
        if data.get('code') != 0:
            print(f'  ⚠️ B站 API 错误 (mid={mid}): {data.get("message", "未知错误")}')
            return items
        vlist = data.get('data', {}).get('list', {}).get('vlist', [])
        for v in vlist:
            bvid = v.get('bvid', '')
            items.append({
                'id': f'bili_{bvid}',
                'title': v.get('title', ''),
                'title_en': None,
                'url': f'https://www.bilibili.com/video/{bvid}',
                'source': f'B站：{v.get("author", "UP主")}',
                'publishedAt': _normalize_rss_date(v.get('created', '')),
                'summary': v.get('description', '')[:200] or v.get('title', ''),
                'category': 'tip',
            })
    except Exception as e:
        print(f'  ⚠️ B站抓取失败 (mid={mid}): {e}')
    return items


def contains_any(text, keywords):
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def calc_tech_score(item):
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    score = 0
    if contains_any(text, TECH_KEYWORDS):
        score += 2
    if item.get('category') == 'ai-models':
        score += 1
    summary = item.get('summary', '')
    if summary and len(summary) > 20 and not contains_any(summary, ['训练', '蒸馏', '骨干网络', '量化']):
        score -= 1
    return score


def match_interest_tags(item):
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    tags = []
    for key, config in INTEREST_TAGS.items():
        if contains_any(text, config['keywords']):
            tags.append(key)
    return tags


def format_date(iso_str):
    try:
        d = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        diff = now - d
        hours = int(diff.total_seconds() / 3600)
        if hours < 1:
            return '刚刚'
        if hours < 24:
            return f'{hours}小时前'
        days = hours // 24
        if days == 1:
            return '昨天'
        if days < 7:
            return f'{days}天前'
        return f'{d.month}月{d.day}日'
    except:
        return iso_str[:10]


def fetch_and_filter():
    print('📡 正在从 AI HOT 拉取数据...')

    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    data = fetch_json(f'/api/public/items?mode=selected&since={since}&take=100')

    items = data.get('items', [])
    print(f'📥 AI HOT 获取到 {len(items)} 条原始数据')

    # ===== 抓取国内 RSS =====
    print('📡 正在抓取国内 RSS 源...')
    rss_items = []
    for feed in RSS_FEEDS:
        print(f'  → {feed["name"]}')
        xml = fetch_rss(feed['url'])
        parsed = parse_rss_items(xml, feed['name'], feed['category'])
        rss_items.extend(parsed)
        print(f'     解析到 {len(parsed)} 条')
    print(f'📥 RSS 总计 {len(rss_items)} 条')

    # ===== 抓取 B 站 UP 主（预留，可能风控失败）=====
    print('📡 正在抓取 B 站 UP 主视频...')
    bili_items = []
    for up in BILIBILI_UPS:
        print(f'  → {up["name"]}')
        parsed = fetch_bilibili_videos(up['mid'])
        bili_items.extend(parsed)
        print(f'     解析到 {len(parsed)} 条')
    if not bili_items:
        print('  ⚠️ B站抓取为空，可能触发风控，请稍后重试或配置 cookie')
    print(f'📥 B站总计 {len(bili_items)} 条')

    # 合并所有来源
    all_items = items + rss_items + bili_items
    print(f'📦 合并后总计 {len(all_items)} 条')

    # ===== 第一层筛选 =====
    filtered = []
    for item in all_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        if contains_any(text, BLOCKED_KEYWORDS):
            continue
        tech_score = calc_tech_score(item)
        if tech_score >= 3:
            continue
        filtered.append(item)

    print(f'🔍 过滤后剩余 {len(filtered)} 条')

    # 打标签
    enriched = []
    for item in filtered:
        tags = match_interest_tags(item)
        tech_score = calc_tech_score(item)
        enriched.append({
            **item,
            'interestTags': tags,
            'techScore': tech_score,
            'formattedTime': format_date(item.get('publishedAt', ''))
        })

    # 精选策略
    with_tags = [i for i in enriched if i['interestTags']]
    without_tags = [i for i in enriched if not i['interestTags']]
    print(f'🏷️  有明确兴趣标签匹配: {len(with_tags)} 条')

    selected = []
    used_ids = set()
    tag_count = {}

    sorted_by_tech = sorted(with_tags, key=lambda x: x['techScore'])

    for item in sorted_by_tech:
        if len(selected) >= 12:  # v2.0 增加候选池，因为来源更多了
            break
        if item['id'] in used_ids:
            continue
        primary_tag = item['interestTags'][0]
        if tag_count.get(primary_tag, 0) >= 3:  # 每类放宽到 3 条
            continue
        selected.append(item)
        used_ids.add(item['id'])
        tag_count[primary_tag] = tag_count.get(primary_tag, 0) + 1

    # 补充
    if len(selected) < 8:
        for item in sorted_by_tech:
            if len(selected) >= 8:
                break
            if item['id'] in used_ids:
                continue
            selected.append(item)
            used_ids.add(item['id'])

    # 最后补充
    if len(selected) < 8:
        sorted_no_tags = sorted(without_tags, key=lambda x: x['techScore'])
        for item in sorted_no_tags:
            if len(selected) >= 8:
                break
            if item['id'] in used_ids:
                continue
            selected.append({**item, 'interestTags': ['general']})
            used_ids.add(item['id'])

    print(f'✅ 最终精选 {len(selected)} 条')

    grouped = {}
    for item in selected:
        tag = item['interestTags'][0] if item['interestTags'] else 'general'
        grouped.setdefault(tag, []).append(item)

    for tag, items_list in grouped.items():
        config = INTEREST_TAGS.get(tag, {'emoji': '📰', 'label': '综合', 'desc': '其他资讯'})
        print(f"  {config['emoji']} {config['label']}: {len(items_list)} 条")

    return {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'totalSource': len(all_items),
        'totalFiltered': len(filtered),
        'totalSelected': len(selected),
        'sources': {
            'aihot': len(items),
            'rss': len(rss_items),
            'bilibili': len(bili_items),
        },
        'grouped': grouped,
        'items': selected
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    result = fetch_and_filter()
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\n💾 数据已保存到 {OUTPUT_PATH}')


if __name__ == '__main__':
    main()
