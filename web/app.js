const TABLE_HEAD = {
  seq: '序号',
  bond_id: '转债代码',
  bond_name: '转债名称',
  stock_id: '正股代码',
  stock_name: '正股名称',
  bond_price: '转债最新价',
  bond_change: '转债涨跌幅',
  stock_price: '正股最新价',
  stock_change: '正股涨跌幅',
  premium_rate: '转股溢价率',
  force_redeem_days: '强赎天计数',
  force_redeem_space: '强赎空间',
  convert_price: '转股价',
  force_redeem_price: '强赎价',
  left_market_value: '剩余规模',
  redeem_status: '赎回状态',
  redeem_price_detail: '赎回价',
  first_trade_date: '首个交易日',
  maturity_price: '到期价',
  redeem_price: '到期赎回价',
  convert_ratio: '已转股比例',
  market_value_ratio: '转债总市值占比',
  lowering_trigger_price: '下修触发价',
  sell_start_date: '回售起算日',
  listing_date: '上市日',
  year_left: '剩余年限',
  force_redeem_status: '强赎状态',
  last_trade_date: '最后交易日',
  last_convert_date: '最后转股日',
};

const COLUMN_FILTER_KEYS = [
  'bond_id', 'bond_name', 'stock_id', 'stock_name',
  'bond_price', 'bond_change', 'stock_price', 'stock_change',
  'premium_rate', 'force_redeem_days', 'force_redeem_space', 'convert_price', 'force_redeem_price',
  'left_market_value', 'year_left', 'maturity_price', 'force_redeem_status'
];

let data = [];
let filteredData = [];
let currentSort = { key: 'seq', order: 'asc' };
let refreshInterval = null;
let visibleColumns = [...COLUMN_FILTER_KEYS];
let currentDataSource = 'all';
let selectedRowIndex = null; // 选中行的索引

function calculateForceRedeemSpace(row) {
  const forceRedeemPrice = row.force_redeem_price != null ? Number(row.force_redeem_price) : null;
  const stockPrice = row.stock_price != null ? Number(row.stock_price) : null;

  if (forceRedeemPrice == null || stockPrice == null || stockPrice === 0) {
    return '';
  }

  const space = (forceRedeemPrice / stockPrice) - 1;
  return (space * 100).toFixed(2) + '%';
}

function isNumeric(value) {
  return !isNaN(parseFloat(value)) && isFinite(value);
}

function formatDisplayValue(key, value, row) {
  if (key === 'force_redeem_space') {
    return calculateForceRedeemSpace(row);
  }

  if (value == null || value === '') return '';

  if (key === 'bond_change' || key === 'stock_change') {
    const num = parseFloat(value);
    if (!isNaN(num)) {
      return num.toFixed(2) + '%';
    }
    return value;
  }

  if (key === 'premium_rate') {
    const num = parseFloat(value);
    if (!isNaN(num)) {
      return num.toFixed(2) + '%';
    }
    return value;
  }

  if (key === 'bond_price' || key === 'stock_price' || key === 'convert_price' || key === 'force_redeem_price' || key === 'left_market_value' || key === 'maturity_price') {
    const num = parseFloat(value);
    if (!isNaN(num)) {
      return num.toFixed(2);
    }
    return value;
  }

  if (key === 'year_left') {
    const num = parseFloat(value);
    if (!isNaN(num)) {
      return num.toFixed(3);
    }
    return value;
  }

  return value;
}

function applySort() {
  const { key, order } = currentSort;
  filteredData.sort((a, b) => {
    let valA = a[key];
    let valB = b[key];

    if (key === 'force_redeem_space') {
      const forceRedeemPriceA = a.force_redeem_price != null ? Number(a.force_redeem_price) : null;
      const stockPriceA = a.stock_price != null ? Number(a.stock_price) : null;
      valA = (forceRedeemPriceA != null && stockPriceA != null && stockPriceA !== 0) ?
        ((forceRedeemPriceA / stockPriceA) - 1) : null;

      const forceRedeemPriceB = b.force_redeem_price != null ? Number(b.force_redeem_price) : null;
      const stockPriceB = b.stock_price != null ? Number(b.stock_price) : null;
      valB = (forceRedeemPriceB != null && stockPriceB != null && stockPriceB !== 0) ?
        ((forceRedeemPriceB / stockPriceB) - 1) : null;
    } else if (key === 'force_redeem_days') {
      valA = a.force_redeem_days != null ? parseInt(String(a.force_redeem_days).split('/')[0]) : null;
      valB = b.force_redeem_days != null ? parseInt(String(b.force_redeem_days).split('/')[0]) : null;
    }

    if (valA != null && valB != null && !isNaN(valA) && !isNaN(valB)) {
      return order === 'asc' ? valA - valB : valB - valA;
    }

    if (valA == null && valB == null) return 0;
    if (valA == null) return order === 'asc' ? 1 : -1;
    if (valB == null) return order === 'asc' ? -1 : 1;

    const strA = String(valA).toLowerCase();
    const strB = String(valB).toLowerCase();
    return order === 'asc' ? strA.localeCompare(strB) : strB.localeCompare(strA);
  });

  renderTable();
}

