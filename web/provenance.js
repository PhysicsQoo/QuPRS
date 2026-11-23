// Local, build-reported provenance. These hashes identify source inputs and
// published WASM binaries; they do not certify any mathematical verdict.
const SHA=/^[0-9a-f]{40}$/;
const DIGEST=/^[0-9a-f]{64}$/;
const bytes=new TextEncoder();
const hex=array=>Array.from(new Uint8Array(array),b=>b.toString(16).padStart(2,'0')).join('');

export function validateBuildIdentity(source,meta){
  const sha=typeof source==='string'?source.trim():null;
  const source_sha=sha&&SHA.test(sha)?sha:null;
  const valid=source_sha&&meta?.format==='quprs-browser-build'&&
    meta.schema===1&&meta.identity_kind==='build-reported'&&
    meta.source_sha===source_sha&&DIGEST.test(meta.core_wasm_sha256)&&
    DIGEST.test(meta.gpmc_wasm_sha256)&&SHA.test(meta.gpmc_revision)&&
    /^v\d+\.\d+\.\d+$/.test(meta.gpmc_version);
  return {source_sha,build:valid?meta:null};
}

export async function readBuildIdentity(baseUrl){
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),4000);
  const read=async name=>{
    const response=await fetch(new URL(name,baseUrl),{cache:'no-store',signal:controller.signal});
    if(!response.ok)throw new Error('Build marker unavailable: '+name);
    return response;
  };
  try{
    const source=await read('./source-sha.txt').then(x=>x.text()).catch(()=>null);
    const meta=await read('./build-provenance.json').then(x=>x.json()).catch(()=>null);
    return validateBuildIdentity(source,meta);
  }finally{clearTimeout(timer);}
}

export async function reportProvenance(request,identityPromise){
  let identity={source_sha:null,build:null};
  try{identity=await identityPromise}catch{}
  let request_sha256=null;
  try{
    if(crypto?.subtle){
      const hash=await crypto.subtle.digest('SHA-256',bytes.encode(JSON.stringify(request)));
      request_sha256=hex(hash);
    }
  }catch{} // Legacy/insecure local previews may lack WebCrypto.
  const build=identity.build;
  return {
    schema:1,
    provenance_kind:'site-reported-not-a-proof-certificate',
    metadata_status:build?'available':'unavailable',
    source_sha:identity.source_sha,
    request_sha256,
    core_wasm_sha256:build?.core_wasm_sha256??null,
    gpmc_wasm_sha256:build?.gpmc_wasm_sha256??null,
    gpmc_revision:build?.gpmc_revision??null,
    gpmc_version:build?.gpmc_version??null,
  };
}
