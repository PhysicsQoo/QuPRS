#!/usr/bin/env python3
"""Apply identical research-only precision floor to two ephemeral native source trees."""
import sys,hashlib
from pathlib import Path
target=Path(sys.argv[1])
src=target.read_text()
anchor="    Ok(selected.max(MIN_BITS) as usize)"
assert src.count(anchor)==1
out=src.replace(anchor,'''    let selected = selected.max(MIN_BITS) as usize;
    // Explicit D8d laboratory override. Not a production precision policy.
    if let Ok(value) = std::env::var("QUPRS_RESEARCH_D8D_WEIGHT_BITS") {
        let requested: usize = value.parse()?;
        if ![96, 128, 160, 192].contains(&requested) || requested < selected {
            return Err(anyhow!("Invalid D8d precision floor"));
        }
        return Ok(requested);
    }
    Ok(selected)''')
target.write_text(out)
print("D8D_PATCH_SHA256",hashlib.sha256(target.read_bytes()).hexdigest())
