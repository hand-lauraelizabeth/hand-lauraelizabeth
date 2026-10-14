export function locationFor(element) {
 const tag=element?.tagName?.toLowerCase()||'document';
 const id=element?.id ? '#'+element.id.slice(0,80) : '';
 return tag+id;
}
