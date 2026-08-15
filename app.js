const DATA_URL = "promotions.json";
const PAGE_SIZE = 8;

let allPromotions = [];
let filteredPromotions = [];

let currentStore = "ทั้งหมด";
let currentSearch = "";
let currentPage = 1;
let currentSort = "default";


document.addEventListener(
    "DOMContentLoaded",
    init
);


async function init(){

    bindEvents();

    restoreTheme();

    await loadPromotions();

}



/* =====================================================
EVENTS
===================================================== */

function bindEvents(){


    const searchInput =
        document.getElementById("searchInput");


    const searchBtn =
        document.getElementById("searchBtn");


    const storeTabs =
        document.getElementById("storeTabs");


    const loadMoreBtn =
        document.getElementById("loadMoreBtn");


    const refreshBtn =
        document.getElementById("refreshBtn");


    const themeBtn =
        document.getElementById("themeBtn");


    const sortSelect =
        document.getElementById("sortSelect");



    if(searchInput){

        searchInput.addEventListener(
            "input",
            event => {

                currentSearch =
                    event.target.value
                    .trim()
                    .toLowerCase();

                currentPage = 1;

                applyFilters();

            }
        );

    }



    if(searchBtn){

        searchBtn.addEventListener(
            "click",
            () => {

                currentSearch =
                    searchInput.value
                    .trim()
                    .toLowerCase();

                currentPage = 1;

                applyFilters();

            }
        );

    }



    if(storeTabs){

        storeTabs.addEventListener(
            "click",
            event => {

                const button =
                    event.target.closest(
                        "[data-store]"
                    );


                if(!button){
                    return;
                }


                currentStore =
                    button.dataset.store;


                currentPage = 1;


                document
                    .querySelectorAll(
                        ".store-tab"
                    )
                    .forEach(
                        item =>
                            item.classList
                            .remove("active")
                    );


                button.classList
                    .add("active");


                applyFilters();

            }
        );

    }



    document
        .querySelectorAll(
            "[data-quick]"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        handleQuickFilter(
                            button.dataset.quick
                        );

                    }
                );

            }
        );



    if(loadMoreBtn){

        loadMoreBtn.addEventListener(
            "click",
            () => {

                currentPage++;

                renderPromotions();

            }
        );

    }



    if(refreshBtn){

        refreshBtn.addEventListener(
            "click",
            async () => {

                showToast(
                    "กำลังอัปเดตข้อมูล..."
                );

                await loadPromotions(
                    true
                );

            }
        );

    }



    if(themeBtn){

        themeBtn.addEventListener(
            "click",
            toggleTheme
        );

    }



    if(sortSelect){

        sortSelect.addEventListener(
            "change",
            event => {

                currentSort =
                    event.target.value;

                currentPage = 1;

                applySorting();

                renderPromotions();

            }
        );

    }

}



/* =====================================================
LOAD DATA
===================================================== */

