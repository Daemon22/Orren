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
