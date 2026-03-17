import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import base64
import urllib.request
import urllib.error
import json
import os
from PIL import Image

# ── CONFIG ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = "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"        # 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
ENDPOINT     = "https://models.inference.ai.azure.com"
MODELS       = {
    "GPT-4o  (best accuracy)":     "gpt-4o",
    "GPT-4o mini  (faster, free)": "gpt-4o-mini",
}
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert automotive engine diagnostic AI. "
    "The user will provide a photo of a car engine bay. "
    "Carefully examine the image and:\n"
    "1. Identify the general engine type / make if visible.\n"
    "2. List any visible problems, damage, leaks, corrosion, worn parts, "
    "   missing components, or anything that looks abnormal.\n"
    "3. Rate the overall engine condition: Excellent / Good / Fair / Poor.\n"
    "4. Recommend next steps or repairs.\n"
    "Be concise, practical, and clear. Use simple language a car owner can understand."
)

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#00c6ff"
BG     = "#0f0f0f"
PANEL  = "#1a1a1a"
BORDER = "#2a2a2a"


# ── API ───────────────────────────────────────────────────────────────────────

def encode_image(path):
    ext = os.path.splitext(path)[1].lower()
    media_type = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), media_type


def analyze_engine(image_path, model):
    b64, media_type = encode_image(image_path)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                    {"type": "text", "text": "Please diagnose this engine."},
                ],
            },
        ],
        "max_tokens": 900,
        "temperature": 0.3,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ENDPOINT}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


# ── App ───────────────────────────────────────────────────────────────────────

class CarScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Engine Scanner AI")
        self.geometry("1000x740")
        self.minsize(820, 600)
        self.configure(fg_color=BG)

        self._image_path = None
        self._ctk_img = None

        # Fix: clean shutdown so mouse/keyboard never get stuck
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Fix: release any grabs when window loses focus
        self.bind("<FocusOut>", lambda e: self._safe_release_grab())

        self._build_ui()

    def _safe_release_grab(self):
        try:
            self.grab_release()
        except Exception:
            pass

    def _on_close(self):
        self._safe_release_grab()
        try:
            self.quit()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=66)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="ENGINE SCANNER AI",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=24)

        ctk.CTkLabel(
            header,
            text="GitHub Models  |  GPT-4o Vision",
            font=ctk.CTkFont(size=11),
            text_color="#555555",
        ).pack(side="left", padx=6)

        # Body
        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True, padx=20, pady=20)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.rowconfigure(3, weight=1)
        left.columnconfigure(0, weight=1)

        # Model selector
        model_frame = ctk.CTkFrame(left, fg_color=PANEL, corner_radius=10,
                                   border_width=1, border_color=BORDER)
        model_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            model_frame,
            text="Model",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#888888",
        ).pack(anchor="w", padx=14, pady=(10, 2))

        self.model_var = ctk.StringVar(value=list(MODELS.keys())[0])
        self.model_menu = ctk.CTkOptionMenu(
            model_frame,
            values=list(MODELS.keys()),
            variable=self.model_var,
            font=ctk.CTkFont(size=12),
            fg_color="#252525",
            button_color="#333333",
            button_hover_color="#3a3a3a",
            dropdown_fg_color="#1e1e1e",
            text_color="#dddddd",
            corner_radius=8,
            dynamic_resizing=False,
            width=260,
        )
        self.model_menu.pack(padx=14, pady=(0, 12), fill="x")

        # Upload button
        ctk.CTkButton(
            left,
            text="Upload Engine Photo",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=PANEL,
            hover_color="#252525",
            border_width=1,
            border_color=ACCENT,
            text_color=ACCENT,
            command=self._choose_image,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.file_label = ctk.CTkLabel(
            left,
            text="No file selected",
            font=ctk.CTkFont(size=11),
            text_color="#555555",
            anchor="w",
        )
        self.file_label.grid(row=2, column=0, sticky="w", pady=(0, 10))

        # Image preview
        self.preview_frame = ctk.CTkFrame(
            left, fg_color=PANEL, corner_radius=10,
            border_width=1, border_color=BORDER,
        )
        self.preview_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 14))

        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="No image loaded",
            font=ctk.CTkFont(size=12),
            text_color="#444444",
        )
        self.preview_label.pack(expand=True)

        # Scan button
        self.scan_btn = ctk.CTkButton(
            left,
            text="Run Scan",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=52,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color="#009ecc",
            text_color="#000000",
            command=self._start_scan,
        )
        self.scan_btn.grid(row=4, column=0, sticky="ew", pady=(0, 8))

        # Progress bar
        self.progress = ctk.CTkProgressBar(left, mode="indeterminate",
                                           height=5, corner_radius=4)
        self.progress.grid(row=5, column=0, sticky="ew")
        self.progress.grid_remove()

        # Status
        self.status_var = ctk.StringVar(value="Ready. Upload a photo to begin.")
        ctk.CTkLabel(
            left,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=10),
            text_color="#555555",
            wraplength=270,
            anchor="w",
            justify="left",
        ).grid(row=6, column=0, sticky="w", pady=(6, 0))

    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        top = ctk.CTkFrame(right, fg_color=BG)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text="DIAGNOSTIC REPORT",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#444444",
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top,
            text="Copy",
            font=ctk.CTkFont(size=11),
            width=76, height=28,
            corner_radius=6,
            fg_color=PANEL,
            hover_color="#252525",
            text_color="#888888",
            border_width=1,
            border_color=BORDER,
            command=self._copy_report,
        ).grid(row=0, column=1, sticky="e")

        self.result_text = ctk.CTkTextbox(
            right,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=PANEL,
            text_color="#dddddd",
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
            wrap="word",
            state="disabled",
        )
        self.result_text.grid(row=1, column=0, sticky="nsew")

        self._set_result("Awaiting scan...\n\nUpload an engine photo and press  Run Scan  to begin.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _choose_image(self):
        path = filedialog.askopenfilename(
            title="Select engine photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif"), ("All", "*.*")],
        )
        if not path:
            return
        self._image_path = path
        self.file_label.configure(text=f"  {os.path.basename(path)}", text_color="#888888")
        self._show_preview(path)
        self._set_result("Image loaded. Press  Run Scan  to analyse.")
        self.status_var.set("Image ready.")

    def _show_preview(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((300, 240), Image.LANCZOS)
            self._ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.preview_label.configure(image=self._ctk_img, text="")
        except Exception as e:
            self.status_var.set(f"Preview error: {e}")

    def _set_result(self, text):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", text)
        self.result_text.configure(state="disabled")

    def _append_result(self, text):
        self.result_text.configure(state="normal")
        self.result_text.insert("end", text)
        self.result_text.see("end")
        self.result_text.configure(state="disabled")

    def _copy_report(self):
        content = self.result_text.get("1.0", "end").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_var.set("Report copied to clipboard.")

    # ── Scan ──────────────────────────────────────────────────────────────────

    def _start_scan(self):
        if not self._image_path:
            messagebox.showwarning("No image", "Please upload an engine photo first.")
            return
        if GITHUB_TOKEN == "YOUR_GITHUB_TOKEN_HERE":
            messagebox.showerror(
                "Token missing",
                "Open car_scanner.py and replace YOUR_GITHUB_TOKEN_HERE "
                "with your GitHub personal access token.",
            )
            return

        selected_label = self.model_var.get()
        model_id = MODELS[selected_label]

        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.model_menu.configure(state="disabled")
        self.progress.grid()
        self.progress.start()
        self.status_var.set(f"Sending to {selected_label.split('(')[0].strip()}...")
        self._set_result(f"Scanning with {selected_label.split('(')[0].strip()}...\n\nPlease wait.")

        # Fix: use daemon thread so it dies with the app
        t = threading.Thread(target=self._run_scan, args=(model_id,), daemon=True)
        t.start()

    def _run_scan(self, model_id):
        try:
            diagnosis = analyze_engine(self._image_path, model_id)
            self.after(0, self._display_result, diagnosis)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            self.after(0, self._show_error, f"HTTP {e.code}:\n{body}")
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _display_result(self, text):
        self._set_result("")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("**", "#")):
                clean = stripped.lstrip("#* ").rstrip("*")
                self._append_result(f"\n-- {clean.upper()} --\n")
            else:
                self._append_result(line + "\n")
        self._append_result("\n---------------------------------\nScan complete.\n")
        self._stop_scan_ui()

    def _show_error(self, msg):
        self._set_result(f"ERROR\n\n{msg}")
        self._stop_scan_ui(failed=True)

    def _stop_scan_ui(self, failed=False):
        self.progress.stop()
        self.progress.grid_remove()
        self.scan_btn.configure(state="normal", text="Run Scan")
        self.model_menu.configure(state="normal")
        self.status_var.set("Scan failed." if failed else "Scan complete.")


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess, sys

    # Fix: set DPI awareness on Windows to prevent rendering/freeze issues
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = CarScannerApp()
    app.mainloop()
