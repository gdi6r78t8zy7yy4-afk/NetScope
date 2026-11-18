// Copyright 2024 NetScope Team
// SPDX-License-Identifier: GPL-3.0

use tauri::{CustomMenuItem, Menu, MenuItem, Submenu};

pub fn create_menu() -> Menu {
    let app_menu = Submenu::new(
        "NetScope",
        Menu::new()
            .add MenuItem::about("About NetScope", "Copyright (c) 2024 NetScope Team")
            .add(MenuItem::separator())
            .add(CustomMenuItem::new("preferences", "Preferences")
                .accelerator("CmdOrCtrl+,"))
            .add(MenuItem::separator())
            .add(CustomMenuItem::new("quit", "Quit NetScope")
                .accelerator("CmdOrCtrl+Q")),
    );

    let scan_menu = Submenu::new(
        "Scan",
        Menu::new()
            .add(CustomMenuItem::new("start_scan", "Start New Scan")
                .accelerator("CmdOrCtrl+S"))
            .add(MenuItem::separator())
            .add(CustomMenuItem::new("stop_scan", "Stop Current Scan")
                .accelerator("Esc")),
    );

    let view_menu = Submenu::new(
        "View",
        Menu::new()
            .add(CustomMenuItem::new("refresh", "Refresh")
                .accelerator("CmdOrCtrl+R"))
            .add(MenuItem::separator())
            .add(CustomMenuItem::new("full_screen", "Toggle Full Screen")
                .accelerator("CmdOrCtrl+F")),
    );

    Menu::new()
        .add_submenu(app_menu)
        .add_submenu(scan_menu)
        .add_submenu(view_menu)
}
