/* Browser-local money helpers. */
function parseAmount(value){const n=Number(value);if(!Number.isFinite(n))throw new Error('Enter an amount.');return Math.round(n*100);}
if(typeof module!=='undefined')module.exports={parseAmount};
