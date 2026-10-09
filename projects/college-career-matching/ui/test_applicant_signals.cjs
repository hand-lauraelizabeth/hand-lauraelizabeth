const M = require('./applicant-signals.js');
if (!M.validateGpa('3.5','4','unweighted').ok) throw Error('GPA validation failed');
console.log('PASS applicant signal smoke test');
