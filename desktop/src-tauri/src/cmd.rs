// Copyright 2024 NetScope Team
// SPDX-License-Identifier: GPL-3.0

use serde::{Deserialize, Serialize};
use tauri::command;
use tokio::process::Command;

#[derive(Serialize)]
pub struct ScanResponse {
    pub status: String,
    pub result: Option<String>,
}

#[derive(Deserialize)]
pub struct ScanRequest {
    pub target: String,
    #[serde(default)]
    pub scan_type: String,
}

#[command]
pub async fn start_scan(request: ScanRequest) -> Result<ScanResponse, String> {
    let target = request.target;
    let scan_type = request.scan_type;

    // Validate target
    if !validate_target(&target) {
        return Err("Invalid target".to_string());
    }

    // Determine command based on scan type
    let (cmd, args) = match scan_type.as_str() {
        "discovery" => ("nmap", vec!["-sn", &target]),
        "port_scan" => ("nmap", vec!["-sV", "-p", "1-65535", &target]),
        _ => return Err("Unknown scan type".to_string()),
    };

    // Run the command
    let output = Command::new(cmd)
        .args(&args)
        .output()
        .await
        .map_err(|e| format!("Failed to run command: {}", e))?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        Ok(ScanResponse {
            status: "completed".to_string(),
            result: Some(stdout.to_string()),
        })
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Ok(ScanResponse {
            status: "failed".to_string(),
            result: Some(stderr.to_string()),
        })
    }
}

#[command]
pub async fn cancel_scan(_scan_id: i64) -> Result<ScanResponse, String> {
    // For now, just return success
    Ok(ScanResponse {
        status: "cancelled".to_string(),
        result: None,
    })
}

#[command]
pub async fn discover_assets() -> Result<Vec<String>, String> {
    // Run nmap ping scan
    let output = Command::new("nmap")
        .args(&["-sn", "192.168.1.0/24"])
        .output()
        .await
        .map_err(|e| format!("Failed to run scan: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);

    // Parse output (simplified)
    let mut assets = Vec::new();
    
    for line in stdout.lines() {
        if line.contains("Nmap scan report") {
            let parts: Vec<&str> = line.split(' ').collect();
            if parts.len() >= 5 {
                let ip = parts[4].trim_matches(')');
                assets.push(ip.to_string());
            }
        }
    }

    Ok(assets)
}

#[command]
pub async fn get_asset_info(_ip: String) -> Result<String, String> {
    // Placeholder for asset info
    Ok("Asset info".to_string())
}

#[command]
pub async fn sync_intelligence() -> Result<String, String> {
    // Placeholder for intelligence sync
    Ok("Intelligence synced".to_string())
}

fn validate_target(target: &str) -> bool {
    // Simple validation
    target.len() > 0 && target.len() <= 255
}
