/* 元画像に対する相対矩形。画像とSVGを同じstageでズームする。 */
window.PlantBoxes = (() => {
  const ns = 'http://www.w3.org/2000/svg';
  const ranks = {unknown:'分類未確定',family:'科',subfamily:'亜科',genus:'属',section:'節',species_group:'種群',species:'種',subspecies:'亜種',variety:'変種',form:'品種',cultivar:'栽培品種',hybrid:'交雑群'};
  const el = (tag, attrs = {}) => {const e = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k,v]) => e.setAttribute(k,v)); return e;};
  const text = (tag, value) => {const e = document.createElement(tag); e.textContent = value; return e;};
  function focus(image, obj) {
    const modal = document.createElement('div'); modal.className = 'plant-modal'; modal.setAttribute('role','dialog'); modal.setAttribute('aria-modal','true'); modal.setAttribute('aria-label',obj.taxon.name);
    const section = document.createElement('section'), close = text('button','閉じる');
    const onKey = e => {if(e.key === 'Escape') dismiss();};
    const dismiss = () => {modal.remove(); document.removeEventListener('keydown',onKey);};
    close.onclick = dismiss; modal.onclick = e => {if(e.target === modal) dismiss();};
    document.addEventListener('keydown',onKey);
    section.append(close, text('h2',obj.taxon.name));
    section.append(text('p',[obj.taxon.scientific_name,ranks[obj.taxon.rank] || '分類未確定',obj.certainty==='confirmed'?'確認した分類':'未確定'].filter(Boolean).join(' / ')));
    if(obj.candidates.length) section.append(text('p','候補：'+obj.candidates.map(c=>typeof c==='string'?c:c.name).join(' / ')));
    if(obj.morphology.length) section.append(text('p','形態：'+obj.morphology.join(' / ')));
    const [x,y,w,h] = obj.bbox, iw = image.naturalWidth, ih = image.naturalHeight;
    const svg = el('svg',{viewBox:[x*iw,y*ih,w*iw,h*ih].join(' ')});
    svg.append(el('image',{href:image.src,width:iw,height:ih})); section.append(svg);
    section.append(text('p',obj.evidence.join(' / ')),text('p','同定の限界：'+obj.limitations));
    if(obj.diagnostic_comparison) section.append(text('p','識別点：'+obj.diagnostic_comparison));
    obj.sources.forEach(s => {const a = text('a',s.supports); a.href=s.url; a.target='_blank'; a.rel='noopener noreferrer'; section.append(a,document.createElement('br'));});
    modal.append(section); document.body.append(modal); close.focus();
  }
  let available;
  const availableIds = () => available || (available = fetch('plant_reviews/index.json').then(r=>r.ok?r.json():{image_ids:[]}).then(d=>new Set(d.image_ids)).catch(()=>new Set()));
  async function attach(box, stage, id) {
    if(!(await availableIds()).has(id)) return;
    const response = await fetch('plant_reviews/'+encodeURIComponent(id)+'.json');
    if(!response.ok || !box.isConnected) return;
    const record = await response.json(); if(!box.isConnected) return;
    const image = stage.querySelector('img');
    // ビルド済み元画像に切り替える。旧配信用の全天球中央cropへ枠を重ねない。
    await new Promise((resolve,reject) => {image.onload=resolve; image.onerror=reject; image.src='review_photos/'+id+'.jpg';});
    if(!box.isConnected) return;
    const iw=record.source_size[0], ih=record.source_size[1];
    if(image.naturalWidth!==iw || image.naturalHeight!==ih) throw Error('矩形の元画像寸法が一致しません');
    const svg=el('svg',{viewBox:`0 0 ${iw} ${ih}`,class:'plant-overlay','aria-hidden':'true'});
    const groups=[];
    record.objects.forEach((o,i)=>{const [x,y,w,h]=o.bbox,g=el('g');g.append(el('rect',{x:x*iw,y:y*ih,width:w*iw,height:h*ih}));const t=el('text',{x:x*iw+6,y:y*ih+24});t.textContent=i+1;g.append(t);g.addEventListener('click',e=>{e.stopPropagation();focus(image,o);});svg.append(g);groups.push(g);});
    stage.append(svg);
    const controls=document.createElement('div'); controls.className='plant-controls';
    const toggle=text('button','枠を隠す'); toggle.setAttribute('aria-pressed','true');
    toggle.onclick=()=>{svg.hidden=!svg.hidden;svg.style.display=svg.hidden?'none':'';toggle.textContent=svg.hidden?'枠を表示':'枠を隠す';toggle.setAttribute('aria-pressed',String(!svg.hidden));};
    controls.append(toggle,text('span',record.status==='complete'?'全景確認済み':'一次確認・詳細判定待ち'));
    const list=document.createElement('div'); list.className='plant-list';
    record.objects.forEach((o,i)=>{const b=document.createElement('button');b.className='plant-item';b.setAttribute('aria-pressed','false');
      const status=o.certainty==='confirmed'?'確認した分類':o.certainty==='provisional'?'暫定候補':'分類未確定';
      b.append(text('strong',`${i+1}. ${o.taxon.name}（${status}）`));
      b.append(text('small',o.evidence.join(' / ')),text('small','限界：'+o.limitations));
      if(o.candidates.length){const c=text('small','候補：'+o.candidates.map(c=>typeof c==='string'?c:c.name).join(' / '));c.className='plant-candidate';b.append(c);}
      if(o.morphology.length)b.append(text('small','形態：'+o.morphology.join(' / ')));
      b.onclick=()=>{groups.forEach((g,j)=>g.classList.toggle('selected',i===j));list.querySelectorAll('button').forEach((v,j)=>v.setAttribute('aria-pressed',String(i===j)));focus(image,o);};list.append(b);
    });
    if(!record.objects.length)list.append(text('p',record.image_notes));
    box.after(controls,list);
  }
  return {attach:(...args)=>attach(...args).catch(error=>console.error('植物の枠を表示できません',error))};
})();