async function loadPromotions(
    forceRefresh = false
){

    setLoading();


    try{

        const url =
            forceRefresh
            ? `${DATA_URL}?t=${Date.now()}`
            : DATA_URL;


        const response =
            await fetch(
                url,
                {
                    cache:"no-store"
                }
            );


        if(!response.ok){

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        if(Array.isArray(data)){

            allPromotions =
                data;

        }

        else if(
            data &&
            Array.isArray(
                data.promotions
            )
        ){

            allPromotions =
                data.promotions;

        }

        else{

            allPromotions = [];

        }


        filteredPromotions =
            [...allPromotions];


        currentPage = 1;


        applySorting();


        renderAll();


        updateLastUpdate();


        if(forceRefresh){

            showToast(
                "อัปเดตข้อมูลล่าสุดแล้ว"
            );

        }

    }

    catch(error){

        console.error(
            "โหลด promotions.json ไม่สำเร็จ",
            error
        );


        allPromotions = [];

        filteredPromotions = [];


        renderAll();


        showToast(
            "ไม่สามารถโหลดข้อมูลได้"
        );

    }

}



/* =====================================================
FILTER
===================================================== */

function applyFilters(){

    filteredPromotions =
        allPromotions.filter(
            promotion => {

                const matchStore =
                    currentStore ===
                    "ทั้งหมด"
                    ||
                    promotion.store ===
                    currentStore;


                const searchableText =
                    [
                        promotion.product,
                        promotion.store,
                        promotion.branch,
                        promotion.category,
                        promotion.source
                    ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();


                const matchSearch =
                    !currentSearch
                    ||
                    searchableText.includes(
                        currentSearch
                    );


                return (
                    matchStore &&
                    matchSearch
                );

            }
        );


    currentPage = 1;


    applySorting();


    renderAll();

}



/* =====================================================
QUICK FILTER
===================================================== */

function handleQuickFilter(type){


    if(type === "all"){

        resetFilters();

        return;

    }



    if(type === "discount"){

        currentStore = "ทั้งหมด";

        filteredPromotions =
            allPromotions.filter(
                promotion =>
                    getDiscountPercent(
                        promotion
                    ) >= 30
            );

    }



    if(type === "urgent"){

        currentStore = "ทั้งหมด";

        filteredPromotions =
            allPromotions.filter(
                promotion =>
                    promotion.urgent ===
                    true
            );

    }



    if(type === "bigc"){

        currentStore =
            "Big C";


        filteredPromotions =
            allPromotions.filter(
                promotion =>
                    promotion.store ===
                    "Big C"
            );

    }


    currentPage = 1;


    updateStoreButtons();


    applySorting();


    renderAll();

}



/* =====================================================
RESET
===================================================== */

function resetFilters(){

    currentStore =
        "ทั้งหมด";


    currentSearch =
        "";


    currentPage =
        1;


    currentSort =
        "default";


    const search =
        document.getElementById(
            "searchInput"
        );


    if(search){

        search.value = "";

    }


    const sort =
        document.getElementById(
            "sortSelect"
        );


    if(sort){

        sort.value =
            "default";

    }


    filteredPromotions =
        [...allPromotions];


    updateStoreButtons();


    renderAll();

}


window.resetFilters =
    resetFilters;



/* =====================================================
SORT
===================================================== */

function applySorting(){


    const data =
        [...filteredPromotions];


    if(currentSort === "discount"){

        data.sort(
            (a,b) =>
                getDiscountPercent(b)
                -
                getDiscountPercent(a)
        );

    }



    else if(
        currentSort ===
        "price-low"
    ){

        data.sort(
            (a,b) => {

                const priceA =
                    getValidPrice(a);

                const priceB =
                    getValidPrice(b);


                if(priceA === null){
                    return 1;
                }


                if(priceB === null){
                    return -1;
                }


                return (
                    priceA -
                    priceB
                );

            }
        );

    }



    else if(
        currentSort ===
        "store"
    ){

        data.sort(
            (a,b) =>
                String(a.store || "")
                .localeCompare(
                    String(
                        b.store || ""
                    ),
                    "th"
                )
        );

    }



    filteredPromotions =
        data;

}



/* =====================================================
RENDER ALL
===================================================== */

function renderAll(){

    renderStats();

    renderPromotions();

}



/* =====================================================
STATS
===================================================== */

function renderStats(){


    const total =
        filteredPromotions.length;


    const storeTotal =
        new Set(
            filteredPromotions
            .map(
                item =>
                    item.store
            )
            .filter(Boolean)
        ).size;



    const discounts =
        filteredPromotions
        .map(
            getDiscountPercent
        )
        .filter(
            value =>
                value > 0
        );


    const averageDiscount =
        discounts.length
        ?
        Math.round(
            discounts.reduce(
                (sum,value) =>
                    sum + value,
                0
            )
            /
            discounts.length
        )
        :
        0;



    setText(
        "resultCount",
        `${total} รายการ`
    );


    setText(
        "totalCount",
        total
    );


    setText(
        "storeCount",
        storeTotal
    );


    setText(
        "discountCount",
        `${averageDiscount}%`
    );



    setText(
        "heroDealCount",
        allPromotions.length
    );


    const allStores =
        new Set(
            allPromotions
            .map(
                item =>
                    item.store
            )
            .filter(Boolean)
        ).size;


    setText(
        "heroStoreCount",
        allStores
    );



    const allDiscounts =
        allPromotions
        .map(
            getDiscountPercent
        )
        .filter(
            value =>
                value > 0
        );


    const overallAverage =
        allDiscounts.length
        ?
        Math.round(
            allDiscounts.reduce(
                (sum,value) =>
                    sum + value,
                0
            )
            /
            allDiscounts.length
        )
        :
        0;


    setText(
        "heroAvgDiscount",
        `${overallAverage}%`
    );

}



/* =====================================================
PROMOTION CARDS
===================================================== */

function renderPromotions(){


    const container =
        document.getElementById(
            "promotionList"
        );


    const emptyState =
        document.getElementById(
            "emptyState"
        );


    const loadMore =
        document.getElementById(
            "loadMoreBtn"
        );


    if(!container){
        return;
    }



    if(
        filteredPromotions
        .length === 0
    ){

        container.innerHTML = "";


        if(emptyState){

            emptyState.classList
                .remove("hidden");

        }


        if(loadMore){

            loadMore.classList
                .add("hidden");

        }


        return;

    }



    if(emptyState){

        emptyState.classList
            .add("hidden");

    }



    const visibleData =
        filteredPromotions.slice(
            0,
            currentPage
            *
            PAGE_SIZE
        );



    container.innerHTML =
        visibleData.map(
            createPromotionCard
        )
        .join("");



    if(loadMore){

        const hasMore =
            visibleData.length
            <
            filteredPromotions.length;


        loadMore.classList
            .toggle(
                "hidden",
                !hasMore
            );

    }

}



/* =====================================================
CARD
===================================================== */

function createPromotionCard(
    promotion
){


    const title =
        escapeHtml(
            promotion.product
            ||
            "โปรโมชั่น"
        );


    const store =
        escapeHtml(
            promotion.store
            ||
            "ร้านค้า"
        );


    const branch =
        escapeHtml(
            promotion.branch
            ||
            "ตรวจสอบสาขาที่ร่วมรายการ"
        );


    const expiry =
        escapeHtml(
            promotion.expiry
            ||
            "ตรวจสอบรายละเอียด"
        );


    const image =
        promotion.image
        ?
        escapeAttribute(
            promotion.image
        )
        :
        "";


    const discount =
        getDiscountPercent(
            promotion
        );


    const priceHTML =
        createPriceHTML(
            promotion
        );


    const discountBadge =
        discount > 0
        ?
        `
        <span
        class="badge discount-badge">
        -${discount}%
        </span>
        `
        :
        "";


    const urgentBadge =
        promotion.urgent === true
        ?
        `
        <span
        class="badge expiry-badge">
        ⏰ ใกล้หมด
        </span>
        `
        :
        "";


    const sourceButton =
        promotion.source_url
        ?
        `
        <a
        class="source-btn"
        href="${escapeAttribute(
            promotion.source_url
        )}"
        target="_blank"
        rel="noopener noreferrer">
        ต้นทาง ↗
        </a>
        `
        :
        "";


    return `

    <article class="promo-card">


        <div class="promo-image">


            ${
                image
                ?
                `
                <img
                src="${image}"
                alt="${title}"
                loading="lazy"
                onerror="this.style.display='none'"
                >
                `
                :
                `
                <div
                style="
                width:100%;
                height:100%;
                display:grid;
                place-items:center;
                font-size:52px;
                background:#eef2f6;
                ">
                🛒
                </div>
                `
            }


            <span
            class="badge store-badge">

            ${store}

            </span>


            ${discountBadge}


            ${urgentBadge}


        </div>



        <div class="promo-body">


            <h3>
            ${title}
            </h3>


            ${priceHTML}


            <p class="branch">

            📍 ${branch}

            </p>


            <div class="card-footer">


                <span>

                ${expiry}

                </span>



                <div class="card-actions">


                    ${sourceButton}


                    <button
                    class="share-btn"
                    type="button"
                    onclick="sharePromotion(
                    '${escapeAttribute(
                        String(
                            promotion.id
                            ||
                            ""
                        )
                    )}'
                    )">

                    แชร์ ↗

                    </button>


                </div>


            </div>


        </div>


    </article>

    `;

}



/* =====================================================
PRICE
===================================================== */

function createPriceHTML(
    promotion
){


    const oldPrice =
        Number(
            promotion.old_price
            ||
            promotion.oldPrice
            ||
            0
        );


    const newPrice =
        Number(
            promotion.new_price
            ||
            promotion.newPrice
            ||
            0
        );


    /*
    Collector Big C V1
    อาจมีราคาเป็น 0
    เพราะหน้าโปรโมชั่นต้นทาง
    ไม่ได้เปิดเผยราคาสินค้ารายตัว
    */


    if(
        newPrice <= 0
    ){

        return `

        <div class="no-price">

        🏷️ ดูรายละเอียดโปรโมชั่นจากต้นทาง

        </div>

        `;

    }



    const saved =
        oldPrice > newPrice
        ?
        oldPrice - newPrice
        :
        0;



    return `

    <div class="price-row">


        <span class="new-price">

        ฿${formatNumber(
            newPrice
        )}

        </span>


        ${
            oldPrice >
            newPrice
            ?
            `
            <span class="old-price">

            ฿${formatNumber(
                oldPrice
            )}

            </span>
            `
            :
            ""
        }


        ${
            saved > 0
            ?
            `
            <span class="save-pill">

            ประหยัด
            ฿${formatNumber(
                saved
            )}

            </span>
            `
            :
            ""
        }


    </div>

    `;

}



/* =====================================================
SHARE
===================================================== */

function sharePromotion(id){


    const promotion =
        allPromotions.find(
            item =>
                String(item.id)
                ===
                String(id)
        );


    if(!promotion){
        return;
    }



    let text =
        `🔥 ${promotion.product || "โปรโมชั่น"}\n`
        +
        `🏪 ${promotion.store || ""}\n`;



    const price =
        getValidPrice(
            promotion
        );


    if(price !== null){

        text +=
            `💰 ฿${formatNumber(price)}\n`;

    }



    if(promotion.branch){

        text +=
            `📍 ${promotion.branch}\n`;

    }



    if(promotion.source_url){

        text +=
            `${promotion.source_url}`;

    }



    if(
        navigator.share
    ){

        navigator.share(
            {
                title:
                    promotion.product
                    ||
                    "PromoPrachin",

                text:text,

                url:
                    promotion.source_url
                    ||
                    location.href
            }
        )
        .catch(
            () => {}
        );

    }


    else if(
        navigator.clipboard
    ){

        navigator.clipboard
            .writeText(text);


        showToast(
            "คัดลอกโปรโมชั่นแล้ว"
        );

    }


    else{

        showToast(
            "อุปกรณ์นี้ยังไม่รองรับการแชร์"
        );

    }

}


window.sharePromotion =
    sharePromotion;



/* =====================================================
HELPERS
===================================================== */

function getDiscountPercent(
    promotion
){


    const oldPrice =
        Number(
            promotion.old_price
            ||
            promotion.oldPrice
            ||
            0
        );


    const newPrice =
        Number(
            promotion.new_price
            ||
            promotion.newPrice
            ||
            0
        );


    if(
        oldPrice <= 0
        ||
        newPrice <= 0
        ||
        oldPrice <= newPrice
    ){

        return 0;

    }


    return Math.round(
        (
            (
                oldPrice -
                newPrice
            )
            /
            oldPrice
        )
        *
        100
    );

}



function getValidPrice(
    promotion
){


    const value =
        Number(
            promotion.new_price
            ||
            promotion.newPrice
            ||
            0
        );


    if(value <= 0){

        return null;

    }


    return value;

}



function formatNumber(
    value
){

    return Number(
        value || 0
    )
    .toLocaleString(
        "th-TH"
    );

}



function setText(
    id,
    value
){

    const element =
        document.getElementById(
            id
        );


    if(element){

        element.textContent =
            value;

    }

}



function updateLastUpdate(){


    const now =
        new Date();


    setText(
        "lastUpdate",
        now.toLocaleString(
            "th-TH",
            {
                dateStyle:"medium",
                timeStyle:"short"
            }
        )
    );

}



function updateStoreButtons(){


    document
        .querySelectorAll(
            ".store-tab"
        )
        .forEach(
            button => {

                button.classList
                    .toggle(
                        "active",
                        button.dataset.store
                        ===
                        currentStore
                    );

            }
        );

}



/* =====================================================
LOADING
===================================================== */

function setLoading(){


    const container =
        document.getElementById(
            "promotionList"
        );


    if(!container){
        return;
    }


    container.innerHTML = `

        <div class="skeleton"></div>

        <div class="skeleton"></div>

        <div class="skeleton"></div>

        <div class="skeleton"></div>

    `;

}



/* =====================================================
DARK MODE
===================================================== */

function toggleTheme(){


    document.body
        .classList
        .toggle("dark");


    const dark =
        document.body
        .classList
        .contains("dark");


    localStorage.setItem(
        "promo-theme",
        dark
        ?
        "dark"
        :
        "light"
    );


    const button =
        document.getElementById(
            "themeBtn"
        );


    if(button){

        button.textContent =
            dark
            ?
            "☀"
            :
            "☾";

    }

}



function restoreTheme(){


    const dark =
        localStorage.getItem(
            "promo-theme"
        )
        ===
        "dark";


    document.body
        .classList
        .toggle(
            "dark",
            dark
        );


    const button =
        document.getElementById(
            "themeBtn"
        );


    if(button){

        button.textContent =
            dark
            ?
            "☀"
            :
            "☾";

    }

}



/* =====================================================
TOAST
===================================================== */

function showToast(
    message
){


    const toast =
        document.getElementById(
            "toast"
        );


    if(!toast){
        return;
    }


    toast.textContent =
        message;


    toast.classList
        .remove("hidden");


    clearTimeout(
        showToast.timer
    );


    showToast.timer =
        setTimeout(
            () => {

                toast.classList
                    .add("hidden");

            },
            2600
        );

}



/* =====================================================
SECURITY
===================================================== */

function escapeHtml(
    value = ""
){

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );

}



function escapeAttribute(
    value = ""
){

    return escapeHtml(
        value
    );

}