function sortData(key) {
  console.log('sortData called, key:', key);
  const order = currentSort.key === key && currentSort.order === 'asc' ? 'desc' : 'asc';
  currentSort = { key, order };
  applySort();
}

function renderTable() {
  console.log('renderTable called, filteredData length:', filteredData.length);
  const table = document.getElementById('bond-table');
  console.log('table element:', table);
  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');
  console.log('thead:', thead, 'tbody:', tbody);

  const avgBondPrice = filteredData.reduce((sum, row) => sum + (parseFloat(row.bond_price) || 0), 0) / filteredData.length;
  const avgBondChange = filteredData.reduce((sum, row) => sum + (parseFloat(row.bond_change) || 0), 0) / filteredData.length;
  const avgStockChange = filteredData.reduce((sum, row) => sum + (parseFloat(row.stock_change) || 0), 0) / filteredData.length;
  const avgPremiumRate = filteredData.reduce((sum, row) => sum + (parseFloat(row.premium_rate) || 0), 0) / filteredData.length;

  thead.innerHTML = `
    <tr>
      ${visibleColumns.map(key => {
        let avgDisplay = '';
        if (key === 'bond_price') {
          const color = avgBondPrice >= 0 ? '#e83123' : '#00a000';
          avgDisplay = `<span style="color: ${color}; font-size: 11px; margin-left: 6px;">${avgBondPrice.toFixed(2)}</span>`;
        } else if (key === 'bond_change') {
          const color = avgBondChange >= 0 ? '#e83123' : '#00a000';
          avgDisplay = `<span style="color: ${color}; font-size: 11px; margin-left: 6px;">${avgBondChange.toFixed(2)}%</span>`;
        } else if (key === 'stock_change') {
          const color = avgStockChange >= 0 ? '#e83123' : '#00a000';
          avgDisplay = `<span style="color: ${color}; font-size: 11px; margin-left: 6px;">${avgStockChange.toFixed(2)}%</span>`;
        } else if (key === 'premium_rate') {
          const color = avgPremiumRate >= 0 ? '#e83123' : '#00a000';
          avgDisplay = `<span style="color: ${color}; font-size: 11px; margin-left: 6px;">${avgPremiumRate.toFixed(2)}%</span>`;
        }
        return `
          <th data-key="${key}" onclick="sortData('${key}')">
            ${TABLE_HEAD[key]}
            ${currentSort.key === key ? (currentSort.order === 'asc' ? ' ↑' : ' ↓') : ''}
            ${avgDisplay}
          </th>
        `;
      }).join('')}
    </tr>
  `;

  tbody.innerHTML = filteredData.map((row, index) => {
    row.seq = index + 1;
    return `
      <tr data-index="${index}" class="${selectedRowIndex === index ? 'selected' : ''}" onclick="handleRowClick(${index})">
        ${visibleColumns.map(key => {
          const value = formatDisplayValue(key, row[key], row);
          let className = '';
          if (key === 'bond_price' || key === 'bond_change') {
            const bondChange = parseFloat(row['bond_change']);
            className = bondChange > 0 ? 'up' : (bondChange < 0 ? 'down' : '');
          } else if (key === 'stock_price' || key === 'stock_change') {
            const stockChange = parseFloat(row['stock_change']);
            className = stockChange > 0 ? 'up' : (stockChange < 0 ? 'down' : '');
          } else if (key === 'premium_rate' || key === 'force_redeem_space') {
            className = parseFloat(value) > 0 ? 'up' : (parseFloat(value) < 0 ? 'down' : '');
          } else if (key === 'bond_name') {
            const premiumRate = parseFloat(row['premium_rate']) || 0;
            const forceRedeemSpaceStr = calculateForceRedeemSpace(row);
            const forceRedeemSpace = forceRedeemSpaceStr ? parseFloat(forceRedeemSpaceStr.replace('%', '')) : 0;
            if (premiumRate - forceRedeemSpace < 7) {
              className = 'red-name';
            }
          }
          return `<td class="${className}">${value}</td>`;
        }).join('')}
      </tr>
    `;
  }).join('');

  document.getElementById('record-count').textContent = `共 ${filteredData.length} 条记录`;
}

