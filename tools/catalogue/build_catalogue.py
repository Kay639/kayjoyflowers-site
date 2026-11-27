#!/usr/bin/env python3
"""Build projections from the authoritative Drive master. Never edits the master."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from urllib.parse import urlparse
FIELDS=['item_id','title','description','url','brand','seller_name','image_url','availability','price','target_countries','store_country','is_digital','is_eligible_checkout','is_ads_eligible']
STATUSES={'available','coming_soon','retired','needs_confirmation'}
def validate(m):
    errors=[];seen=set()
    for p in m['items']:
        if p['id'] in seen:errors.append('Duplicate ID: '+p['id'])
        seen.add(p['id'])
        for key,limit in [('name',150),('description',5000)]:
            if not isinstance(p.get(key),str) or not p[key].strip() or len(p[key])>limit:errors.append('Missing or overlong '+key+': '+p['id'])
        if p['status'] not in STATUSES:errors.append('Invalid status: '+p['id'])
        if p['status']=='coming_soon':
            if p.get('purchase_url'):errors.append('Coming Soon item must not carry checkout: '+p['id'])
            if p.get('pricing') and (p.get('pricing_approval')!='approved' or not p.get('approval_evidence')):errors.append('Coming Soon price needs explicit approval evidence: '+p['id'])
        for key in ['detail_url','purchase_url','access_url','image_url']:
            value=p.get(key)
            if value and (urlparse(value).scheme!='https' or not urlparse(value).netloc):errors.append('Invalid HTTPS '+key+': '+p['id'])
        if p.get('pricing'):
            q=p['pricing']
            if not re.fullmatch(r'\d+\.\d{2}',q['amount']):errors.append('Invalid price: '+p['id'])
            if q['currency'] not in ['USD','NZD']:errors.append('Unconfigured currency: '+p['id'])
        if p['feed']['status']=='eligible' and not p['feed'].get('evidence'):errors.append('Eligibility needs evidence: '+p['id'])
    return errors

def feed_rows(m,staging=False):
    rows=[]
    for p in m['items']:
        if p['status']!='available' or p['kind'] not in ['digital_book','digital_bundle']:continue
        if not staging and p['feed']['status']!='eligible':continue
        if not staging and p.get('commercial_approval') not in ['existing_live_offer','approved']:raise ValueError('Commercial approval required: '+p['id'])
        q=p['pricing']
        if q['billing']!='one_time' or float(q['amount'])<=0:continue
        if not all(p.get(k) for k in ['detail_url','purchase_url','image_url']):raise ValueError('Missing detail/purchase/image: '+p['id'])
        rows.append(dict(item_id=p['id'],title=p['name'],description=p['description'],url=p['detail_url'],brand='Kay Joy Flowers',seller_name='Kay Joy Flowers',image_url=p['image_url'],availability='in_stock',price=q['amount']+' '+q['currency'],target_countries=m['integration'].get('target_countries') or (['US'] if staging else []),store_country=m['integration']['store_country'],is_digital=True,is_eligible_checkout=False,is_ads_eligible=False))
    return rows

def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,separators=(',',':')) if isinstance(v,(bool,list,dict)) else v for k,v in r.items()})

def price_text(q):
    if not q:return 'No price announced.'
    prefix='US$' if q['currency']=='USD' else 'NZ$'
    amount=prefix+f"{float(q['amount']):g}"
    if q['billing']=='free':return 'Free access.'
    text=amount+({'one_time':' one time','month':' per month','year':' per year','one_time_add_on':' one-time add-on'}[q['billing']])+'.'
    if q.get('initial_charge'):text+=' Initial payment: '+prefix+f"{float(q['initial_charge']):g}"+'.'
    if q.get('trial_days'):text+=f" {q['trial_days']}-day free trial; card required."
    return text

def business_info(m):
    lines=['PROPOSED BUSINESS INFO ADDITION — APPROVAL REQUIRED','Add to the existing Business info; preserve agent instructions and unrelated business information.','']
    for p in m['items']:
        if not p['business_info']['include'] or p['status'] not in ['available','coming_soon']:continue
        price=price_text(p.get('pricing'))
        if p['kind']=='included_component':
            price='Included in the Sovereignty Bundle.'
            if p.get('standalone_offer'):
                price+=' Approved standalone price: '+price_text(p['standalone_offer']['pricing'])+' Standalone checkout is not verified; do not offer a standalone purchase link.'
        if p['status']=='coming_soon':price+=' Coming Soon; not available to purchase. No confirmed launch date or purchase link.'
        lines += [p['name']+(' — Coming Soon' if p['status']=='coming_soon' else ''),p['description'],price]
        if p.get('purchase_url'):lines.append('Purchase: '+p['purchase_url'])
        if p.get('access_url'):lines.append('Access: '+p['access_url'])
        if p.get('detail_url'):lines.append('Details: '+p['detail_url'])
        lines.append('')
    return '\n'.join(lines)

def build(master,out,production=False):
    raw=Path(master).read_bytes();m=json.loads(raw);errors=validate(m)
    if errors:raise ValueError('; '.join(errors))
    out=Path(out)
    gates=[]
    i=m['integration']
    for k in ['digital_support_confirmed','nz_store_supported']:
        if not i.get(k):gates.append(k)
    if not i.get('target_countries'):gates.append('target_countries_not_confirmed')
    if not i.get('support_evidence'):gates.append('integration_evidence_missing')
    if i.get('store_country')!='NZ':gates.append('unexpected_store_country')
    if i.get('target_countries') and (not isinstance(i['target_countries'],list) or any(not isinstance(c,str) or not re.fullmatch('[A-Z]{2}',c) for c in i['target_countries'])):gates.append('invalid_target_countries')
    rows=feed_rows(m,staging=not production)
    if production and (gates or not rows):raise ValueError('Production blocked: '+', '.join(gates or ['no eligible rows; review removals explicitly']))
    out.mkdir(parents=True,exist_ok=True)
    label='products.csv' if production else 'products_STAGED.csv'
    write_csv(out/label,rows)
    (out/'business_info_FOR_APPROVAL.txt').write_text(business_info(m),encoding='utf-8')
    overview=['# Commercial catalogue review','Generated from the Drive master; do not edit this projection.','', '| Offering | Status | Price | Feed status |','|---|---|---|---|']
    for p in m['items']:overview.append('| '+p['name']+' | '+p['status']+' | '+price_text(p.get('pricing'))+' | '+p['feed']['status']+' |')
    (out/'catalogue_review.md').write_text('\n'.join(overview)+'\n')
    report={'source_sha256':hashlib.sha256(raw).hexdigest(),'revision':m['revision'],'master_records':len(m['items']),'feed_rows':len(rows),'local_validation':'PASS','production':production,'remaining_gates':gates,'business_info_approved':all(p['business_info']['approval']=='approved' for p in m['items'] if p['business_info']['include']),'remote_upload':'not_attempted','live_agent_verification':'not_run'}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--master',required=True);a.add_argument('--out',required=True);a.add_argument('--production',action='store_true');args=a.parse_args()
    print(json.dumps(build(args.master,args.out,args.production),indent=2))
