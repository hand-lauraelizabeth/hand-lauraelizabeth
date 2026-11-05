import {uniqueIds} from './ids.mjs';
if (!uniqueIds([{id:'A'},{id:'B'}])) throw Error('Distinct IDs must pass');
if (uniqueIds([{id:'A'},{id:'A'}])) throw Error('Duplicate IDs must fail');
