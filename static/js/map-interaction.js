// 載入最新 fraudData（從後端 fetch）—— 放在最前面，其他程式照舊
window.fraudData = {}; // 先設定空物件，避免 undefined

fetch("/api/fraud-stats")
  .then(res => res.json())
  .then(data => {
    const converted = {};
    (data.county_counts || []).forEach(({ county, count, top5 }) => {
      converted[county] = {
        count: count,
        top5: top5 || []
      };
    });
    window.fraudData = converted;
    console.log("✅ fraudData 從後端更新完畢");
    document.dispatchEvent(new Event("fraudDataReady"));

  })

// document.addEventListener("DOMContentLoaded", () => {
//   console.log("Script loaded and DOM ready");

//   const width = 960;
//   const height = 600;

//   const mapContainer = d3.select("#taiwan-map")
//     .style("padding", "1rem")
//     .style("margin", "1rem auto")
//     .style("max-width", "960px")


//     const svg = mapContainer
//     .append("svg")
//     .attr("viewBox", `0 0 ${width} ${height}`)
//     .attr("preserveAspectRatio", "xMidYMid meet")
//     .style("width", "100%")
//     .style("height", "auto");

//   // const svg = d3.select("#taiwan-map")
//   //   .append("svg")
//   //   .attr("viewBox", `0 0 ${width} ${height}`)
//   //   .attr("preserveAspectRatio", "xMidYMid meet");

//   const tooltip = d3.select("#map-tooltip");
//   const countyDetails = d3.select("#county-details");

//   window.fraudData = window.fraudData || {};

//   d3.json("./static/tw_map.json").then(topoData => {
//     const geojsonData = topojson.feature(topoData, topoData.objects["tw"]);
//     const validFeatures = geojsonData.features.filter(feature =>
//       feature.geometry &&
//       Array.isArray(feature.geometry.coordinates) &&
//       feature.geometry.coordinates.length > 0
//     );

//     geojsonData.features.forEach(feature => {
//       const name = feature.properties.COUNTYNAME;
//       let offset = [0, 0];
//       const offsetCoords = coords => coords.map(ring => ring.map(([x, y]) => [x + offset[0], y + offset[1]]));
//       if (name === "金門縣") {
//         offset = [1.5, 0.1];
//         feature.geometry.coordinates = offsetCoords(feature.geometry.coordinates);
//       }
//       if (name === "連江縣") {
//         offset = [0.5, -0.8];
//         feature.geometry.coordinates = feature.geometry.coordinates.map(offsetCoords);
//       }
//     });

//     const path = d3.geoPath().projection(
//       d3.geoMercator()
//         .center([121, 24])
//         .scale(1000)
//         .translate([width / 2, height / 2])
//         .fitSize([width, height], geojsonData)
//     );

//     function toggleSelection(d) {
//       const countyName = d.properties.COUNTYNAME;
//       const pathEl = d3.select(`path[data-county="${countyName}"]`);
//       const labelEl = d3.select(`text[data-county="${countyName}"]`);
//       const isActive = pathEl.classed("active");

//       // 隱藏所有縣市文字與取消選取樣式
//       d3.selectAll(".label").style("display", "none");
//       d3.selectAll(".county").classed("active", false);
//       d3.selectAll(".label").classed("active", false);

//       if (isActive) {
//         countyDetails.style("display", "none");
//         window.showAllCounties();
//         d3.selectAll(".label").style("display", "block");
//       } else {
//         pathEl.classed("active", true);
//         labelEl.classed("active", true);
//         labelEl.style("display", "block");
//         countyDetails.style("display", "none");
//         window.showCountyDetails(countyName);
//       }
//     };


//     window.showCountyDetails = function(countyName) {
//       const detailContainer = document.getElementById("county-fraud-details");
//       const tableContainer = document.getElementById("fraud-double-table");
//       let data = window.fraudData[countyName];
//       if (!data) {
//         data = { count: 0, loss: 0, top5: [] };
//         window.fraudData[countyName] = data;
//       }
//       if (!Array.isArray(data.top5)) {
//         data.top5 = [];
//       }

//       const top5 = data.top5
//         .slice()
//         .sort((a, b) => (b.count || 0) - (a.count || 0))
//         .slice(0, 5);

