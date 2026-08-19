#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use orren_native_core::process;
use serde::Serialize;

#[derive(Serialize)]
struct StateResponse {
    records: Vec<String>,
    json: String,
}

#[tauri::command]
fn realize_state(application: String, input_title: String) -> StateResponse {
    let state = process(&application, &input_title);
    StateResponse {
        records: state.to_records(),
        json: state.to_json_object(),
    }
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![realize_state])
        .run(tauri::generate_context!())
        .expect("error while running Orren Tauri shell");
}

#[cfg(test)]
mod tests {
    use super::realize_state;
    use serde_json::Value;

    #[test]
    fn command_bridge_returns_shared_core_records() {
        let response = realize_state("desktop-app".to_string(), "open file".to_string());
        assert_eq!(response.records, vec![
            "application=desktop-app",
            "input_title=open file",
        ]);
        let json: Value = serde_json::from_str(&response.json).expect("core JSON must be valid");
        assert_eq!(json["application"], "desktop-app");
        assert_eq!(json["input_title"], "open file");
    }

    #[test]
    fn command_bridge_preserves_special_characters() {
        let response = realize_state("quote\\app".to_string(), "say \"hello\"".to_string());
        let json: Value = serde_json::from_str(&response.json).expect("escaped core JSON must be valid");
        assert_eq!(json["application"], "quote\\app");
        assert_eq!(json["input_title"], "say \"hello\"");
    }
}
