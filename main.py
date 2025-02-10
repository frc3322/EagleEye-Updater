import os
import threading
from multiprocessing import freeze_support

import customtkinter as ctk

from network import discover_server, tcp_client
from update_manager import (
    get_current_version,
    get_latest_version,
    download_update,
    get_update_dir
)

freeze_support()

class UpdateApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Software Update Tool")
        self.geometry("600x450")

        # Configure grid layout for the root window.
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=2)
        self.grid_columnconfigure(0, weight=1)

        # Top frame (split into two columns: version display and controls)
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.top_frame.grid_rowconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=1)

        # Left frame: Version display.
        self.version_frame = ctk.CTkFrame(self.top_frame)
        self.version_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Right frame: Controls.
        self.control_frame = ctk.CTkFrame(self.top_frame)
        self.control_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Bottom frame: Log output.
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        # --- Version Display (Left Frame) ---
        self.current_version_label = ctk.CTkLabel(
            self.version_frame, text="Current Version: None", font=("Arial", 16)
        )
        self.current_version_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.latest_version_label = ctk.CTkLabel(
            self.version_frame, text="Latest Version: Unknown", font=("Arial", 16)
        )
        self.latest_version_label.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="w")

        # --- Moved GitHub Version Button to Left Frame ---
        self.check_github_button = ctk.CTkButton(
            self.version_frame, text="Check GitHub Version", command=self.check_github_version_thread
        )
        self.check_github_button.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")

        # --- Controls (Right Frame) ---
        self.server_ip_label = ctk.CTkLabel(self.control_frame, text="Server IP (optional):")
        self.server_ip_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.server_ip_entry = ctk.CTkEntry(self.control_frame, width=200)
        self.server_ip_entry.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        self.download_button = ctk.CTkButton(
            self.control_frame, text="Download Update", command=self.download_update_thread
        )
        self.download_button.grid(row=2, column=0, padx=15, pady=10, sticky="ew")

        self.deploy_button = ctk.CTkButton(
            self.control_frame, text="Deploy Update", command=self.deploy_update_thread
        )
        self.deploy_button.grid(row=3, column=0, padx=15, pady=10, sticky="ew")

        # --- Log Output (Bottom Frame) ---
        self.log_box = ctk.CTkTextbox(self.bottom_frame)
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.log_box.configure(state="disabled")

        # On startup, check for an already downloaded version.
        self.update_current_version_label()

        # And check the latest GitHub version.
        self.check_latest_version_thread()

    # --- Helper Methods ---
    def safe_log(self, message: str):
        """Append a message to the log box in a thread-safe way."""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def update_current_version_label(self):
        current_version = get_current_version()
        if current_version is None:
            current_version = "None"
        self.current_version_label.configure(text=f"Current Version: {current_version}")

    def update_latest_version_label(self, latest_version):
        if latest_version is None:
            latest_version = "Error"
        self.latest_version_label.configure(text=f"Latest Version: {latest_version}")

    # --- Thread Wrappers ---
    def download_update_thread(self):
        threading.Thread(target=self.download_update, daemon=True).start()

    def deploy_update_thread(self):
        threading.Thread(target=self.deploy_update, daemon=True).start()

    def check_latest_version_thread(self):
        threading.Thread(target=self.check_latest_version, daemon=True).start()

    def check_github_version_thread(self):
        threading.Thread(target=self.check_github_version, daemon=True).start()

    # --- Operation Methods ---
    def download_update(self):
        self.safe_log("Starting update download...")
        tag = download_update(log_callback=self.safe_log)
        if tag:
            self.safe_log(f"Downloaded update version: {tag}")
            self.update_current_version_label()
            self.check_latest_version()
        else:
            self.safe_log("Download update failed.")

    def deploy_update(self):
        self.safe_log("Starting deployment...")
        # Use the update folder based on the base directory (instead of a relative working dir)
        update_folder = os.path.join(get_update_dir(), "src")
        if not os.path.exists(update_folder):
            self.safe_log("Update not found. Please download the update first.")
            return
        server_ip = self.server_ip_entry.get().strip()
        if not server_ip:
            server_ip = discover_server()
            if server_ip is None:
                self.safe_log("Server could not be discovered. Provide a server IP manually.")
                return
        self.safe_log(f"Deploying update to server at {server_ip}...")
        tcp_client(server_ip, update_folder, log_callback=self.safe_log)

    def check_latest_version(self):
        self.safe_log("Checking latest GitHub version...")
        latest = get_latest_version()
        self.update_latest_version_label(latest)
        if latest:
            self.safe_log(f"Latest GitHub version is: {latest}")
        else:
            self.safe_log("Failed to fetch latest GitHub version.")

    def check_github_version(self):
        self.check_latest_version()

if __name__ == "__main__":
    app = UpdateApp()
    app.mainloop()
