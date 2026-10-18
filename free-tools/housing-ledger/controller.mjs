import {buildHousingLedger} from './housing-core.mjs';
const ledger=buildHousingLedger({sources:[],events:[]});
document.getElementById('status').textContent=ledger.events.length+' events.';
