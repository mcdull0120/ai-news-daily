const https = require('https');
const fs = require('fs');
const path = require('path');

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0';
const BASE_URL = 'aihot.virxact.com';
const OUTPUT_PATH = path.join(__dirname, 'public', 'data.json');

// 确保 public 目录存在
if (!fs.existsSync(path.join(__dirname, 'public'))) {
  fs.mkdirSync(path.join(__dirname, 'public'));
}

// ========== 筛选配置 ==========

// 1. 负面/敏感词：直接过滤
const BLOCKED_KEYWORDS = [
  '死亡', '致死', '自杀', '犯罪', '黑客', '投毒', '漏洞', '攻击', '窃取',
  '诉讼', '起诉', '官司', '被告', '原告', '赔偿', '判决', '宣判',
  '裁员', '失业', '造假', '欺诈', '骗局', '泄露', '隐私泄露',
  '事故', '灾难', '危机', '崩溃', '暴跌', '崩盘'
];

// 2. 过于技术/开发者向：降低权重或过滤
const TECH_KEYWORDS = [
  '基准测试', 'benchmark', '权重', '参数', '架构', '骨干网络',
  '训练方案', '强化学习', '蒸馏', '梯度', '损失函数', '推理速度',
  '注意力机制', 'transformer', 'token', '微调', 'fine-tuning',
  'npm', 'git', '代码库', 'sdk', 'cli', 'api', '编程接口',
  '论文', 'arxiv', '技术报告深度', '模型结构', '量化',
  '多任务模型', '视觉语言模型', '原生多模态'
];

// 3. 兴趣标签映射
const INTEREST_TAGS = {
  creative: {
    emoji: '🎨',
    label: '创意',
    desc: 'AI做图/视频/音乐',
    keywords: ['视频', '图像', '图片', '绘画', '画图', '设计', '音乐', '音频', 'sora', 'midjourney', 'runway', 'pika', 'suno', 'flux', '动画', '摄影', '摄像', '剪辑', '生成图', '文生图', '文生视频', '配音', '音效', '3d', '渲染', '视觉']
  },
  app: {
    emoji: '💻',
    label: '应用',
    desc: 'AI做工具/网站/智能体',
    keywords: ['应用', 'app', '工具', '平台', '软件', '智能体', 'agent', '小程序', '网站', '建站', '无代码', '低代码', 'cursor', 'claude code', '产品', '上线', '发布', 'v0', 'replit']
  },
  writing: {
    emoji: '✍️',
    label: '文案',
    desc: 'AI写作/内容创作',
    keywords: ['写作', '文案', '内容', '自媒体', '笔记', '文档', '文章', '博客', '脚本', '小说', '故事', '营销', '稿件', '剧本', ' prompt', '提示词']
  },
  education: {
    emoji: '🎓',
    label: '教育',
    desc: 'AI学习/教学',
    keywords: ['教育', '学习', '教学', '课程', '辅导', '学生', '老师', '学校', '知识', '培训', '考试', '教材', '学堂', 'tutor', '导师']
  },
  productivity: {
    emoji: '🏢',
    label: '提效',
    desc: 'AI办公/效率',
    keywords: ['办公', '效率', 'ppt', 'excel', '表格', '文档', '会议', '自动化', '工作流', '邮件', '日程', '管理', '协作', 'copilot', 'notion', 'gamma', '幻灯片', '汇报', '整理']
  }
};

// ========== 工具函数 ==========

