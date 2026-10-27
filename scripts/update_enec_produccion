#!/usr/bin/env python3
"""Actualización aislada ENEC producción; no altera CSV cuando falta validación.
IDs configurables: INEGI_ID_ENEC_PROD_EDIFICACION, INEGI_ID_ENEC_PROD_PUBLICA,
INEGI_ID_ENEC_PROD_PRIVADA. Nunca supone que los IDs de subsector
representan desagregaciones por sector contratante.
"""
import csv, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from update_inegi_series import api_series, read_csv, overlap_error, write_csv, ROOT

DEST=ROOT/'enec_actividad_historica.csv'
STATUS=ROOT/'enec_produccion_update_status.json'
SPEC={
 'edificacion_indice':'INEGI_ID_ENEC_PROD_EDIFICACION',
 'publico_indice':'INEGI_ID_ENEC_PROD_PUBLICA',
 'privado_indice':'INEGI_ID_ENEC_PROD_PRIVADA',
}

def main():
    report={'consultado_utc':datetime.now(timezone.utc).isoformat(),'estado':'sin_validar','series':{}}
    try:
        existing=read_csv(DEST)
        if not existing: raise ValueError('No existe histórico de referencia ENEC')
        series={}
        for col,env in SPEC.items():
            iid=os.getenv(env,'').strip()
            if not iid: raise ValueError(f'Falta {env}: identificar y verificar esta serie antes de activarla')
            values,meta=api_series(iid,'monthly')
            error=overlap_error(values,existing,'periodo',col)
            if error is None or error>0.03:
                raise ValueError(f'{col}: ID {iid} no coincide con el histórico; error relativo mediano={error}')
            series[col]=values
            report['series'][col]={'id':iid,'descripcion':meta['description'],'error_relativo_mediano':error,'ultimo':max(values)}
        periods=sorted(set.intersection(*(set(s) for s in series.values())))
        periods=[p for p in periods if p>='2016-01']
        if len(periods)<96 or max(periods)<existing[-1]['periodo']:
            raise ValueError('Cobertura insuficiente o periodo más antiguo que el CSV vigente')
        rows=[]
        for p in periods:
            rows.append({'periodo':p,**{col:series[col][p] for col in SPEC},
                         'unidad':existing[0].get('unidad',''), 'fuente':'INEGI - ENEC',
                         'nota':'Series validadas contra histórico; verificar metadatos por indicador'})
        write_csv(DEST,rows,['periodo',*SPEC,'unidad','fuente','nota'])
        report.update(estado='actualizado',primero=periods[0],ultimo=periods[-1],observaciones=len(rows))
        print(f'ENEC producción actualizada: {periods[0]} a {periods[-1]}')
    except Exception as exc:
        report.update(estado='conservado_sin_cambio',error=str(exc))
        print(f'ENEC producción: {exc}',file=sys.stderr)
        returncode=1
    else:returncode=0
    finally:
        STATUS.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return returncode

if __name__=='__main__':sys.exit(main())