//       detailContainer.innerHTML = `
//         <div style="position: relative; padding: 2rem; background: #fff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
//           <div style="position: absolute; top: 1rem; right: 1rem; font-size: 0.9rem; color: #444; cursor: pointer;" onclick="showAllCounties()">＜ 返回全國縣市</div>
//           <div style="text-align: center; margin-bottom: 1rem;">
//             <h2 style="margin: 0; font-weight: bold; font-size: 1.5rem; color: #007777;">${countyName}數據統計</h2>
//           </div>
//           <div style="display: flex; justify-content: center; align-items: center; gap: 4rem; background: #f4f4f4; border-radius: 12px; padding: 1rem 2rem; margin-bottom: 2rem;">
//             <div style="text-align: center;">
//               <div style="font-size: 2rem; font-weight: bold; color: #009999;">${data.count}</div>
//               <div>問答件數</div>
//             </div>
//           </div>
//           <div style="background: #444; color: #fff; font-weight: bold; display: flex; justify-content: space-between; align-items: center; padding: 0.8rem 1.5rem; border-radius: 8px 8px 0 0;">
//             <div>詐騙手法前 5 名</div>
//             <div style="display: flex; gap: 2rem;">
//               <div>問答件數</div>
//             </div>
//           </div>
//           ${top5.map((item, i) => `
//             <div style="display: flex; justify-content: space-between; align-items: center; background: #fff; border-top: 1px solid #eee; padding: 1rem 1.5rem;">
//               <div style="display: flex; align-items: center; gap: 1rem;">
//                 <div style="background: #009999; color: #fff; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold;">${i + 1}</div>
//                 <div style="color: #006666; font-weight: bold;">${item.type}</div>
//               </div>
//               <div style="display: flex; gap: 2rem; font-weight: 600;">
//                 <div style="min-width: 60px; text-align: right;">${item.count || '0'}</div>

//               </div>
//             </div>
//           `).join('')}
//         </div>
//       `;

//       tableContainer.style.display = "none";
//       detailContainer.style.display = "block";
//     };

//     window.showAllCounties = function() {
//       const detailContainer = document.getElementById("county-fraud-details");
//       const tableContainer = document.getElementById("fraud-double-table");
//       detailContainer.style.display = "none";
//       tableContainer.style.display = "flex";

//       d3.selectAll(".label").style("display", "block");
//       d3.selectAll(".county").classed("active", false);
//       d3.selectAll(".label").classed("active", false);
//     };

//     svg.selectAll("path")
//       .data(validFeatures)
//       .enter()
//       .append("path")
//       .attr("class", "county")
//       .attr("d", path)
//       .attr("data-county", d => d.properties.COUNTYNAME)
//       .on("mouseover", function(event, d) {
//         d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
//         d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
//         tooltip
//           .style("display", "block")
//           .html(`縣市: ${d.properties.COUNTYNAME}<br>問答件數: ${fraudData[d.properties.COUNTYNAME]?.count || 0}`)
//           .style("left", (event.pageX + 10) + "px")
//           .style("top", (event.pageY - 10) + "px");
//       })
//       .on("mouseout", function (event, d) {
//         d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
//         d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
//         tooltip.style("display", "none");
//       })
//       .on("click", function(event, d) {
//         toggleSelection(d);
//       });

//       svg.selectAll(".label")
//       .data(validFeatures)
//       .enter()
//       .append("text")
//       .attr("class", "label")
//       .attr("x", d => {
//         const name = d.properties.COUNTYNAME;
//         const [x, _] = path.centroid(d);
//         if (name === "嘉義市") return x + 25;
//         if (name === "嘉義縣") return x - 10;
//         if (name === "基隆市") return x + 10;
//         if (name === "新北市") return x;
//         if (name === "台北市") return x;
//         return x;
//       })
//       .attr("y", d => {
//         const name = d.properties.COUNTYNAME;
//         const [_, y] = path.centroid(d);
//         if (name === "嘉義市") return y + 20;
//         if (name === "嘉義縣") return y - 8;
//         if (name === "基隆市") return y - 8;
//         if (name === "新北市") return y + 20;
//         if (name === "台北市") return y + 18;
//         return y;
//       })
//       .text(d => d.properties.COUNTYNAME)
//       .attr("data-county", d => d.properties.COUNTYNAME)
//       .attr("text-anchor", "middle")
//       .attr("fill", "#000")
//       .attr("font-size", "1rem")
//       .attr("stroke", "#000")
//       .attr("stroke-width", "0.5px")
    
