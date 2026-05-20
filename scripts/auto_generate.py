#!/usr/bin/env python3
"""
Auto-generate daily content for AI News Daily
Triggered by GitHub Actions
"""
import json
import os
import datetime
import re
import requests


def get_today_type():
    """Return 'brief' or 'deep' based on today's weekday (UTC+8)"""
    tz = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(tz)
    day = now.weekday()  # 0=Monday, 6=Sunday
    # Deep dive days: Tuesday(1), Friday(4)
    if day in [1, 4]:
        return 'deep', now
    return 'brief', now


def read_data_json():
    path = os.path.join(os.path.dirname(__file__), '..', 'public', 'data.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_file(rel_path):
    path = os.path.join(os.path.dirname(__file__), '..', rel_path)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def call_claude_api(prompt):
    """Call Claude API to generate content"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    base_url = os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return None

    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    }

    model = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-6-20251001')
    payload = {
        'model': model,
        'max_tokens': 8000,
        'messages': [
            {'role': 'user', 'content': prompt}
        ]
    }

    url = f"{base_url}/v1/messages"
    response = requests.post(url, headers=headers, json=payload, timeout=300)

    if response.status_code == 200:
        return response.json()['content'][0]['text']
    else:
        print(f"API Error: {response.status_code} - {response.text}")
        return None


def clean_html(raw):
    """Strip HTML tags from text"""
    if not raw:
        return ''
    return re.sub(r'<[^>]+>', '', raw)


def select_news(data, count=5):
    """Select best candidate news from data.json"""
    items = data.get('items', [])
    # Filter out items with too-short or HTML-only summaries
    candidates = []
    for i in items:
        summary = clean_html(i.get('summary', '')).strip()
        if len(summary) >= 30:
            candidates.append({**i, 'summary': summary})

    # Sort by techScore (lower is better)
    candidates.sort(key=lambda x: x.get('techScore', 0))

    # Prefer diverse interest tags
    selected = []
    seen_tags = set()
    for item in candidates:
        if len(selected) >= count:
            break
        tags = item.get('interestTags', [])
        primary_tag = tags[0] if tags else 'general'
        if primary_tag not in seen_tags or len(selected) < count:
            selected.append(item)
            seen_tags.add(primary_tag)

    # Fill up if not enough
    if len(selected) < count:
        for item in candidates:
            if len(selected) >= count:
                break
            if item not in selected:
                selected.append(item)

    return selected


def format_news_for_prompt(news_list):
    lines = []
    for i, item in enumerate(news_list, 1):
        lines.append(f"新闻{i}：")
        lines.append(f"标题：{item.get('title', '')}")
        lines.append(f"来源：{item.get('source', '')}")
        lines.append(f"摘要：{item.get('summary', '')[:400]}")
        lines.append(f"链接：{item.get('url', '')}")
        lines.append(f"兴趣标签：{', '.join(item.get('interestTags', []))}")
        lines.append("")
    return "\n".join(lines)


def parse_file_outputs(text):
    """Parse <FILE name="...">...</FILE> tags from API response"""
    pattern = r'<FILE\s+name=["\']([^"\']+)["\']>(.*?)</FILE>'
    matches = re.findall(pattern, text, re.DOTALL)
    return {name.strip(): content.strip() for name, content in matches}


def write_output(filename, content):
    path = os.path.join(os.path.dirname(__file__), '..', 'public', filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Written: {path} ({len(content)} chars)")


def build_brief_prompt(today, news_list, template_html, template_md):
    date_str = today.strftime('%Y.%m.%d')
    date_full = today.strftime('%Y年%m月%d日')
    weekday_names = ['一', '二', '三', '四', '五', '六', '日']
    weekday = weekday_names[today.weekday()]
    news_text = format_news_for_prompt(news_list)

    prompt = f"""你是"AI小白进阶日报"的内容生成助手。请根据以下候选新闻，生成今日轻度版内容。

日期：{date_full}，星期{weekday}

【候选新闻】
{news_text}

【参考模板】
以下是上一期轻度版的完整HTML（请保持完全相同的结构、CSS、类名和JavaScript，只替换内容部分如标题、日期、新闻卡片内容）：

```html
{template_html}
```

以下是上一期轻度版的公众号Markdown参考：

```markdown
{template_md}
```

【输出要求】
请生成{date_full}的轻度版内容，输出两个文件：

1. daily-brief.html：
   - 保持与参考模板完全相同的HTML结构、CSS样式、类名和JavaScript
   - 头图标题：用一个8-12字的本期主题句，要与今日新闻相关（不要"AI小白日报"这种泛标题）
   - 日期改为：{date_str} 早报
   - 3条新闻卡片（从候选新闻中选3条最合适的）：
     * 标签分配：重磅 / 突破 / 趣味（3条尽量不同标签）
     * 来源：保留原始来源信息
     * 标题：直接陈述事实，17px加粗效果对应的文字
     * 摘要：2-3句话，包含核心数据，关键数字用<strong>包裹
     * "为什么值得关注"：2个bullet，每个bullet第一句加粗，必须落回"对你我有什么用"
     * 原文链接：`<a href="..." target="_blank" rel="noopener">阅读原文 →</a>`
   - 底部固定按钮保持链接到 deep-dive-news.html

2. daily-brief-wechat.md：
   - 总字数600-900字（含标点）
   - 格式：`# 主题句 > 📅 {date_str} 早报 | 预计阅读 3 分钟` 然后 `## 🔥 标签 标题` ...
   - 底部引导用户点击"阅读原文"查看完整版

【写作风格】
- 去AI味：禁用"首先""其次""最后""值得注意的是""不难发现""在当今AI快速发展的时代""综上所述"
- 口语化：用"坦率的讲""说白了""你想想看""说真的"替代书面表达
- 数据要口语化翻译：不要只写"70%"，要写"交付时间缩短70%，也就是原来一周的活现在两天干完"
- 每个"为什么值得关注"都回答"对你我有什么用"
- 日报情绪浓度比卡兹克原文低一档，核心内容保持严肃

请严格用以下XML格式输出两个文件：

<FILE name="daily-brief.html">
（完整的HTML文件内容）
</FILE>

<FILE name="daily-brief-wechat.md">
（公众号Markdown内容）
</FILE>
"""
    return prompt


def build_deep_prompt(today, news_list, template_html, template_md):
    date_str = today.strftime('%Y.%m.%d')
    date_full = today.strftime('%Y年%m月%d日')
    weekday_names = ['一', '二', '三', '四', '五', '六', '日']
    weekday = weekday_names[today.weekday()]

    # Issue number calculation: base is 2026-05-19 (issue #1)
    base_date = datetime.date(2026, 5, 19)
    issue_num = 1
    d = base_date
    while d < today.date():
        d += datetime.timedelta(days=1)
        if d.weekday() in [1, 4]:
            issue_num += 1

    news_text = format_news_for_prompt(news_list)

    prompt = f"""你是"AI小白进阶日报"的内容生成助手。请根据以下候选新闻，生成今日深度版内容。

日期：{date_full}，星期{weekday}
期数：第 {issue_num} 期

【候选新闻】
{news_text}

【参考模板】
以下是上一期深度版的完整HTML（请保持完全相同的结构、CSS、类名和JavaScript，只替换内容部分）：

```html
{template_html}
```

以下是上一期深度版的公众号Markdown参考：

```markdown
{template_md}
```

【输出要求】
请生成{date_full}的深度版内容（第{issue_num}期），输出两个文件：

1. deep-dive-news.html：
   - 保持与参考模板完全相同的HTML结构、CSS样式、类名和JavaScript
   - 头图标题：用一个8-15字的本期主题句，与今日核心概念相关
   - 期数显示：第 {issue_num} 期 · 预计阅读 15 分钟
   - 01 AI观潮（3条手风琴新闻，从候选中选3条最合适的）：
     * 每条包含：pc-source（日期·来源）、pc-abstract（新闻简述2-3句）、pc-bg（背景补充，2-3个维度用<h4>🔍 xxx</h4>分块）、pc-analysis（为什么值得关注，2个bullet每句第一句加粗）、pc-link（相关阅读链接）
     * 标签分配：重磅 / 突破 / 趣味
   - 02 学识（知识深潜）：
     * 从01的某条新闻中自然引出1个核心概念
     * 永远从问题出发，不要直接下定义
     * 用一个生活化类比解释概念（用.analogy-box包裹）
     * 工具对比：3档（❌不用 / ⚠️手动 / ✅最佳方案），用.compare-card.bad/.mid/.good包裹，差距拉得足够大，每档配一句人话点评
     * 最后用一个.knowledge-summary做总结
   - 03 悟心（灵魂洞察）：
     * 必须有一个类比/故事包裹观点（禁止套用"相机没有取代画家"等往期类比，必须原创新的）
     * 先站读者角度承认焦虑（"很多人担心..."），再说"但关键在..."
     * 只保留一处升华（引言和结尾只留一个）
     * 情绪真实，用体感记忆代替知识性描述
     * 内容要从当期新闻中自然生长出来，不能硬塞
   - 04 相询（今日一问）：
     * 问题固定："这期哪个方向你还没看够？或者下期想让我往哪挖？（可多选）"
     * 选项：3个预测话题（从本期内容埋的钩子里选）+ "暂无想法，等下期看看 👀"
     * 每个选项配一句解释（为什么这个话题值得下期讲）
     * 保留自定义输入框和提交按钮

2. deep-dive-wechat.md：
   - 总字数400-600字（含标点），只当"钩子"用
   - 格式：`# 主题句 > 📅 第 X 期 · 预计阅读 15 分钟 > 🎯 本期深潜：[核心概念]`
   - 包含：本期速览（3条一句话概括）、本期核心洞察（200字左右）、深潜内容预告
   - 底部引导点击"阅读原文"查看完整深度版

【写作风格】
- 去AI味：禁用"首先""其次""最后""值得注意的是""不难发现""在当今AI快速发展的时代""综上所述""让我们来看看"
- 口语化：用"坦率的讲""说白了""你想想看""说真的""怎么说呢""其实吧"替代书面表达
- 数据要口语化翻译，每个数字都解释"这意味着什么"
- 延伸启发必须落回读者："对你我来说"
- 深度版新闻要与近期轻度版尽量差异化选题（基于候选新闻中与图像/视频/工具/概念相关的新鲜角度）

请严格用以下XML格式输出两个文件：

<FILE name="deep-dive-news.html">
（完整的HTML文件内容）
</FILE>

<FILE name="deep-dive-wechat.md">
（公众号Markdown内容）
</FILE>
"""
    return prompt


def main():
    today_type, today = get_today_type()
    print(f"Today (UTC+8): {today.strftime('%Y-%m-%d %H:%M')}")
    print(f"Content type: {today_type}")

    data = read_data_json()
    news = select_news(data, count=5)
    print(f"Selected {len(news)} candidate news items")

    script_dir = os.path.dirname(__file__)

    if today_type == 'brief':
        template_html = read_file('public/daily-brief.html')
        template_md = read_file('public/daily-brief-wechat.md')
        prompt = build_brief_prompt(today, news, template_html, template_md)
        expected_files = ['daily-brief.html', 'daily-brief-wechat.md']
    else:
        template_html = read_file('public/deep-dive-news.html')
        template_md = read_file('public/deep-dive-wechat.md')
        prompt = build_deep_prompt(today, news, template_html, template_md)
        expected_files = ['deep-dive-news.html', 'deep-dive-wechat.md']

    print(f"Prompt length: {len(prompt)} chars, calling Claude API...")
    response = call_claude_api(prompt)

    if not response:
        print("ERROR: Failed to generate content from API")
        return False

    files = parse_file_outputs(response)
    print(f"API returned files: {list(files.keys())}")

    success = True
    for filename in expected_files:
        if filename in files:
            write_output(filename, files[filename])
        else:
            print(f"WARNING: Expected file {filename} not found in API response")
            success = False

    if success:
        print("All files generated successfully.")
    else:
        print("Some files were missing. Please check the API response.")

    return success


if __name__ == '__main__':
    main()
