// Copyright 2024 NetScope Team
// SPDX-License-Identifier: GPL-3.0

#![cfg_attr(
    all(not(debug_assertions), target_os = "macos"),
    windows_subsystem = "windows"
)]

mod cmd;
mod menu;

use tauri::Manager;

fn main() {
    let context = tauri::generate_context!();

    tauri::Builder::default()
        .menu(menu::create_menu)
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                window.close().ok();
            }
        })
        .invoke_handler(tauri::generate_handler![
            cmd::start_scan,
            cmd::cancel_scan,
            cmd::discover_assets,
            cmd::get_asset_info,
            cmd::sync_intelligence
        ])
        .run(context)
        .expect("error while running tauri application");
}