//       .on("mouseover", function(event, d) {
//         d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
//         d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
//       })
//       .on("mouseout", function(event, d) {
//         d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
//         d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
//       })
//       .on("click", function(event, d) {
//         toggleSelection(d);
//       });
//   }).catch(error => {
//     console.error("載入 GeoJSON 失敗:", error);
//   });
// });

document.addEventListener("fraudDataReady", () => {
  console.log("🧭 fraudDataReady 事件觸發，準備載入地圖");
  initMap();  // 寫一個獨立函式來初始化地圖
});

function initMap() {
  const width = 960;
  const height = 600;

  const mapContainer = d3.select("#taiwan-map")
    .style("padding", "1rem")
    .style("margin", "1rem auto")
    .style("max-width", "960px")


    const svg = mapContainer
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet")
    .style("width", "100%")
    .style("height", "auto");

  // const svg = d3.select("#taiwan-map")
  //   .append("svg")
  //   .attr("viewBox", `0 0 ${width} ${height}`)
  //   .attr("preserveAspectRatio", "xMidYMid meet");

  const tooltip = d3.select("#map-tooltip");
  const countyDetails = d3.select("#county-details");

  window.fraudData = window.fraudData || {};

  d3.json("./static/tw_map.json").then(topoData => {
    const geojsonData = topojson.feature(topoData, topoData.objects["tw"]);
    const validFeatures = geojsonData.features.filter(feature =>
      feature.geometry &&
      Array.isArray(feature.geometry.coordinates) &&
      feature.geometry.coordinates.length > 0
    );

    geojsonData.features.forEach(feature => {
      const name = feature.properties.COUNTYNAME;
      let offset = [0, 0];
      const offsetCoords = coords => coords.map(ring => ring.map(([x, y]) => [x + offset[0], y + offset[1]]));
      if (name === "金門縣") {
        offset = [1.5, 0.1];
        feature.geometry.coordinates = offsetCoords(feature.geometry.coordinates);
      }
      if (name === "連江縣") {
        offset = [0.5, -0.8];
        feature.geometry.coordinates = feature.geometry.coordinates.map(offsetCoords);
      }
    });

    const path = d3.geoPath().projection(
      d3.geoMercator()
        .center([121, 24])
        .scale(1000)
        .translate([width / 2, height / 2])
        .fitSize([width, height], geojsonData)
    );

    function toggleSelection(d) {
      const countyName = d.properties.COUNTYNAME;
      const pathEl = d3.select(`path[data-county="${countyName}"]`);
      const labelEl = d3.select(`text[data-county="${countyName}"]`);
      const isActive = pathEl.classed("active");

      // 隱藏所有縣市文字與取消選取樣式
      d3.selectAll(".label").style("display", "none");
      d3.selectAll(".county").classed("active", false);
      d3.selectAll(".label").classed("active", false);

      if (isActive) {
        countyDetails.style("display", "none");
        window.showAllCounties();
        d3.selectAll(".label").style("display", "block");
      } else {
        pathEl.classed("active", true);
        labelEl.classed("active", true);
        labelEl.style("display", "block");
        countyDetails.style("display", "none");
        window.showCountyDetails(countyName);
      }
    };


    window.showCountyDetails = function(countyName) {
      const detailContainer = document.getElementById("county-fraud-details");
      const tableContainer = document.getElementById("fraud-double-table");
      let data = window.fraudData[countyName];
      if (!data) {
        data = { count: 0, loss: 0, top5: [] };
        window.fraudData[countyName] = data;
      }
      if (!Array.isArray(data.top5)) {
        data.top5 = [];
      }

      const top5 = data.top5
        .slice()
        .sort((a, b) => (b.count || 0) - (a.count || 0))
        .slice(0, 5);

      detailContainer.innerHTML = `
        <div style="position: relative; padding: 2rem; background: #fff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
          <div style="position: absolute; top: 1rem; right: 1rem; font-size: 0.9rem; color: #444; cursor: pointer;" onclick="showAllCounties()">＜ 返回全國縣市</div>
          <div style="text-align: center; margin-bottom: 1rem;">
            <h2 style="margin: 0; font-weight: bold; font-size: 1.5rem; color: #007777;">${countyName}數據統計</h2>
          </div>
          <div style="display: flex; justify-content: center; align-items: center; gap: 4rem; background: #f4f4f4; border-radius: 12px; padding: 1rem 2rem; margin-bottom: 2rem;">
            <div style="text-align: center;">
              <div style="font-size: 2rem; font-weight: bold; color: #009999;">${data.count}</div>
              <div>問答件數</div>
            </div>
          </div>
          <div style="background: #444; color: #fff; font-weight: bold; display: flex; justify-content: space-between; align-items: center; padding: 0.8rem 1.5rem; border-radius: 8px 8px 0 0;">
            <div>詐騙手法前 5 名</div>
            <div style="display: flex; gap: 2rem;">
              <div>問答件數</div>
            </div>
          </div>
          ${top5.map((item, i) => `
            <div style="display: flex; justify-content: space-between; align-items: center; background: #fff; border-top: 1px solid #eee; padding: 1rem 1.5rem;">
              <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="background: #009999; color: #fff; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold;">${i + 1}</div>
                <div style="color: #006666; font-weight: bold;">${item.type}</div>
              </div>
              <div style="display: flex; gap: 2rem; font-weight: 600;">
                <div style="min-width: 60px; text-align: right;">${item.count || '0'}</div>

              </div>
            </div>
          `).join('')}
        </div>
      `;

      tableContainer.style.display = "none";
      detailContainer.style.display = "block";
    };

    window.showAllCounties = function() {
      const detailContainer = document.getElementById("county-fraud-details");
      const tableContainer = document.getElementById("fraud-double-table");
      detailContainer.style.display = "none";
      tableContainer.style.display = "flex";

      d3.selectAll(".label").style("display", "block");
      d3.selectAll(".county").classed("active", false);
      d3.selectAll(".label").classed("active", false);
    };

    svg.selectAll("path")
      .data(validFeatures)
      .enter()
      .append("path")
      .attr("class", "county")
      .attr("d", path)
      .attr("data-county", d => d.properties.COUNTYNAME)
      .on("mouseover", function(event, d) {
        d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
        d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
        tooltip
          .style("display", "block")
          .html(`縣市: ${d.properties.COUNTYNAME}<br>問答件數: ${fraudData[d.properties.COUNTYNAME]?.count || 0}`)
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY - 10) + "px");
      })
      .on("mouseout", function (event, d) {
        d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
        d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
        tooltip.style("display", "none");
      })
      .on("click", function(event, d) {
        toggleSelection(d);
      });

      svg.selectAll(".label")
      .data(validFeatures)
      .enter()
      .append("text")
      .attr("class", "label")
      .attr("x", d => {
        const name = d.properties.COUNTYNAME;
        const [x, _] = path.centroid(d);
        if (name === "嘉義市") return x + 25;
        if (name === "嘉義縣") return x - 10;
        if (name === "基隆市") return x + 10;
        if (name === "新北市") return x;
        if (name === "台北市") return x;
        return x;
      })
      .attr("y", d => {
        const name = d.properties.COUNTYNAME;
        const [_, y] = path.centroid(d);
        if (name === "嘉義市") return y + 20;
        if (name === "嘉義縣") return y - 8;
        if (name === "基隆市") return y - 8;
        if (name === "新北市") return y + 20;
        if (name === "台北市") return y + 18;
        return y;
      })
      .text(d => d.properties.COUNTYNAME)
      .attr("data-county", d => d.properties.COUNTYNAME)
      .attr("text-anchor", "middle")
      .attr("fill", "#000")
      .attr("font-size", "1rem")
      .attr("stroke", "#000")
      .attr("stroke-width", "0.5px")
    
      .on("mouseover", function(event, d) {
        d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
        d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", true);
      })
      .on("mouseout", function(event, d) {
        d3.select(`[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
        d3.select(`text[data-county="${d.properties.COUNTYNAME}"]`).classed("hover", false);
      })
      .on("click", function(event, d) {
        toggleSelection(d);
      });
  }).catch(error => {
    console.error("載入 GeoJSON 失敗:", error);
  });
}
