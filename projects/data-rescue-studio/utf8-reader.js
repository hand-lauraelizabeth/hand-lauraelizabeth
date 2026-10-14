/* Browser-local byte decoder for CSV and TSV. */
(function(root,factory){
  const api=factory();
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.DataRescueFileReader=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  const MAX_BYTES=5000000;
  function decode(bytes){
    if(!(bytes instanceof ArrayBuffer)&&!ArrayBuffer.isView(bytes))
      throw new Error('Expected a byte array.');
    if(bytes.byteLength>MAX_BYTES)throw new Error('File exceeds 5 MB.');
    try{return new TextDecoder('utf-8',{fatal:true}).decode(bytes);}
    catch(e){throw new Error('This file is not valid UTF-8. Save as UTF-8 and try again.');}
  }
  return {decode,MAX_BYTES};
});
