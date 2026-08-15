const DATA_URL = "promotions.json";
const PAGE_SIZE = 8;

let allPromotions = [];
let filteredPromotions = [];
let currentStore = "ทั้งหมด";
let currentSearch = "";
let currentPage = 1;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  bindEvents();
  restoreTheme();
  await loadPromotions();
}

function bindEvents() {
  document.getElementById("searchInput").addEventListener("input", e => {
    currentSearch = e.target.value.trim().toLowerCase();
    currentPage = 1;
    applyFilters();
  });

  document.getElementById("searchBtn").addEventListener("click", () => {
    currentSearch = document.getElementById("searchInput").value.trim().toLowerCase();
    currentPage = 1;
    applyFilters();
  });

  document.getElementById("storeTabs").addEventListener("click", e => {
    const btn = e.target.closest("[data-store]");
    if (!btn) return;

    currentStore = btn.dataset.store;
    currentPage = 1;

    document.querySelectorAll(".store-tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    applyFilters();
  });

  document.querySelectorAll("[data-quick]").forEach(btn => {
    btn.addEventListener("click", () => handleQuickFilter(btn.dataset.quick));
  });

  document.getElementById("loadMoreBtn").addEventListener("click", () => {
    currentPage += 1;
    renderPromotions();
  });

  document.getElementById("refreshBtn").addEventListener("click", async () => {
    showToast("กำลังอัปเดตข้อมูล...");
    await loadPromotions(true);
  });

  document.getElementById("themeBtn").addEventListener("click", toggleTheme);
}

async function loadPromotions(force = false) {
  setLoading();

  try {
    const response = await fetch(`${DATA_URL}${force ? `?t=${Date.now()}` : ""}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    allPromotions = Array.isArray(data) ? data : (data.promotions || []);
  } catch (error) {
    console.warn("โหลด promotions.json ไม่ได้ ใช้ข้อมูลสำรอง", error);
    allPromotions = getFallbackData();
    showToast("ใช้ข้อมูลสำรอง — หากเปิดจาก ACode ให้ใช้ Preview/Live Server");
  }

  filteredPromotions = [...allPromotions];
  currentPage = 1;
  renderAll();

  document.getElementById("lastUpdate").textContent =
    `อัปเดต ${new Date().toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" })}`;
}

function applyFilters() {
  filteredPromotions = allPromotions.filter(p => {
    const storeMatch = currentStore === "ทั้งหมด" || p.store === currentStore;
    const text = `${p.product || ""} ${p.store || ""} ${p.branch || ""} ${p.category || ""}`.toLowerCase();
    const searchMatch = !currentSearch || text.includes(currentSearch);
    return storeMatch && searchMatch;
  });

  currentPage = 1;
  renderAll();
}

function handleQuickFilter(type) {
  if (type === "ทั้งหมด") {
    currentStore = "ทั้งหมด";
    currentSearch = "";
    document.getElementById("searchInput").value = "";
    filteredPromotions = [...allPromotions];
    document.querySelectorAll(".store-tab").forEach(b => {
      b.classList.toggle("active", b.dataset.store === "ทั้งหมด");
    });
  }

  if (type === "ลดเกิน 30%") {
    filteredPromotions = allPromotions.filter(p => getDiscountPercent(p) >= 30);
  }

  if (type === "ใกล้หมด") {
    filteredPromotions = allPromotions.filter(p => p.urgent === true);
  }

  currentPage = 1;
  renderAll();
}

function renderAll() {
  renderStats();
  renderPromotions();
}

function renderStats() {
  const total = filteredPromotions.length;
  const stores = new Set(filteredPromotions.map(p => p.store)).size;
  const avg = total
    ? Math.round(filteredPromotions.reduce((sum, p) => sum + getDiscountPercent(p), 0) / total)
    : 0;

  document.getElementById("resultCount").textContent = `${total} รายการ`;
  document.getElementById("totalCount").textContent = total;
  document.getElementById("storeCount").textContent = stores;
  document.getElementById("discountCount").textContent = `${avg}%`;

  document.getElementById("heroDealCount").textContent = allPromotions.length;
  document.getElementById("heroStoreCount").textContent = new Set(allPromotions.map(p => p.store)).size;

  const heroAvg = allPromotions.length
    ? Math.round(allPromotions.reduce((sum, p) => sum + getDiscountPercent(p), 0) / allPromotions.length)
    : 0;
  document.getElementById("heroAvgDiscount").textContent = `${heroAvg}%`;
}

function renderPromotions() {
  const list = document.getElementById("promotionList");
  const empty = document.getElementById("emptyState");
  const loadMore = document.getElementById("loadMoreBtn");

  if (!filteredPromotions.length) {
    list.innerHTML = "";
    empty.classList.remove("hidden");
    loadMore.classList.add("hidden");
    return;
  }

  empty.classList.add("hidden");

  const displayData = filteredPromotions.slice(0, currentPage * PAGE_SIZE);

  list.innerHTML = displayData.map(p => {
    const discount = getDiscountPercent(p);
    const saved = Math.max(0, Number(p.old_price || 0) - Number(p.new_price || 0));
    const image = escapeAttr(p.image || "https://images.unsplash.com/photo-1542838132-92c53300491e?w=800");

    return `
      <article class="promo-card">
        <div class="promo-image">
          <img src="${image}" alt="${escapeAttr(p.product)}" loading="lazy"
            onerror="this.src='https://images.unsplash.com/photo-1542838132-92c53300491e?w=800'">
          <span class="badge store-badge">${escapeHtml(p.store)}</span>
          <span class="badge discount-badge">-${discount}%</span>
          ${p.urgent ? `<span class="badge expiry-badge">⏰ ใกล้หมด</span>` : ""}
        </div>

        <div class="promo-body">
          <h3>${escapeHtml(p.product)}</h3>

          <div class="price-row">
            <span class="new-price">฿${formatNumber(p.new_price)}</span>
            <span class="old-price">฿${formatNumber(p.old_price)}</span>
            <span class="save-pill">ประหยัด ฿${formatNumber(saved)}</span>
          </div>

          <p class="branch">📍 ${escapeHtml(p.branch || "ปราจีนบุรี")}</p>

          <div class="card-footer">
            <span>ถึง ${escapeHtml(p.expiry || "ตรวจสอบกับร้าน")}</span>
            <button class="share-btn" onclick="sharePromotion('${escapeAttr(String(p.id))}')">แชร์ ↗</button>
          </div>
        </div>
      </article>
    `;
  }).join("");

  loadMore.classList.toggle("hidden", displayData.length >= filteredPromotions.length);
}

function setLoading() {
  document.getElementById("promotionList").innerHTML = `
    <div class="skeleton card-skeleton"></div>
    <div class="skeleton card-skeleton"></div>
    <div class="skeleton card-skeleton"></div>
    <div class="skeleton card-skeleton"></div>
  `;
}

function getDiscountPercent(p) {
  const oldPrice = Number(p.old_price || 0);
  const newPrice = Number(p.new_price || 0);
  if (!oldPrice || oldPrice <= newPrice) return 0;
  return Math.round(((oldPrice - newPrice) / oldPrice) * 100);
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("th-TH");
}

function sharePromotion(id) {
  const p = allPromotions.find(item => String(item.id) === String(id));
  if (!p) return;

  const text = `🔥 ${p.product}\n${p.store}\n฿${formatNumber(p.new_price)} จาก ฿${formatNumber(p.old_price)}\n📍 ${p.branch}`;

  if (navigator.share) {
    navigator.share({ title: p.product, text, url: location.href }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(`${text}\n${location.href}`);
    showToast("คัดลอกโปรโมชั่นแล้ว");
  } else {
    showToast("อุปกรณ์นี้ยังไม่รองรับการแชร์");
  }
}

function toggleTheme() {
  document.body.classList.toggle("dark");
  localStorage.setItem("promo-theme", document.body.classList.contains("dark") ? "dark" : "light");
  document.getElementById("themeBtn").textContent = document.body.classList.contains("dark") ? "☀" : "☾";
}

function restoreTheme() {
  const dark = localStorage.getItem("promo-theme") === "dark";
  document.body.classList.toggle("dark", dark);
  document.getElementById("themeBtn").textContent = dark ? "☀" : "☾";
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add("hidden"), 2600);
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value = "") {
  return escapeHtml(value);
}

function getFallbackData() {
  return [
    {id:"1",store:"Lotus's",product:"ข้าวหอมมะลิ 5 กก.",old_price:189,new_price:149,expiry:"18 ส.ค. 69",branch:"Lotus's ปราจีนบุรี",category:"อาหาร",urgent:false,image:"https://images.unsplash.com/photo-1586201375761-83865001e31c?w=800"},
    {id:"2",store:"Big C",product:"นมยูเอชที แพ็ค 12 กล่อง",old_price:142,new_price:99,expiry:"17 ส.ค. 69",branch:"Big C ปราจีนบุรี",category:"เครื่องดื่ม",urgent:true,image:"https://images.unsplash.com/photo-1550583724-b2692b85b150?w=800"},
    {id:"3",store:"CJ More",product:"บะหมี่กึ่งสำเร็จรูป แพ็ค 10",old_price:62,new_price:49,expiry:"20 ส.ค. 69",branch:"CJ More โซน 304",category:"อาหาร",urgent:false,image:"https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800"},
    {id:"4",store:"Lotus's",product:"น้ำมันพืช 1 ลิตร",old_price:68,new_price:42,expiry:"16 ส.ค. 69",branch:"Lotus's ปราจีนบุรี",category:"อาหาร",urgent:true,image:"https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=800"}
  ];
}
