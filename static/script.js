// ========== 1. 控制聊天頁面的問題輸入和回覆 ==========
function sendQuestion() {
    const questionInput = document.getElementById("questionInput");
    const chatbox = document.getElementById("chatbox");
    const question = questionInput.value.trim();

    if (!question) {
        alert("請輸入問題！");
        return;
    }

    // 顯示用戶訊息
    const userMessage = document.createElement("div");
    userMessage.className = "msg user";
    userMessage.innerHTML = `
        <div class="bubble">${question}</div>
        <div class="timestamp">${new Date().toLocaleTimeString()}</div>
        <div class="read-receipt">已讀</div>
    `;
    chatbox.appendChild(userMessage);

    // 清空輸入框
    questionInput.value = "";

    // 發送請求
    fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question })
    })
    .then(response => response.json())
    .then(data => {
        // 處理換行符，將 \n 轉換為 <br>
        const formattedAnswer = data.answer.replace(/\n/g, '<br>');

        // 顯示機器人回覆
        const botMessage = document.createElement("div");
        botMessage.className = "msg bot";
        botMessage.innerHTML = `
            <div class="avatar"></div>
            <div class="bubble">${formattedAnswer}</div>
            <div class="timestamp">${new Date().toLocaleTimeString()}</div>
        `;
        chatbox.appendChild(botMessage);

        // 自動滾動到底部
        chatbox.scrollTop = chatbox.scrollHeight;
    })
    .catch(error => {
        console.error("錯誤:", error);
        const errorMessage = document.createElement("div");
        errorMessage.className = "msg bot";
        errorMessage.innerHTML = `
            <div class="avatar"></div>
            <div class="bubble">⚠️ 發生錯誤</div>
            <div class="timestamp">${new Date().toLocaleTimeString()}</div>
        `;
        chatbox.appendChild(errorMessage);

        // 自動滾動到底部
        chatbox.scrollTop = chatbox.scrollHeight;
    });
}

// 監聽 Enter 鍵送出問題
document.getElementById("questionInput")?.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        sendQuestion();
    }
});

// ========== 2. 控制漢堡選單 ==========
function toggleMenu() {
    console.log("選單按鈕被點擊");
    const menuLinks = document.querySelector(".navbar-links");

    if (menuLinks) {
        menuLinks.classList.toggle("active");
        console.log("navbar-links active 狀態:", menuLinks.classList.contains("active"));

        // 檢查當前 display 狀態
        const computedStyle = window.getComputedStyle(menuLinks);
        console.log("navbar-links display 狀態:", computedStyle.display);

        // 檢查位置和尺寸
        console.log("navbar-links 位置:", menuLinks.getBoundingClientRect());
    } else {
        console.error("❌ 找不到 .navbar-links 元素");
    }
}

// ========== 3. 按鈕點擊效果 ==========
function addButtonClickEffect() {
    const buttons = document.querySelectorAll(".home-button");
    console.log("找到的 home-button 數量:", buttons.length);
    buttons.forEach(button => {
        button.addEventListener("click", function(e) {
            e.preventDefault();
            console.log("home-button 點擊觸發:", this.textContent);

            // 執行動畫
            this.style.transition = "transform 0.2s ease";
            this.style.transform = "scale(1.1)";
            setTimeout(() => {
                this.style.transform = "scale(1)";
                // 動畫完成後執行跳轉
                window.location.href = this.href;
            }, 200);
        });
    });
}

// ========== 4. 更新詐騙手法表格 ==========
function updateFraudMethods(methodsData) {
    const tbody = document.getElementById('fraud-methods-table-body');
    tbody.innerHTML = '';  // 清空現有內容
    methodsData.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${index + 1}</td><td>${item.type}</td><td>${item.amount}</td>`;
        tbody.appendChild(tr);
    });
}

// 範例詐騙手法資料
const fraudMethods = [
    { type: '網路詐騙', amount: 250 },
    { type: '電話詐騙', amount: 180 },
    { type: '金融詐騙', amount: 320 },
    { type: '投資詐騙', amount: 150 },
    { type: '其他詐騙', amount: 90 }
];

// ========== 5. 確保 DOM 載入完成後綁定事件 ==========
document.addEventListener("DOMContentLoaded", function() {
    // 綁定漢堡選單點擊事件
    const menuButton = document.querySelector(".navbar-toggle");
    if (menuButton) {
        menuButton.addEventListener("click", toggleMenu);
        menuButton.addEventListener("touchstart", function(e) {
            e.preventDefault();
            toggleMenu();
        });
        console.log("漢堡選單事件綁定成功");
    } else {
        console.error("❌ 找不到 .navbar-toggle 元素");
    }

    // 綁定 home-button 點擊效果
    addButtonClickEffect();

    // 更新詐騙手法表格
    updateFraudMethods(fraudMethods);
});