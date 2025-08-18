import ctypes, utility
from ctypes import wintypes
from consts import *
import tkinter as tk
import time
import keyboard as kb

proc_name = "PowerWashSimulator.exe"
kernel32 = ctypes.windll.kernel32
pid = None
base_address = None
unityplayer_dll = None
gameassembly_dll = None
handle = None
menu_visible = True  # Track menu state

root = tk.Tk()
root.title("Trippy's Deluxe Washer")
root.geometry("400x220")
root.overrideredirect(True)
root.configure(bg="#333333")


can_fly = False
long_highlight = tk.BooleanVar() 

#cheat vars
flight_enabled = tk.BooleanVar()
original_gravity_bytes = None
instant_patch_active = tk.BooleanVar()
instant_patch_orig = None
instant_patch_oldprot = 0
instant_patch_addr = None  # will calculate later

class Tooltip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay  # delay in milliseconds before showing
        self.tipwindow = None
        self.id = None
        widget.bind("<Enter>", self.schedule)
        widget.bind("<Leave>", self.hide)
        widget.bind("<Motion>", self.move)

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show(self, event=None):
        if self.tipwindow:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#333333", foreground="white",
                        relief='solid', borderwidth=1,
                        font=("Arial", 9))
        label.pack(ipadx=5, ipady=3)


    def hide(self, event=None):
        self.unschedule()
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

    def move(self, event):
        if self.tipwindow:
            x = event.x_root + 20
            y = event.y_root + 10
            self.tipwindow.wm_geometry(f"+{x}+{y}")

def toggle_menu():
    global menu_visible
    if menu_visible:
        root.withdraw()  # Hide window
        menu_visible = False
    else:
        root.deiconify()  # Show window
        root.lift()  # Bring it to the front
        root.focus_force()  # Focus the window
        menu_visible = True

kb.add_hotkey("insert", toggle_menu)

def instant_clean():
    global instant_patch_orig, instant_patch_oldprot, instant_patch_addr
    if not instant_patch_addr:
        instant_patch_addr = gameassembly_dll + 0xAA9261
    patch_length = 0x18

    if not getattr(instant_clean, "active", False):  # track internal state
        instant_patch_orig = utility.nopBytes(handle, instant_patch_addr, patch_length)
        patch_bytes = b'\xA9\x00\x00\x00\x00'
        utility.patchBytes(handle, patch_bytes.hex(), instant_patch_addr, len(patch_bytes))
        remaining = patch_length - len(patch_bytes)
        if remaining > 0:
            utility.nopBytes(handle, instant_patch_addr + len(patch_bytes), remaining)
        instant_clean.active = True
        instant_patch_active.set(True)
        print("Instant clean patch applied")
    else:
        if instant_patch_orig:
            utility.patchBytes(handle, instant_patch_orig.hex(), instant_patch_addr, len(instant_patch_orig))
        instant_clean.active = False
        instant_patch_active.set(False)
        print("Instant clean patch removed")


def do_long_highlight():
    hdur_addr = gameassembly_dll + 0x0444F830
    hdur_offsets = [0x80,0xB8,0x10,0x0,0xB8,0x18,0xEC]
    addr = utility.findDMAddy(handle, hdur_addr, hdur_offsets)
    if not addr:
        return
    if long_highlight.get():
        value=99
    else:
        value=2.5
    kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), ctypes.byref(ctypes.c_float(value)), ctypes.sizeof(ctypes.c_float), None)

def do_flight():
    y_base_addr = unityplayer_dll + 0x01ACA028
    y_offsets = [0x390,0x250,0x28,0x3A8,0x140,0x28,0x154]
    addr = utility.findDMAddy(handle, y_base_addr, y_offsets)
    if not addr:
        print("Failed to resolve dynamic address")
        return
    buf = ctypes.c_float()
    bytesRead = ctypes.c_size_t()
    success = kernel32.ReadProcessMemory(handle,ctypes.c_void_p(addr),ctypes.byref(buf),ctypes.sizeof(buf),ctypes.byref(bytesRead))
    if success:
        print("Y:", buf.value)
        if kb.is_pressed("space"):
            kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), ctypes.byref(ctypes.c_float(buf.value+0.2)), ctypes.sizeof(ctypes.c_float), None)
        if kb.is_pressed("v"):
            kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), ctypes.byref(ctypes.c_float(buf.value-0.2)), ctypes.sizeof(ctypes.c_float), None)
    else:
        print("Failed to read memory for y_value")

def toggle_flight():
    global can_fly, original_gravity_bytes, gravity_addr
    gravity_addr = unityplayer_dll + 0x121148D
    if not can_fly:
        buf = (ctypes.c_char * 6)()
        bytesRead = ctypes.c_size_t()
        if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(gravity_addr), buf, 6, ctypes.byref(bytesRead)):
            original_gravity_bytes = bytes(buf)
            utility.nopBytes(handle, gravity_addr, 6)
            print("Flight enabled (gravity NOPed)")
        else:
            print("Failed to read original gravity bytes")
        can_fly = True
    else:
        if original_gravity_bytes:
            utility.patchBytes(handle, original_gravity_bytes.hex(), gravity_addr, 6)
            print("Flight disabled (gravity restored)")
        else:
            print("No original bytes stored, cannot restore")
        can_fly = False

