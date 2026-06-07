let stockLabels = {};

const DATA_FILE = '/stocks/stock_label.json';

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2000);
}

function loadStockLabels() {
  return fetch(DATA_FILE, { cache: 'no-cache' })
    .then(response => {
      if (!response.ok) {
        throw new Error('加载失败');
      }
      return response.json();
    })
    .then(data => {
      stockLabels = data;
    })
    .catch(error => {
      console.error('加载股票标签数据失败:', error);
      stockLabels = {};
    });
}

function saveStockLabels() {
  console.log('saveStockLabels called, DATA_FILE:', DATA_FILE);
  console.log('Current stockLabels:', JSON.stringify(stockLabels, null, 2));
  
  return fetch(DATA_FILE, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(stockLabels, null, 2),
  })
    .then(response => {
      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);
      if (!response.ok) {
        throw new Error('保存失败，状态码: ' + response.status);
      }
      return response.json();
    })
    .then(result => {
      console.log('Server response:', result);
      if (result.data) {
        stockLabels = result.data;
        console.log('Updated stockLabels from server:', JSON.stringify(stockLabels, null, 2));
      } else {
        return loadStockLabels();
      }
    })
    .catch(error => {
      console.error('保存股票标签数据失败:', error);
      showToast('保存失败，请检查服务端配置', 'error');
      throw error;
    });
}

function queryLabels() {
  const stockInput = document.getElementById('stock-input').value.trim().toLowerCase();
  const tagInput = document.getElementById('tag-input').value.trim().toLowerCase();
  
  let results = [];
  
  Object.entries(stockLabels).forEach(([code, stock]) => {
    stock.label.forEach(tag => {
      const matchStock = !stockInput || 
        code.toLowerCase().includes(stockInput) || 
        stock.name.toLowerCase().includes(stockInput);
      const matchTag = !tagInput || tag.toLowerCase().includes(tagInput);
      
      if (matchStock && matchTag) {
        results.push({
          code: code,
          name: stock.name,
          label: tag
        });
      }
    });
  });
  
  results.sort((a, b) => {
    if (a.code !== b.code) return a.code.localeCompare(b.code);
    return a.label.localeCompare(b.label);
  });
  
  renderTable(results);
}

function renderTable(data) {
  const tbody = document.getElementById('table-body');
  const countDiv = document.getElementById('result-count');
  
  if (data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">暂无数据</td></tr>';
    countDiv.textContent = '共 0 条记录';
    return;
  }
  
  countDiv.textContent = `共 ${data.length} 条记录`;
  
  tbody.innerHTML = data.map(item => `
    <tr>
      <td class="code">${item.code}</td>
      <td>${item.name}</td>
      <td><span class="tag">${item.label}</span></td>
      <td><button class="delete-btn" onclick="removeTag('${item.code}', '${item.label}')">删除</button></td>
    </tr>
  `).join('');
}

function addTag() {
  const stockInput = document.getElementById('stock-input').value.trim();
  const tagInput = document.getElementById('tag-input').value.trim();
  
  if (!stockInput) {
    showToast('请输入股票代码', 'error');
    return;
  }
  
  if (!tagInput) {
    showToast('请输入标签名称', 'error');
    return;
  }
  
  if (!/^\d{6}$/.test(stockInput)) {
    showToast('股票代码必须是6位数字', 'error');
    return;
  }
  
  const stockCode = stockInput;
  
  if (!stockLabels[stockCode]) {
    stockLabels[stockCode] = {
      name: stockCode,
      label: []
    };
  }
  
  if (stockLabels[stockCode].label.includes(tagInput)) {
    showToast('该标签已存在', 'error');
    return;
  }
  
  stockLabels[stockCode].label.push(tagInput);
  
  saveStockLabels().then(() => {
    showToast('标签添加成功', 'success');
    document.getElementById('tag-input').value = '';
    queryLabelsByStock(stockCode);
  });
}

function queryLabelsByStock(stockCode) {
  let results = [];
  
  if (stockLabels[stockCode]) {
    stockLabels[stockCode].label.forEach(tag => {
      results.push({
        code: stockCode,
        name: stockLabels[stockCode].name,
        label: tag
      });
    });
  }
  
  results.sort((a, b) => a.label.localeCompare(b.label));
  renderTable(results);
}

function removeTag(stockCode, tagName) {
  if (!stockLabels[stockCode]) return;
  
  const index = stockLabels[stockCode].label.indexOf(tagName);
  if (index > -1) {
    stockLabels[stockCode].label.splice(index, 1);
    
    saveStockLabels().then(() => {
      showToast('标签删除成功', 'success');
      const currentStockInput = document.getElementById('stock-input').value.trim();
      if (currentStockInput) {
        queryLabelsByStock(currentStockInput);
      } else {
        queryLabels();
      }
    });
  }
}

function setupEventListeners() {
  const queryBtn = document.getElementById('query-btn');
  const addBtn = document.getElementById('add-btn');
  
  console.log('queryBtn:', queryBtn);
  console.log('addBtn:', addBtn);
  
  if (queryBtn) {
    queryBtn.addEventListener('click', queryLabels);
  }
  if (addBtn) {
    addBtn.addEventListener('click', addTag);
  }
  
  document.getElementById('stock-input').addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      queryLabels();
    }
  });
  
  document.getElementById('tag-input').addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      addTag();
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM loaded, setting up listeners');
  setupEventListeners();
  loadStockLabels().then(() => {
    renderTable([]);
  });
});