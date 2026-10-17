//! Private diagnostic instrumentation. No solver or algebra decisions depend on this module.
//! Snapshot scans and TLS/counter operations perturb diagnostic timings. Reduction/Elim
//! timings include nested instrumentation; JSON serialization happens only at RunScope drop.
use crate::pathsum::PathSum;
use std::{cell::RefCell, time::Instant, io::Write};
#[derive(Clone, Copy, Default)]
struct Size { variables: usize, phase_terms: usize, max_degree: usize }
impl Size {
    fn of(p: &PathSum) -> Self { Self { variables: p.v.path_vars.len(), phase_terms: p.p.terms.len(), max_degree: p.p.terms.keys().map(|m| m.len()).max().unwrap_or(0) } }
    fn json(self) -> String { format!("{{\"variables\":{},\"phase_terms\":{},\"max_degree\":{}}}", self.variables,self.phase_terms,self.max_degree) }
    fn merge(&mut self, x: Self) { self.variables=self.variables.max(x.variables); self.phase_terms=self.phase_terms.max(x.phase_terms); self.max_degree=self.max_degree.max(x.max_degree); }
}
#[derive(Clone, Copy, Default)]
struct Used { calls:u64, ns:u128, terms:u64, entries:u64 }
impl Used {
    fn json(self)->String { format!("{{\"calls\":{},\"ns\":{},\"terms_scanned\":{},\"monomial_entries_scanned\":{}}}",self.calls,self.ns,self.terms,self.entries) }
    fn delta(self, b:Self)->Self { Self{calls:self.calls-b.calls,ns:self.ns-b.ns,terms:self.terms-b.terms,entries:self.entries-b.entries} }
    fn add(&mut self,x:Self) {self.calls+=x.calls;self.ns+=x.ns;self.terms+=x.terms;self.entries+=x.entries;}
}
struct Trace { path:std::path::PathBuf, start:Instant, ket:u64, bra:u64, gate:Option<bool>, peak:Size, gate_peak:Size, attempts:[u64;3], successes:[u64;3], used:Used, used_elim:Used, elim_depth:u32, elim_ns:u128, encoding_ns:u128, reduce_ns:u128, events:Vec<String> }
thread_local! { static TRACE: RefCell<Option<Trace>> = const { RefCell::new(None) }; }
fn with(f:impl FnOnce(&mut Trace)) { TRACE.with(|t| {if let Some(t)=t.borrow_mut().as_mut(){f(t)}}); }
fn active()->bool {TRACE.with(|t|t.borrow().is_some())}
pub(crate) struct RunScope(bool);
impl RunScope { pub(crate) fn new()->Self {
    let path=match std::env::var_os("QUPRS_TRACE_PATH") {Some(p)=>p.into(),None=>return Self(false)};
    let mut enabled=false;
    TRACE.with(|slot| { let mut slot=slot.borrow_mut(); if slot.is_none(){*slot=Some(Trace{path,start:Instant::now(),ket:0,bra:0,gate:None,peak:Size::default(),gate_peak:Size::default(),attempts:[0;3],successes:[0;3],used:Used::default(),used_elim:Used::default(),elim_depth:0,elim_ns:0,encoding_ns:0,reduce_ns:0,events:Vec::new()});enabled=true;} });Self(enabled)
} }
impl Drop for RunScope {fn drop(&mut self){if !self.0{return} let t=TRACE.with(|s|s.borrow_mut().take()); if let Some(t)=t {
    let elapsed=t.start.elapsed().as_nanos();
    let line=format!("{{\"schema\":1,\"diagnostic_only\":true,\"run_ns\":{},\"completed_ket\":{},\"completed_bra\":{},\"full_reduce_ns\":{},\"encoding_ns\":{},\"elim_ns\":{},\"get_used_vars\":{},\"get_used_vars_in_elim\":{},\"attempts\":{:?},\"successes\":{:?},\"peak\":{},\"gate_boundary_peak\":{},\"reductions\":[{}]}}\n", elapsed,t.ket,t.bra,t.reduce_ns,t.encoding_ns,t.elim_ns,t.used.json(),t.used_elim.json(),t.attempts,t.successes,t.peak.json(),t.gate_peak.json(),t.events.join(","));
    match std::fs::OpenOptions::new().create(true).append(true).open(&t.path).and_then(|mut f|f.write_all(line.as_bytes())) {Ok(())=>(),Err(e)=>eprintln!("QuPRS attribution write failed: {}",e)}
} } }
pub(crate) fn sample(p:&PathSum){if active(){let x=Size::of(p);with(|t|t.peak.merge(x));}}
pub(crate) fn gate_begin(p:&PathSum,bra:bool){if active(){let x=Size::of(p);with(|t|{t.gate=Some(bra);t.peak.merge(x);t.gate_peak.merge(x);});}}
pub(crate) fn gate_end(p:&PathSum,bra:bool){if active(){let x=Size::of(p);with(|t|{if bra{t.bra+=1}else{t.ket+=1}t.gate=None;t.peak.merge(x);t.gate_peak.merge(x);});}}
pub(crate) fn rule(i:usize, success:bool){with(|t|{if success{t.successes[i]+=1}else{t.attempts[i]+=1}})}
pub(crate) struct Reduce { start:Instant,before:Size, attempts:[u64;3],successes:[u64;3],used:Used,used_elim:Used,ket:u64,bra:u64,gate:Option<bool> }
pub(crate) fn reduce_begin(p:&PathSum)->Option<Reduce>{if !active(){return None} let before=Size::of(p);let mut out=None;with(|t|{t.peak.merge(before);out=Some(Reduce{start:Instant::now(),before,attempts:t.attempts,successes:t.successes,used:t.used,used_elim:t.used_elim,ket:t.ket,bra:t.bra,gate:t.gate})});out}
pub(crate) fn reduce_end(r:Option<Reduce>,p:&PathSum){if let Some(r)=r{let ns=r.start.elapsed().as_nanos();let after=Size::of(p);with(|t|{t.reduce_ns+=ns;t.peak.merge(after);let ad:Vec<_>=(0..3).map(|i|t.attempts[i]-r.attempts[i]).collect();let sd:Vec<_>=(0..3).map(|i|t.successes[i]-r.successes[i]).collect();let position=match r.gate{None=>"checkpoint",Some(false)=>"gate_ket",Some(true)=>"gate_bra"};t.events.push(format!("{{\"position\":\"{}\",\"completed_ket\":{},\"completed_bra\":{},\"ns\":{},\"before\":{},\"after\":{},\"attempts\":{:?},\"successes\":{:?},\"attempts_delta\":{:?},\"successes_delta\":{:?},\"get_used_vars_delta\":{},\"get_used_vars_in_elim_delta\":{}}}",position,r.ket,r.bra,ns,r.before.json(),after.json(),t.attempts,t.successes,ad,sd,t.used.delta(r.used).json(),t.used_elim.delta(r.used_elim).json()));});}}
pub(crate) struct ElimSpan(Option<Instant>);
impl ElimSpan{pub(crate) fn new()->Self{if !active(){return Self(None)}with(|t|t.elim_depth+=1);Self(Some(Instant::now()))}}
impl Drop for ElimSpan{fn drop(&mut self){if let Some(s)=self.0{let ns=s.elapsed().as_nanos();with(|t|{t.elim_depth-=1;t.elim_ns+=ns;});}}}
pub(crate) struct UsedSpan {start:Option<Instant>,terms:u64,entries:u64}
impl UsedSpan{pub(crate) fn new(terms:usize)->Self{Self{start:if active(){Some(Instant::now())}else{None},terms:terms as u64,entries:0}}pub(crate) fn entries(&mut self,n:usize){if self.start.is_some(){self.entries+=n as u64}}}
impl Drop for UsedSpan{fn drop(&mut self){if let Some(s)=self.start{let x=Used{calls:1,ns:s.elapsed().as_nanos(),terms:self.terms,entries:self.entries};with(|t|{t.used.add(x);if t.elim_depth>0{t.used_elim.add(x)}});}}}

pub(crate) fn encoding(ns:u128){with(|t|t.encoding_ns+=ns)}
