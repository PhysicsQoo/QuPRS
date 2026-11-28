use serde_json::{json, Value};
use std::io::{self, Read};
fn run() -> Result<Value, Box<dyn std::error::Error>> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let v: Value = serde_json::from_str(&input)?;
    let j = quprs_web::BrowserJob::new(&v["request"].to_string())?;
    let result = match v["action"].as_str() {
        Some("capture") => j.job(),
        Some("gpmc") => j.finish(v["stdout"].as_str().ok_or("stdout")?),
        Some("rawmocs") => j.finish_rawmocs(
            v["engine"].as_str().ok_or("engine")?,
            v["status"].as_i64().ok_or("status")?.try_into()?,
            v["stdout"].as_str().ok_or("stdout")?,
            v["stderr"].as_str().ok_or("stderr")?,
            v["ack"].as_str().ok_or("ack")?,
        ),
        _ => return Err("action".into()),
    };
    Ok(serde_json::from_str(&result)?)
}
fn main() {
    match run() {
        Ok(v) => println!("{v}"),
        Err(e) => { println!("{}", json!({"error":e.to_string()})); std::process::exit(1); }
    }
}
