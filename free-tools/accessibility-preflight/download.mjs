export function saveLocal(name, mime, content) {
 const url=URL.createObjectURL(new Blob([content],{type:mime}));
 const link=document.createElement('a');
 link.href=url;link.download=name;document.body.append(link);link.click();link.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
