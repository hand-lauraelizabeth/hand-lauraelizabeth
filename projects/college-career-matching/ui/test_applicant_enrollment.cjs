const M=require('./applicant-signals.js');
const a={enrollment:{undergraduate:2500,total:3100}};
if (!M.sizeMatch(a,'undergraduate',2000,3000).include) throw Error('Undergraduate threshold');
if (M.sizeMatch(a,'total',2000,3000).include) throw Error('Total threshold');
if (!M.sizeMatch({},'total',0,4000).unknown) throw Error('Unknown enrollment');
if (!M.sizeMatch({enrollment:{undergraduate:0}},'undergraduate',0,0).include) throw Error('Zero enrollment');
