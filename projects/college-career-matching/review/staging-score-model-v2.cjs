'use strict';
function stagingScoreModel(overlay, unitid, createView, describeRecord) {
 if(typeof createView!=='function'||typeof describeRecord!=='function') throw Error('Missing staging adapters');
 return describeRecord(String(unitid),createView(overlay));
}
module.exports={stagingScoreModel};
