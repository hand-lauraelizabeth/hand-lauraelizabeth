import {TOOLS,STATUS_LABELS} from './catalog.mjs';
import {filterTools} from './directory.mjs';
const root=document.getElementById('ft15-directory');
const query=root.querySelector('#tool-query'),category=root.querySelector('#tool-category'),status=root.querySelector('#tool-status');
const cards=root.querySelector('#tool-results'),count=root.querySelector('#tool-count');
for(const name of [...new Set(TOOLS.map(t=>t.category))].sort()){
 const opt=document.createElement('option');opt.value=name;opt.textContent=name;category.append(opt);
}
function element(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function render(){
 const visible=filterTools(TOOLS,{query:query.value,category:category.value,status:status.value});
 const fragment=document.createDocumentFragment();
 for(const tool of visible){
  const article=element('article','ft15-card');
  const heading=element('h3',null,tool.title),badge=element('span','ft15-badge',STATUS_LABELS[tool.status]);
  badge.setAttribute('data-status',tool.status);
  article.append(badge,heading,element('p',null,tool.description));
  if(tool.url){const a=element('a','ft15-link','Open '+tool.title);a.href=tool.url;article.append(a)}
  else article.append(element('p','ft15-unavailable','Not yet available'));
  fragment.append(article);
 }
 cards.replaceChildren(fragment);
 count.textContent=visible.length+' of '+TOOLS.length+' resources shown';
 if(!visible.length)cards.append(element('p','ft15-empty','No resources match these filters. Try a different search or clear the filters.'));
}
for(const input of [query,category,status])input.addEventListener(input===query?'input':'change',render);
root.querySelector('#tool-clear').addEventListener('click',()=>{query.value='';category.value='all';status.value='all';render();query.focus()});
render();
