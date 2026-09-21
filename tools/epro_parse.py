# -*- coding: utf-8 -*-
"""
epro_parse.py —— 解析嘉立创EDA专业版工程文件(.epro2)

.epro2 是 zip 容器：
    project2.json                      工程元数据
    IMAGE/<uuid>.webp                  各文档预览图
    <工程名>.epru                      工程数据正文（纯文本，多文档拼接）

.epru 内部格式：
    {"type":"DOCHEAD","ticket":N}||{"docType":"XXX","uuid":"...",...}||<记录>||<记录>...
    每个 DOCHEAD 起始一个新文档；文档内记录以 || 分隔。

用法：
    from epro_parse import load_project, docs_of_type
    proj = load_project('xxx.epro2')
    for d in proj:
        print(d['docType'], d['uuid'], len(d['records']))
"""
import zipfile, json, re, collections, os


def _split_docs(text):
    """按 DOCHEAD 把 .epru 正文切成文档列表"""
    idx = [m.start() for m in re.finditer(r'\{"type":"DOCHEAD"', text)]
    idx.append(len(text))
    docs = []
    for a, b in zip(idx, idx[1:]):
        seg = text[a:b]
        dec = json.JSONDecoder()
        i, recs = 0, []
        while i < len(seg):
            while i < len(seg) and seg[i] in '| \r\n\t':
                i += 1
            if i >= len(seg):
                break
            try:
                obj, end = dec.raw_decode(seg, i)
            except Exception:
                break
            recs.append(obj)
            i = end
        if len(recs) >= 2 and isinstance(recs[1], dict) and 'docType' in recs[1]:
            head = recs[1]
            docs.append({
                'docType': head.get('docType'),
                'uuid': head.get('uuid'),
                'head': head,
                'records': recs[2:],
            })
    return docs


def load_project(epro2_path):
    """返回 (meta, docs)；meta 为 project2.json 内容"""
    z = zipfile.ZipFile(epro2_path)
    meta = json.loads(z.read('project2.json').decode('utf-8'))
    epru_name = [n for n in z.namelist()
                 if n.endswith('.epru') and not n.startswith('IMAGE')][0]
    text = z.read(epru_name).decode('utf-8', errors='replace')
    return meta, _split_docs(text)


def doc_of_type(docs, docType, uuid=None):
    out = [d for d in docs if d['docType'] == docType
           and (uuid is None or d['uuid'] == uuid)]
    return out


def recs_matching(doc, key):
    return [r for r in doc['records'] if isinstance(r, dict) and key in r]


if __name__ == '__main__':
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else 'STM32F103C8T6-MinSys.epro2'
    meta, docs = load_project(p)
    print('meta:', meta)
    print('docs:', len(docs))
    for d in docs:
        print('  %-12s %-20s recs=%d' % (d['docType'], d['uuid'], len(d['records'])))
