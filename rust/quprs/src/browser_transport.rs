//! Browser/native capture-and-replay boundary. The upstream verifier and
//! numerical classifier remain authoritative. Native calls are unchanged
//! unless a transport session is explicitly activated. MIT licensed.
use std::cell::{RefCell,Cell};
use anyhow::{anyhow,Result};
#[derive(Clone,Debug)]
pub struct Job {pub tool:String,pub cnf:String,epsilon:f64}
#[derive(Debug)]
pub struct Pending;
impl std::fmt::Display for Pending {fn fmt(&self,f:&mut std::fmt::Formatter<'_>)->std::fmt::Result{write!(f,"Browser weighted count required")}}
impl std::error::Error for Pending {}
enum State {Off,Capture(Option<Job>),Replay{job:Job,stdout:String,used:bool}}
thread_local! {static STATE:RefCell<State>=const{RefCell::new(State::Off)};static EPSILON:Cell<f64>=const{Cell::new(1e-8)};}
struct Restore(Option<State>,f64);
impl Drop for Restore {fn drop(&mut self){let old=self.0.take().unwrap();STATE.with(|s|{s.replace(old);});EPSILON.with(|e|e.set(self.1));}}
fn enter(state:State,epsilon:f64)->Restore {let old=EPSILON.with(|e|e.replace(epsilon));Restore(Some(STATE.with(|s|s.replace(state))),old)}
pub(crate) fn epsilon()->f64{EPSILON.with(Cell::get)}
pub fn active()->bool {STATE.with(|s|!matches!(*s.borrow(),State::Off))}
fn canonical(cnf:&str)->Vec<String> {let mut lines:Vec<_>=cnf.lines().map(str::trim).filter(|s|!s.is_empty()).map(str::to_owned).collect();lines.sort();lines}
pub fn exchange(tool:&str,cnf:&str)->Result<String> {
 STATE.with(|s|match &mut *s.borrow_mut(){
  State::Off=>Err(anyhow!("Browser transport is not active")),
  State::Capture(job)=>{if job.is_some(){return Err(anyhow!("Multiple browser counter jobs are unsupported"))}*job=Some(Job{tool:tool.into(),cnf:cnf.into(),epsilon:epsilon()});Err(Pending.into())},
  State::Replay{job,stdout,used}=>{
   if *used || job.tool!=tool || canonical(&job.cnf)!=canonical(cnf){return Err(anyhow!("Browser result does not match the prepared weighted problem"))}
   let phases=cnf.lines().filter(|l|l.starts_with("c p quprs-phase ")).count();
   if phases>0 && !stdout.lines().any(|l|l==format!("c o quprs-phase-weights {phases}")){return Err(anyhow!("Counter did not acknowledge source-preserving MPFR input weights"))}
   *used=true;Ok(stdout.clone())
  }
 })
}
pub fn capture<T>(f:impl FnOnce()->Result<T>)->(Result<T>,Option<Job>) {
 capture_with_epsilon(1e-8,f)
}
pub fn capture_with_epsilon<T>(epsilon:f64,f:impl FnOnce()->Result<T>)->(Result<T>,Option<Job>) {
 let _restore=enter(State::Capture(None),epsilon);let result=f();
 let job=STATE.with(|s|match &mut *s.borrow_mut(){State::Capture(job)=>job.take(),_=>None});(result,job)
}
pub fn replay<T>(job:&Job,stdout:&str,f:impl FnOnce()->Result<T>)->Result<T> {
 let _restore=enter(State::Replay{job:job.clone(),stdout:stdout.into(),used:false},job.epsilon);let result=f();
 let used=STATE.with(|s|matches!(*s.borrow(),State::Replay{used:true,..}));
 if !used{return match result{Err(error)=>Err(error),Ok(_)=>Err(anyhow!("Prepared browser counter result was not consumed"))}}result
}
#[cfg(test)]mod tests{
 use super::*;
 #[test]fn pending_replay_and_cleanup(){
  let (result,job)=capture(||exchange("gpmc","p cnf 1 1\n1 0\n"));assert!(result.unwrap_err().downcast_ref::<Pending>().is_some());assert!(!active());let job=job.unwrap();
  assert_eq!(replay(&job,"count",||exchange("gpmc","1 0\np cnf 1 1\n")).unwrap(),"count");assert!(!active());
  assert!(replay(&job,"count",||exchange("gpmc","p cnf 1 1\n-1 0\n")).is_err());assert!(!active());
  assert!(replay(&job,"count",||Ok(())).is_err());assert!(!active());
 }
 #[test]fn phase_acknowledgment_is_required(){
  let cnf="c p quprs-phase 1 1 8 0 1 0 96\n";let (_,job)=capture(||exchange("gpmc",cnf));let job=job.unwrap();
  let error=replay(&job,"count",||exchange("gpmc",cnf)).unwrap_err();assert!(error.to_string().contains("acknowledge"));
  assert!(replay(&job,"c o quprs-phase-weights 1\ncount",||exchange("gpmc",cnf)).is_ok());
 }
 #[test]fn nested_sessions_restore_and_duplicate_result_rejected(){
  let (_,job)=capture(||{let (_,inner)=capture(||exchange("gpmc","inner"));assert!(inner.is_some());exchange("gpmc","outer")});let job=job.unwrap();assert_eq!(job.cnf,"outer");
  assert!(replay(&job,"count",||{exchange("gpmc","outer")?;exchange("gpmc","outer")}).is_err());assert!(!active());
 }
}
