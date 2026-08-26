from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, asdict
from pathlib import Path

POLICY_VERSION='8-final-vegetarian-nationwide-v1'
PROVINCES=(
'กรุงเทพมหานคร','กระบี่','กาญจนบุรี','กาฬสินธุ์','กำแพงเพชร','ขอนแก่น','จันทบุรี','ฉะเชิงเทรา','ชลบุรี','ชัยนาท','ชัยภูมิ','ชุมพร','เชียงราย','เชียงใหม่','ตรัง','ตราด','ตาก','นครนายก','นครปฐม','นครพนม','นครราชสีมา','นครศรีธรรมราช','นครสวรรค์','นนทบุรี','นราธิวาส','น่าน','บึงกาฬ','บุรีรัมย์','ปทุมธานี','ประจวบคีรีขันธ์','ปราจีนบุรี','ปัตตานี','พระนครศรีอยุธยา','พะเยา','พังงา','พัทลุง','พิจิตร','พิษณุโลก','เพชรบุรี','เพชรบูรณ์','แพร่','ภูเก็ต','มหาสารคาม','มุกดาหาร','แม่ฮ่องสอน','ยโสธร','ยะลา','ร้อยเอ็ด','ระนอง','ระยอง','ราชบุรี','ลพบุรี','ลำปาง','ลำพูน','เลย','ศรีสะเกษ','สกลนคร','สงขลา','สตูล','สมุทรปราการ','สมุทรสงคราม','สมุทรสาคร','สระแก้ว','สระบุรี','สิงห์บุรี','สุโขทัย','สุพรรณบุรี','สุราษฎร์ธานี','สุรินทร์','หนองคาย','หนองบัวลำภู','อ่างทอง','อำนาจเจริญ','อุดรธานี','อุตรดิตถ์','อุทัยธานี','อุบลราชธานี')
QUERY_PATTERNS=(
'ร้านอาหารเจ {province}','ร้านเจ {province}','อาหารเจ {province}','ข้าวเจ {province}',
'ร้านมังสวิรัติ {province}','อาหารมังสวิรัติ {province}','vegetarian restaurant {province}','vegan restaurant {province}')
PRIMARY_NAME_TERMS=('อาหารเจ','ร้านเจ','เจ ','มังสวิรัติ','vegetarian','vegan')

def build_plan():
    jobs=[]
    for province in PROVINCES:
        for i,p in enumerate(QUERY_PATTERNS,1):
            q=p.format(province=province)
            jid=hashlib.sha1(f'web|{province}|{q}'.encode()).hexdigest()[:16]
            jobs.append({'job_id':jid,'province':province,'channel':'web_query','query':q,'status':'pending'})
        jid=hashlib.sha1(f'osm|{province}'.encode()).hexdigest()[:16]
        jobs.append({'job_id':jid,'province':province,'channel':'osm_province_sweep','query':'diet:vegetarian/diet:vegan + vegetarian-name sweep','status':'pending'})
    return jobs

def classify_candidate(name='', tags=None):
    tags=tags or {}; n=str(name or '').casefold()
    veg=str(tags.get('diet:vegetarian','')).casefold(); vegan=str(tags.get('diet:vegan','')).casefold()
    dedicated=any(t.casefold() in n for t in PRIMARY_NAME_TERMS)
    diet_positive=veg=='yes' or vegan=='yes'
    if dedicated:return {'scope':'DEDICATED_OR_NAMED','primary_candidate':True,'reason':'dedicated_name_signal'}
    if diet_positive:return {'scope':'OPTION_AVAILABLE','primary_candidate':False,'reason':'diet_option_signal'}
    return {'scope':'UNRESOLVED','primary_candidate':False,'reason':'insufficient_diet_scope'}

def load_ledger(path):
    p=Path(path)
    if not p.exists():return {'policy_version':POLICY_VERSION,'jobs':{}}
    x=json.loads(p.read_text(encoding='utf8')); x.setdefault('jobs',{}); return x

def merge_plan_with_ledger(plan,ledger):
    old=ledger.get('jobs',{}); out=[]
    for j in plan:
        x=dict(j); prev=old.get(j['job_id'],{})
        if prev.get('status') in {'completed','failed','partial'}:
            x.update({k:v for k,v in prev.items() if k not in {'province','channel','query'}})
            x['province']=j['province'];x['channel']=j['channel'];x['query']=j['query']
        out.append(x)
    return out

def coverage_summary(jobs):
    by={p:{'total':0,'completed':0,'pending':0,'failed':0,'partial':0} for p in PROVINCES}
    for j in jobs:
        d=by[j['province']];d['total']+=1;s=j.get('status','pending');d[s]=d.get(s,0)+1
    swept=sum(1 for d in by.values() if d['completed']+d['partial']>0)
    complete=sum(1 for d in by.values() if d['completed']==d['total'])
    return {'province_count':len(PROVINCES),'jobs_total':len(jobs),'provinces_started':swept,'provinces_complete':complete,'all_provinces_planned':len(by)==77,'by_province':by,'real_world_completeness_claimed':False}

def build_osm_query(area_id:int):
    # Area-specific sweep: dietary tags plus names that explicitly signal veg/jay.
    return f'''[out:json][timeout:90];\narea({int(area_id)})->.a;\n(\n nwr["amenity"~"^(restaurant|cafe|fast_food|food_court)$"]["diet:vegetarian"="yes"](area.a);\n nwr["amenity"~"^(restaurant|cafe|fast_food|food_court)$"]["diet:vegan"="yes"](area.a);\n nwr["name"~"เจ|มังสวิรัติ|vegetarian|vegan",i](area.a);\n);\nout center tags;'''