def increase_money():
    money_base_addr = gameassembly_dll + 0x0440D410
    money_offsets = [0xB8, 0x18, 0xD8, 0xAE0, 0x98, 0xA0, 0x128]
    addr = utility.findDMAddy(handle, money_base_addr, money_offsets)
    if not addr:
        print("Failed to resolve dynamic address")
        return
    buf = ctypes.c_float()
    bytesRead = ctypes.c_size_t()
    if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(bytesRead)):
        print("Money:", buf.value)
        new_val = ctypes.c_float(buf.value + 50.0)
        kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), ctypes.byref(new_val), ctypes.sizeof(new_val), None)
    else:
        print("Failed to read memory for money")

def close_cheat():
    global gravity_addr, original_gravity_bytes, handle
    hdur_addr = gameassembly_dll + 0x0444F830
    hdur_offsets = [0x80,0xB8,0x10,0x0,0xB8,0x18,0xEC]
    addr = utility.findDMAddy(handle, hdur_addr, hdur_offsets)
    if not addr:
        return
    value = ctypes.c_float(2.5)
    kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), ctypes.byref(value), ctypes.sizeof(value), None)
    if original_gravity_bytes:
        utility.patchBytes(handle, original_gravity_bytes.hex(), gravity_addr, 6)
        print("Flight disabled (gravity restored)")
    kernel32.CloseHandle(handle)
    

def load_menu():
    global flight_enabled, esp_on, TRIGGER_HIGHLIGHT_ADDR
    flight_enabled = tk.BooleanVar(value=False)
    esp_on = tk.BooleanVar(value=False)                                                                                
    fly_toggle = tk.Checkbutton(root, text="Enable Flight", variable=flight_enabled,
	    font=("Arial", 10), command=toggle_flight, bg="#980ee9", fg="#fff", selectcolor="#000", activebackground="#980ee9", activeforeground="#000000", width=14)
    fly_toggle.place(relx=0.05, rely=0.2)
    long_highlight_toggle = tk.Checkbutton(root, text="Extra Long Highlight", variable=long_highlight,
	    font=("Arial", 10), bg="#980ee9", fg="#fff", selectcolor="#000", activebackground="#980ee9", activeforeground="#000000")
    long_highlight_toggle.place(relx=0.45, rely=0.2)
    add_money_btn = tk.Button(root, width=15, text="Increase Money", command=increase_money, bg="#980ee9", fg="#fff", relief="flat", font=("Arial", 12))
    add_money_btn.place(relx=0.05, rely=0.35)
    clean_btn = tk.Checkbutton(root, text="Instant Clean", variable=instant_patch_active, command=instant_clean, bg="#980ee9", fg="#fff", selectcolor="#000", relief="flat", font=("Arial", 12))
    clean_btn.place(relx=0.45, rely=0.35)
    
    Tooltip(clean_btn, "Automatically cleans surfaces instantly. (May lag game, May cause crashes)", delay=500)
    Tooltip(fly_toggle, "Simple fly: SPACE = go up, V = go down", delay=500)
    Tooltip(long_highlight_toggle, "Increases the highlight length to effectively make dirt ESP.", delay=500)
    Tooltip(add_money_btn, "Increases your money by 50. Must change money or reset game to see it in the menu.", delay=500)

    cheat_loop()


def attempt_inject():
    global pid, handle, base_address, unityplayer_dll, gameassembly_dll
    pid = utility.GetProcId(proc_name)
    if (pid == None):
        dbg_label.configure(text="Are you sure the game is running?")
    else:
        handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, 0, ctypes.wintypes.DWORD(pid))
        base_address = utility.GetModuleBaseAddress(pid, "PowerWashSimulator.exe")
        unityplayer_dll = utility.GetModuleBaseAddress(pid, "UnityPlayer.dll")
        gameassembly_dll = utility.GetModuleBaseAddress(pid, "GameAssembly.dll")
        dbg_label.configure(text="Succesfully Injected")
        time.sleep(0.5)
        dbg_label.destroy()
        inject_button.destroy()
        load_menu()

def cheat_loop():
    global can_fly, long_highlight
    if can_fly:
        do_flight()
    
    do_long_highlight()

    root.after(50, cheat_loop)



title_bar = tk.Frame(root, bg="#980ee9", relief="flat")
title_bar.pack(fill="x")

title_label = tk.Label(title_bar, text="Trippy's Deluxe Washer", bg="#980ee9", fg="#fff", font=("Arial", 12))
title_label.pack(side="left", padx=5, pady=2)

close_button = tk.Button(title_bar, text="X", command=root.destroy, bg="#980ee9", fg="white", font=("Arial", 8), width=2)
close_button.pack(side="right", padx=5, pady=2)

def start_move(event):
	root.x = event.x
	root.y = event.y

def stop_move(event):
	root.x = None
	root.y = None

def on_move(event):
	deltax = event.x - root.x
	deltay = event.y - root.y
	root.geometry(f"+{root.winfo_x() + deltax}+{root.winfo_y() + deltay}")

title_bar.bind("<Button-1>", start_move)
title_bar.bind("<ButtonRelease-1>", stop_move)
title_bar.bind("<B1-Motion>", on_move)

dbg_label = tk.Label(root, text="Press button to inject", fg="#980ee9", bg="#333333", font=("Arial", 14))
dbg_label.place(relx=0.5,rely=0.4, anchor="center")
inject_button = tk.Button(root, text="Inject", bg="#980ee9", fg="white", font=("Arial", 12), command=attempt_inject)
inject_button.place(relx=0.5, rely=0.6, anchor="center")

root.mainloop()