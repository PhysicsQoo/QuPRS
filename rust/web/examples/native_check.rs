//! Same browser adapter compiled natively for differential tests and timing.
use std::{env,fs,io::{self,Read},process::Command,time::Instant};
use serde_json::{json,Value};
fn run()->Result<Value,Box<dyn std::error::Error>>{
 let binary=env::args().nth(1).ok_or("Expected native GPMC path")?;
 let mut input=String::new();io::stdin().read_to_string(&mut input)?;let start=Instant::now();
 let job=quprs_web::BrowserJob::new(&input)?;let v:Value=serde_json::from_str(&job.job())?;
 if v.get("report").is_some(){return Ok(json!({"report":v["report"],"request_ms":start.elapsed().as_secs_f64()*1000.0}))}
 let dir=env::temp_dir().join(format!("quprs-web-native-{}",std::process::id()));fs::create_dir(&dir)?;
 let result=(||->Result<Value,Box<dyn std::error::Error>>{
  let file=dir.join("input.cnf");fs::write(&file,v["cnf"].as_str().ok_or("Missing CNF")?)?;
  let tick=Instant::now();let output=Command::new(binary).args(["-mode=1","-prec=30","-cs=64"]).arg(&file).output()?;let counter_ms=tick.elapsed().as_secs_f64()*1000.0;
  if !output.status.success(){return Err(format!("GPMC {}: {}",output.status,String::from_utf8_lossy(&output.stderr)).into())}
  let stdout=String::from_utf8(output.stdout)?;let mut value:Value=serde_json::from_str(&job.finish(&stdout))?;
  value["request_ms"]=json!(start.elapsed().as_secs_f64()*1000.0);value["counter_ms"]=json!(counter_ms);Ok(value)
 })();let _=fs::remove_dir_all(&dir);result
}
fn main(){match run(){Ok(v)=>println!("{}",v),Err(e)=>{println!("{}",json!({"error":e.to_string()}));std::process::exit(1)}}}
