document.addEventListener('DOMContentLoaded', () => {
    // 修改位置 1：新增漢堡選單點擊事件
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
    });

    // 修改位置 2：初始化聊天功能
    const chatbox = document.getElementById('chatbox');
    const questionInput = document.getElementById('questionInput');

    // 自動滾動到聊天底部
    const scrollToBottom = () => {
        chatbox.scrollTop = chatbox.scrollHeight;
    };

    // 格式化時間
    const getCurrentTime = () => {
        const now = new Date();
        return now.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
    };

    // 修改位置 3：控制聊天頁面的問題輸入和回覆
    window.sendQuestion = () => {
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
            <div class="timestamp">${getCurrentTime()}</div>
            <div class="read-receipt">已讀</div>
        `;
        chatbox.appendChild(userMessage);
        questionInput.value = "";

        // 使用者送出時，再觸發定位
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;

                    fetch("/api/ask", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            question: question,
                            latitude: latitude,
                            longitude: longitude
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        const formattedAnswer = data.answer.replace(/\n/g, '<br>');
                        const botMessage = document.createElement("div");
                        botMessage.className = "msg bot";
                        botMessage.innerHTML = `
                            <div class="avatar"></div>
                            <div class="bubble">${formattedAnswer}</div>
                            <div class="timestamp">${getCurrentTime()}</div>
                        `;
                        chatbox.appendChild(botMessage);
                        scrollToBottom();
                    })
                    .catch(error => {
                        console.error("錯誤:", error);
                        const errorMessage = document.createElement("div");
                        errorMessage.className = "msg bot";
                        errorMessage.innerHTML = `
                            <div class="avatar"></div>
                            <div class="bubble">⚠️ 發生錯誤</div>
                            <div class="timestamp">${getCurrentTime()}</div>
                        `;
                        chatbox.appendChild(errorMessage);
                        scrollToBottom();
                    });
                },
                (error) => {
                    console.warn("❌ 無法取得位置：", error.message);
                    // 若定位失敗也照樣送出問題，但不含位置
                    fetch("/api/ask", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ question: question })
                    })
                    .then(response => response.json())
                    .then(data => {
                        const formattedAnswer = data.answer.replace(/\n/g, '<br>');
                        const botMessage = document.createElement("div");
                        botMessage.className = "msg bot";
                        botMessage.innerHTML = `
                            <div class="avatar"></div>
                            <div class="bubble">${formattedAnswer}</div>
                            <div class="timestamp">${getCurrentTime()}</div>
                        `;
                        chatbox.appendChild(botMessage);
                        scrollToBottom();
                    });
                }
            );
        } else {
            alert("⚠️ 瀏覽器不支援地理位置功能");
        }
    };

    // 修改位置 4：監聽 Enter 鍵送出問題
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendQuestion();
        }
    });
});
