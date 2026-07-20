import sys
import os
import queue
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# Import our modular packages
import main
import config
from logger_helper import logger

class TkinterConsoleHandler(logging.Handler):
    """
    Feeds log records dynamically into a thread-safe log queue.
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put_nowait(msg)
        except Exception:
            pass


class ToggleSwitch(tk.Canvas):
    """
    A custom Canvas-based toggle switch that behaves like a beautiful modern iOS/material switch.
    """
    def __init__(self, parent, width=42, height=22, variable=None, command=None, *args, **kwargs):
        self.bg_active = "#3b82f6"  # Beautiful vibrant blue
        self.bg_inactive = "#94a3b8"  # Slate-400
        self.fg_circle = "#ffffff"
        
        kwargs.update({
            "width": width,
            "height": height,
            "bd": 0,
            "highlightthickness": 0,
            "cursor": "hand2"
        })
        super().__init__(parent, *args, **kwargs)
        self.width = width
        self.height = height
        self.variable = variable if variable is not None else tk.BooleanVar(value=False)
        self.command = command
        
        self.bind("<Button-1>", self._toggle)
        self.draw()

    def _toggle(self, event=None):
        self.variable.set(not self.variable.get())
        self.draw()
        if self.command:
            self.command()

    def draw(self):
        self.delete("all")
        val = self.variable.get()
        r = self.height / 2
        
        # Pill Background Color
        bg = self.bg_active if val else self.bg_inactive
        
        # Match parent background dynamically
        try:
            self.configure(bg=self.master["bg"])
        except Exception:
            pass
            
        # Draw pill outline & fill using two circles and a rectangle
        self.create_oval(0, 0, self.height, self.height, fill=bg, outline=bg)
        self.create_oval(self.width - self.height, 0, self.width, self.height, fill=bg, outline=bg)
        self.create_rectangle(r, 0, self.width - r, self.height, fill=bg, outline=bg)
        
        # Circle Slider position
        margin = 2
        circle_size = self.height - (margin * 2)
        cx = self.width - r if val else r
        
        self.create_oval(cx - circle_size/2, margin, cx + circle_size/2, self.height - margin, fill=self.fg_circle, outline=self.fg_circle)


class ThemeToggleSwitch(tk.Canvas):
    """
    A premium theme-toggle switch drawing a sun on light blue in Light Mode, and a crescent moon with stars in Dark Mode.
    """
    def __init__(self, parent, width=65, height=28, variable=None, command=None, *args, **kwargs):
        kwargs.update({
            "width": width,
            "height": height,
            "bd": 0,
            "highlightthickness": 0,
            "cursor": "hand2"
        })
        super().__init__(parent, *args, **kwargs)
        self.width = width
        self.height = height
        self.variable = variable if variable is not None else tk.BooleanVar(value=False)
        self.command = command
        
        self.bind("<Button-1>", self._toggle)
        self.draw()

    def _toggle(self, event=None):
        self.variable.set(not self.variable.get())
        self.draw()
        if self.command:
            self.command()

    def draw(self):
        self.delete("all")
        is_dark = self.variable.get()
        r = self.height / 2
        
        # Match parent background
        try:
            self.configure(bg=self.master["bg"])
        except Exception:
            pass
            
        if not is_dark:
            # Light Mode (Light Blue Pill Background)
            bg = "#60a5fa"
            self.create_oval(0, 0, self.height, self.height, fill=bg, outline=bg)
            self.create_oval(self.width - self.height, 0, self.width, self.height, fill=bg, outline=bg)
            self.create_rectangle(r, 0, self.width - r, self.height, fill=bg, outline=bg)
            
            # Sun Circle on Left
            margin = 3
            circle_size = self.height - (margin * 2)
            cx = r
            self.create_oval(cx - circle_size/2, margin, cx + circle_size/2, self.height - margin, fill="#ffffff", outline="#ffffff")
            
            # Decorative sun ray sparkles/clouds on right
            self.create_oval(self.width - 22, 10, self.width - 18, 14, fill="#ffffff", outline="")
            self.create_oval(self.width - 14, 16, self.width - 10, 20, fill="#ffffff", outline="")
        else:
            # Dark Mode (Dark Midnight Background)
            bg = "#0f172a"
            self.create_oval(0, 0, self.height, self.height, fill=bg, outline=bg)
            self.create_oval(self.width - self.height, 0, self.width, self.height, fill=bg, outline=bg)
            self.create_rectangle(r, 0, self.width - r, self.height, fill=bg, outline=bg)
            
            # Yellow Crescent Moon on Right
            margin = 3
            circle_size = self.height - (margin * 2)
            cx = self.width - r
            
            self.create_oval(cx - circle_size/2, margin, cx + circle_size/2, self.height - margin, fill="#fef08a", outline="#fef08a")
            # Mask to overlay crescent
            self.create_oval(cx - circle_size/2 - 4, margin - 1, cx + circle_size/2 - 4, self.height - margin + 1, fill=bg, outline=bg)
            
            # Tiny yellow stars on the left
            self.create_oval(12, 12, 14, 14, fill="#fef08a", outline="")
            self.create_oval(20, 8, 22, 10, fill="#fef08a", outline="")
            self.create_oval(18, 18, 19, 19, fill="#fef08a", outline="")


class SimulatorControlUI:
    def __init__(self, root):
        self.root = root
        self.root.title(config.Config.get("ui", "title", default="Expleo PT Payment REST Simulator"))
        self.root.geometry("1150x720")
        
        # Load settings early to establish the theme configurations
        self.load_settings()
        is_dark = self.dark_mode_var.get()
        
        # Color Styling Theme Tokens
        if is_dark:
            self.bg_color = "#0f172a"
            self.panel_color = "#1e293b"
            self.accent_color = "#a78bfa"
            self.text_color = "#f8fafc"
            self.text_muted = "#94a3b8"
            self.border_color = "#334155"
            self.entry_bg = "#0f172a"
            self.entry_fg = "#f8fafc"
        else:
            self.bg_color = "#f1f5f9"
            self.panel_color = "#ffffff"
            self.accent_color = "#7c3aed"
            self.text_color = "#1e293b"
            self.text_muted = "#64748b"
            self.border_color = "#cbd5e1"
            self.entry_bg = "#f8fafc"
            self.entry_fg = "#1e293b"
            
        self.root.configure(bg=self.bg_color)
        
        # Window Icon Setup
        icon_path = os.path.join(os.path.dirname(__file__), "Template", "app_icon.png")
        if os.path.exists(icon_path):
            try:
                import ctypes
                myappid = 'expleo.upi.acmt.simulator.v2'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass
            
            try:
                icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(False, icon_img)
                self._icon_img = icon_img
            except Exception as e:
                logger.warning(f"Could not load taskbar icon image: {e}")
        
        # Broker engine instance reference
        self.broker_engine = None
        
        # Shared communication queue with StompBrokerEngine
        self.traffic_queue = queue.Queue()
        main.set_traffic_queue(self.traffic_queue)

        # Thread-safe logging queue for console updates
        self.log_queue = queue.Queue()
        
        # Local cache database of transactions shown in Treeview
        self.transactions_db = {}

        # Build UI Components in a side-by-side split layout
        self.create_header()
        
        # Main split container using PanedWindow for resizability and deterministic sizing
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.bg_color, bd=0, sashwidth=4)
        self.paned.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Left Panel (Settings, Controls, Logging)
        self.left_frame = tk.Frame(self.paned, bg=self.bg_color)
        self.paned.add(self.left_frame, width=470)
        
        # Right Panel (Recent Grid, XML Inspectors)
        self.right_frame = tk.Frame(self.paned, bg=self.bg_color)
        self.paned.add(self.right_frame, width=640)
        
        self.build_left_panel()
        self.build_right_panel()

        # Check background queue traffic events
        self.root.after(100, self.poll_traffic_queue)
        # Check background log events safely on GUI thread
        self.root.after(100, self.poll_logs_queue)

    def load_settings(self):
        self.host_var = tk.StringVar(value=config.Config.get("server", "api_host", default="127.0.0.1"))
        self.port_var = tk.StringVar(value=config.Config.get("server", "api_port", default="8080"))
        self.delay_var = tk.StringVar(value=str(config.Config.get("server", "response_delay_seconds", default=2.0)))
        
        raw_post = config.Config.get("server", "post_response_mode", default="201 - 000")
        raw_get = config.Config.get("server", "get_response_mode", default="200 - 000")
        raw_delete = config.Config.get("server", "delete_response_mode", default="200 - 022")

        def norm_post(val):
            if val == "201": return "201 - 000"
            if val == "202": return "202 - 000"
            if val == "400": return "400 - 001 - Signature calculation failed"
            if val == "401": return "401 - 002 - Invalid client credentials"
            if val == "404": return "404 - 012 - Transaction not found"
            if val == "409": return "409 - 013 - Duplicate transaction ID"
            if val == "500": return "500 - 999 - Internal system error"
            if val == "503": return "503 - 009 - Service Temporarily Unavailable"
            return val

        def norm_get(val):
            if val == "200": return "200 - 000"
            if val == "202": return "202 - 000"
            if val == "400": return "400 - 001 - Signature calculation failed"
            if val == "401": return "401 - 002 - Invalid client credentials"
            if val == "404": return "404 - 012 - Transaction not found"
            if val == "409": return "409 - 013 - Duplicate transaction ID"
            if val == "500": return "500 - 999 - Internal system error"
            if val == "503": return "503 - 009 - Service Temporarily Unavailable"
            return val

        def norm_delete(val):
            if val == "200": return "200 - 022"
            if val == "202": return "202 - 023"
            if val == "400": return "400 - 001 - Signature calculation failed"
            if val == "401": return "401 - 002 - Invalid client credentials"
            if val == "404": return "404 - 012 - Transaction not found"
            if val == "409": return "409 - 013 - Duplicate transaction ID"
            if val == "500": return "500 - 999 - Internal system error"
            if val == "503": return "503 - 009 - Service Temporarily Unavailable"
            return val

        self.post_response_var = tk.StringVar(value=norm_post(raw_post))
        self.get_response_var = tk.StringVar(value=norm_get(raw_get))
        self.delete_response_var = tk.StringVar(value=norm_delete(raw_delete))
        self.timeout_mode_var = tk.StringVar(value=config.Config.get("server", "timeout_mode", default="Sleep"))
        self.poll_success_var = tk.StringVar(value=str(config.Config.get("server", "poll_success_count", default=3)))
        self.retry_count_var = tk.StringVar(value=str(config.Config.get("server", "retry_count", default=3)))
        self.logging_enabled_var = tk.BooleanVar(value=config.Config.get("server", "logging_enabled", default=True))
        self.random_response_var = tk.BooleanVar(value=config.Config.get("server", "random_response_enabled", default=False))
        self.high_perf_var = tk.BooleanVar(value=config.Config.get("server", "high_perf", default=False))
        self.dark_mode_var = tk.BooleanVar(value=config.Config.get("ui", "theme", "dark_mode", default=False))

    def save_settings(self):
        config.Config.set("server", "api_host", value=self.host_var.get())
        config.Config.set("server", "api_port", value=self.port_var.get())
        config.Config.set("server", "response_delay_seconds", value=float(self.delay_var.get()) if self.delay_var.get().replace('.','',1).isdigit() else 0.0)
        config.Config.set("server", "post_response_mode", value=self.post_response_var.get())
        config.Config.set("server", "get_response_mode", value=self.get_response_var.get())
        config.Config.set("server", "delete_response_mode", value=self.delete_response_var.get())
        config.Config.set("server", "timeout_mode", value=self.timeout_mode_var.get())
        config.Config.set("server", "poll_success_count", value=int(self.poll_success_var.get()) if self.poll_success_var.get().isdigit() else 3)
        config.Config.set("server", "retry_count", value=int(self.retry_count_var.get()) if self.retry_count_var.get().isdigit() else 3)
        config.Config.set("server", "logging_enabled", value=self.logging_enabled_var.get())
        config.Config.set("server", "random_response_enabled", value=self.random_response_var.get())
        config.Config.set("server", "high_perf", value=self.high_perf_var.get())
        config.Config.set("ui", "theme", "dark_mode", value=self.dark_mode_var.get())

    def create_header(self):
        self.header_frame = tk.Frame(self.root, bg=self.bg_color, pady=10, padx=20)
        self.header_frame.pack(fill="x")
        
        # Left Title
        self.title_lbl = tk.Label(self.header_frame, text="UAEIPP Buyer Participant Simulator", font=("Segoe UI", 16, "bold"), fg=self.accent_color, bg=self.bg_color)
        self.title_lbl.pack(side="left")
        
        # Right Status and Counters
        status_container = tk.Frame(self.header_frame, bg=self.bg_color)
        status_container.pack(side="right", pady=5)
        
        status_lbl_desc = tk.Label(status_container, text="Status: ", font=("Segoe UI", 10, "bold"), fg=self.text_color, bg=self.bg_color)
        status_lbl_desc.pack(side="left")
        
        self.status_val_lbl = tk.Label(status_container, text="● STOPPED", font=("Segoe UI", 10, "bold"), fg="#ef4444", bg=self.bg_color)
        self.status_val_lbl.pack(side="left")
        
        self.sep_lbl = tk.Label(status_container, text="  |  ", font=("Segoe UI", 10), fg=self.text_muted, bg=self.bg_color)
        self.sep_lbl.pack(side="left")
        
        self.stats_lbl = tk.Label(status_container, text="Total: 0  Success: 0  Errors: 0", font=("Segoe UI", 10, "bold"), fg=self.text_muted, bg=self.bg_color)
        self.stats_lbl.pack(side="left")

        # Theme Toggle Sep and Canvas
        self.theme_sep_lbl = tk.Label(status_container, text="  |  ", font=("Segoe UI", 10), fg=self.text_muted, bg=self.bg_color)
        self.theme_sep_lbl.pack(side="left")

        self.theme_lbl = tk.Label(status_container, text="Dark Theme" if self.dark_mode_var.get() else "Light Theme", font=("Segoe UI", 9, "bold"), fg=self.accent_color, bg=self.bg_color)
        self.theme_lbl.pack(side="left", padx=(0, 8))

        self.theme_toggle = ThemeToggleSwitch(status_container, variable=self.dark_mode_var, command=self.apply_theme)
        self.theme_toggle.pack(side="left")

    def build_left_panel(self):
        # Settings Card Panel
        card = tk.Frame(self.left_frame, bg=self.panel_color, bd=1, highlightbackground=self.border_color, highlightthickness=1, padx=15, pady=15)
        card.pack(fill="x", pady=(0, 10))
        
        # Header Label
        tk.Label(card, text="Verify Reserve Simulator Settings", font=("Segoe UI", 11, "bold"), fg=self.accent_color, bg=self.panel_color).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        entry_style = {
            "bg": self.entry_bg,
            "fg": self.entry_fg,
            "bd": 0,
            "highlightthickness": 1,
            "highlightbackground": self.border_color,
            "highlightcolor": self.accent_color,
            "insertbackground": self.entry_fg,
            "font": ("Segoe UI", 9)
        }

        # API Host/Port (Row 1)
        tk.Label(card, text="API Host : Port", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=1, column=0, sticky="w", pady=4)
        conn_frame = tk.Frame(card, bg=self.panel_color)
        conn_frame.grid(row=1, column=1, sticky="w", pady=4)
        
        self.host_entry = tk.Entry(conn_frame, textvariable=self.host_var, width=20, **entry_style)
        self.host_entry.pack(side="left", ipady=1)
        tk.Label(conn_frame, text=" : ", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.panel_color).pack(side="left", padx=2)
        self.port_entry = tk.Entry(conn_frame, textvariable=self.port_var, width=7, **entry_style)
        self.port_entry.pack(side="left", ipady=1)

        # POST Response (Row 2)
        tk.Label(card, text="POST Response", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=2, column=0, sticky="w", pady=4)
        self.configure_ttk_styles()
        post_values = [
            "201 - 000",
            "202 - 000",
            "400 - 001 - Signature calculation failed",
            "400 - 003 - Invalid Headers",
            "400 - 004 - Invalid Request Parameter",
            "400 - 005 - Idempotency Key Violation",
            "400 - 006 - Decryption failed",
            "401 - 002 - Invalid client credentials",
            "409 - 013 - Duplicate transaction ID",
            "500 - 999 - Internal system error",
            "503 - 009 - Service Temporarily Unavailable",
            "Timeout",
            "No Response"
        ]
        self.post_resp_menu = ttk.Combobox(card, textvariable=self.post_response_var, values=post_values, state="readonly", width=45)
        self.post_resp_menu.grid(row=2, column=1, sticky="w", pady=4)

        # GET Response (Row 3)
        tk.Label(card, text="GET Response (Poll)", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=3, column=0, sticky="w", pady=4)
        get_values = [
            "200 - 000",
            "202 - 000",
            "400 - 001 - Signature calculation failed",
            "400 - 003 - Invalid Headers",
            "400 - 005 - Idempotency Key Violation",
            "401 - 002 - Invalid client credentials",
            "404 - 012 - Transaction not found",
            "409 - 013 - Duplicate transaction ID",
            "500 - 999 - Internal system error",
            "503 - 009 - Service Temporarily Unavailable",
            "Timeout",
            "Timeout - Polling",
            "No Response"
        ]
        self.get_resp_menu = ttk.Combobox(card, textvariable=self.get_response_var, values=get_values, state="readonly", width=45)
        self.get_resp_menu.grid(row=3, column=1, sticky="w", pady=4)

        # DELETE Response (Row 4)
        tk.Label(card, text="DELETE Response", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=4, column=0, sticky="w", pady=4)
        delete_values = [
            "200 - 022",
            "200 - 024",
            "202 - 023",
            "202 - 025",
            "400 - 001 - Signature calculation failed",
            "400 - 003 - Invalid Headers",
            "400 - 004 - Invalid Request Parameter",
            "400 - 005 - Idempotency Key Violation",
            "400 - 006 - Decryption failed",
            "401 - 002 - Invalid client credentials",
            "404 - 012 - Transaction not found",
            "409 - 013 - Duplicate transaction ID",
            "500 - 999 - Internal system error",
            "503 - 009 - Service Temporarily Unavailable",
            "Timeout",
            "No Response"
        ]
        self.delete_resp_menu = ttk.Combobox(card, textvariable=self.delete_response_var, values=delete_values, state="readonly", width=45)
        self.delete_resp_menu.grid(row=4, column=1, sticky="w", pady=4)

        # Timeout Mode (Row 5)
        tk.Label(card, text="Timeout Mode", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=5, column=0, sticky="w", pady=4)
        self.timeout_menu = ttk.Combobox(card, textvariable=self.timeout_mode_var, values=["Sleep", "Never Respond", "Close Connection"], state="readonly", width=25)
        self.timeout_menu.grid(row=5, column=1, sticky="w", pady=4)

        # Poll Count / Retry Count (Row 6)
        tk.Label(card, text="Poll Limit / Retries", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=6, column=0, sticky="w", pady=4)
        counts_frame = tk.Frame(card, bg=self.panel_color)
        counts_frame.grid(row=6, column=1, sticky="w", pady=4)
        self.poll_entry = tk.Entry(counts_frame, textvariable=self.poll_success_var, width=8, **entry_style)
        self.poll_entry.pack(side="left", ipady=1)
        tk.Label(counts_frame, text=" / ", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.panel_color).pack(side="left", padx=2)
        self.retry_entry = tk.Entry(counts_frame, textvariable=self.retry_count_var, width=8, **entry_style)
        self.retry_entry.pack(side="left", ipady=1)

        # Delay (Row 7)
        tk.Label(card, text="Delay (seconds)", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=7, column=0, sticky="w", pady=4)
        self.delay_entry = tk.Entry(card, textvariable=self.delay_var, width=10, **entry_style)
        self.delay_entry.grid(row=7, column=1, sticky="w", pady=4, ipady=1)

        # Options Toggles (Row 8)
        tk.Label(card, text="Options", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=8, column=0, sticky="w", pady=6)
        opts_frame = tk.Frame(card, bg=self.panel_color)
        opts_frame.grid(row=8, column=1, sticky="w", pady=6)
        
        self.logging_chk = ToggleSwitch(opts_frame, variable=self.logging_enabled_var, command=self.save_settings)
        self.logging_chk.pack(side="left")
        self.logging_lbl = tk.Label(opts_frame, text="Log", font=("Segoe UI", 8, "bold"), fg=self.text_color, bg=self.panel_color)
        self.logging_lbl.pack(side="left", padx=(5, 10))

        self.random_chk = ToggleSwitch(opts_frame, variable=self.random_response_var, command=self.save_settings)
        self.random_chk.pack(side="left")
        self.random_lbl = tk.Label(opts_frame, text="Rand", font=("Segoe UI", 8, "bold"), fg=self.text_color, bg=self.panel_color)
        self.random_lbl.pack(side="left", padx=(5, 10))

        self.perf_chk = ToggleSwitch(opts_frame, variable=self.high_perf_var, command=self.save_settings)
        self.perf_chk.pack(side="left")
        self.perf_lbl = tk.Label(opts_frame, text="Hi-Perf", font=("Segoe UI", 8, "bold"), fg=self.text_color, bg=self.panel_color)
        self.perf_lbl.pack(side="left", padx=(5, 0))

        # UI display toggles for grid and inspector panels (Row 9)
        tk.Label(card, text="Display Panels", font=("Segoe UI", 9), fg=self.text_color, bg=self.panel_color).grid(row=9, column=0, sticky="w", pady=6)
        toggles_frame = tk.Frame(card, bg=self.panel_color)
        toggles_frame.grid(row=9, column=1, sticky="w", pady=6)
        
        self.show_tracker_var = tk.BooleanVar(value=True)
        self.show_inspector_var = tk.BooleanVar(value=True)
        
        self.tracker_chk = ToggleSwitch(toggles_frame, variable=self.show_tracker_var, command=self.toggle_panels_action)
        self.tracker_chk.pack(side="left")
        
        self.tracker_lbl = tk.Label(toggles_frame, text="Recent Tracker", font=("Segoe UI", 8, "bold"), fg=self.text_color, bg=self.panel_color)
        self.tracker_lbl.pack(side="left", padx=(5, 15))
        
        self.inspector_chk = ToggleSwitch(toggles_frame, variable=self.show_inspector_var, command=self.toggle_panels_action)
        self.inspector_chk.pack(side="left")
        
        self.inspector_lbl = tk.Label(toggles_frame, text="JSON Inspector", font=("Segoe UI", 8, "bold"), fg=self.text_color, bg=self.panel_color)
        self.inspector_lbl.pack(side="left", padx=(5, 0))

        # Button Panel
        btn_frame = tk.Frame(self.left_frame, bg=self.bg_color)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.start_btn = tk.Button(btn_frame, text="▶ Start Simulator", font=("Segoe UI", 9, "bold"), bg="#10b981", fg="white", bd=0, activebackground="#059669", cursor="hand2", padx=15, pady=6, command=self.start_simulator_action)
        self.start_btn.pack(side="left", padx=(0, 10))
        
        self.stop_btn = tk.Button(btn_frame, text="■ Stop Simulator", font=("Segoe UI", 9, "bold"), bg="#cbd5e1", fg=self.text_muted, bd=0, activebackground="#cbd5e1", state="disabled", cursor="arrow", padx=15, pady=6, command=self.stop_simulator_action)
        self.stop_btn.pack(side="left")

        # Console Frame
        console_frame = tk.Frame(self.left_frame, bg=self.bg_color)
        console_frame.pack(fill="both", expand=True)
        
        log_header = tk.Frame(console_frame, bg=self.bg_color)
        log_header.pack(fill="x", pady=(0, 3))
        tk.Label(log_header, text="System Activity Log", font=("Segoe UI", 10, "bold"), fg=self.text_color, bg=self.bg_color).pack(side="left")
        
        clear_btn = tk.Button(log_header, text="Clear Logs", font=("Segoe UI", 8, "bold"), bg="#cbd5e1", fg=self.text_color, bd=0, activebackground="#94a3b8", cursor="hand2", padx=8, pady=2, command=self.clear_logs_action)
        clear_btn.pack(side="right")

        # Log text container with vertical scrollbar
        console_container = tk.Frame(console_frame, bg="#0f172a", bd=1, relief="solid")
        console_container.pack(fill="both", expand=True)

        self.log_textbox = tk.Text(console_container, bg="#0f172a", fg="#38bdf8", insertbackground="#ffffff", font=("Consolas", 8), bd=0, highlightthickness=0, padx=6, pady=6)
        self.log_textbox.pack(side="left", fill="both", expand=True)
        self.log_textbox.config(state="disabled")
        
        console_scroll = ttk.Scrollbar(console_container, orient="vertical", command=self.log_textbox.yview)
        self.log_textbox.configure(yscrollcommand=console_scroll.set)
        console_scroll.pack(side="right", fill="y")
        
        # Route standard logs to scrolling Activity Log console safely via queue
        handler = TkinterConsoleHandler(self.log_queue)
        logger.addHandler(handler)

    def build_right_panel(self):
        # Vertical split container for right panel resizability and deterministic layouts
        self.right_paned = tk.PanedWindow(self.right_frame, orient=tk.VERTICAL, bg=self.bg_color, bd=0, sashwidth=4)
        self.right_paned.pack(fill="both", expand=True)

        # Transaction grid layout (Recent items)
        self.grid_frame = tk.Frame(self.right_paned, bg=self.panel_color, bd=1, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=10)
        self.right_paned.add(self.grid_frame, minsize=180, height=270)
        
        # Grid Header with Clear option
        grid_header = tk.Frame(self.grid_frame, bg=self.panel_color)
        grid_header.pack(fill="x", pady=(0, 5))
        
        tk.Label(grid_header, text="Recent Queue Messages (Real-Time Tracker)", font=("Segoe UI", 10, "bold"), fg=self.accent_color, bg=self.panel_color).pack(side="left")
        
        clear_messages_btn = tk.Button(grid_header, text="Clear Tracker", font=("Segoe UI", 8, "bold"), bg="#cbd5e1", fg=self.text_color, bd=0, activebackground="#94a3b8", cursor="hand2", padx=8, pady=2, command=self.clear_tracker_action)
        clear_messages_btn.pack(side="right")
        
        # Scrollable Treeview
        tree_container = tk.Frame(self.grid_frame)
        tree_container.pack(fill="both", expand=True)
        
        # Configure initial TTK styles
        self.configure_ttk_styles()
        
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(tree_container, columns=("Timestamp", "Queue", "BizMsgIdr", "MsgId", "Status"), show="headings", style="Custom.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Define Columns (With dynamic Timestamp and generic column sorting)
        self.tree.heading("Timestamp", text="Timestamp", command=lambda: self.sort_column("Timestamp", False))
        self.tree.heading("Queue", text="Source", command=lambda: self.sort_column("Queue", False))
        self.tree.heading("BizMsgIdr", text="Correlation ID", command=lambda: self.sort_column("BizMsgIdr", False))
        self.tree.heading("MsgId", text="Message ID", command=lambda: self.sort_column("MsgId", False))
        self.tree.heading("Status", text="Status", command=lambda: self.sort_column("Status", False))
        
        self.tree.column("Timestamp", width=120, anchor="center")
        self.tree.column("Queue", width=150, anchor="w")
        self.tree.column("BizMsgIdr", width=130, anchor="w")
        self.tree.column("MsgId", width=130, anchor="w")
        self.tree.column("Status", width=100, anchor="center")
        
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Grid Select Binding
        self.tree.bind("<<TreeviewSelect>>", self.on_grid_select)

        # XML Payload Inspector Tabs
        self.inspector_frame = tk.Frame(self.right_paned, bg=self.panel_color, bd=1, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=10)
        self.right_paned.add(self.inspector_frame, minsize=200, height=360)
        
        # Inspector Header with Clear option
        inspector_header = tk.Frame(self.inspector_frame, bg=self.panel_color)
        inspector_header.pack(fill="x", pady=(0, 5))
        
        tk.Label(inspector_header, text="JSON Payload Inspector", font=("Segoe UI", 10, "bold"), fg=self.accent_color, bg=self.panel_color).pack(side="left")
        
        clear_inspector_btn = tk.Button(inspector_header, text="Clear Inspector", font=("Segoe UI", 8, "bold"), bg="#cbd5e1", fg=self.text_color, bd=0, activebackground="#94a3b8", cursor="hand2", padx=8, pady=2, command=self.clear_inspector_action)
        clear_inspector_btn.pack(side="right")
        
        self.inspector_notebook = ttk.Notebook(self.inspector_frame)
        self.inspector_notebook.pack(fill="both", expand=True)
        
        # Tab 1: Incoming Request (Scrollable)
        self.req_tab = tk.Frame(self.inspector_notebook, bg="#0f172a")
        
        req_scroll_frame = tk.Frame(self.req_tab, bg="#0f172a")
        req_scroll_frame.pack(fill="both", expand=True)
        
        self.req_text = tk.Text(req_scroll_frame, bg="#0f172a", fg="#22c55e", font=("Consolas", 9), bd=0, wrap="none")
        self.req_text.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=(5, 0))
        self.req_text.config(state="disabled")
        
        req_scroll_y = ttk.Scrollbar(req_scroll_frame, orient="vertical", command=self.req_text.yview)
        self.req_text.configure(yscrollcommand=req_scroll_y.set)
        req_scroll_y.pack(side="right", fill="y", pady=(5, 0))
        
        req_scroll_x = ttk.Scrollbar(self.req_tab, orient="horizontal", command=self.req_text.xview)
        self.req_text.configure(xscrollcommand=req_scroll_x.set)
        req_scroll_x.pack(fill="x", side="bottom", padx=5, pady=(0, 5))
        
        # Tab 2: Outgoing Response (Scrollable)
        self.resp_tab = tk.Frame(self.inspector_notebook, bg="#0f172a")
        
        resp_scroll_frame = tk.Frame(self.resp_tab, bg="#0f172a")
        resp_scroll_frame.pack(fill="both", expand=True)
        
        self.resp_text = tk.Text(resp_scroll_frame, bg="#0f172a", fg="#c084fc", font=("Consolas", 9), bd=0, wrap="none")
        self.resp_text.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=(5, 0))
        self.resp_text.config(state="disabled")
        
        resp_scroll_y = ttk.Scrollbar(resp_scroll_frame, orient="vertical", command=self.resp_text.yview)
        self.resp_text.configure(yscrollcommand=resp_scroll_y.set)
        resp_scroll_y.pack(side="right", fill="y", pady=(5, 0))
        
        resp_scroll_x = ttk.Scrollbar(self.resp_tab, orient="horizontal", command=self.resp_text.xview)
        self.resp_text.configure(xscrollcommand=resp_scroll_x.set)
        resp_scroll_x.pack(fill="x", side="bottom", padx=5, pady=(0, 5))
        
        self.inspector_notebook.add(self.req_tab, text=" Incoming JSON Request ")
        self.inspector_notebook.add(self.resp_tab, text=" Outgoing JSON Response ")

    def start_simulator_action(self):
        # Save inputs
        self.save_settings()
        
        host = self.host_var.get()
        port = self.port_var.get()

        logger.info(f"Initiating background FastAPI server...")
        
        # Reset counters
        main.reset_stats()
        self.update_gui_stats({"total": 0, "processed": 0, "errors": 0})
        
        # Clear database and list
        self.transactions_db.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Start FastAPI Engine
        self.broker_engine = main.FastAPIServerEngine(
            host=host,
            port=port
        )
        self.broker_engine.start()
        
        # Update UI Controls state
        self.status_val_lbl.config(text="● RUNNING", fg="#10b981")
        self.start_btn.config(bg="#cbd5e1", fg=self.text_muted, state="disabled", cursor="arrow")
        self.stop_btn.config(bg="#ef4444", fg="white", state="normal", cursor="hand2")
        
        # Disable editing settings fields
        self.host_entry.config(state="disabled", disabledbackground=self.panel_color, disabledforeground=self.text_muted)
        self.port_entry.config(state="disabled", disabledbackground=self.panel_color, disabledforeground=self.text_muted)
        self.post_resp_menu.config(state="disabled")
        self.get_resp_menu.config(state="disabled")
        self.delete_resp_menu.config(state="disabled")
        self.timeout_menu.config(state="disabled")
        self.poll_entry.config(state="disabled", disabledbackground=self.panel_color, disabledforeground=self.text_muted)
        self.retry_entry.config(state="disabled", disabledbackground=self.panel_color, disabledforeground=self.text_muted)
        self.delay_entry.config(state="disabled", disabledbackground=self.panel_color, disabledforeground=self.text_muted)
        
        logger.info("FastAPI simulator started successfully.")

    def stop_simulator_action(self):
        if self.broker_engine:
            logger.info("Stopping FastAPI server...")
            self.broker_engine.stop()
            self.broker_engine = None
            
        # Re-enable inputs
        self.host_entry.config(state="normal")
        self.port_entry.config(state="normal")
        self.post_resp_menu.config(state="readonly")
        self.get_resp_menu.config(state="readonly")
        self.delete_resp_menu.config(state="readonly")
        self.timeout_menu.config(state="readonly")
        self.poll_entry.config(state="normal")
        self.retry_entry.config(state="normal")
        self.delay_entry.config(state="normal")
        
        # Update UI Controls state
        self.status_val_lbl.config(text="● STOPPED", fg="#ef4444")
        self.start_btn.config(bg="#10b981", fg="white", state="normal", cursor="hand2")
        self.stop_btn.config(bg="#cbd5e1", fg=self.text_muted, state="disabled", cursor="arrow")
        
        logger.info("FastAPI simulator stopped successfully.")

    def clear_logs_action(self):
        self.log_textbox.config(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.config(state="disabled")
        
        main.reset_stats()
        self.update_gui_stats({"total": 0, "processed": 0, "errors": 0})
        
        # Clear list
        self.transactions_db.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
            
    def clear_tracker_action(self):
        self.tree.delete(*self.tree.get_children())
        self.transactions_db.clear()
        self.clear_inspector_action()
        logger.info("Real-time transaction tracker cleared.")

    def clear_inspector_action(self):
        self.req_text.config(state="normal")
        self.req_text.delete("1.0", tk.END)
        self.req_text.insert(tk.END, "<!-- Empty -->")
        self.req_text.config(state="disabled")
        
        self.resp_text.config(state="normal")
        self.resp_text.delete("1.0", tk.END)
        self.resp_text.insert(tk.END, "<!-- Empty -->")
        self.resp_text.config(state="disabled")
        logger.info("XML payload inspector cleared.")

    def sort_column(self, col, reverse):
        # Retrieve all items from the Treeview
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        
        # Sort items in-place
        l.sort(reverse=reverse)
        
        # Re-arrange sorted rows
        for index, (val, k) in enumerate(l):
            self.tree.move(k, "", index)
            
        # Bind header to toggle order on next click
        self.tree.heading(col, command=lambda _col=col: self.sort_column(_col, not reverse))
        logger.info(f"Treeview sorted by {col} (reverse={reverse})")

    def toggle_panels_action(self):
        show_tracker = self.show_tracker_var.get()
        show_inspector = self.show_inspector_var.get()
        
        # Hide panes first safely
        try:
            self.right_paned.forget(self.grid_frame)
        except Exception:
            pass
            
        try:
            self.right_paned.forget(self.inspector_frame)
        except Exception:
            pass
            
        # Re-add only the active ones
        if show_tracker:
            self.right_paned.add(self.grid_frame, minsize=180, height=270)
        if show_inspector:
            self.right_paned.add(self.inspector_frame, minsize=200, height=360)
            
        # logger.info(f"UI Layout panels updated: Tracker={show_tracker} | Inspector={show_inspector}")

    def configure_ttk_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
            
        # Configure TCombobox styling
        style.configure("TCombobox", 
                        fieldbackground=self.entry_bg, 
                        background=self.panel_color, 
                        foreground=self.text_color, 
                        arrowcolor=self.accent_color, 
                        bordercolor=self.border_color,
                        padding=4)
                        
        # Force readonly state to use vibrant high-contrast colors instead of default dim style
        style.map("TCombobox", 
                  fieldbackground=[("readonly", self.entry_bg), ("disabled", self.panel_color)],
                  foreground=[("readonly", self.text_color), ("disabled", self.text_muted)],
                  arrowcolor=[("readonly", self.accent_color)])
                  
        # Update dropdown option database for high-contrast colors
        self.root.option_add("*TCombobox*Listbox.background", self.entry_bg)
        self.root.option_add("*TCombobox*Listbox.foreground", self.text_color)
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.accent_color)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
                        
        # Configure TNotebook styling
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", 
                        background=self.panel_color, 
                        foreground=self.text_color, 
                        padding=[12, 4], 
                        font=("Segoe UI", 9))
        style.map("TNotebook.Tab", 
                  background=[("selected", self.accent_color)], 
                  foreground=[("selected", "#ffffff")])
                  
        # Treeview styling
        style.configure("Custom.Treeview", 
                        background=self.panel_color,
                        foreground=self.text_color,
                        fieldbackground=self.panel_color,
                        font=("Segoe UI", 9),
                        rowheight=20)
        style.configure("Custom.Treeview.Heading", 
                        background=self.bg_color,
                        foreground=self.text_color,
                        bordercolor=self.border_color,
                        font=("Segoe UI", 9, "bold"))

    def apply_theme(self):
        is_dark = self.dark_mode_var.get()
        
        # 1. Update theme color tokens
        if is_dark:
            self.bg_color = "#0f172a"
            self.panel_color = "#1e293b"
            self.accent_color = "#a78bfa"
            self.text_color = "#f8fafc"
            self.text_muted = "#94a3b8"
            self.border_color = "#334155"
            self.entry_bg = "#0f172a"
            self.entry_fg = "#f8fafc"
            self.theme_lbl.config(text="Dark Theme", fg="#a78bfa")
        else:
            self.bg_color = "#f1f5f9"
            self.panel_color = "#ffffff"
            self.accent_color = "#7c3aed"
            self.text_color = "#1e293b"
            self.text_muted = "#64748b"
            self.border_color = "#cbd5e1"
            self.entry_bg = "#f8fafc"
            self.entry_fg = "#1e293b"
            self.theme_lbl.config(text="Light Theme", fg="#7c3aed")
            
        # Update root background
        self.root.configure(bg=self.bg_color)
        
        # Configure TTK styles dynamically
        self.configure_ttk_styles()
        
        # Traverse and update widget colors recursively
        self.update_widget_colors(self.root)
        
        # Redraw all toggle canvases to match new parent backgrounds
        for widget in [self.tracker_chk, self.inspector_chk, self.perf_chk, self.theme_toggle]:
            if hasattr(widget, "draw"):
                widget.draw()
                
        # Save dark mode choice
        self.save_settings()
        logger.info(f"UI Theme updated to {'Dark' if is_dark else 'Light'} Mode.")

    def update_widget_colors(self, widget):
        widget_type = widget.winfo_class()
        
        # Skip canvases that handle their own drawing
        if hasattr(widget, "draw"):
            return
            
        try:
            if widget_type in ("Frame", "LabelFrame", "Panedwindow"):
                # Handle layout elements vs card widgets
                if widget in (self.left_frame, self.right_frame, self.right_paned, self.paned):
                    widget.configure(bg=self.bg_color)
                # Check for header frame or console frame backgrounds
                elif widget.master == self.root or widget == self.left_frame or widget == self.right_frame:
                    widget.configure(bg=self.bg_color)
                else:
                    widget.configure(bg=self.panel_color)
                    
            elif widget_type == "Label":
                # Check for special label text matches or locations
                text = widget.cget("text")
                if widget == self.title_lbl:
                    widget.configure(bg=self.bg_color, fg=self.accent_color)
                elif widget.master == self.root or widget.master.winfo_class() == "Panedwindow":
                    widget.configure(bg=self.bg_color, fg=self.text_color)
                elif widget in (self.status_val_lbl, self.sep_lbl, self.stats_lbl, self.theme_sep_lbl, self.theme_lbl):
                    # These belong to the status container (which sits in the header_frame with self.bg_color)
                    widget.configure(bg=self.bg_color)
                    if widget == self.stats_lbl:
                        try:
                            t_val = int(widget.cget("text").split("Total: ")[1].split()[0])
                            widget.configure(fg=self.text_color if t_val > 0 else self.text_muted)
                        except Exception:
                            widget.configure(fg=self.text_muted)
                    elif widget == self.theme_lbl:
                        widget.configure(fg=self.accent_color)
                    elif widget == self.status_val_lbl:
                        # Keep running/stopped colors
                        pass
                    else:
                        widget.configure(fg=self.text_muted)
                elif "Recent Queue Messages" in text or "XML Payload Inspector" in text or "System Activity Log" in text:
                    # Section titles
                    widget.configure(bg=self.panel_color, fg=self.accent_color)
                elif widget.master.winfo_class() == "Frame" and widget.master.master == self.left_frame:
                    # Log header label
                    widget.configure(bg=self.bg_color, fg=self.text_color)
                else:
                    widget.configure(bg=self.panel_color, fg=self.text_color)
                    
            elif widget_type == "Entry":
                state = widget.cget("state")
                if state == "disabled":
                    widget.configure(bg=self.panel_color, fg=self.text_muted, disabledbackground=self.panel_color, disabledforeground=self.text_muted, readonlybackground=self.panel_color, highlightbackground=self.border_color)
                else:
                    widget.configure(bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg, highlightbackground=self.border_color)
                    
            elif widget_type == "Button":
                text = widget.cget("text")
                if "Start" in text:
                    widget.configure(bg="#10b981", activebackground="#059669")
                elif "Stop" in text:
                    if widget.cget("state") == "disabled":
                        widget.configure(bg=self.border_color, fg=self.text_muted)
                    else:
                        widget.configure(bg="#ef4444", fg="white", activebackground="#dc2626")
                else:
                    # Clear Buttons, etc.
                    widget.configure(bg=self.border_color, fg=self.text_color, activebackground=self.accent_color)
                    
            elif widget_type == "Text":
                if widget == self.log_textbox:
                    # Keep terminal log styling consistent (always dark tech theme)
                    widget.configure(bg="#0f172a", fg="#38bdf8")
                else:
                    # XML textboxes
                    widget.configure(
                        bg="#0f172a" if self.dark_mode_var.get() else "#f8fafc",
                        fg="#34d399" if self.dark_mode_var.get() else "#16a34a",
                        insertbackground="#ffffff" if self.dark_mode_var.get() else "#000000"
                    )
                    
        except Exception:
            pass
            
        # Recursive traverse
        for child in widget.winfo_children():
            self.update_widget_colors(child)

    def update_gui_stats(self, stats_dict):
        total = stats_dict.get("total", 0)
        success = stats_dict.get("processed", 0)
        errors = stats_dict.get("errors", 0)
        self.stats_lbl.config(
            text=f"Total: {total}  Success: {success}  Errors: {errors}",
            fg=self.text_color if total > 0 else self.text_muted
        )

    def on_grid_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        tx_data = self.transactions_db.get(item_id)
        if not tx_data:
            return
        
        # Show Incoming XML
        self.req_text.config(state="normal")
        self.req_text.delete("1.0", tk.END)
        self.req_text.insert(tk.END, tx_data.get("request_xml", ""))
        self.req_text.config(state="disabled")
        
        # Show Outgoing XML
        self.resp_text.config(state="normal")
        self.resp_text.delete("1.0", tk.END)
        self.resp_text.insert(tk.END, tx_data.get("response_xml", ""))
        self.resp_text.config(state="disabled")

    def poll_traffic_queue(self):
        try:
            while True:
                event = self.traffic_queue.get_nowait()
                if isinstance(event, dict):
                    # Process statistics
                    if "stats" in event:
                        self.update_gui_stats(event["stats"])
                    
                    # Process Treeview grid updates
                    if "request_xml" in event and "response_xml" in event:
                        timestamp = event.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        in_q = event.get("input_queue", "N/A")
                        corr_id = event.get("biz_msg_idr", "N/A")
                        msg_id = event.get("msg_id", "N/A")
                        status = event.get("status", "VERIFIED")
                        
                        item_id = self.tree.insert("", 0, values=(timestamp, in_q, corr_id, msg_id, status))
                        self.transactions_db[item_id] = event
                        
                        # Auto-select the newly added item to inspect it instantly!
                        self.tree.selection_set(item_id)
                        
                self.traffic_queue.task_done()
        except queue.Empty:
            pass
        self.root.after(100, self.poll_traffic_queue)

    def poll_logs_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_textbox.config(state="normal")
                self.log_textbox.insert(tk.END, msg + "\n")
                self.log_textbox.see(tk.END)
                self.log_textbox.config(state="disabled")
                self.log_queue.task_done()
        except queue.Empty:
            pass
        self.root.after(100, self.poll_logs_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = SimulatorControlUI(root)
    
    def on_closing():
        if app.broker_engine:
            app.broker_engine.stop()
        root.destroy()
        sys.exit(0)
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()