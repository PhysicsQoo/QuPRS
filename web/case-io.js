// Versioned, local-only comparison request interchange. Imported reports are
// untrusted documents: the browser must rerun their requests, never their verdicts.
export const CASE_FORMAT='quprs-browser-case';
export const CASE_SCHEMA=1;
export const MAX_CIRCUIT_BYTES=256*1024;
export const MAX_CASE_BYTES=768*1024;

const modes=new Set(['hybrid','wmc','reduction']);
const strategies=new Set(['difference','proportional','naive','straightforward']);
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);

export function normalizeRequest(request){
  if(!object(request))throw new Error('The JSON does not contain a comparison request.');
  const {circuit1,circuit2,mode,strategy,distance_tolerance,rr_tolerance}=request;
  const utf8=new TextEncoder();
  for(const [label,text] of [['Circuit A',circuit1],['Circuit B',circuit2]]){
    if(typeof text!=='string'||!text.trim())
      throw new Error(label+' requires nonempty OpenQASM text.');
    if(utf8.encode(text).byteLength>MAX_CIRCUIT_BYTES)
      throw new Error(label+' exceeds the 256 KiB limit.');
  }
  if(!modes.has(mode))throw new Error('Unsupported verification mode.');
  if(!strategies.has(strategy))throw new Error('Unsupported WMC strategy.');
  if(typeof distance_tolerance!=='number'||!Number.isFinite(distance_tolerance)||
     distance_tolerance<0||distance_tolerance>1)
    throw new Error('Projective distance tolerance must be from 0 to 1.');
  if(typeof rr_tolerance!=='number'||!Number.isFinite(rr_tolerance)||rr_tolerance<0)
    throw new Error('Reduction coefficient tolerance must be non-negative.');
  return {circuit1,circuit2,mode,strategy,distance_tolerance,rr_tolerance};
}

export function exportCase(request){
  return {format:CASE_FORMAT,schema:CASE_SCHEMA,request:normalizeRequest(request)};
}

export function importCase(text){
  if(new TextEncoder().encode(text).byteLength>MAX_CASE_BYTES)
    throw new Error('JSON exceeds the 768 KiB import limit.');
  let value;
  try{value=JSON.parse(text)}catch{throw new Error('Invalid JSON document.')}
  if(!object(value))throw new Error('Expected a JSON object.');
  if(Object.prototype.hasOwnProperty.call(value,'format')){
    if(value.format!==CASE_FORMAT||value.schema!==CASE_SCHEMA)
      throw new Error('Unsupported case format or schema version.');
    return {request:normalizeRequest(value.request),kind:'case'};
  }
  // Previously downloaded browser reports carry the exact original request.
  // Deliberately discard status, distance, warning and claimed proof metadata.
  if(object(value.request))
    return {request:normalizeRequest(value.request),kind:'report'};
  throw new Error('Expected a versioned case or browser report with a request.');
}
