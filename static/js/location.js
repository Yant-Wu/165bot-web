document.addEventListener('DOMContentLoaded', () => {
    console.log("✅ location.js 已載入並啟動");
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                fetch('/location', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ latitude, longitude })
                });
            },
            (error) => {
                console.warn('❗無法取得使用者位置：', error.message);
            }
        );
    } else {
        console.warn('❗瀏覽器不支援地理位置功能');
    }
});
