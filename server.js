const http = require('http');
const fs = require('fs');
const path = require('path');
const { fetchAndFilter } = require('./fetch-data');

const PORT = 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon'
};

// 静态文件服务
function serveStatic(req, res) {
  const url = req.url === '/' ? '/index.html' : req.url;
  const filePath = path.join(PUBLIC_DIR, decodeURIComponent(url.split('?')[0]));
  const ext = path.extname(filePath).toLowerCase();

  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    res.writeHead(404);
    res.end('Not found');
    return;
  }

  const content = fs.readFileSync(filePath);
  res.writeHead(200, {
    'Content-Type': MIME_TYPES[ext] || 'application/octet-stream',
    'Cache-Control': ext === '.json' ? 'no-cache' : 'max-age=3600'
  });
  res.end(content);
}

// 刷新数据
async function handleRefresh(req, res) {
  try {
    const result = await fetchAndFilter();
    fs.writeFileSync(path.join(PUBLIC_DIR, 'data.json'), JSON.stringify(result, null, 2));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, count: result.totalSelected }));
  } catch (err) {
    res.writeHead(500);
    res.end(JSON.stringify({ error: err.message }));
  }
}

// 启动时拉取一次数据
async function initData() {
  try {
    const dataPath = path.join(PUBLIC_DIR, 'data.json');
    // 如果数据不存在或超过1小时，重新拉取
    let needFetch = true;
    if (fs.existsSync(dataPath)) {
      const stat = fs.statSync(dataPath);
      const age = Date.now() - stat.mtimeMs;
      if (age < 60 * 60 * 1000) needFetch = false;
    }

    if (needFetch) {
      console.log('📡 初始化数据...');
      const result = await fetchAndFilter();
      fs.writeFileSync(dataPath, JSON.stringify(result, null, 2));
    } else {
      console.log('📂 使用缓存数据');
    }
  } catch (err) {
    console.error('❌ 初始化数据失败:', err.message);
  }
}

// HTTP 服务器
const server = http.createServer((req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.url === '/api/refresh' && req.method === 'POST') {
    handleRefresh(req, res);
    return;
  }

  serveStatic(req, res);
});

// 启动
(async () => {
  await initData();

  server.listen(PORT, () => {
    console.log('');
    console.log('🚀 AI 每日精选 已启动！');
    console.log('');
    console.log(`   本地访问: http://localhost:${PORT}`);
    console.log('');
    console.log('   操作提示:');
    console.log('   • 打开浏览器访问上面的链接');
    console.log('   • 点击顶部标签可筛选分类');
    console.log('   • 点击"刷新"按钮获取最新数据');
    console.log('   • 按 Ctrl+C 停止服务');
    console.log('');
  });
})();
