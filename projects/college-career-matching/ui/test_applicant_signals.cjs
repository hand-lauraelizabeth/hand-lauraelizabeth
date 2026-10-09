const M = require('./applicant-signals.js');
if (!M.validateGpa('3.5','4','unweighted').ok) throw Error('GPA validation failed');
if (M.validateGpa('4.5','4','weighted').ok) throw Error('Invalid GPA accepted');
console.log('PASS GPA bounds');