function handleRowClick(index) {
  if (selectedRowIndex === index) {
    selectedRowIndex = null;
  } else {
    selectedRowIndex = index;
  }
  renderTable();
}

function applyFilters() {
  console.log('applyFilters called, data length:', data.length);
  const searchQuery = document.getElementById('search-input').value.toLowerCase();
  const yearLeftMin = parseFloat(document.getElementById('year-left-min').value);
  const yearLeftMax = parseFloat(document.getElementById('year-left-max').value);
  const bondPriceMin = parseFloat(document.getElementById('bond-price-min').value);
  const bondPriceMax = parseFloat(document.getElementById('bond-price-max').value);

  filteredData = data.filter(row => {
    if (searchQuery) {
      const searchFields = ['bond_name', 'bond_id', 'stock_name', 'stock_id'];
      const match = searchFields.some(field =>
        String(row[field]).toLowerCase().includes(searchQuery)
      );
      if (!match) return false;
    }

    if (!isNaN(yearLeftMin) && parseFloat(row.year_left) < yearLeftMin) return false;
    if (!isNaN(yearLeftMax) && parseFloat(row.year_left) > yearLeftMax) return false;

    if (!isNaN(bondPriceMin) && parseFloat(row.bond_price) < bondPriceMin) return false;
    if (!isNaN(bondPriceMax) && parseFloat(row.bond_price) > bondPriceMax) return false;

    const statusCheckboxes = document.querySelectorAll('#status-filter-menu input[type="checkbox"]:checked');
    if (statusCheckboxes.length > 0) {
      const selectedStatus = Array.from(statusCheckboxes).map(cb => cb.value);
      if (!selectedStatus.includes(row.force_redeem_status)) return false;
    }

    return true;
  });

  applySort();
}

function loadData() {
  console.log('loadData called');
  document.getElementById('record-count').textContent = '加载中...';

  if (currentDataSource === 'all') {
    fetch('../kzz/all.json')
      .then(response => {
        console.log('all.json response status:', response.status);
        return response.json();
      })
      .then(jsonData => {
        console.log('all.json data length:', jsonData.length);
        data = jsonData;
        applyFilters();
        document.getElementById('refresh-status').textContent = '更新时间: ' + new Date().toLocaleString();
      })
      .catch(error => {
        console.error('加载数据失败:', error);
        document.getElementById('record-count').textContent = '加载失败，请刷新重试';
      });
  } else if (currentDataSource === 'small') {
    fetch('../kzz/all.json')
      .then(response => {
        console.log('all.json response status:', response.status);
        return response.json();
      })
      .then(jsonData => {
        console.log('all.json data length:', jsonData.length);
        data = jsonData.filter(row => {
          const leftMarketValue = parseFloat(row.left_market_value);
          return !isNaN(leftMarketValue) && leftMarketValue < 5;
        });
        console.log('filtered small data length:', data.length);
        applyFilters();
        document.getElementById('refresh-status').textContent = '更新时间: ' + new Date().toLocaleString();
      })
      .catch(error => {
        console.error('加载数据失败:', error);
        document.getElementById('record-count').textContent = '加载失败，请刷新重试';
      });
  } else if (currentDataSource === 'low_premium') {
    fetch('../kzz/all.json')
      .then(response => {
        console.log('all.json response status:', response.status);
        return response.json();
      })
      .then(jsonData => {
        console.log('all.json data length:', jsonData.length);
        data = jsonData.filter(row => {
          const premiumRate = parseFloat(row.premium_rate);
          return !isNaN(premiumRate) && premiumRate < 60;
        });
        console.log('filtered low_premium data length:', data.length);
        applyFilters();
        document.getElementById('refresh-status').textContent = '更新时间: ' + new Date().toLocaleString();
      })
      .catch(error => {
        console.error('加载数据失败:', error);
        document.getElementById('record-count').textContent = '加载失败，请刷新重试';
      });
  } else if (currentDataSource === 'three_low') {
    fetch('../kzz/all.json')
      .then(response => {
        console.log('all.json response status:', response.status);
        return response.json();
      })
      .then(jsonData => {
        console.log('all.json data length:', jsonData.length);
        data = jsonData.filter(row => {
          const premiumRate = parseFloat(row.premium_rate);
          const leftMarketValue = parseFloat(row.left_market_value);
          const bondPrice = parseFloat(row.bond_price);
          return !isNaN(premiumRate) && premiumRate < 60 &&
                 !isNaN(leftMarketValue) && leftMarketValue < 5 &&
                 !isNaN(bondPrice) && bondPrice < 170;
        });
        console.log('filtered three_low data length:', data.length);
        applyFilters();
        document.getElementById('refresh-status').textContent = '更新时间: ' + new Date().toLocaleString();
      })
      .catch(error => {
        console.error('加载数据失败:', error);
        document.getElementById('record-count').textContent = '加载失败，请刷新重试';
      });
  } else {
    Promise.all([
      fetch('../kzz/all.json').then(r => r.json()),
      fetch('../kzz/self.json').then(r => r.json())
    ])
      .then(([allData, selfCodes]) => {
        console.log('all.json data length:', allData.length);
        console.log('self.json codes length:', selfCodes.length);

        const selfCodeSet = new Set(selfCodes);

        data = allData.filter(item => {
          const code = parseInt(item.bond_id);
          const isBond = code >= 100000 && code <= 130000;
          const isInSelf = selfCodeSet.has(item.bond_id);
          return isBond && isInSelf;
        });

        applyFilters();
        document.getElementById('refresh-status').textContent = '更新时间: ' + new Date().toLocaleString();
      })
      .catch(error => {
        console.error('加载数据失败:', error);
        document.getElementById('record-count').textContent = '未找到关注列表，请先添加关注';
        data = [];
        filteredData = [];
        renderTable();
      });
  }
}

