//! Minimal native executable adapter; no libtest registry.
#[path="cpr_support/public.rs"]
mod public;
fn snapshot(stage: &str) {
    // Diagnostics are separate trials, never used for acceptance timing/RSS.
    if std::env::var_os("CPR_MEMORY_DIAGNOSTIC").is_none() { return; }
    let status=std::fs::read_to_string("/proc/self/status").unwrap();
    let rollup=std::fs::read_to_string("/proc/self/smaps_rollup").unwrap();
    for (source,body) in [("status",status),("smaps_rollup",rollup)] {
        for line in body.lines() {
            if ["VmRSS:","VmHWM:","RssAnon:","RssFile:","RssShmem:","Rss:","Pss:","Pss_Anon:","Pss_File:","Private_Clean:","Private_Dirty:"].iter().any(|k|line.starts_with(k)) {
                println!("CPR_MEMORY_SNAPSHOT stage={stage} source={source} {}",line.split_whitespace().collect::<Vec<_>>().join(" "));
            }
        }
    }
}
fn main() {
    let mode=std::env::args().nth(1).expect("mode");
    snapshot("before");
    match mode.as_str() {
        "public"=>public::cpr_public_hybrid(),
        "noop"=>(),
        _=>panic!("unknown mode"),
    }
    snapshot("after");
}
