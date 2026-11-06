#!/usr/bin/env python3
"""Construye metadatos de actualización desde estados y series locales."""
import csv, json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATUS_LABELS={
 'igae_imai_update_status.json':('IGAE e IMAI construcción','INEGI'),
 'ifb_residencial_update_status.json':('IFB construcción residencial','INEGI'),
 'icc_inpp_update_status.json':('ICC e INPP construcción','INEGI'),
 'enoe_update_status.json':('Empleo en construcción','INEGI ENOE'),
 'imss_datamx_update_status.json':('Puestos IMSS construcción','IMSS / DataMX'),
 'imss_update_status.json':('Indicadores IMSS','IMSS'),
 'shf_update_status.json':('Índice SHF de precios de vivienda','SHF'),
 'pib_vab_update_status.json':('PIB y VAB de construcción','INEGI'),
 'pvb_update_status.json':('Avance del Programa de Vivienda para el Bienestar','Sedatu / Presidencia'),
 'conditions_update_status.json':('Condiciones habitacionales','INEGI / SNIIV'),
 'enec_indices_update_status.json':('Índices laborales ENEC','INEGI'),
 'enec_produccion_update_status.json':('Producción ENEC','INEGI'),
 'ruv_update_status.json':('Flujo de vivienda RUV','RUV / SNIIV'),
 'ruv_produccion_update_status.json':('Producción de vivienda RUV','RUV / SNIIV'),
 'sniiv_kpis_update_status.json':('Indicadores SNIIV','Sedatu'),
 'csvm_update_status.json':('PIB de vivienda','INEGI · Cuenta Satélite de Vivienda'),
}
TIME_KEYS=('checked_at_utc','fecha_consulta_utc','fecha_actualizacion_utc','updated_at_utc','generated_at','run_at_utc','fecha_utc')
PERIOD_KEYS=('ultimo_periodo','ultimo','last_period','latest_period','last_quarter','last_month','anio','year')
def walk(obj):
 if isinstance(obj,dict):
  for k,v in obj.items():
   if k in TIME_KEYS and isinstance(v,str): yield ('time',v)
   if k in PERIOD_KEYS and isinstance(v,(str,int)): yield ('period',str(v))
   yield from walk(v)
 elif isinstance(obj,list):
  for v in obj: yield from walk(v)
def period_key(v):
 s=str(v).strip()
 m=re.fullmatch(r'(20\d{2})-(\d{2})-(\d{2})',s)
 if m:return (int(m[1]),int(m[2]),int(m[3]),4)
 m=re.fullmatch(r'(20\d{2})-(\d{2})',s)
 if m:return (int(m[1]),int(m[2]),0,3)
 m=re.fullmatch(r'(20\d{2})-T([1-4])',s)
 if m:return (int(m[1]),int(m[2])*3,0,2)
 m=re.fullmatch(r'(20\d{2})',s)
 if m:return (int(m[1]),0,0,1)
 return None
def main():
 sources=[]; verifications=[]; periods=[]
 for fn,(label,provider) in STATUS_LABELS.items():
  path=ROOT/fn
  if not path.exists(): continue
  try: data=json.loads(path.read_text(encoding='utf-8'))
  except Exception: continue
  vals=list(walk(data)); times=[v for k,v in vals if k=='time']; ps=[v for k,v in vals if k=='period' and period_key(v)]
  if times: verifications.extend(times)
  latest=max(ps,key=lambda x:period_key(x)) if ps else None
  # Estados heterogéneos: no declarar éxito solo por exit code del grupo.
  states=[]; flags=[]
  for key,value in vals:
   if key=='period': continue
  def collect_states(obj):
   if isinstance(obj,dict):
    for k,v in obj.items():
     if k in ('status','estado','resultado') and isinstance(v,(str,bool)): states.append(str(v).lower())
     if k=='updated' and isinstance(v,bool): flags.append(v)
     collect_states(v)
   elif isinstance(obj,list):
    for v in obj: collect_states(v)
  collect_states(data)
  if any(x in ('actualizado','ok','success') for x in states) or True in flags: status='actualizado / verificado'
  elif any('sin_nuevo' in x or 'sin_cambios' in x or 'sin_novedades' in x for x in states): status='consultado sin novedades'
  elif any('conservado' in x or 'pendiente' in x for x in states): status='conservado / pendiente'
  else: status='revisar estado'
  sources.append({'label':label,'provider':provider,'published_latest_period':latest,'status':status,'status_file':fn})
 # Periodo más reciente se calcula a partir de series canónicas y de estados.
 candidates=[]
 csv_period_files={
  'csvm_pib_vivienda_anual.csv':['anio'], 'enoe_construccion_trimestral.csv':['periodo','period'],
  'shf_indice_trimestral.csv':['periodo','period'], 'igae_construccion_mensual.csv':['periodo','period'],
  'ifb_residencial_mensual.csv':['periodo','period'], 'icc_incevis_base2025_mensual.csv':['periodo','period'],
  'inpp_construccion_edificacion_base2025_mensual.csv':['periodo','period'], 'imss_construccion_mensual.csv':['periodo','period'],
  'pvb_avance.csv':['periodo','period']}
 for fn,keys in csv_period_files.items():
  path=ROOT/fn
  if not path.exists():continue
  try:
   with path.open(encoding='utf-8-sig',newline='') as f:
    for row in csv.DictReader(f):
     for key in keys:
      val=row.get(key)
      if val and period_key(val):candidates.append(val)
  except Exception: pass
 candidates += [s['published_latest_period'] for s in sources if s.get('published_latest_period')]
 latest=max(candidates,key=lambda x:period_key(x)) if candidates else None
 latest_verification=max(verifications) if verifications else None
 payload={'generated_at':datetime.now(timezone.utc).isoformat(),'latest_data_period':latest,'last_verification':latest_verification,'sources':sources,'audit_note':'La fecha de verificación procede de los archivos de estado disponibles; cada fuente conserva su propio periodo publicado.'}
 tmp=ROOT/'updates.js.tmp'; tmp.write_text('window.DashboardUpdates='+json.dumps(payload,ensure_ascii=False,indent=2)+';\n',encoding='utf-8'); tmp.replace(ROOT/'updates.js')
 print(json.dumps({'latest_data_period':latest,'last_verification':latest_verification,'sources':len(sources)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
