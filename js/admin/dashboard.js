(function(global){
"use strict";
const $=id=>document.getElementById(id);
const labels={
  category_view:"เปิดหมวด",
  search:"ค้นหา",
  near_me:"Near Me",
  decision_view:"AI แสดงคำแนะนำ",
  decision_select:"เลือกคำแนะนำ",
  place_detail:"เปิดรายละเอียด",
  map_action:"กดแผนที่",
  decision_feedback_helpful:"AI มีประโยชน์",
  decision_feedback_not_helpful:"AI ยังไม่ช่วย"
};
const n=v=>Number(v)||0;
function render(){
  const analytics=global.PrachinLife?.core?.usageAnalytics;
  const counts=analytics?.summary?.()||{};
  const total=Object.values(counts).reduce((sum,v)=>sum+n(v),0);
  $("events").textContent=total;
  $("searches").textContent=n(counts.search);
  $("nearMe").textContent=n(counts.near_me);
  $("placeDetail").textContent=n(counts.place_detail);
  $("decision").textContent=n(counts.decision_view)+n(counts.decision_select);
  $("mapAction").textContent=n(counts.map_action);
  $("eventTable").innerHTML=Object.keys(labels).map(
    key=>`<div><span>${labels[key]}</span><strong>${n(counts[key])}</strong></div>`
  ).join("");
}
async function health(){
  const targets=[
    ["promotions.json","โปรโมชั่น"],
    ["prachinlife_index.json","ช้อป / กิน"],
    ["vegetarian_index.json","เจ / มังสวิรัติ"],
    ["go_index.json","เที่ยว"],
    ["service_index.json","บริการ"]
  ];
  const rows=await Promise.all(targets.map(async([url,label])=>{
    try{
      const r=await fetch(url,{cache:"no-store"});
      if(!r.ok) throw new Error("http");
      const d=await r.json();
      const count=Array.isArray(d)?d.length:
        Array.isArray(d.items)?d.items.length:
        Array.isArray(d.places)?d.places.length:
        Number(d.total)||"พร้อม";
      return `<div><span>${label}</span><strong class="ok">${count}</strong></div>`;
    }catch(_){
      return `<div><span>${label}</span><strong class="bad">อ่านไม่ได้</strong></div>`;
    }
  }));
  $("dataHealth").innerHTML=rows.join("");
}
$("refreshBtn")?.addEventListener("click",()=>{render();health();});
render();
health();
})(window);
