import {parseWorkspaceJSON} from './import.mjs';
const result=parseWorkspaceJSON('{"version":1,"requests":[],"events":[]}');
if(result.version!==1)throw Error('Invalid workspace');
console.log('FT09 basic check passed');
