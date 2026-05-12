use log::{error, info, warn};
use std::panic;
use std::process::Command;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager,
};

mod db;
mod trainer;
mod gpu;
mod process;

use trainer::{Job, TrainingConfig};
use gpu::GPUInfo;
use process::ModelFile;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn init_database(app: tauri::AppHandle) -> Result<(), String> {
    let app_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&app_dir).map_err(|e| e.to_string())?;
    trainer::init_database(app_dir)
}

#[tauri::command]
fn create_training_job(config: TrainingConfig) -> Result<Job, String> {
    trainer::create_job(config)
}

#[tauri::command]
fn get_job_status(job_id: String) -> Result<Job, String> {
    trainer::get_job_status(&job_id)
}

#[tauri::command]
fn update_job_progress(job_id: String, epoch: i32, loss: f64) -> Result<(), String> {
    trainer::update_job_progress(&job_id, epoch, loss)
}

#[tauri::command]
fn cancel_training_job(job_id: String) -> Result<(), String> {
    trainer::cancel_job(&job_id)
}

#[tauri::command]
fn list_training_jobs() -> Result<Vec<Job>, String> {
    trainer::list_jobs()
}

#[tauri::command]
fn get_gpu_info() -> Result<GPUInfo, String> {
    gpu::get_gpu_info()
}

#[tauri::command]
fn has_gpu() -> bool {
    gpu::has_nvidia_gpu()
}

#[tauri::command]
fn start_training(job_id: String) -> Result<(), String> {
    process::run_training(&job_id)
}

#[tauri::command]
fn cancel_training(job_id: String) -> Result<(), String> {
    process::cancel_training(&job_id)
}

#[tauri::command]
fn is_training_running(job_id: String) -> bool {
    process::is_training_running(&job_id)
}

#[tauri::command]
fn scan_model_files() -> Result<Vec<ModelFile>, String> {
    process::scan_models()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    std::env::set_var("GDK_BACKEND", "x11");
    std::env::remove_var("WAYLAND_DISPLAY");

    std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
    std::env::set_var("WEBKIT_FORCE_SOFTWARE_RENDERING", "1");
    std::env::set_var("MOZ_DISABLE_GPU", "1");
    std::env::set_var("GTK_THEME", "Adwaita");

    panic::set_hook(Box::new(|panic_info| {
        error!("PANIC: {:?}", panic_info);
    }));

    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();
    info!("Starting N-Xyme MIND Desktop");

    let result = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, shortcut, _event| {
                    info!("Global shortcut triggered: {:?}", shortcut);
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                })
                .build(),
        )
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            warn!("Single instance callback triggered");
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            info!("Setting up system tray");

            std::thread::spawn(move || {
                info!("Starting N-Xyme backend services...");
                
                let start_mcp = Command::new("bash")
                    .args(["-c", "source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin/env.sh && cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND && nohup python3 -m packages.brain_mcp > /tmp/nx-brain-mcp.log 2>&1 &"])
                    .spawn();
                
                match start_mcp {
                    Ok(_) => info!("Brain MCP started on port 8765"),
                    Err(e) => warn!("Brain MCP start skipped: {}", e),
                }
                
                let start_gateway = Command::new("bash")
                    .args(["-c", "source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin/env.sh && cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND && nohup python3 packages/http_gateway.py > /tmp/nx-gateway.log 2>&1 &"])
                    .spawn();
                
                match start_gateway {
                    Ok(_) => info!("HTTP Gateway started on port 8766"),
                    Err(e) => warn!("HTTP Gateway start skipped: {}", e),
                }
                
                info!("Starting Next.js...");
                let result = Command::new("npm")
                    .args(["run", "dev"])
                    .current_dir("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/frontend")
                    .spawn();

                match result {
                    Ok(_) => info!("Next.js started"),
                    Err(e) => error!("Failed to start Next.js: {}", e),
                }
            });

            std::thread::sleep(std::time::Duration::from_secs(8));

            if let Some(window) = app.get_webview_window("main") {
                let _ = window.eval("window.location.href = 'http://localhost:3000'");
                info!("Navigated webview to Next.js");
            }

            let show_item = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
            let dashboard_item =
                MenuItem::with_id(app, "dashboard", "Dashboard", true, None::<&str>)?;
            let orchestration_item =
                MenuItem::with_id(app, "orchestration", "Orchestration", true, None::<&str>)?;
            let memory_item = MenuItem::with_id(app, "memory", "Memory", true, None::<&str>)?;
            let chat_item = MenuItem::with_id(app, "chat", "Chat", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

            let menu = Menu::with_items(
                app,
                &[
                    &show_item,
                    &dashboard_item,
                    &orchestration_item,
                    &memory_item,
                    &chat_item,
                    &quit_item,
                ],
            )?;

            let _tray = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("N-Xyme MIND")
                .on_menu_event(|app, event| {
                    let id = event.id.as_ref();
                    info!("Tray menu event: {}", id);

                    if let Some(window) = app.get_webview_window("main") {
                        match id {
                            "show" | "dashboard" | "orchestration" | "memory" | "chat" => {
                                let _ = window.show();
                                let _ = window.set_focus();
                                if id != "show" {
                                    let _ =
                                        window.eval(&format!("window.location.href = '/{}'", id));
                                }
                            }
                            "quit" => {
                                info!("Quit requested from tray");
                                app.exit(0);
                            }
                            _ => {}
                        }
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            info!("System tray configured successfully");

            use tauri_plugin_global_shortcut::GlobalShortcutExt;
            let app_handle = app.handle().clone();
            if let Err(e) =
                app.global_shortcut()
                    .on_shortcut("ctrl+shift+n", move |_app, _shortcut, _event| {
                        info!("Ctrl+Shift+N pressed");
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    })
            {
                warn!("Failed to register global shortcut: {}", e);
            } else {
                info!("Global shortcut Ctrl+Shift+N registered");
            }

            if let Some(_window) = app.get_webview_window("main") {
                info!("Main window found, ready to display");
            } else {
                warn!("Main window not found in setup");
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            info!("Window event: {:?}", event);
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                info!("Window close requested - minimizing to tray");
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![
    greet,
    init_database,
    create_training_job,
    get_job_status,
    update_job_progress,
    cancel_training_job,
    list_training_jobs,
    get_gpu_info,
    has_gpu,
    start_training,
    cancel_training,
    is_training_running,
    scan_model_files
])
        .run(tauri::generate_context!());

    if let Err(e) = result {
        error!("Application error: {:?}", e);
        std::process::exit(1);
    }
}
