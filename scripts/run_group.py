#!/usr/bin/env python3
"""Ejecuta trabajos según la frecuencia; registra fallos con precisión."""
import sys, os, subprocess, json
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
group=sys.argv[1]
tasks=sys.argv[2:]
results=[]
for task in tasks:
    name,_,subgroup=task.partition(':')
    env=os.environ.copy()
    if subgroup:env['INEGI_UPDATE_GROUP']=subgroup
    script=(root/'scripts'/name).resolve()
    if script.parent != (root/'scripts').resolve() or not script.is_file():
        print(f'ERROR: script no encontrado o ruta inválida: {name}',file=sys.stderr)
        exit_code=2
    else:
        exit_code=subprocess.run([sys.executable,str(script)],cwd=root,env=env).returncode
    results.append({'script':name,'group':subgroup or None,'exit_code':exit_code,'status':'ok' if exit_code==0 else 'error'})
report={'group':group,'run_at_utc':datetime.now(timezone.utc).isoformat(),'results':results,'failed':[r['script'] for r in results if r['exit_code']!=0]}
(root/('update_'+group+'_status.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if report['failed']:sys.exit(1)


