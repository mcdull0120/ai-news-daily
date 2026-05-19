const TAG_CONFIG = {
  creative:   { emoji: '🎨', label: '创意',   desc: 'AI做图/视频/音乐',  className: 'tag-creative' },
  app:        { emoji: '💻', label: '应用',   desc: 'AI做工具/网站',      className: 'tag-app' },
  writing:    { emoji: '✍️', label: '文案',   desc: 'AI写作/内容',        className: 'tag-writing' },
  education:  { emoji: '🎓', label: '教育',   desc: 'AI学习/教学',        className: 'tag-education' },
  productivity:{ emoji: '🏢', label: '提效',  desc: 'AI办公/效率',        className: 'tag-productivity' },
  general:    { emoji: '📰', label: '综合',   desc: '其他资讯',           className: 'tag-general' }
};

let currentData = null;
let currentFilter = 'all';

const contentEl = document.getElementById('content');
const updateTimeEl = document.getElementById('updateTime');
const refreshBtn = document.getElementById('refreshBtn');
const filterBtns = document.querySelectorAll('.filter-btn');

// 初始化
async function init() {
  await loadData();
  setupFilters();
  setupRefresh();
}

// 加载数据
async function loadData() {
  showLoading();
  try {
    const res = await fetch('data.json?t=' + Date.now());
    if (!res.ok) throw new Error('加载失败');
    currentData = await res.json();
    render();
  } catch (err) {
    showError('数据加载失败，请确保已运行 node fetch-data.js 生成数据');
  }
}

// 渲染
function render() {
  if (!currentData) return;

  const { generatedAt, grouped, items } = currentData;
  const date = new Date(generatedAt);
  updateTimeEl.textContent = `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')} 更新`;

  // 按当前筛选过滤
  let displayItems = items;
  if (currentFilter !== 'all') {
    displayItems = items.filter(item => item.interestTags.includes(currentFilter));
  }

  if (displayItems.length === 0) {
    contentEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <p>该分类下暂无今日内容</p>
        <p style="font-size:12px;color:#bbb;margin-top:8px;">试试切换其他标签</p>
      </div>
    `;
    return;
  }

  // 按标签分组渲染
  const groupedToRender = {};
  for (const item of displayItems) {
    const tag = item.interestTags[0] || 'general';
    if (!groupedToRender[tag]) groupedToRender[tag] = [];
    groupedToRender[tag].push(item);
  }

  // 按优先级排序标签
  const tagOrder = ['creative', 'app', 'writing', 'education', 'productivity', 'general'];
  const sortedTags = tagOrder.filter(t => groupedToRender[t]);

  let html = '';
  for (const tag of sortedTags) {
    const tagItems = groupedToRender[tag];
    const config = TAG_CONFIG[tag] || TAG_CONFIG.general;
    html += `
      <div class="section-title">
        <span>${config.emoji}</span>
        <span>${config.label}</span>
        <span class="section-count">${tagItems.length}</span>
      </div>
    `;
    for (const item of tagItems) {
      html += renderCard(item);
    }
  }

  contentEl.innerHTML = html;
}

// 渲染单张卡片
function renderCard(item) {
  const primaryTag = item.interestTags[0] || 'general';
  const tagConfig = TAG_CONFIG[primaryTag] || TAG_CONFIG.general;
  const otherTags = item.interestTags.slice(1).map(t => {
    const c = TAG_CONFIG[t];
    return c ? `<span class="tag ${c.className}">${c.emoji} ${c.label}</span>` : '';
  }).join('');

  return `
    <article class="card" data-id="${item.id}">
      <div class="card-header">
        <span class="tag ${tagConfig.className}">${tagConfig.emoji} ${tagConfig.label}</span>
        ${otherTags}
      </div>
      <h3 class="card-title">${escapeHtml(item.title)}</h3>
      <p class="card-summary">${escapeHtml(item.summary || '暂无摘要')}</p>
      <div class="card-footer">
        <span class="card-meta">${item.source} · ${item.formattedTime}</span>
        <a href="${item.url}" target="_blank" rel="noopener" class="card-link">阅读原文 →</a>
      </div>
    </article>
  `;
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// 筛选
function setupFilters() {
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      render();
    });
  });
}

// 刷新
function setupRefresh() {
  refreshBtn.addEventListener('click', async () => {
    refreshBtn.classList.add('spinning');
    await loadData();
    refreshBtn.classList.remove('spinning');
  });
}

function showLoading() {
  contentEl.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <p>正在加载精选内容...</p>
    </div>
  `;
}

function showError(msg) {
  contentEl.innerHTML = `
    <div class="error-state">
      <p>😅 ${msg}</p>
      <button onclick="location.reload()">重新加载</button>
    </div>
  `;
}

// 启动
init();
