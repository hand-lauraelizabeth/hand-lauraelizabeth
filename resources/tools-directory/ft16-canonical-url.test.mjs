/** Public, synthetic-only URL contract for FT-16 tool destinations. */
import assert from 'node:assert/strict';
import { TOOLS } from './catalog.mjs';
import { validateCatalog, approvedLiveURL } from './directory.mjs';

const good = {
  id:'synthetic-tool', title:'Synthetic resource', category:'Research',
  description:'A local test fixture, not a published resource', status:'live',
  url:'https://www.lauraelizabethhand.com/resources/example/'
};
const ambiguous = [
  ' https://www.lauraelizabethhand.com/resources/example/',
  'HTTPS://www.lauraelizabethhand.com/resources/example/',
  'https://WWW.lauraelizabethhand.com/resources/example/',
  'https://www.lauraelizabethhand.com/resources/./example/',
  'https://www.lauraelizabethhand.com/resources/dir/../example/',
  'https://www.lauraelizabethhand.com/resources//example/',
  'https://www.lauraelizabethhand.com/resources/%2fexample/',
  'https://www.lauraelizabethhand.com/resources/%65xample/',
  'https:\\\\www.lauraelizabethhand.com/resources/example/',
  'https://www.lauraelizabethhand.com/resources/%252e%252e/example/',
  'https://www.lauraelizabethhand.com:443/resources/example/',
  'https://www.lauraelizabethhand.com/resources/example/\\n'
];
let checks=0;
for(const url of ambiguous){
  assert.throws(()=>validateCatalog([{...good,url}]),'reject ambiguous URL '+JSON.stringify(url));
  assert.equal(approvedLiveURL({...good,url}),false,'render guard rejects ambiguous URL '+JSON.stringify(url));
  checks+=2;
}
for(const url of [
  good.url,
  'https://www.lauraelizabethhand.com/resources/research-writing-tools/text-lens/',
  'https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/prompt-lab/'
]){
  assert.equal(validateCatalog([{...good,url}]),true,'accept canonical resource '+url);
  assert.equal(approvedLiveURL({...good,url}),true,'render guard accepts canonical URL '+url);
  checks+=2;
}
assert.equal(validateCatalog(TOOLS),true,'preserve actual public catalog');checks++;
assert.throws(()=>validateCatalog([{...good,status:'preview'}]),'preview URL must not be linked');checks++;
const {url: _url, ...unlinked}=good;
assert.equal(validateCatalog([{...unlinked,status:'preview'}]),true,'unlinked preview remains discoverable');checks++;
assert.throws(()=>validateCatalog([{...good,status:'development'}]),'unreleased resource must not link');checks++;
for(const bad of [
 'javascript:alert(1)',
 'https://outside.invalid/resources/example/',
 'https://user@www.lauraelizabethhand.com/resources/example/',
 'https://www.lauraelizabethhand.com/resources/example/?token=synthetic',
 'https://www.lauraelizabethhand.com/resources/example/#fragment',
 'https://www.lauraelizabethhand.com/resources/../admin/'
]){
 assert.equal(approvedLiveURL({...good,url:bad}),false,'unsafe destination blocked at render: '+bad);checks++;
}
assert.equal(approvedLiveURL({...good,status:'preview'}),false,'preview cannot link');checks++;
assert.equal(approvedLiveURL({...good,url:undefined}),false,'missing destination cannot link');checks++;
console.log('FT-16 canonical URL contract '+checks+'/'+checks+' PASS');