function setupEventListeners() {
  document.getElementById('filter-form').addEventListener('submit', (e) => {
    e.preventDefault();
    applyFilters();
  });

  document.getElementById('reset-button').addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    document.getElementById('year-left-min').value = '';
    document.getElementById('year-left-max').value = '';
    document.getElementById('bond-price-min').value = '';
    document.getElementById('bond-price-max').value = '';
    document.querySelectorAll('#status-filter-menu input[type="checkbox"]').forEach(cb => cb.checked = false);
    applyFilters();
  });

  document.getElementById('refresh-button').addEventListener('click', loadData);

  document.getElementById('data-source').addEventListener('change', (e) => {
    currentDataSource = e.target.value;
    loadData();
  });

  document.getElementById('refresh-interval').addEventListener('change', (e) => {
    const interval = parseInt(e.target.value);
    if (refreshInterval) clearInterval(refreshInterval);
    if (interval > 0) {
      refreshInterval = setInterval(loadData, interval * 1000);
    }
  });

  document.getElementById('status-filter-toggle').addEventListener('click', (e) => {
    e.stopPropagation();
    const dropdown = document.getElementById('status-filter-dropdown');
    const isOpen = dropdown.classList.contains('open');

    document.querySelectorAll('.multi-select-dropdown.open').forEach(dropdown => {
      dropdown.classList.remove('open');
    });
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => toggle.setAttribute('aria-expanded', 'false'));

    if (!isOpen) {
      dropdown.classList.add('open');
    }
    e.currentTarget.setAttribute('aria-expanded', !isOpen);
  });

  document.getElementById('status-clear-all').addEventListener('click', (e) => {
    e.stopPropagation();
    document.querySelectorAll('#status-filter-menu input[type="checkbox"]').forEach(cb => cb.checked = false);
    applyFilters();
  });

  document.querySelectorAll('#status-filter-menu input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
      applyFilters();
    });
  });

  document.getElementById('column-filter-toggle').addEventListener('click', (e) => {
    e.stopPropagation();
    const dropdown = document.getElementById('column-filter-dropdown');
    const isOpen = dropdown.classList.contains('open');

    document.querySelectorAll('.multi-select-dropdown.open').forEach(dropdown => {
      dropdown.classList.remove('open');
    });
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => toggle.setAttribute('aria-expanded', 'false'));

    if (!isOpen) {
      dropdown.classList.add('open');
    }
    e.currentTarget.setAttribute('aria-expanded', !isOpen);
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.multi-select-dropdown')) {
      document.querySelectorAll('.multi-select-dropdown.open').forEach(dropdown => {
        dropdown.classList.remove('open');
      });
      document.querySelectorAll('.dropdown-toggle').forEach(toggle => toggle.setAttribute('aria-expanded', 'false'));
    }
  });
}

function initColumnFilter() {
  const container = document.getElementById('column-filter-options');
  container.innerHTML = Object.keys(TABLE_HEAD).map(key => `
    <label>
      <input type="checkbox" value="${key}" ${visibleColumns.includes(key) ? 'checked' : ''} />
      ${TABLE_HEAD[key]}
    </label>
  `).join('');

  container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
      visibleColumns = Array.from(container.querySelectorAll('input[type="checkbox"]:checked'))
        .map(cb => cb.value);
      renderTable();
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initColumnFilter();
  setupEventListeners();

  const refreshIntervalSelect = document.getElementById('refresh-interval');
  refreshIntervalSelect.value = '5';
  refreshIntervalSelect.dispatchEvent(new Event('change'));

  loadData();
});