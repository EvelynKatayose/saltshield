"""Stage the self-contained website and a bilingual presenter walkthrough."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from shutil import copyfile

ROOT=Path(__file__).resolve().parent


def build(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    config=json.loads((ROOT/'deployment/site.json').read_text())
    url=config['expected_url'].rstrip('/')+'/?demo=1#experience'
    if 'codex' in url.lower() or not url.startswith('https://'):raise ValueError('The demo requires a clean HTTPS URL')
    guide=json.loads((ROOT/'demo_steps.json').read_text());esc=html.escape
    markdown=['# SaltShield：三分钟 Demo','',f'演示入口：{url}','','演示模式不读取或覆盖普通模式保存的预算、项目和容量。每次重新加载或点 Restart demo 都从默认情景开始。','']
    sections=[]
    for index,step in enumerate(guide['steps'],1):
        markdown.extend([f"## {index}. {step['title']}（{step['time']}）",'',f"**怎么点：** {step['action']}",'',f"**应当看到：** {step['expect']}",'',f"> {step['say']}",''])
        sections.append(f'<section><div class="time">{esc(step["time"])}</div><h2>{index}. {esc(step["title"])}</h2><p><b>操作：</b>{esc(step["action"])}</p><p class="note">{esc(step["expect"])}</p><blockquote>{esc(step["say"])}</blockquote></section>')
    markdown.extend(['## 临场处理','',*[f'- {item}' for item in guide['recovery']],'','## 技术核心（被问到时）','',guide['technical_answer'],''])
    (ROOT/'DEMO.md').write_text('\n'.join(markdown))
    style='body{font:15px/1.8 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f3f6f6;color:#183a42;margin:0;padding:38px 20px}main{max-width:850px;margin:auto}h1{font-size:34px;letter-spacing:-1px;line-height:1.2}h2{font-size:21px;margin:5px 0 17px}section{padding:28px;background:white;border:1px solid #dbe5e6;border-radius:16px;margin:20px 0}.time{color:#488679;font-size:11px;letter-spacing:1px}p{margin:10px 0}.note{font-size:13px;color:#648087}blockquote{margin:20px 0 0;border-left:3px solid #7fc7b4;padding:12px 18px;background:#f3f8f6;color:#244f51}a{color:#1d7264}.entry{display:inline-block;padding:11px 18px;background:#1d6459;color:#fff;border-radius:8px;text-decoration:none}small{color:#6b858c}@media print{body{background:white;padding:0}section{break-inside:avoid}.entry{display:none}}'
    recovery=''.join('<li>'+esc(item)+'</li>' for item in guide['recovery'])
    page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SaltShield — Demo walkthrough</title><style>'+style+'</style></head><body><main><small>SALTSHIELD / PRESENTER WALKTHROUGH</small><h1>三分钟 Demo，一步一步来。</h1><p>中文操作提示，英文现场讲稿。</p><p><a class="entry" href="/?demo=1#experience">打开固定演示案例 ↗</a></p><p class="note">演示模式从 $75,000 默认案例开始，保留你普通模式保存的参数。这个网址的访问权限与主站相同。</p>'+''.join(sections)+'<section><h2>临场处理</h2><ul>'+recovery+'</ul><h2>技术核心</h2><p>'+esc(guide['technical_answer'])+'</p></section></main></body></html>'
    copyfile(ROOT/'results/SaltShield_Wachusett.html',output/'index.html')
    (output/'demo.html').write_text(page)
    manifest={'source_report_sha256':hashlib.sha256((output/'index.html').read_bytes()).hexdigest(),'demo_entry':url,'files':['index.html','demo.html']}
    (output/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'output':str(output),'files':manifest['files'],'demo_entry':url},indent=2))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT.parent/'saltshield-hosted/dist'));args=parser.parse_args();build(args.output)
