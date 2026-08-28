(() => {
"use strict"; const $=id=>document.getElementById(id), CONFIRM="PUBLISH_VERIFIED_UPDATE";
const val=id=>($(id)?.value||"").trim();
function payload(){return {place_id:val("verifiedPlaceId"),field_name:val("verifiedField"),value:val("verifiedValue"),
source_name:val("verifiedSourceName"),source_url:val("verifiedSourceUrl"),observed_at:val("verifiedObservedAt"),
trust_tier:"operator_verified_independent_source",community_report:false,
community_source_url:val("verifiedCommunitySourceUrl"),operator_note:val("verifiedNote")};}
async function call(url,body){const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
const d=await r.json(); if(!r.ok) throw new Error(d.error||`HTTP ${r.status}`); return d;}
async function preview(){try{const d=await call("/api/admin/verified-update/preview",payload());$("verifiedResult").textContent=JSON.stringify(d,null,2);
$("verifiedCommit").disabled=d.dry_run?.status!=="READY";$("verifiedStatus").textContent=d.dry_run?.status==="READY"?"Dry-run ผ่าน":"Dry-run ยังไม่พร้อม";}
catch(e){$("verifiedStatus").textContent=e.message;$("verifiedCommit").disabled=true;}}
async function commit(){if(val("verifiedConfirm")!==CONFIRM){$("verifiedStatus").textContent=`กรอก ${CONFIRM}`;return;}
try{const d=await call("/api/admin/verified-update/commit",{payload:payload(),confirm:val("verifiedConfirm")});
$("verifiedResult").textContent=JSON.stringify(d,null,2);$("verifiedStatus").textContent=`ผล: ${d.result?.status||d.status}`;}
catch(e){$("verifiedStatus").textContent=e.message;}}

function prefillFromQuery(){
  const q=new URLSearchParams(location.search);
  const map={
    verifiedPlaceId:"place_id",verifiedField:"field",verifiedValue:"value",
    verifiedSourceName:"source_name",verifiedSourceUrl:"source_url",
    verifiedCommunitySourceUrl:"community_source_url",verifiedObservedAt:"observed_at",
    verifiedNote:"note"
  };
  for(const [id,key] of Object.entries(map)){
    const node=$(id), value=q.get(key);
    if(node&&value!=null&&value!=="") node.value=value;
  }
  if(q.get("from_approved_draft")==="1"){
    $("verifiedStatus").textContent="มาจาก Admin Draft ที่อนุมัติแล้ว — ตรวจ Dry-run ก่อน Publish";
  }
}

function start(){prefillFromQuery();$("verifiedPreview")?.addEventListener("click",preview);$("verifiedCommit")?.addEventListener("click",commit);}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});else start();
})();