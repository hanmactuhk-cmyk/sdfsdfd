import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    APP_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_client import WebhookClient, WebhookError
from workflow import save as save_workflow, validate as validate_workflow


class Studio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("G-Labs Studio")
        self.geometry("1180x760")
        self.minsize(900, 600)
        self.configure(bg="#111827")
        self._setup_style()
        self._build()

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background="#111827", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 10), background="#1f2937", foreground="#e5e7eb")
        style.map("TNotebook.Tab", background=[("selected", "#374151")])
        style.configure("TFrame", background="#111827")
        style.configure("Card.TFrame", background="#1f2937")
        style.configure("TLabel", background="#111827", foreground="#e5e7eb")
        style.configure("Card.TLabel", background="#1f2937", foreground="#e5e7eb")
        style.configure("TButton", padding=(12, 8))
        style.configure("TEntry", fieldbackground="#0f172a", foreground="#e5e7eb")
        style.configure("TCombobox", fieldbackground="#0f172a", foreground="#111827")

    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        notebook.add(self._studio_tab(notebook), text="Studio")
        notebook.add(self._workflow_tab(notebook), text="Workflow")
        notebook.add(self._webhook_tab(notebook), text="Webhook")
        notebook.add(self._settings_tab(notebook), text="Settings")

    def _studio_tab(self, parent):
        frame = ttk.Frame(parent)
        tk.Label(frame, text="G-Labs Studio", bg="#111827", fg="#f9fafb", font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=24, pady=(24, 4))
        tk.Label(frame, text="Authorized Webhook + Workflow desktop workspace", bg="#111827", fg="#9ca3af", font=("Segoe UI", 11)).pack(anchor="w", padx=24, pady=(0, 20))
        card = tk.Frame(frame, bg="#1f2937", bd=0, highlightthickness=1, highlightbackground="#374151")
        card.pack(fill="x", padx=24)
        for name in ("Image", "Video", "Grok", "Meta AI", "OpenAI", "Upscale", "Workflow Engine"):
            row = tk.Frame(card, bg="#1f2937")
            row.pack(fill="x", padx=18, pady=8)
            tk.Label(row, text="●", fg="#22c55e", bg="#1f2937", font=("Segoe UI", 11)).pack(side="left")
            tk.Label(row, text=name, fg="#f3f4f6", bg="#1f2937", font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
            tk.Label(row, text="Ready for configured Webhook server", fg="#9ca3af", bg="#1f2937").pack(side="right")
        return frame

    def _workflow_tab(self, parent):
        frame = ttk.Frame(parent)
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", padx=12, pady=12)
        ttk.Button(toolbar, text="Open Flow", command=self.open_flow).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Save Flow", command=self.save_flow).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Validate", command=self.validate_flow).pack(side="left", padx=4)
        self.flow_status = tk.StringVar(value="No workflow loaded")
        ttk.Label(toolbar, textvariable=self.flow_status).pack(side="left", padx=16)
        self.flow_text = tk.Text(frame, bg="#0b1220", fg="#e5e7eb", insertbackground="#fff", undo=True, wrap="none")
        self.flow_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        return frame

    def _webhook_tab(self, parent):
        frame = ttk.Frame(parent)
        top = ttk.Frame(frame)
        top.pack(fill="x", padx=12, pady=12)
        ttk.Label(top, text="Server URL").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.url_var = tk.StringVar(value="http://127.0.0.1:8765")
        ttk.Entry(top, textvariable=self.url_var, width=45).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(top, text="API Key").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.key_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.key_var, show="*", width=45).grid(row=1, column=1, sticky="ew", padx=4)
        top.columnconfigure(1, weight=1)
        actions = ttk.Frame(frame)
        actions.pack(fill="x", padx=12, pady=4)
        ttk.Button(actions, text="Check Health", command=self.check_health).pack(side="left", padx=4)
        self.kind_var = tk.StringVar(value="image")
        ttk.Combobox(actions, textvariable=self.kind_var, values=("image", "video", "grok", "meta", "openai", "upscale"), state="readonly", width=12).pack(side="left", padx=4)
        ttk.Button(actions, text="Submit", command=self.submit).pack(side="left", padx=4)
        ttk.Button(actions, text="Clear Log", command=lambda: self.log.delete("1.0", "end")).pack(side="left", padx=4)
        ttk.Label(frame, text="Prompt or JSON payload").pack(anchor="w", padx=16, pady=(12, 4))
        self.prompt = tk.Text(frame, height=10, bg="#0b1220", fg="#e5e7eb", insertbackground="#fff", wrap="word")
        self.prompt.pack(fill="x", padx=12)
        ttk.Label(frame, text="Response log").pack(anchor="w", padx=16, pady=(12, 4))
        self.log = tk.Text(frame, bg="#0b1220", fg="#a7f3d0", insertbackground="#fff", wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        return frame

    def _settings_tab(self, parent):
        frame = ttk.Frame(parent)
        tk.Label(frame, text="G-Labs Studio Settings", bg="#111827", fg="#f9fafb", font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=24, pady=24)
        tk.Label(frame, text="Credentials remain local to this application.\nUse the authorized Webhook API for external generation services.", bg="#111827", fg="#9ca3af", justify="left", font=("Segoe UI", 11)).pack(anchor="w", padx=24)
        return frame

    def _client(self):
        return WebhookClient(self.url_var.get(), self.key_var.get())

    def _append_log(self, value):
        self.log.insert("end", value + "\n\n")
        self.log.see("end")

    def check_health(self):
        def worker():
            try:
                result = self._client().health()
                text = json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as exc:
                text = str(exc)
            self.after(0, lambda: self._append_log(text))
        threading.Thread(target=worker, daemon=True).start()

    def submit(self):
        raw = self.prompt.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("G-Labs Studio", "Enter a prompt or JSON payload first.")
            return
        try:
            payload = json.loads(raw) if raw.startswith("{") else {"prompt": raw}
        except json.JSONDecodeError as exc:
            messagebox.showerror("Invalid JSON", str(exc))
            return
        kind = self.kind_var.get()
        def worker():
            try:
                result = self._client().generate(kind, payload)
                text = json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as exc:
                text = str(exc)
            self.after(0, lambda: self._append_log(text))
        threading.Thread(target=worker, daemon=True).start()

    def open_flow(self):
        path = filedialog.askopenfilename(title="Open Workflow", filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            self.flow_text.delete("1.0", "end")
            self.flow_text.insert("1.0", text)
            self.flow_status.set(path)
            self.validate_flow()
        except Exception as exc:
            messagebox.showerror("Open error", str(exc))

    def save_flow(self):
        raw = self.flow_text.get("1.0", "end").strip()
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as exc:
            messagebox.showerror("Invalid JSON", str(exc))
            return
        path = filedialog.asksaveasfilename(title="Save Workflow", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            save_workflow(doc, path)
            self.flow_status.set(path)
        except Exception as exc:
            messagebox.showerror("Save error", str(exc))

    def validate_flow(self):
        raw = self.flow_text.get("1.0", "end").strip()
        if not raw:
            self.flow_status.set("No workflow loaded")
            return
        try:
            doc = json.loads(raw)
            errors, warnings = validate_workflow(doc)
            if errors:
                self.flow_status.set("INVALID | " + "; ".join(errors + warnings))
            elif warnings:
                self.flow_status.set("VALID WITH WARNINGS | " + "; ".join(warnings))
            else:
                self.flow_status.set("VALID | No issues")
        except Exception as exc:
            self.flow_status.set("JSON ERROR | " + str(exc))


if __name__ == "__main__":
    app = Studio()
    app.mainloop()
