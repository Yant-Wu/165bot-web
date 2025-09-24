document.addEventListener('DOMContentLoaded', () => {
  console.log('Script loaded and DOM ready');

  const hamburger = document.querySelector('.hamburger');
  const navLinks = document.querySelector('.nav-links');
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('active');
      navLinks.classList.toggle('active');
    });
  }

  // 等待 fraudData 載入完成
  document.addEventListener("fraudDataReady", () => {
    console.log("✅ fraudData 載入完成，開始 dashboard 渲染");

    if (!window.fraudData || Object.keys(window.fraudData).length === 0) {
      console.warn('⚠️ fraudData 還是空的');
      return;
    }

    renderDashboard();  // 執行渲染
  });
});

// 將 dashboard 的主邏輯封裝為一個 function
function renderDashboard() {
  const tableContainer = document.getElementById('fraud-double-table');
  const isMobile = window.innerWidth <= 768;

  const entries = Object.entries(fraudData).map(([county, data]) => ({
    name: county,
    count: data.count,
    top5: data.top5 || []
  }));

  entries.sort((a, b) => b.count - a.count);

  const leftCol = entries.slice(0, 11);
  const rightCol = entries.slice(11);

  const createTableColumn = (colData, includeThead = true) => {
    return `<table class="fraud-table">
      ${includeThead ? `
        <thead class="hide-on-mobile">
          <tr><th>縣市</th><th>問答件數</th></tr>
        </thead>` : ''}
      <tbody>
        ${colData.map(entry => {
          let levelClass = '';
          if (entry.count >= 7) levelClass = 'level-high';
          else if (entry.count >= 4) levelClass = 'level-mid';
          else levelClass = 'level-low';

          return `
            <tr class="${levelClass}">
              <td class="county-name"><span class="left-color"></span>${entry.name}</td>
              <td class="count">${entry.count}</td>
            </tr>`;
        }).join('')}
      </tbody>
    </table>`;
  };

  if (tableContainer) {
    tableContainer.innerHTML = isMobile
      ? `<div class="table-column">${createTableColumn(entries, false)}</div>`
      : `<div class="table-column">${createTableColumn(leftCol)}</div>
         <div class="table-column">${createTableColumn(rightCol)}</div>`;
  }

  // 詐騙手法前五名表格
  const top5Counts = {};
  entries.forEach(entry => {
    entry.top5.forEach(type => {
      if (type && type.type) {
        const t = type.type;
        top5Counts[t] = (top5Counts[t] || 0) + 1;
      }
    });
  });

  const sortedTop5 = Object.entries(top5Counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const top5Container = document.getElementById('fraud-top5-table');
  if (top5Container) {
    top5Container.innerHTML = `
      <table class="fraud-table">
        <thead>
          <tr><th>詐騙手法</th><th>縣市出現數</th></tr>
        </thead>
        <tbody>
          ${sortedTop5.map(([type, count]) => `
            <tr>
              <td>${type}</td>
              <td>${count}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    `;
  }
}
