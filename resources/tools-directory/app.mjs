import {TOOLS,STATUS_LABELS} from './catalog.mjs';
import {filterTools,queryIssue,firstUnsafeQueryControl,approvedLiveURL} from './directory.mjs';
const root=document.getElementById('ft15-directory');
const query=root.querySelector('#tool-query'),category=root.querySelector('#tool-category'),status=root.querySelector('#tool-status');
const cards=root.querySelector('#tool-results'),count=root.querySelector('#tool-count');
const queryError=root.querySelector('#tool-query-error');
for(const name of [...new Set(TOOLS.map(t=>t.category))].sort()){
 const opt=document.createElement('option');opt.value=name;opt.textContent=name;category.append(opt);
}
function element(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function render(){
 // Never silently truncate or index an overlong query. Keep the exact input
 // available for correction, announce the error, and skip catalog work.
 const issue=queryIssue(query.value);
 queryError.hidden=!issue;
 if(issue){
  queryError.textContent=issue==='too-long'
   ?'Search is limited to 256 Unicode code points. Shorten your query or clear the filters.'
   :issue==='malformed-unicode'
   ?'Search contains an incomplete Unicode character. Re-enter the affected text or clear the filters.'
   :(()=>{const detail=firstUnsafeQueryControl(query.value);
     return 'Search includes invisible or control characters at Unicode code point '+detail.position+
      ' ('+detail.codePoint+'). Remove that character and try again.';})();
  query.setAttribute('aria-invalid','true');
  query.setAttribute('aria-describedby','tool-search-help tool-query-error');
  cards.replaceChildren();
  count.textContent=issue==='too-long'
   ?'Search paused until the query is shortened'
   :issue==='malformed-unicode'
   ?'Search paused until incomplete Unicode text is corrected'
   :'Search paused until invisible formatting is removed';
  return;
 }
 query.removeAttribute('aria-invalid');
 query.setAttribute('aria-describedby','tool-search-help');
 const visible=filterTools(TOOLS,{query:query.value,category:category.value,status:status.value});
 const fragment=document.createDocumentFragment();
 for(const tool of visible){
  const article=element('article','ft15-card');
  const heading=element('h3',null,tool.title),badge=element('span','ft15-badge',STATUS_LABELS[tool.status]);
  badge.setAttribute('data-status',tool.status);
  article.append(badge,heading,element('p',null,tool.description));
  // Defense in depth: even if metadata validation is bypassed, previews never become links.
  if(approvedLiveURL(tool)){const a=element('a','ft15-link','Open '+tool.title);a.href=tool.url;
   // Do not disclose the directory URL as a Referer when navigating to a live tool.
   // HTML Standard, link type noreferrer: https://html.spec.whatwg.org/dev/links.html
   a.rel='noreferrer';article.append(a)}
  else article.append(element('p','ft15-unavailable',tool.status==='live'?'Link unavailable':'Not yet available'));
  fragment.append(article);
 }
 cards.replaceChildren(fragment);
 count.textContent=visible.length+' of '+TOOLS.length+' resources shown';
 if(!visible.length)cards.append(element('p','ft15-empty','No resources match these filters. Try a different search or clear the filters.'));
}
for(const input of [query,category,status])input.addEventListener(input===query?'input':'change',render);
root.querySelector('#tool-clear').addEventListener('click',()=>{query.value='';category.value='all';status.value='all';render();query.focus()});
render();
// Enable controls only after the local catalog and event handlers are ready.
// Without scripting, the visible noscript explanation accompanies disabled controls.
root.querySelector('fieldset').disabled=false;
root.querySelector('#ft15-load-status').hidden=true;
