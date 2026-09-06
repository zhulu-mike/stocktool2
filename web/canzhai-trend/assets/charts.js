var _chartInstances = {};

async function initCharts() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var series3 = style.getPropertyValue('--series3').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();
  var bg = style.getPropertyValue('--bg').trim();

  var resp = await fetch('assets/data.json');
  var raw = await resp.json();

  // data is stored newest-first; reverse to oldest-first for left-to-right time axis
  var dates = raw.dates.slice().reverse();
  var premium = raw.premium.slice().reverse();
  var avgPrice = raw.avgPrice.slice().reverse();
  var medPrice = raw.medPrice.slice().reverse();

  // ---- update footer date range ----
  var footerInfo = document.querySelector('footer .sources ol li:first-child .src-title');
  if (footerInfo && dates.length > 0) {
    footerInfo.textContent = '仓位结构.xlsx · 工作表「可转债等权指数」，' + dates[0] + ' 至 ' + dates[dates.length - 1] + ' 共 ' + dates.length + ' 个交易日。';
  }

  function latest(arr) {
    for (var i = arr.length - 1; i >= 0; i--) {
      if (arr[i] != null) return arr[i];
    }
    return null;
  }
  function minMax(arr) {
    var mn = Infinity, mx = -Infinity;
    arr.forEach(function (v) { if (v != null) { if (v < mn) mn = v; if (v > mx) mx = v; } });
    return [mn === Infinity ? 0 : mn, mx === -Infinity ? 0 : mx];
  }

  // ---- fill KPI cards ----
  var mm;
  function fillKpi(id, idR, val, unit, mmv) {
    document.getElementById(id).textContent = val != null ? val + (unit || '') : '—';
    document.getElementById(idR).textContent = '区间 ' + mmv[0] + ' – ' + mmv[1];
  }
  var lp = latest(premium), la = latest(avgPrice), lm = latest(medPrice);
  fillKpi('kpi-premium', 'kpi-premium-r', lp.toFixed(2), '%', minMax(premium).map(function (x) { return x.toFixed(2); }));
  fillKpi('kpi-avgprice', 'kpi-avgprice-r', la.toFixed(2), '', minMax(avgPrice).map(function (x) { return x.toFixed(2); }));
  fillKpi('kpi-medprice', 'kpi-medprice-r', lm.toFixed(2), '', minMax(medPrice).map(function (x) { return x.toFixed(2); }));

  function baseTooltip() {
    return {
      trigger: 'axis',
      appendToBody: true,
      backgroundColor: bg2,
      borderColor: rule,
      textStyle: { color: ink },
      valueFormatter: function (v) { return v != null ? v.toFixed(2) : '—'; }
    };
  }
  function axisStyle(val) {
    return { axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, fontSize: 11 }, splitLine: { lineStyle: { color: rule } } };
  }

  function buildChart(id, color, values, unit, yName) {
    // dispose old chart instance if exists
    if (_chartInstances[id]) {
      _chartInstances[id].dispose();
    }

    var data = dates.map(function (d, i) { return [d, values[i]]; });
    var chart = echarts.init(document.getElementById(id), null, { renderer: 'svg' });
    _chartInstances[id] = chart;
    chart.setOption({
      animation: false,
      color: [color],
      tooltip: Object.assign(baseTooltip(), {
        formatter: function (ps) {
          var p = ps[0];
          return p.axisValue + '<br/><b>' + yName + '</b>：' + (p.value[1] != null ? p.value[1].toFixed(2) : '—') + (unit || '');
        }
      }),
      grid: { left: 14, right: 20, top: 14, bottom: 74, containLabel: true },
      xAxis: Object.assign(axisStyle(false), { type: 'category', boundaryGap: false, data: dates, axisLabel: { color: muted, fontSize: 11, interval: 'auto' } }),
      yAxis: Object.assign(axisStyle(true), { type: 'value', name: yName + (unit || ''), nameTextStyle: { color: muted, fontSize: 11 }, scale: true }),
      dataZoom: [
        { type: 'inside', start: 98, end: 100 },
        { type: 'slider', start: 98, end: 100, height: 22, bottom: 16, borderColor: rule, fillerColor: color + '22', textStyle: { color: muted } }
      ],
      series: [{
        type: 'line',
        data: data,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 2, color: color },
        areaStyle: { color: buildGrad(color) },
        markPoint: {
          symbol: 'pin', symbolSize: 42, label: { fontSize: 10, color: bg },
          data: [
            { type: 'max', name: '最高' },
            { type: 'min', name: '最低' }
          ],
          itemStyle: { color: color }
        }
      }]
    });
    window.addEventListener('resize', function () { chart.resize(); });
  }

  function buildGrad(color) {
    return {
      type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
      colorStops: [{ offset: 0, color: color + '2e' }, { offset: 1, color: color + '00' }]
    };
  }

  buildChart('chart-premium', accent2, premium, '%', '平均溢价率');
  buildChart('chart-avgprice', accent, avgPrice, '', '平均价格');
  buildChart('chart-medprice', series3, medPrice, '', '价格中位数');
}