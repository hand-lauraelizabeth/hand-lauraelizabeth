(function(){
"use strict";

var URLS={
 pdf:"https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.min.js",
 pdfWorker:"https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js",
 docxRead:"https://unpkg.com/mammoth@1.13.0/mammoth.browser.min.js",
 docxWrite:"https://unpkg.com/docx@9.14.0/dist/index.iife.js",
 pdfWrite:"https://unpkg.com/jspdf@2.5.2/dist/jspdf.umd.min.js"
};
var libraries={};
function make(d,tag,cls,text){var e=d.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function label(d,txt,forId){var e=make(d,"label","",txt);if(forId)e.htmlFor=forId;return e;}
function install(){
 try{
  var d=document,w=window;
  if(!d||!w||!d.getElementById("candidate")||!d.getElementById("resume-workbench")||d.getElementById("leh-doc-editor"))return;
  var source=null,rows=[],originalImportedText="",baseName="resume-revision";
  var css=make(d,"style");css.textContent=".leh-upload{border:2px dashed #a6c4b3;border-radius:12px;background:#f3f8f4;padding:13px;margin:12px 0}.leh-upload.is-over{background:#e2f1e8;border-color:#245b45}.leh-upload label{font-size:14px;font-weight:750;display:block;margin-bottom:5px}.leh-upload input{max-width:100%;font-size:14px}.leh-upload .leh-small,.leh-revision .leh-small{font-size:13px;color:#52665a;margin:5px 0}.leh-revision{padding:20px!important;border:2px solid #c0d5c7!important}.leh-revision h2{font-size:clamp(23px,3vw,29px)!important;margin-bottom:7px!important}.leh-revision .leh-flex{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:12px 0}.leh-revision button{border:1px solid #245c49;border-radius:8px;background:#245c49;color:white;padding:10px 13px;min-height:44px;font-weight:700;font-size:14px;cursor:pointer}.leh-revision button.alt{background:#fff;color:#245c49}.leh-revision button:disabled{opacity:.5;cursor:default}.leh-revision button:focus-visible,.leh-upload input:focus-visible{outline:3px solid #8bad9d;outline-offset:2px}.leh-row{border:1px solid #d4dfd7;border-radius:10px;background:#fcfefd;margin:11px 0;padding:12px}.leh-row .leh-top{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:7px}.leh-row .leh-id{font-size:12px;font-weight:800;color:#1d5741;background:#e5f0e7;border-radius:999px;padding:3px 9px}.leh-row textarea{width:100%;min-height:62px;line-height:1.45;padding:9px;border-radius:7px;border:1px solid #879c90;font-family:inherit;font-size:14px;resize:vertical;color:#1a3226;background:white}.leh-row select{min-height:37px;max-width:160px;background:white;color:#1a3226;border:1px solid #aebeb4;border-radius:6px;padding:5px}.leh-row details{padding:7px 9px;margin:8px 0 0;border:1px solid #d9e4dc;border-radius:7px;background:#f5f8f5}.leh-row details summary{font-size:13px!important;padding:0!important;color:#244b39!important;font-weight:700!important;cursor:pointer}.leh-row .leh-quote{font-size:13px;color:#345141;white-space:pre-wrap;overflow-wrap:anywhere}.leh-revision .leh-alert{background:#fff7ec;border-left:4px solid #9d6d23;padding:10px 12px;margin:10px 0;font-size:13px}.leh-revision .leh-ok{background:#ebf4ec;border-left:4px solid #356a4e;padding:10px 12px;margin:10px 0;font-size:13px}.leh-revision .leh-scroll{max-height:700px;overflow-y:auto;padding-right:5px}.leh-revision .leh-preview{white-space:pre-wrap;border:1px solid #d2ddd3;padding:12px;border-radius:8px;max-height:290px;overflow:auto;background:#fff;font-size:13px}.leh-revision .leh-verify{font-size:12px;color:#9b5a18;font-weight:650}.leh-revision input[type=checkbox]{accent-color:#225f48;min-height:18px;min-width:18px}@media(max-width:600px){.leh-revision{padding:12px!important}.leh-revision .leh-flex button{width:100%}}";d.head.appendChild(css);
  function announce(s){notice.textContent=s;}
  function appendParagraph(parent,txt,cls){var p=make(d,"p",cls||"",txt);parent.appendChild(p);return p;}
  function library(key,predicate){
   if(predicate())return Promise.resolve();
   if(libraries[key])return libraries[key];
   libraries[key]=new Promise(function(resolve,reject){
    var tag=make(d,"script");tag.src=URLS[key];tag.async=true;
    var timer=setTimeout(function(){tag.remove();reject(new Error("Document library timed out. Check browser security settings or try again."));},20000);
    tag.onload=function(){clearTimeout(timer);if(predicate())resolve();else reject(new Error("Document library did not initialize."));};
    tag.onerror=function(){clearTimeout(timer);reject(new Error("Could not load the document library. Check content blockers or network access."));};
    d.head.appendChild(tag);
   }).catch(function(e){delete libraries[key];throw e;});
   return libraries[key];
  }
  function sectionsFromText(text,kind,page){
   var lines=String(text||"").replace(/\r/g,"\n").split(/\n+/).map(function(x){return x.replace(/[\u00a0\t ]+/g," ").trim();}).filter(function(x){return x.length>1;});
   return lines.map(function(x,i){return {text:x,location:kind+(page?" — page "+page:" — paragraph "+(i+1))};});
  }
  async function pdfExtract(buffer){
   await library("pdf",function(){return !!w.pdfjsLib;});
   w.pdfjsLib.GlobalWorkerOptions.workerSrc=URLS.pdfWorker;
   var task=w.pdfjsLib.getDocument({data:new Uint8Array(buffer)});
   var pdf=await task.promise,units=[],texts=[],limit=Math.min(pdf.numPages,40);
   for(var i=1;i<=limit;i++){
    var p=await pdf.getPage(i),content=await p.getTextContent(),lines=[],current="",lastY=null;
    content.items.forEach(function(it){
      var v=String(it.str||"").trim();if(!v)return;
      var y=it.transform&&it.transform.length>5?Number(it.transform[5]):null;
      if(current&&lastY!==null&&y!==null&&Math.abs(y-lastY)>3){lines.push(current.trim());current="";}
      current+=(current&&!/\s$/.test(current)?" ":"")+v;
      if(it.hasEOL){lines.push(current.trim());current="";}lastY=y;
    });
    if(current.trim())lines.push(current.trim());
    var pageText=lines.join("\n");if(pageText)texts.push(pageText);
    units.push.apply(units,sectionsFromText(pageText,"PDF",i));
   }
   if(!units.length)throw Error("This PDF has no selectable text. Scanned/image-only PDFs need OCR before importing.");
   return {text:texts.join("\n"),units:units,note:pdf.numPages>limit?"Only the first "+limit+" pages were imported.":""};
  }
  async function docxExtract(buffer){
   await library("docxRead",function(){return !!w.mammoth;});
   var result=await w.mammoth.extractRawText({arrayBuffer:buffer});
   var text=String(result.value||"").trim();
   if(!text)throw Error("No readable text found in the DOCX. Content inside images or drawing objects may need manual extraction.");
   var notes=(result.messages||[]).filter(function(m){return m.type==="warning";}).slice(0,2).map(function(m){return m.message;}).join(" ");
   return {text:text,units:sectionsFromText(text,"DOCX"),note:notes};
  }
  function normNum(x){return (String(x).match(/\b\d[\d,.]*%?\b/g)||[]).join("|");}
  function safeRevision(s){
   return String(s||"").replace(/^\s*[-•*]\s*/,"").replace(/^\s*I (managed|led|coordinated|developed|created|designed|implemented|analyzed|supervised|directed|built|trained|supported)\b/i,function(_,verb){return verb[0].toUpperCase()+verb.slice(1);}).replace(/^\s*(?:was )?responsible for (managing|leading|coordinating|developing|creating|designing|implementing|analyzing|supervising)\b/i,function(_,verb){return verb.replace(/ing$/,"ed").replace(/^lead?ed$/,"Led").replace(/^./,function(x){return x.toUpperCase();});}).replace(/^\s*Successfully\s+/i,"").trim();
  }
  function sourceLineUnits(){var t=d.getElementById("candidate").value.trim();return {text:t,units:sectionsFromText(t,"Entered résumé"),note:""};}
  function sourceForCurrent(){
   var current=d.getElementById("candidate").value.trim();
   if(source&&current===originalImportedText)return source;
   return sourceLineUnits();
  }
  var inputBox=make(d,"div","leh-upload");inputBox.id="leh-upload";
  inputBox.appendChild(label(d,"Import a résumé (.pdf or .docx)","leh-import-file"));
  var inp=make(d,"input");inp.id="leh-import-file";inp.type="file";inp.accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";inputBox.appendChild(inp);
  appendParagraph(inputBox,"Or drag a PDF or DOCX onto this area. Text is extracted in your browser, then added to the résumé field. 10 MB limit. No document is uploaded by this importer.","leh-small");
  var importStatus=appendParagraph(inputBox,"","leh-small");importStatus.setAttribute("role","status");importStatus.setAttribute("aria-live","polite");
  var candidate=d.getElementById("candidate");candidate.insertAdjacentElement("afterend",inputBox);
  async function importFile(f){
   if(!f)return;
   if(!/\.(pdf|docx)$/i.test(f.name)){importStatus.textContent="Choose a .pdf or .docx file.";return;}
   if(f.size>10*1024*1024){importStatus.textContent="The maximum file size is 10 MB.";return;}
   if(candidate.value.trim()&&!w.confirm("Replace the text currently in the résumé input with the imported document?"))return;
   importStatus.textContent="Reading "+f.name+" locally…";
   try{
    var buffer=await f.arrayBuffer(),data=/\.pdf$/i.test(f.name)?await pdfExtract(buffer):await docxExtract(buffer);
    if(data.text.trim().length<40)throw Error("Too little selectable text was extracted to build a reliable revision.");
    if(data.text.length>120000)throw Error("This file exceeds the 120,000-character text limit. Use a shorter résumé.");
    source=data;originalImportedText=data.text.trim();baseName=f.name.replace(/\.(docx|pdf)$/i,"").replace(/[^a-z0-9-_]+/gi,"-").slice(0,60)||"resume";
    candidate.value=data.text;candidate.dispatchEvent(new Event("input",{bubbles:true}));
    importStatus.textContent="Imported "+f.name+": "+data.units.length+" evidence excerpts. "+(data.note||"Review headings and reading order, particularly for multicolumn layouts.");
    announce("Résumé imported. Choose Build evidence-linked revision below; the existing occupation and ATS tools can also use the extracted text.");
    var parent=d.getElementById("candidate");parent.focus();
   }catch(e){importStatus.textContent="Import failed: "+(e.message||String(e));announce("The document could not be imported. You can paste plain text instead.");}
  }
  inp.addEventListener("change",function(){importFile(inp.files&&inp.files[0]);});
  inputBox.addEventListener("dragover",function(e){e.preventDefault();inputBox.classList.add("is-over");});
  inputBox.addEventListener("dragleave",function(){inputBox.classList.remove("is-over");});
  inputBox.addEventListener("drop",function(e){e.preventDefault();inputBox.classList.remove("is-over");importFile(e.dataTransfer.files[0]);});
  var sec=make(d,"section","panel leh-revision");sec.id="leh-doc-editor";sec.setAttribute("aria-labelledby","leh-doc-editor-title");
  var head=make(d,"h2","","Evidence-linked résumé editor");head.id="leh-doc-editor-title";sec.appendChild(head);
  appendParagraph(sec,"Turn your source résumé into an editable, clearly structured draft. Each proposed line points to its original PDF page, DOCX paragraph, or pasted résumé line. Reordering follows the posting only within contiguous bullet groups; employers and dates remain in their original order.","leh-small");
  var ctl=make(d,"div","leh-flex");
  var build=make(d,"button","","Build evidence-linked revision");build.type="button";ctl.appendChild(build);
  var downDoc=make(d,"button","alt","Download DOCX");downDoc.type="button";downDoc.disabled=true;ctl.appendChild(downDoc);
  var downPdf=make(d,"button","alt","Download PDF");downPdf.type="button";downPdf.disabled=true;ctl.appendChild(downPdf);
  sec.appendChild(ctl);
  var chkWrap=label(d,"","");chkWrap.style.display="inline-flex";chkWrap.style.alignItems="center";chkWrap.style.gap="8px";
  var appendix=make(d,"input");appendix.type="checkbox";appendix.checked=true;chkWrap.appendChild(appendix);chkWrap.appendChild(d.createTextNode("Include evidence appendix in downloads (uncheck for employer-facing résumé)"));sec.appendChild(chkWrap);
  var notice=appendParagraph(sec,"Import a PDF/DOCX above, or paste your résumé, then build a revision.","leh-small");notice.setAttribute("role","status");notice.setAttribute("aria-live","polite");
  var edits=make(d,"div","leh-scroll");edits.id="leh-edits";sec.appendChild(edits);
  var previewWrap=make(d,"details");var summary=make(d,"summary","","Preview complete revised résumé text");previewWrap.appendChild(summary);
  var preview=make(d,"pre","leh-preview","");previewWrap.appendChild(preview);sec.appendChild(previewWrap);
  var existing=d.getElementById("resume-workbench");existing.parentNode.insertBefore(sec,existing.nextSibling);
  var headers=/^(experience|professional\s+summary|summary|profile|objective|work\s+experience|professional\s+experience|relevant\s+experience|employment|education|skills|technical\s+skills|selected\s+projects|projects|certifications|certificates|awards|publications|volunteer\s+experience|leadership|research|languages)\s*:?$/i;
  var roleWords=/\b(?:manager|director|coordinator|specialist|analyst|associate|assistant|consultant|instructor|professor|university|college|school|corporation|organization|company)\b/i;
  function classify(u,i,hasHeaders){
   var t=u.text.trim();
   if(headers.test(t))return "heading";
   if(i===0)return "contact";
   if(!hasHeaders&&i<3&&(/@|https?:|linkedin|phone|\b\d{3}[-. )]/i.test(t)))return "contact";
   if(/^[•*-]\s+/.test(t))return "bullet";
   if(/^\d{1,2}\/(?:19|20)\d{2}/.test(t)||/\b(?:19|20)\d{2}\s*[-–—]\s*(?:present|(?:19|20)\d{2})/i.test(t))return "text";
   if(roleWords.test(t)&&t.length<95&&t.split(/\s+/).length<12)return "text";
   if(hasHeaders&&t.length>60&&/^\w/.test(t))return "bullet";
   return "text";
  }
  function keywords(posting){
   var ignore=new Set("about above across after also and because been before between both candidate candidates company could degree description demonstrated develop development education employer experience from have including into leadership management other over position preferred required responsibilities role skills strong successful support teams than that their them there these they this those through using what when where which will with work working would your years".split(" "));
   var f=new Map();(posting.toLowerCase().match(/[a-z][a-z-]{3,}/g)||[]).forEach(function(x){if(!ignore.has(x))f.set(x,(f.get(x)||0)+1);});
   return [...f].sort(function(a,b){return b[1]-a[1];}).slice(0,30).map(function(x){return x[0];});
  }
  function relevance(line,terms){var a=line.toLowerCase();return terms.reduce(function(v,t){return v+(a.indexOf(t)>=0?1:0);},0);}
  function sortedBullets(entries){
   for(var i=0;i<entries.length;){
    if(entries[i].kind!=="bullet"){i++;continue;}
    var end=i+1;while(end<entries.length&&entries[end].kind==="bullet")end++;
    var replacement=entries.slice(i,end).sort(function(a,b){return b.related-a.related||a.order-b.order;});entries.splice.apply(entries,[i,end-i].concat(replacement));i=end;
   }
   return entries;
  }
  function checkEvidence(row){
   var now=row.input.value.trim(),old=row.original;
   var a=normNum(old),b=normNum(now),differentNumbers=a!==b;
   var changed=now!==row.proposal;
   row.warning.textContent=differentNumbers?"Numbers changed from the source — verify before export.":changed?"Edited from the proposed wording — check against the source.":"Source excerpt retained; verify accuracy and context.";
   return {changed:changed,numberChanged:differentNumbers};
  }
  function selectedRows(){return rows.filter(function(r){return r.keep.checked&&r.input.value.trim();});}
  function compose(){
   var arr=selectedRows(),lines=[];
   arr.forEach(function(r){var v=r.input.value.trim();if(r.type.value==="heading")v=v.replace(/:$/,"").toUpperCase();else if(r.type.value==="bullet")v="• "+v.replace(/^\s*[•*-]\s*/,"");lines.push(v);});
   preview.textContent=lines.join("\n");
   return arr;
  }
  function lineEditor(entry,index){
   var card=make(d,"div","leh-row"),top=make(d,"div","leh-top"),id=String(entry.id);
   top.appendChild(make(d,"span","leh-id",id));
   var keepLabel=label(d,"","");var keep=make(d,"input");keep.type="checkbox";keep.checked=true;keepLabel.appendChild(keep);keepLabel.appendChild(d.createTextNode(" Include"));top.appendChild(keepLabel);
   var typ=make(d,"select");["contact","heading","text","bullet"].forEach(function(t){var o=make(d,"option","",t==="text"?"Role / text":t[0].toUpperCase()+t.slice(1));o.value=t;typ.appendChild(o);});typ.value=entry.kind;typ.setAttribute("aria-label","Line type for "+id);top.appendChild(typ);
   if(entry.related>0)top.appendChild(make(d,"span","leh-id","Posting relevance: "+entry.related+" term"+(entry.related!==1?"s":"")));
   card.appendChild(top);
   var field=make(d,"textarea");field.value=entry.proposal;field.setAttribute("aria-label","Editable résumé line from "+id);card.appendChild(field);
   var warning=appendParagraph(card,"Source excerpt retained; verify accuracy and context.","leh-verify");
   var details=make(d,"details");details.appendChild(make(d,"summary","","Read original evidence "+id+" · "+entry.location));
   details.appendChild(make(d,"p","leh-quote",entry.original));card.appendChild(details);edits.appendChild(card);
   var row={id:id,original:entry.original,location:entry.location,proposal:entry.proposal,input:field,type:typ,keep:keep,warning:warning};
   [field,typ,keep].forEach(function(el){el.addEventListener("input",function(){checkEvidence(row);compose();});el.addEventListener("change",function(){checkEvidence(row);compose();});});
   return row;
  }
  build.addEventListener("click",function(){
   var data=sourceForCurrent();
   if(!data.text||data.text.length<60){announce("Paste or import your résumé first (at least 60 characters).");return;}
   if(data.units.length>500){announce("This résumé contains more than 500 text lines. Please use a shorter version so no content is silently omitted.");return;}
   var terms=keywords((d.getElementById("job")||{}).value||"");
   var hasHeaders=data.units.some(function(x){return headers.test(x.text);});
   var entries=data.units.map(function(u,i){var kind=classify(u,i,hasHeaders),raw=u.text,clean=kind==="heading"?raw.replace(/:$/,"").toUpperCase():safeRevision(raw);return {id:"E"+String(i+1).padStart(3,"0"),order:i,kind:kind,original:raw,proposal:clean,location:u.location,related:relevance(raw,terms)};});
   sortedBullets(entries);edits.replaceChildren();rows=entries.map(lineEditor);compose();downDoc.disabled=false;downPdf.disabled=false;
   announce("Draft created from "+rows.length+" traceable source excerpts. Edit each line, change its type, or exclude it. Export with or without the evidence appendix.");
   sec.scrollIntoView({block:"start",behavior:"smooth"});
  });
  function download(blob,name){
   var u=w.URL.createObjectURL(blob),a=make(d,"a");a.href=u;a.download=name;d.body.appendChild(a);a.click();a.remove();setTimeout(function(){w.URL.revokeObjectURL(u);},30000);
  }
  function evidenceStatus(r){var x=checkEvidence(r);return x.numberChanged?"Numbers modified — manually verify":x.changed?"Wording edited — manually verify":"Original source available — check context";}
  async function exportDocx(){
   var arr=compose();if(!arr.length)throw Error("Add at least one included résumé line.");
   await library("docxWrite",function(){return !!(w.docx&&w.docx.Packer&&w.docx.Document);});
   var D=w.docx,p=[];
   function para(text,kind){
    var options={text:text,spacing:{after:kind==="heading"?130:75},keepWithNext:kind==="heading"};
    if(kind==="heading")options.heading=D.HeadingLevel.HEADING_1;
    if(kind==="bullet")options.bullet={level:0};
    return new D.Paragraph(options);
   }
   arr.forEach(function(r){p.push(para(r.input.value.trim().replace(/^\s*[•*-]\s*/,""),r.type.value));});
   if(appendix.checked){
    p.push(new D.Paragraph({text:"SOURCE-TO-REVISION EVIDENCE REGISTER",pageBreakBefore:true,heading:D.HeadingLevel.HEADING_1}));
    p.push(para("Review copy only. The source excerpts below document what was extracted or entered; edits and employment claims still require human verification.","text"));
    arr.forEach(function(r){p.push(new D.Paragraph({children:[new D.TextRun({text:r.id+" · "+r.location,bold:true})],spacing:{before:170,after:65}}));p.push(para("Original: "+r.original,"text"));p.push(para("Revision: "+r.input.value.trim(),"text"));p.push(para("Review status: "+evidenceStatus(r),"text"));});
   }
   var document=new D.Document({creator:"Role Evidence Studio",title:"Evidence-linked résumé revision",description:"Applicant-edited résumé with optional original-excerpt evidence register",sections:[{properties:{},children:p}]});
   var blob=await D.Packer.toBlob(document);download(blob,baseName+"-revised"+(appendix.checked?"-evidence":"")+".docx");
  }
  async function exportPdf(){
   var arr=compose();if(!arr.length)throw Error("Add at least one included résumé line.");
   await library("pdfWrite",function(){return !!(w.jspdf&&w.jspdf.jsPDF);});
   var pdf=new w.jspdf.jsPDF({orientation:"portrait",unit:"pt",format:"letter"}),top=57,bottom=748,x=56,width=500,y=top;
   function safe(v){return String(v||"").replace(/[•]/g,"-").replace(/[–—]/g,"-").replace(/[“”]/g,'"').replace(/[‘’]/g,"'");}
   function write(text,kind){
    var font=kind==="heading"?"bold":"normal",size=kind==="heading"?12:10.5,line=kind==="heading"?16:14;
    pdf.setFont("helvetica",font);pdf.setFontSize(size);pdf.setTextColor(30,46,37);
    var prefix=kind==="bullet"?"   - ":"",lines=pdf.splitTextToSize(prefix+safe(text),width);
    if(y+lines.length*line+8>bottom){pdf.addPage();y=top;}
    pdf.text(lines,x,y);y+=line*lines.length+(kind==="heading"?10:6);
   }
   arr.forEach(function(r){write(r.input.value.trim().replace(/^\s*[•*-]\s*/,""),r.type.value);});
   if(appendix.checked){
    pdf.addPage();y=top;write("SOURCE-TO-REVISION EVIDENCE REGISTER","heading");
    write("Review copy: source excerpts and all revisions require human verification.","text");
    arr.forEach(function(r){write(r.id+" | "+r.location,"heading");write("Original: "+r.original,"text");write("Revision: "+r.input.value.trim(),"text");write("Review status: "+evidenceStatus(r),"text");});
   }
   var pages=pdf.getNumberOfPages();for(var i=1;i<=pages;i++){pdf.setPage(i);pdf.setFontSize(8);pdf.setTextColor(100,110,104);pdf.text("Role Evidence Studio | Page "+i+" of "+pages,56,773);}
   pdf.save(baseName+"-revised"+(appendix.checked?"-evidence":"")+".pdf");
  }
  async function perform(fn){downDoc.disabled=true;downPdf.disabled=true;announce("Preparing your download…");try{await fn();announce("Download generated locally from the currently selected, editable résumé lines.");}catch(e){announce("Export failed: "+(e.message||String(e))+". Try the other format or check browser content blockers.");}finally{downDoc.disabled=false;downPdf.disabled=false;}}
  downDoc.addEventListener("click",function(){perform(exportDocx);});
  downPdf.addEventListener("click",function(){perform(exportPdf);});
  }catch(err){/* The original matching, audit, and résumé builder remain operational. */}
}
install();
})();
