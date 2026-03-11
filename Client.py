import tkinter as tk
from tkinter import messagebox
import socket
import json
from PIL import Image, ImageTk
from cards import tarot_cards # สำหรับดึงข้อมูลมาแสดงผลฝั่ง Client

# Configuration
SERVER_ADDR = ("127.0.0.1", 5005)
client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_sock.settimeout(2)

COLORS = {"bg_dark": "#0a0a0c", "gold": "#d4af37", "purple": "#2d1b4e", "white": "#ffffff"}

CATEGORIES = {
    "รายวัน": {"count": 1, "field": "daily"},
    "ความรัก": {"count": 3, "field": "love"},
    "การงาน": {"count": 4, "field": "career"},
    "รายเดือน": {"count": 10, "field": "monthly"} # เพิ่มหมวด 10 ใบ
}

# State
current_category = "รายวัน"
max_picks = 1
selected_indices_data = [] # เก็บ index ไพ่ที่เลือกแล้ว
card_objects_on_canvas = [] # ไพ่ทั้งหมดบนจอ
card_objects_in_wait = []   # ไพ่ที่เลือกแล้วย้ายไปจุดพัก
current_indices = []        # ไพ่ 15 ใบที่สุ่มมาปัจจุบัน
back_card_image = None

def send_to_server(data):
    try:
        client_sock.sendto(json.dumps(data).encode('utf-8'), SERVER_ADDR)
    except: pass

def set_category(name):
    global current_category, max_picks, selected_indices_data, card_objects_in_wait
    current_category = name
    max_picks = CATEGORIES[name]["count"]
    
    # รีเซ็ตข้อมูลทั้งหมดเมื่อเปลี่ยนหมวดหมู่
    selected_indices_data = []
    card_objects_in_wait = []
    card_canvas.delete("all")
    prediction_container.pack_forget()
    
    send_to_server({"command": "RESET"}) # แจ้ง Server ให้ล้างข้อมูล session
    
    status_label.config(text=f"หมวด: {name} | เลือกให้ครบ {max_picks} ใบ")
    shuffle_auto() # สับไพ่ให้อัตโนมัติ

def shuffle_auto():
    global current_indices, card_objects_on_canvas
    try:
        send_to_server({"command": "GET_SHUFFLE"})
        data, _ = client_sock.recvfrom(4096)
        current_indices = json.loads(data.decode('utf-8'))["indices"]
        
        # ลบไพ่ที่ยังไม่ได้เลือกออกจากหน้าจอ
        for obj in card_objects_on_canvas:
            if obj not in card_objects_in_wait:
                card_canvas.delete(obj)
        
        animate_spread()
    except:
        messagebox.showerror("Error", "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้")

def animate_spread():
    global card_objects_on_canvas
    new_objs = []
    cx, cy = 290, 150
    for i in range(len(current_indices)):
        cid = card_canvas.create_image(cx, cy, image=back_card_image)
        new_objs.append(cid)
        tx = 50 + (i % 8) * 65
        ty = 60 + (i // 8) * 100
        root.after(i * 30, lambda c=cid, x=tx, y=ty: smooth_move(c, x, y))
    card_objects_on_canvas = card_objects_in_wait + new_objs

def smooth_move(obj_id, tx, ty):
    curr = card_canvas.coords(obj_id)
    if not curr: return
    dx, dy = (tx - curr[0]) / 5, (ty - curr[1]) / 5
    if abs(tx - curr[0]) > 1:
        card_canvas.move(obj_id, dx, dy)
        root.after(20, lambda: smooth_move(obj_id, tx, ty))
    else:
        card_canvas.tag_bind(obj_id, "<Button-1>", lambda e, c=obj_id: on_card_click(c))

def on_card_click(card_id):
    if len(selected_indices_data) >= max_picks: return

    # หาตำแหน่ง index จริง
    pool_idx = card_objects_on_canvas.index(card_id) - len(card_objects_in_wait)
    actual_idx = current_indices[pool_idx]
    
    # ส่งข้อมูลเก็บเข้า Server
    send_to_server({"command": "MARK_USED", "index": actual_idx})
    
    selected_indices_data.append(actual_idx)
    card_objects_in_wait.append(card_id)
    
    # ย้ายไปจุดพัก (แถวด้านล่าง)
    wait_x = 50 + ((len(selected_indices_data)-1) % 8) * 65
    wait_y = 300 + ((len(selected_indices_data)-1) // 8) * 100
    smooth_move(card_id, wait_x, wait_y)
    card_canvas.itemconfig(card_id, state="disabled")

    if len(selected_indices_data) < max_picks:
        root.after(500, shuffle_auto) # สับใบใหม่มาเติมอัตโนมัติ
    else:
        root.after(1000, show_prediction)

def show_prediction():
    prediction_container.pack(pady=10, fill="x")
    for w in prediction_container.winfo_children(): w.destroy()
    field = CATEGORIES[current_category]["field"]
    all_keys = list(tarot_cards.keys())
    for idx in selected_indices_data:
        key = all_keys[idx]
        frame = tk.Frame(prediction_container, bg=COLORS["bg_dark"])
        frame.pack(pady=5)
        tk.Label(frame, text=f"🔮 {key}", fg=COLORS["gold"], bg=COLORS["bg_dark"], font=("Arial", 11, "bold")).pack()
        tk.Label(frame, text=tarot_cards[key].get(field, ""), fg="white", bg=COLORS["bg_dark"], wraplength=450).pack()

# UI Setup
root = tk.Tk()
root.geometry("600x900")
root.configure(bg=COLORS["bg_dark"])

# โหลดรูปจำลอง (หรือดึงจาก path รูปของคุณ)
img = Image.new('RGB', (55, 90), color='#d4af37')
back_card_image = ImageTk.PhotoImage(img)

btn_frame = tk.Frame(root, bg=COLORS["bg_dark"])
btn_frame.pack(pady=20)
for cat in CATEGORIES:
    tk.Button(btn_frame, text=cat, command=lambda c=cat: set_category(c), 
              bg=COLORS["purple"], fg="white", width=9).pack(side="left", padx=3)

status_label = tk.Label(root, text="เลือกหมวดหมู่เพื่อเริ่ม", fg=COLORS["gold"], bg=COLORS["bg_dark"])
status_label.pack()

card_canvas = tk.Canvas(root, width=580, height=500, bg=COLORS["bg_dark"], highlightthickness=0)
card_canvas.pack()

prediction_container = tk.Frame(root, bg=COLORS["bg_dark"])

root.mainloop()