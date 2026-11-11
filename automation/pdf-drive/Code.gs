/** Pelota Cubana Stats: PDF diarios sin IA. Ejecutar instalar() una vez. */
const PCU = Object.freeze({
  root: '1TrPWqq_ISBpyI0i1lcpBTmjhRuaGy-D9',
  site: 'https://pelotacubanastats.com', zone: 'America/New_York',
  revision: 'cuba-multihits-2026-11-11', maxPdf: 2, budgetMs: 300000
});
function instalar() {
  const root = DriveApp.getFolderById(PCU.root);
  if (root.isTrashed()) throw Error('La carpeta de PDF está en la papelera.');
  if (!ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction() === 'sincronizarPDF'))
    ScriptApp.newTrigger('sincronizarPDF').timeBased().everyMinutes(15).create();
  PropertiesService.getScriptProperties().setProperty('PCU_ACTIVO', '1');
  console.log('Instalado: revisión cada 15 minutos. Carpeta: ' + root.getName());
  sincronizarPDF();
}
function pausar() {
  PropertiesService.getScriptProperties().setProperty('PCU_ACTIVO', '0');
  console.log('Subidas pausadas. No se modifican los archivos existentes.');
}
function estado() {
  const p = PropertiesService.getScriptProperties();
  console.log(JSON.stringify({activo:p.getProperty('PCU_ACTIVO'),ultimo:p.getProperty('PCU_ESTADO')},null,2));
}
function normalizarContenido(value) {
  if (Array.isArray(value)) return value.map(normalizarContenido);
  if (!value || typeof value !== 'object') return value;
  const out = {};
  Object.keys(value).sort().forEach(k => {
    if (!['updatedAt','checkedAt','generatedAt','importedAt','receivedAt','sourceCuts'].includes(k))
      out[k] = normalizarContenido(value[k]);
  });
  return out;
}
function hashTexto(s) { return hashBytes(Utilities.newBlob(s).getBytes()); }
function hashBytes(b) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,b).map(n=>('0'+((n+256)%256).toString(16)).slice(-2)).join('');
}
function fechaMas(d,n) { return new Date(Date.parse(d+'T12:00:00Z')+n*86400000).toISOString().slice(0,10); }
function reloj() {
  const now=new Date();return {date:Utilities.formatDate(now,PCU.zone,'yyyy-MM-dd'),minute:Number(Utilities.formatDate(now,PCU.zone,'H'))*60+Number(Utilities.formatDate(now,PCU.zone,'m'))};
}
function horaMinutos(s) {
  const m=String(s||'').match(/^(\d{1,2}):(\d{2})(?:\s*([AP])\.?M\.?)?$/i);
  if(!m)return 12*60;
  let h=Number(m[1]),min=Number(m[2]);if(m[3])h=h%12+(m[3].toUpperCase()==='P'?12:0);
  return h<24&&min<60?h*60+min:12*60;
}
function noCelebrado(g) {return ['sealed','not-played','rescheduled','postponed','cancelled'].includes(g.status);}
function jornadaIniciada(gs,day,clock) {
  return day<clock.date||gs.some(g=>g.score||g.finished)||day===clock.date&&clock.minute>=Math.min.apply(null,gs.map(g=>horaMinutos(g.time)));
}
function tabla(t,fields) {
  if(!t||!fields.every(c=>t.columns.includes(c)))return null;
  const rows=t.rows.filter(r=>!/^total/i.test(r[0]));
  if(!rows.length)return null;
  const out=rows.map(r=>Object.fromEntries(fields.map(c=>[c,r[t.columns.indexOf(c)]])));
  if(out.some(r=>fields.some(c=>!(c==='INN'?/^\d+(?:\.[012])?$/:/^\d+$/).test(String(r[c])))))return null;
  return out.map(r=>Object.fromEntries(fields.map(c=>[c,Number(r[c])])));
}
function boxValido(g,report) {
  if(!Array.isArray(g.score)||g.score.length!==2||g.score.some(n=>!Number.isInteger(n)||n<0)||g.score[0]===g.score[1])return false;
  const ts=report.structured||[],teams=[g.away,g.home],lines=[];
  for(let i=0;i<2;i++) {
    const b=tabla(ts.find(t=>t.group==='Bateo'&&t.label===teams[i]),['VB','C','H','2B','3B','HR','CI']);
    const p=tabla(ts.find(t=>t.group==='Pitcheo'&&t.label===teams[i]),['INN','H','C','CL','SO','BB']);
    if(!b||!p||b.some(r=>r.H>r.VB||r['2B']+r['3B']+r.HR>r.H)||p.some(r=>r.CL>r.C))return false;
    if(b.reduce((s,r)=>s+r.C,0)!==g.score[i]||p.reduce((s,r)=>s+r.C,0)!==g.score[1-i])return false;
    lines.push({b,p});
  }
  return lines.every((r,i)=>r.p.reduce((s,x)=>s+x.H,0)===lines[1-i].b.reduce((s,x)=>s+x.H,0));
}
function comprobarParte(daily,gs,day) {
  const dates=gs.filter(g=>g.date<day&&!noCelebrado(g)).map(g=>g.date).sort();
  const prior=dates[dates.length-1];if(!prior)throw Error('Sin jornada previa verificable.');
  const previous=gs.filter(g=>g.date===prior&&!noCelebrado(g));
  if(previous.some(g=>!g.score||!g.reportId))throw Error('Faltan resultados o boxscores del '+prior);
  if(!(daily.days||[]).includes(prior))throw Error('Falta el parte del '+prior);
  for(const g of previous)for(const team of [g.away,g.home]) {
    if(!(daily.pitchChecks||[]).some(p=>p.gameNumber===g.number&&p.date===prior&&p.team===team&&p.boxscore))throw Error('Falta pitcheo comprobado del juego '+g.number);
    if(!(daily.pitches||[]).some(p=>p.gameNumber===g.number&&p.date===prior&&p.team===team))throw Error('Falta el parte de lanzamientos del juego '+g.number);
  }
  return {prior,previous};
}
function comprobarModelo(m,g,prior) {
  if(m.game.number!==g.number||m.game.date!==g.date||m.game.away!==g.away||m.game.home!==g.home||!m.sections?.length)throw Error('Identidad incorrecta de las notas');
  if(m.situations?.cutoff!==g.date||m.situations?.leagueLeaders?.version<2||!m.situations?.leagueLeaders?.players?.some(x=>x.metric==='multiHits'))throw Error('Falta el corte previo o multihits');
  if(m.anniversaries?.date!==g.date||!['events','birthdays','deaths'].every(k=>Array.isArray(m.anniversaries[k])))throw Error('Falta el calendario cubano');
  if(!m.sourceCuts?.estadisticas||!m.sourceCuts?.jornada||m.sourceCuts.jornada.slice(0,10)<prior)throw Error('El parte no está incorporado en las notas');
}
let limiteEjecucion = 0;
function solicitud(url,options) {
  const opts=Object.assign({muteHttpExceptions:true,timeoutSeconds:60},options||{});
  if(limiteEjecucion) {
    const remaining=Math.floor((limiteEjecucion-Date.now())/1000)-10;
    if(remaining<10)throw Error('Continuará en la próxima ejecución');
    opts.timeoutSeconds=Math.min(opts.timeoutSeconds,remaining);
  }
  const r=UrlFetchApp.fetch(url,opts);
  if(r.getResponseCode()<200||r.getResponseCode()>=300)throw Error('HTTP '+r.getResponseCode()+' en '+url.split('?')[0]);
  return r;
}
function jsonSitio(path) {return JSON.parse(solicitud(PCU.site+path).getContentText());}
function uno(iterator,label) {
  if(!iterator.hasNext())return null;const found=iterator.next();
  if(iterator.hasNext())throw Error('Hay duplicados de '+label+'; no se elige uno al azar.');return found;
}
function carpetaFecha(day,create) {
  const root=DriveApp.getFolderById(PCU.root);
  const folder=uno(root.getFoldersByName(day),'carpeta '+day);
  return folder||(create?root.createFolder(day):null);
}
function metadataDrive(id) {
  return JSON.parse(solicitud('https://www.googleapis.com/drive/v3/files/'+encodeURIComponent(id)+'?fields=id,size,parents,mimeType,sha256Checksum,trashed',{
    headers:{Authorization:'Bearer '+ScriptApp.getOAuthToken()},followRedirects:false
  }).getContentText());
}
function guardarPDF(folder,name,blob,old,sha) {
  let file=uno(folder.getFilesByName(name),name);
  // A persisted ID cannot escape the selected date folder.
  if(old?.id&&(!file||file.getId()!==old.id))throw Error('El PDF cambió de identidad o carpeta: '+name);
  if(file) {
    const meta=metadataDrive(file.getId());
    if(!meta.parents?.includes(folder.getId())||meta.mimeType!=='application/pdf'||meta.trashed)throw Error('Destino no válido');
    if(meta.sha256Checksum!==sha)solicitud('https://www.googleapis.com/upload/drive/v3/files/'+encodeURIComponent(file.getId())+'?uploadType=media',{
      method:'patch',contentType:'application/pdf',payload:blob.getBytes(),headers:{Authorization:'Bearer '+ScriptApp.getOAuthToken()},followRedirects:false
    });
  } else file=folder.createFile(blob.setName(name).setContentType('application/pdf'));
  const meta=metadataDrive(file.getId()),bytes=blob.getBytes().length;
  if(Number(meta.size)!==bytes||meta.sha256Checksum!==sha||!meta.parents?.includes(folder.getId()))throw Error('La verificación de Drive no coincide');
  return {id:file.getId(),bytes,sha256:sha};
}
function sincronizarPDF() {
  const props=PropertiesService.getScriptProperties();if(props.getProperty('PCU_ACTIVO')!=='1')return;
  const lock=LockService.getScriptLock();if(!lock.tryLock(1000))return;
  const started=Date.now(),clock=reloj(),result={at:new Date().toISOString(),updated:[],pending:[],complete:[]};let count=0;
  limiteEjecucion=started+PCU.budgetMs;
  try {
    const feed=jsonSitio('/api/serie65'),daily=jsonSitio('/api/serie65/daily'),gs=daily.games||feed.games;
    for(const day of [clock.date,fechaMas(clock.date,1)]) {
      const selected=gs.filter(g=>g.date===day&&!noCelebrado(g));
      if(!selected.length||jornadaIniciada(selected,day,clock))continue;
      let gate;
      try {
        gate=comprobarParte(daily,gs,day);
        for(const g of gate.previous) {
          if(Date.now()-started>PCU.budgetMs)throw Error('Continuará en la próxima ejecución');
          const report=jsonSitio('/api/beisbol-cubano?file='+encodeURIComponent(g.reportId));
          if(!boxValido(g,report))throw Error('Boxscore sin reconciliar: '+g.number);
        }
      } catch(e) {result.pending.push(day+': '+e.message);continue;}
      const jobs=selected.map(g=>({g,key:'PCU_'+day+'_'+g.number}));
      // Rotate checks across the whole slate; one unchanged early game cannot starve later ones.
      const cursor=Number(props.getProperty('CURSOR_'+day)||0)%jobs.length;
      let complete=true;
      for(let step=0;step<jobs.length;step++) {
        const index=(cursor+step)%jobs.length,{g,key}=jobs[index];
        if(count>=PCU.maxPdf||Date.now()-started>PCU.budgetMs-90000){complete=false;break;}
        props.setProperty('CURSOR_'+day,String((index+1)%jobs.length));
        try {
          const m=jsonSitio('/api/game-notes?game='+g.number);comprobarModelo(m,g,gate.prior);
          const fingerprint=hashTexto(PCU.revision+JSON.stringify(normalizarContenido(m)));
          const old=JSON.parse(props.getProperty(key)||'null');
          if(old?.fingerprint===fingerprint)continue;
          if(Date.now()-started>PCU.budgetMs-150000)throw Error('Continuará en la próxima ejecución');
          const response=solicitud(PCU.site+'/api/game-notes?game='+g.number+'&format=pdf',{timeoutSeconds:120});
          const blob=response.getBlob(),bytes=blob.getBytes();
          if(bytes.length<1000||String.fromCharCode.apply(null,bytes.slice(0,5))!=='%PDF-'||!Utilities.newBlob(bytes.slice(-1024)).getDataAsString().includes('%%EOF'))throw Error('PDF incompleto');
          if(jornadaIniciada(selected,day,reloj()))throw Error('La jornada ya comenzó; se conservan las previas');
          const samePair=selected.filter(x=>x.away===g.away&&x.home===g.home).length>1;
          const name='Notas_'+g.away+'_'+g.home+'_'+day+(samePair?'_Juego_'+g.number:'')+'.pdf';
          const folder=carpetaFecha(day,true),sha=hashBytes(bytes);
          const saved=guardarPDF(folder,name,blob,old,sha);
          props.setProperty(key,JSON.stringify(Object.assign(saved,{fingerprint,game:g.number,date:day,sourceCuts:m.sourceCuts})));
          result.updated.push(g.number);count++;
        } catch(e) {complete=false;result.pending.push('Juego '+g.number+': '+e.message);}
      }
      if(complete&&jobs.every(j=>props.getProperty(j.key)))result.complete.push(day);
    }
    // Operational metadata stays in this private script, never in the shared PDF folder.
    props.setProperty('PCU_ESTADO',JSON.stringify(result));console.log(JSON.stringify(result));
    // Keep ample space below the Apps Script property storage quota.
    const cutoff=fechaMas(clock.date,-90);
    Object.keys(props.getProperties()).filter(k=>/^PCU_\d{4}-\d{2}-\d{2}_/.test(k)&&k.slice(4,14)<cutoff).forEach(k=>props.deleteProperty(k));
  } catch(e) {
    result.pending.push(e.message);
    props.setProperty('PCU_ESTADO',JSON.stringify(result));
    throw e;
  } finally {limiteEjecucion=0;lock.releaseLock();}
}
