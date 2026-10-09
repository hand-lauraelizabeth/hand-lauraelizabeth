const M=require('./applicant-signals.js');
if (!M.validateTesting('omit','','').omitted) throw Error('Omitted scores invalid');
