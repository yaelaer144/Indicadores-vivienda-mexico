#!/usr/bin/env python3
"""Genera un diagnóstico automático de cobertura histórica de las series objetivo."""
import csv,json,re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
TARGETS={
 'igae_construccion_mensual.csv':('2016-01','mensual'),
 'imai_construccion_mensual.csv':('2016-01','mensual'),
 'ifb_residencial_mensual.csv':('2016-01','mensual'),
 'icc_incevis_base2025_mensual.csv':('2016-01','mensual'),
 'inpp_construccion_edificacion_base2025_mensual.csv':('2016-01','mensual'),
 'enec_indices_laborales_mensual.csv':('2016-01','mensual'),
 'enec_actividad_historica.csv':('2016-01','mensual'),
 'enec_personal_tipo_variacion_mensual.csv':('2016-01','mensual'),
 'enec_vivienda_yoy.csv':('2016-01','mensual'),
 'enec_edificacion_variacion_mensual.csv':('2016-01','mensual'),
 'imss_construccion_mensual.csv':('2016-01','mensual'),
 'imss_sbc_construccion_mensual.csv':('2016-01','mensual'),
 'imss_total_mensual.csv':('2016-01','mensual'),
 'enoe_construccion_trimestral.csv':('2016-T1','trimestral'),
 'vab_construccion_subsectores_trimestral.csv':('2018-T1','trimestral'),
 'ruv_flujo_vivienda_anual.csv':('2016','anual'),
 'bridge_financing_anual.csv':('2016','anual'),
 'shf_indice_trimestral.csv':('2016-T1','trimestral'),
 'csvm_pib_vivienda_anual.csv':('2016','anual')}

def periods(path):
 if not path.exists():return []
 with path.open(encoding='utf-8-sig',newline='') as f:
  rows=list(csv.DictReader(f))
 out=[]
 for r in rows:
  for k in ('periodo','anio','year'):
   if r.get(k):out.append(str(r[k]).strip());break
 return sorted(set(out))

def main():
 items=[]
 for fn,(target,freq) in TARGETS.items():
  ps=periods(ROOT/fn); first=ps[0] if ps else None; last=ps[-1] if ps else None
  items.append({'archivo':fn,'frecuencia':freq,'objetivo_inicio':target,'primer_periodo':first,'ultimo_periodo':last,'observaciones':len(ps),'cobertura_objetivo':'completo' if first and first<=target else 'pendiente_backfill'})
 out={'generated_at':datetime.now().isoformat(timespec='seconds'),'objetivo':'Preferencia 2016; alternativa 2018 cuando la serie validada no tenga histórico anterior o cambie metodología','series':items,'pendientes':[x['archivo'] for x in items if x['cobertura_objetivo']!='completo']}
 (ROOT/'automation_coverage.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
