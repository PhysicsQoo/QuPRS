importScripts("phase.js");
self.onmessage=async ({data})=>{
  const out=[],err=[];
  try{
    const m=await createPhaseBridge({noInitialRun:true,print:x=>out.push(String(x)),printErr:x=>err.push(String(x))});
    m.FS.writeFile("/input.cnf",data.cnf);
    let status=0;
    try{status=m.callMain(["/input.cnf"])||0;}catch(e){if(e&&typeof e.status==="number")status=e.status;else throw e;}
    if(status) throw Error("phase bridge failed "+status+" "+err.join("\n"));
    const cnf=m.FS.readFile("/materialized.cnf",{encoding:"utf8"});
    const expected=data.cnf.split("\n").filter(x=>x.startsWith("c p quprs-phase ")).length;
    const ack=out.filter(x=>x.startsWith("c o quprs-phase-weights "));
    if((expected && (ack.length!==1||ack[0]!=="c o quprs-phase-weights "+expected))||(!expected&&ack.length)||cnf.includes("c p quprs-phase "))throw Error("phase acknowledgement mismatch");
    self.postMessage({cnf,ack:expected,stdout:out.join("\n")});
  }catch(e){self.postMessage({error:String(e)});}
};