function fetchJSON(path) {
  return new Promise((resolve, reject) => {
    const req = https.get({
      hostname: BASE_URL,
      path: path,
      headers: { 'User-Agent': UA }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('JSON parse error: ' + e.message));
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(15000, () => reject(new Error('Request timeout')));
  });
}

function containsAny(text, keywords) {
  const lower = text.toLowerCase();
  return keywords.some(k => lower.includes(k.toLowerCase()));
}

function calcTechScore(item) {
  const text = `${item.title} ${item.summary || ''}`;
  let score = 0;
  if (containsAny(text, TECH_KEYWORDS)) score += 2;
  // 模型类内容默认技术分高一点
  if (item.category === 'ai-models') score += 1;
  // 但有通俗摘要的，降低技术分
  if (item.summary && item.summary.length > 20 && !containsAny(item.summary, ['训练', '蒸馏', '骨干网络', '量化'])) {
    score -= 1;
  }
  return score;
}

function matchInterestTags(item) {
  const text = `${item.title} ${item.summary || ''}`;
  const tags = [];
  for (const [key, config] of Object.entries(INTEREST_TAGS)) {
    if (containsAny(text, config.keywords)) {
      tags.push(key);
    }
  }
  return tags;
}

function formatDate(iso) {
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  const hours = Math.floor(diff / (1000 * 60 * 60));
  if (hours < 1) return '刚刚';
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days === 1) return '昨天';
  if (days < 7) return `${days}天前`;
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

// ========== 主逻辑 ==========

async function fetchAndFilter() {
  console.log('📡 正在从 AI HOT 拉取数据...');

  // 拉最近7天精选
  const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const data = await fetchJSON(`/api/public/items?mode=selected&since=${since}&take=100`);

  if (!data.items || !Array.isArray(data.items)) {
    throw new Error('Invalid response format');
  }

  console.log(`📥 获取到 ${data.items.length} 条原始数据`);

  // 第一层筛选：过滤负面+过于技术
  let filtered = data.items.filter(item => {
    const text = `${item.title} ${item.summary || ''}`;

    // 过滤负面敏感
    if (containsAny(text, BLOCKED_KEYWORDS)) return false;

    // 过滤过于技术的（技术分 >= 3 的不要）
    const techScore = calcTechScore(item);
    if (techScore >= 3) return false;

    return true;
  });

  console.log(`🔍 过滤后剩余 ${filtered.length} 条`);

  // 为每条数据打上兴趣标签
  filtered = filtered.map(item => {
    const tags = matchInterestTags(item);
    const techScore = calcTechScore(item);
    return {
      ...item,
      interestTags: tags,
      techScore,
      formattedTime: formatDate(item.publishedAt)
    };
  });

  // 优先选择有明确兴趣标签匹配的内容
  const withTags = filtered.filter(item => item.interestTags.length > 0);
  const withoutTags = filtered.filter(item => item.interestTags.length === 0);

  console.log(`🏷️  有明确兴趣标签匹配: ${withTags.length} 条`);

  // 精选策略：按标签分组，每个标签最多2条，优先选技术分低的（更通俗）
  const selected = [];
  const tagCount = {};
  const usedIds = new Set();

  // 先选有明确标签的，按标签均匀分布
  const sortedByTech = [...withTags].sort((a, b) => a.techScore - b.techScore);

  for (const item of sortedByTech) {
    if (selected.length >= 8) break;
    if (usedIds.has(item.id)) continue;

    // 检查标签配额
    const primaryTag = item.interestTags[0];
    if (tagCount[primaryTag] && tagCount[primaryTag] >= 2) continue;

    selected.push(item);
    usedIds.add(item.id);
    tagCount[primaryTag] = (tagCount[primaryTag] || 0) + 1;
  }

  // 如果不够6条，从有标签但未入选的补充（允许标签超限）
  if (selected.length < 6) {
    for (const item of sortedByTech) {
      if (selected.length >= 6) break;
      if (usedIds.has(item.id)) continue;
      selected.push(item);
      usedIds.add(item.id);
    }
  }

  // 如果还不够，从无标签但通俗的内容补充
  if (selected.length < 6) {
    const sortedNoTags = [...withoutTags].sort((a, b) => a.techScore - b.techScore);
    for (const item of sortedNoTags) {
      if (selected.length >= 6) break;
      if (usedIds.has(item.id)) continue;
      selected.push({ ...item, interestTags: ['general'] });
      usedIds.add(item.id);
    }
  }

  console.log(`✅ 最终精选 ${selected.length} 条`);

  // 按标签分组
  const grouped = {};
  for (const item of selected) {
    const tag = item.interestTags[0] || 'general';
    if (!grouped[tag]) grouped[tag] = [];
    grouped[tag].push(item);
  }

  // 输出统计
  for (const [tag, items] of Object.entries(grouped)) {
    const config = INTEREST_TAGS[tag] || { emoji: '📰', label: '综合', desc: '其他资讯' };
    console.log(`  ${config.emoji} ${config.label}: ${items.length} 条`);
  }

  return {
    generatedAt: new Date().toISOString(),
    totalSource: data.items.length,
    totalFiltered: filtered.length,
    totalSelected: selected.length,
    grouped,
    items: selected
  };
}

// 如果直接运行此文件
if (require.main === module) {
  fetchAndFilter()
    .then(result => {
      fs.writeFileSync(OUTPUT_PATH, JSON.stringify(result, null, 2));
      console.log(`\n💾 数据已保存到 ${OUTPUT_PATH}`);
    })
    .catch(err => {
      console.error('❌ 错误:', err.message);
      process.exit(1);
    });
}

module.exports = { fetchAndFilter, INTEREST_TAGS };
