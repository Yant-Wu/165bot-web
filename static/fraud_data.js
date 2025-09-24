fetch("/api/fraud-stats")
  .then((res) => res.json())
  .then((data) => {
    const top5 = Array.isArray(data.top5_types) ? data.top5_types : [];

    top5.forEach((item, index) => {
      const card = document.getElementById(`fraud-type-${index + 1}`);
      if (card) {
        const title = card.querySelector('.fraud-title');
        const count = card.querySelector('.fraud-count');
        if (title) title.innerText = item.type;
        if (count) count.innerText = `問答件數: ${item.count}`;
      }
    });
  })
  .catch((err) => {
    console.error("載入 fraud-stats 發生錯誤", err);
  });
