# -*- coding: utf-8 -*-
"""
gen_bom.py —— 从 .epro2 工程文件离线生成 BOM（CSV）

为什么离线生成：
    EDA 官方 getBomFile() 要求原理图文档处于激活状态，依赖 UI 状态、不可脚本化重跑。
    而 .epro2 里已包含全部选型数据，离线解析可重复、可进版本控制、CI 友好。

数据组装：
    1) SCH_PAGE 文档 -> 元件属性（位号/厂商/厂商料号/供应商料号/容差/耐压…）
    2) PCB     文档 -> 位号 -> 封装 uuid
    3) FOOTPRINT 文档 -> 封装 uuid -> 封装名
    三者以位号为主键 join。

用法：
    python gen_bom.py <工程.epro2> <输出目录>
"""
import sys, os, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epro_parse import load_project

COLS = ['位号', '型号 / 值', '厂商', '厂商料号', '供应商', '供应商料号',
        '立创料号', '封装', '容差', '耐压', '数量', '说明']


def sort_key(des):
    pre = ''.join(ch for ch in des if ch.isalpha())
    num = ''.join(ch for ch in des if ch.isdigit())
    order = {'U': 0, 'X': 1, 'SW': 2, 'USB': 3, 'J': 4, 'D': 5, 'R': 6, 'C': 7}
    return (order.get(pre, 99), int(num) if num else 0)


def _kv_by_parent(records):
    """把 key/value 记录按 parentId 聚合成 {parentId: {key: value}}"""
    out = collections.defaultdict(dict)
    for r in records:
        if isinstance(r, dict) and 'key' in r and 'value' in r and r.get('parentId'):
            out[r['parentId']][r['key']] = r.get('value')
    return out


def build(epro2_path):
    meta, docs = load_project(epro2_path)
    sch = [d for d in docs if d['docType'] == 'SCH_PAGE'][0]
    pcb = [d for d in docs if d['docType'] == 'PCB' and len(d['records']) > 100]
    pcb = pcb[0] if pcb else None

    # 1) 封装 uuid -> 封装名（FOOTPRINT 文档中 META 之后的 title 记录）
    fp_name = {}
    for d in docs:
        if d['docType'] != 'FOOTPRINT':
            continue
        for r in d['records']:
            if isinstance(r, dict):
                nm = r.get('name') or r.get('title')
                if nm:
                    fp_name[d['uuid']] = nm
                    break

    # 2) 位号 -> 封装 uuid（来自 PCB）
    des2fp = {}
    if pcb:
        p = _kv_by_parent(pcb['records'])
        for pid, a in p.items():
            if a.get('Designator') and a.get('Footprint'):
                des2fp[a['Designator']] = a['Footprint']

    # 3) 原理图元件属性
    rows = []
    for pid, a in _kv_by_parent(sch['records']).items():
        des = a.get('Designator')
        if not des:
            continue

        def av(k):
            return str(a.get(k) or '').strip()

        mfr_part = av('Manufacturer Part')
        name = mfr_part or av('Value') or av('Name')
        fp_uuid = des2fp.get(des, '')
        rows.append({
            '位号': str(des),
            '型号 / 值': name,
            '厂商': av('Manufacturer'),
            '厂商料号': mfr_part,
            '供应商': av('Supplier'),
            '供应商料号': av('Supplier Part'),
            '立创料号': av('LCSC Part Name'),
            '封装': fp_name.get(fp_uuid, fp_uuid),
            '容差': av('Tolerance'),
            '耐压': av('Voltage Rating'),
            '数量': 1,
            '说明': av('Description')[:120],
        })
    rows.sort(key=lambda r: sort_key(r['位号']))
    return meta, rows


def main():
    epro2, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    meta, rows = build(epro2)

    csv_path = os.path.join(outdir, 'STM32F103C8T6-MinSys_BOM.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print('写入 %s  %d 行' % (csv_path, len(rows)))

    # 按料号汇总（采购视图）
    grp = collections.OrderedDict()
    for r in rows:
        key = (r['厂商料号'] or r['型号 / 值'], r['封装'], r['厂商'])
        g = grp.setdefault(key, {'料号': key[0], '封装': key[1], '厂商': key[2],
                                 '数量': 0, '位号': []})
        g['数量'] += 1
        g['位号'].append(r['位号'])
    gpath = os.path.join(outdir, 'STM32F103C8T6-MinSys_BOM_采购汇总.csv')
    with open(gpath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['料号', '厂商', '封装', '数量', '位号'])
        w.writeheader()
        for g in grp.values():
            g['位号'] = ', '.join(g['位号'])
            w.writerow(g)
    print('写入 %s  %d 种物料' % (gpath, len(grp)))
    print()
    print('%-6s %-20s %-16s %-20s %s' % ('位号', '型号/值', '厂商', '厂商料号', '封装'))
    print('-' * 100)
    for r in rows:
        print('%-6s %-20s %-16s %-20s %s' % (
            r['位号'], r['型号 / 值'][:20], r['厂商'][:16],
            r['厂商料号'][:20], r['封装']))


if __name__ == '__main__':
    main()
