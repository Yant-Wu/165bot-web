document.addEventListener('DOMContentLoaded', () => {
    // 修改位置 5：新增漢堡選單點擊事件
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
    });

    // 卡片輪播邏輯
    const carousel = document.querySelector('.carousel');
    const cards = document.querySelectorAll('.card');
    const cardWidth = cards[0].offsetWidth + 30; // 包含 margin

    // 複製卡片以實現無限輪播
    cards.forEach(card => {
        const clone = card.cloneNode(true);
        carousel.appendChild(clone);
    });

    // 設置輪播動畫
    const totalWidth = cardWidth * cards.length;
    carousel.style.animationDuration = `${totalWidth / 100}s`;

    // 即時互動區塊點擊切換邏輯
    const listItems = document.querySelectorAll('.interaction-list li');
    const contentImages = document.querySelectorAll('.content-image');

    listItems.forEach(item => {
        item.addEventListener('click', () => {
            // 移除所有列表項的 active 類
            listItems.forEach(li => li.classList.remove('active'));
            // 為當前點擊的列表項添加 active 類
            item.classList.add('active');

            // 獲取目標內容
            const target = item.getAttribute('data-target');

            // 移除所有圖片的 active 類
            contentImages.forEach(img => img.classList.remove('active'));
            // 為對應的圖片添加 active 類
            const targetImage = document.querySelector(`.content-image[data-content="${target}"]`);
            if (targetImage) {
                targetImage.classList.add('active');
            }
        });
    });
});