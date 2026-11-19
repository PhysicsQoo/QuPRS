// Bounded diagnostics must never truncate or evict the exact result.
// MIT licensed PathsumWMC browser adapter.
self.createCounterOutput=()=>{
  const exact=[];let diagnostic='',stderr='',resultBytes=0;
  return {
    append(which,line) {
      line=String(line)+'\n';
      if(which==='out' && (line.startsWith('c s exact ') || line.startsWith('c o precision ') || line.startsWith('c o quprs-phase-weights '))) {
        resultBytes+=line.length;
        if(resultBytes>4_000_000) throw new Error('Exact counter result exceeds the 4 MB output capacity.');
        exact.push(line);
      } else if(which==='out') diagnostic=(diagnostic+line).slice(-32_768);
      else stderr=(stderr+line).slice(-32_768);
    },
    stdout:()=>diagnostic+exact.join(''),
    stderr:()=>stderr,
  };
};
