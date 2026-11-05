// Small, uncompressed ZIP writer. No remote assets or third-party runtime required.
export function zipParts(parts) {
  const encoder=new TextEncoder(), chunks=[], central=[];
  let offset=0;
  const crc32=bytes=>{
    let crc=0xffffffff;
    for(const byte of bytes){crc^=byte;for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
    return (crc^0xffffffff)>>>0;
  };
  for(const [name,content] of Object.entries(parts)) {
    const path=encoder.encode(name),data=encoder.encode(content),crc=crc32(data);
    const local=new Uint8Array(30+path.length),v=new DataView(local.buffer);
    v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint16(12,33,true);
    v.setUint32(14,crc,true);v.setUint32(18,data.length,true);v.setUint32(22,data.length,true);v.setUint16(26,path.length,true);local.set(path,30);
    chunks.push(local,data);
    const entry=new Uint8Array(46+path.length),c=new DataView(entry.buffer);
    c.setUint32(0,0x02014b50,true);c.setUint16(4,20,true);c.setUint16(6,20,true);c.setUint16(8,0x800,true);c.setUint16(14,33,true);
    c.setUint32(16,crc,true);c.setUint32(20,data.length,true);c.setUint32(24,data.length,true);c.setUint16(28,path.length,true);c.setUint32(42,offset,true);entry.set(path,46);
    central.push(entry);offset+=local.length+data.length;
  }
  const size=central.reduce((sum,p)=>sum+p.length,0),end=new Uint8Array(22),e=new DataView(end.buffer);
  e.setUint32(0,0x06054b50,true);e.setUint16(8,central.length,true);e.setUint16(10,central.length,true);e.setUint32(12,size,true);e.setUint32(16,offset,true);
  const result=new Uint8Array(offset+size+22);let at=0;
  for(const chunk of [...chunks,...central,end]){result.set(chunk,at);at+=chunk.length;}
  return result;
}
