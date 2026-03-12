import tkinter as tk                          # นำเข้าโมดูล tkinter สำหรับสร้าง GUI
from tkinter import messagebox, font as tkfont  # นำเข้า messagebox (popup) และ font จาก tkinter
import random                                   # นำเข้าโมดูล random สำหรับสุ่มค่า
import os                                       # นำเข้าโมดูล os สำหรับจัดการไฟล์และ path
import math                                     # นำเข้าโมดูล math สำหรับคำนวณคณิตศาสตร์
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageFont  # นำเข้าเครื่องมือจัดการรูปภาพจาก Pillow
from cards import tarot_cards                   # นำเข้าข้อมูลไพ่ทาโรต์จากไฟล์ cards.py
import socket
import json
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000

def get_prediction_from_server(card, category):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(5.0)
        client.sendto(f"{card},{category}".encode(), (SERVER_IP, SERVER_PORT))
        data, _ = client.recvfrom(4096)
        return data.decode().strip('"')  # ตัด " ออก
    except Exception as e:
        return f"เชื่อมต่อผิดพลาด: {e}"
# ==============================
# State Variables (ตัวแปรสถานะของโปรแกรม)
# ==============================
base_path = os.path.dirname(__file__)           # เส้นทางของโฟลเดอร์ที่ไฟล์นี้อยู่
image_folder = os.path.join(base_path, "images")  # เส้นทางโฟลเดอร์รูปภาพไพ่

selected_cards = []      # รายการไพ่ที่ผู้ใช้เลือกไว้
max_picks = 1            # จำนวนไพ่สูงสุดที่เลือกได้ในรอบนี้
card_items = []          # รายการ ID ของไอเท็มไพ่บน canvas
canvas_cards_map = {}    # dict เก็บสถานะว่าไพ่ถูกเลือกแล้วหรือยัง (True = เลือกแล้ว)
image_refs = []          # เก็บ reference ของ PhotoImage เพื่อป้องกัน garbage collection
back_card_image = None   # รูปภาพหลังไพ่ (ใช้ร่วมกันทุกใบ)
star_items = []          # รายการ ID ของดาวบน canvas (สำหรับ background)
glow_animation_id = None  # ID ของ animation loop ของลูกโลก (orb)

# ==============================
# Theme Colors — Mystical Dark Luxury (สีธีมแบบลึกลับหรูหรา)
# ==============================
COLORS = {
    "bg_dark":       "#0A0A1A",   # สีดำอวกาศ — พื้นหลังหลัก
    "bg_mid":        "#10102A",   # สีกรมท่ากลางคืน — พื้นหลังรอง
    "bg_card":       "#14142E",   # สีพื้นหลังของการ์ดคำทำนาย
    "gold":          "#D4AF37",   # สีทองเข้ม
    "gold_light":    "#F0D060",   # สีทองสว่าง
    "gold_dim":      "#8B7520",   # สีทองหม่น
    "purple":        "#6B3FA0",   # สีม่วงลึกลับ
    "purple_light":  "#9B6FD0",   # สีม่วงอ่อน
    "teal":          "#2DD4BF",   # สีเขียวฟ้าสวรรค์
    "white":         "#F5F0FF",   # สีขาวอุ่น
    "gray":          "#5A5A7A",   # สีเทาหม่น
    "card_back":     "#1E1E3F",   # สีหลังไพ่
    "selected":      "#2A2A4A",   # สีช่องไพ่ที่ถูกเลือกแล้ว
    "border_glow":   "#7B5FC0",   # สีเรืองแสงขอบ
}

# ==============================
# Helper: สร้างภาพ Gradient (ไล่สี)
# ==============================
def make_gradient_image(w, h, color1, color2, vertical=True):
    """สร้างภาพ PIL ที่มีการไล่สีจาก color1 ไป color2"""
    img = Image.new("RGB", (w, h))                              # สร้างภาพ RGB ขนาด w x h
    c1 = tuple(int(color1.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))  # แปลง hex → RGB tuple (สี 1)
    c2 = tuple(int(color2.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))  # แปลง hex → RGB tuple (สี 2)
    for i in range(h if vertical else w):                       # วนลูปตามความสูง (แนวตั้ง) หรือความกว้าง (แนวนอน)
        t = i / (h - 1 if vertical else w - 1)                 # คำนวณค่าสัดส่วน 0.0–1.0 ของตำแหน่งปัจจุบัน
        r = int(c1[0] + (c2[0] - c1[0]) * t)                  # ค่า R ที่ interpolate แล้ว
        g = int(c1[1] + (c2[1] - c1[1]) * t)                  # ค่า G ที่ interpolate แล้ว
        b = int(c1[2] + (c2[2] - c1[2]) * t)                  # ค่า B ที่ interpolate แล้ว
        if vertical:
            img.paste((r, g, b), (0, i, w, i + 1))             # วาดแถวสีแนวนอน
        else:
            img.paste((r, g, b), (i, 0, i + 1, h))             # วาดแถบสีแนวตั้ง
    return img                                                  # คืนค่าภาพ gradient

# ==============================
# Helper: สร้างภาพหลังไพ่แบบสวยงาม
# ==============================
def make_card_back(w=44, h=66):
    """วาดภาพหลังไพ่พร้อมลวดลายตกแต่ง ขนาด w x h pixels"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))  # สร้างภาพ RGBA โปร่งใส
    draw = ImageDraw.Draw(img)                       # สร้าง object วาดภาพ

    # วาด Gradient พื้นหลังจากบนลงล่าง
    for y in range(h):
        t = y / (h - 1)                              # สัดส่วนตำแหน่ง 0–1
        r = int(0x1E + (0x2A - 0x1E) * t)           # ค่า R ไล่สี
        g = int(0x1E + (0x10 - 0x1E) * t)           # ค่า G ไล่สี
        b = int(0x3F + (0x50 - 0x3F) * t)           # ค่า B ไล่สี
        draw.rectangle([0, y, w, y + 1], fill=(r, g, b, 255))  # วาดแถบสีทีละพิกเซล

    # วาดกรอบทองด้านนอก
    draw.rectangle([0, 0, w - 1, h - 1], outline=(212, 175, 55, 255), width=2)
    # วาดกรอบม่วงด้านใน
    draw.rectangle([3, 3, w - 4, h - 4], outline=(155, 111, 208, 180), width=1)

    # วาดสัญลักษณ์ดาวตรงกลาง
    cx, cy = w // 2, h // 2    # จุดกึ่งกลางของภาพ
    gold = (212, 175, 55, 255) # สีทอง RGBA
    # วาดเส้น 6 แขน ทุก 60 องศา เพื่อสร้างดาว
    for angle_deg in range(0, 360, 60):
        angle = math.radians(angle_deg)                        # แปลงองศาเป็น radian
        x1 = cx + int(4 * math.cos(angle))                    # จุดเริ่มต้นแขนดาว (ใกล้ศูนย์กลาง)
        y1 = cy + int(4 * math.sin(angle))
        x2 = cx + int(10 * math.cos(angle))                   # จุดปลายแขนดาว (ไกลศูนย์กลาง)
        y2 = cy + int(10 * math.sin(angle))
        draw.line([x1, y1, x2, y2], fill=gold, width=1)       # วาดเส้นแขนดาว
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=gold) # วาดวงกลมศูนย์กลางดาว

    # วาดจุดตกแต่งมุมทั้ง 4
    for (ox, oy) in [(3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4)]:
        draw.ellipse([ox - 2, oy - 2, ox + 2, oy + 2], fill=(155, 111, 208, 220))  # วงกลมม่วงเล็กที่มุม

    return img  # คืนค่าภาพหลังไพ่สำเร็จรูป

# ==============================
# วาดดาวเป็น Background บน Canvas
# ==============================
def draw_stars(canvas, width, height, count=120):
    for _ in range(count):                                      # วนลูปตามจำนวนดาวที่ต้องการ
        x = random.randint(0, width)                            # ตำแหน่ง X แบบสุ่ม
        y = random.randint(0, height)                           # ตำแหน่ง Y แบบสุ่ม
        size = random.choice([1, 1, 1, 2, 2, 3])               # ขนาดดาวสุ่ม (ส่วนใหญ่เล็ก)
        brightness = random.randint(140, 255)                   # ความสว่างสุ่ม
        color = f"#{brightness:02x}{brightness:02x}{int(brightness*0.9):02x}"  # สีขาว/เหลืองอ่อน
        canvas.create_oval(x, y, x + size, y + size, fill=color, outline="")  # วาดดาวเป็นจุดวงรี

# ==============================
# Animation เรืองแสงของลูกโลกกลาง (Orb)
# ==============================
glow_phase = 0  # ตัวแปรเก็บเฟสปัจจุบันของ animation (0–99)

def animate_orb():
    """อัปเดตสีลูกโลกกลางทุก 50ms เพื่อสร้างเอฟเฟกต์ pulse เรืองแสง"""
    global glow_phase, glow_animation_id
    glow_phase = (glow_phase + 1) % 100                          # เพิ่ม phase ทีละ 1 วนรอบ 0–99
    t = (math.sin(glow_phase * 0.063) + 1) / 2                  # แปลง phase → ค่า 0.0–1.0 แบบ sine wave
    alpha = int(60 + 80 * t)                                     # ความสว่าง (ไม่ได้ใช้งานจริงใน tkinter canvas)
    color = f"#{int(0x6B + 0x30 * t):02x}{int(0x3F + 0x10 * t):02x}{int(0xA0 + 0x30 * t):02x}"  # สีม่วงเข้ม–อ่อน
    try:
        card_canvas.itemconfig("orb_glow", fill=color)          # อัปเดตสีของ orb บน canvas
        glow_animation_id = root.after(50, animate_orb)         # ตั้งเวลาเรียกตัวเองซ้ำใน 50ms
    except Exception:
        pass                                                     # ถ้า canvas ถูกทำลายไปแล้ว ให้หยุด animation

# ==============================
# รีเซ็ต / เริ่มทำนายใหม่
# ==============================
def reset_prediction():
    """ล้างสถานะทั้งหมดและเริ่มต้นการทำนายใหม่"""
    global selected_cards, max_picks
    selected_cards.clear()                     # ล้างรายการไพ่ที่เลือกไว้

    cat = category_var.get()                   # อ่านหมวดหมู่ที่เลือก
    max_picks = 10 if cat == "monthly" else 1  # รายเดือนเลือกได้ 10 ใบ, อื่นๆ 1 ใบ

    # รีเซ็ตข้อความแนะนำ
    card_label.config(
        text=f"✦  สัมผัสไพ่ที่คุณรู้สึกดึงดูด  {max_picks} ใบ  ✦",
        fg=COLORS["gold_light"]
    )

    # ลบ widget คำทำนายเก่าทั้งหมด
    for widget in prediction_container.winfo_children():
        widget.destroy()
    image_refs.clear()  # ล้าง reference รูปภาพเก่า

    draw_card_circle()         # วาดวงไพ่ใหม่
    main_canvas.yview_moveto(0)  # เลื่อน scroll กลับขึ้นบนสุด

# ==============================
# วาดวงไพ่บน Canvas
# ==============================
def draw_card_circle():
    """วาดไพ่ 78 ใบเรียงเป็นวงกลมบน card_canvas"""
    global back_card_image
    card_canvas.delete("all")      # ลบทุกอย่างบน canvas
    card_items.clear()             # ล้างรายการ ID ไพ่
    canvas_cards_map.clear()       # ล้างแผนที่สถานะไพ่

    cw, ch = 520, 340              # ขนาด canvas (กว้าง x สูง)
    center_x, center_y = cw // 2, ch // 2  # จุดกึ่งกลาง canvas
    radius = 130                   # รัศมีวงกลมที่วางไพ่
    num_cards = 78                 # จำนวนไพ่ทั้งหมด

    # วาดดาวพื้นหลัง
    draw_stars(card_canvas, cw, ch, count=150)

    # วาดวงแหวนตกแต่งรอบนอก 3 ชั้น
    for r_offset, ring_color in [(145, "#3C3420"), (135, "#615227"), (125, "#8F782D")]:
        card_canvas.create_oval(
            center_x - r_offset, center_y - r_offset,
            center_x + r_offset, center_y + r_offset,
            outline=ring_color, width=1
        )

    # วาดลูกโลกเรืองแสงตรงกลาง (หลายชั้นจากใหญ่ไปเล็ก)
    for r_size, fill in [
        (45, "#3D2060"), (35, "#4B2880"), (25, "#6B3FA0"), (15, "#8B5FC0"), (8, "#B07FE0")
    ]:
        card_canvas.create_oval(
            center_x - r_size, center_y - r_size,
            center_x + r_size, center_y + r_size,
            fill=fill, outline="",
            tags="orb_glow" if r_size == 35 else ""  # ชั้นที่ 2 ได้ tag สำหรับ animation
        )

    # วาดสัญลักษณ์พระจันทร์เสี้ยวตรงกลาง
    card_canvas.create_text(
        center_x, center_y,
        text="☽", font=("Georgia", 16), fill=COLORS["gold_light"]
    )

    # สร้างภาพหลังไพ่เพื่อใช้กับทุกใบ
    card_back_pil = make_card_back(44, 66)            # สร้างภาพหลังไพ่
    back_card_image = ImageTk.PhotoImage(card_back_pil)  # แปลงเป็น PhotoImage สำหรับ tkinter

    for i in range(num_cards):  # วนลูปสร้างไพ่ทั้ง 78 ใบ
        angle = i * (2 * math.pi / num_cards) - (math.pi / 2)  # คำนวณมุมของไพ่ใบที่ i (เริ่มที่บน)
        x = center_x + radius * math.cos(angle)       # ตำแหน่ง X ของไพ่
        y = center_y + radius * math.sin(angle)       # ตำแหน่ง Y ของไพ่

        # วาดสี่เหลี่ยมช่องว่าง (จะเห็นเมื่อไพ่ถูกเลือกออกไปแล้ว)
        card_canvas.create_rectangle(
            x - 22, y - 33, x + 22, y + 33,
            fill=COLORS["selected"], outline=COLORS["gold_dim"], width=1
        )

        # วาดรูปหลังไพ่บน canvas
        card_id = card_canvas.create_image(x, y, image=back_card_image)
        # ผูก event คลิกซ้าย → เรียก pick_card
        card_canvas.tag_bind(card_id, "<Button-1>", lambda e, cid=card_id: pick_card(cid))
        # ผูก event mouse เข้า/ออก → เรียก on_card_hover
        card_canvas.tag_bind(card_id, "<Enter>", lambda e, cid=card_id: on_card_hover(cid, True))
        card_canvas.tag_bind(card_id, "<Leave>", lambda e, cid=card_id: on_card_hover(cid, False))
        card_items.append(card_id)          # เพิ่ม ID ไพ่เข้ารายการ
        canvas_cards_map[card_id] = False   # ตั้งค่าเริ่มต้น: ไพ่ยังไม่ถูกเลือก

    # เริ่ม animation ลูกโลก
    animate_orb()

def on_card_hover(card_id, entering):
    """จัดการ visual feedback เมื่อ mouse hover บนไพ่"""
    if canvas_cards_map.get(card_id, True):  # ถ้าไพ่ถูกเลือกไปแล้ว ไม่ต้องทำอะไร
        return
    pass  # tkinter canvas ไม่รองรับ scale ง่ายๆ จึงข้ามไป

# ==============================
# กำหนด Pool ไพ่ตามหมวดหมู่
# ==============================
# ไพ่ที่เหมาะกับหมวดความรัก
love_pool = ["The Lovers", "The Sun", "The Star", "The Empress",
             "Wheel of Fortune", "The Fool", "The Moon", "Strength"]
# ไพ่ที่เหมาะกับหมวดการงาน
career_pool = ["The Emperor", "The Chariot", "The Magician", "The Sun",
               "Wheel of Fortune", "The Hierophant", "Justice", "The Hermit"]

def pick_card(card_id):
    """ดึงไพ่เมื่อผู้ใช้คลิก"""
    global selected_cards, max_picks

    if canvas_cards_map.get(card_id, True):  # ถ้าไพ่ถูกเลือกไปแล้ว ให้หยุด
        return

    if len(selected_cards) >= max_picks:     # ถ้าเลือกครบแล้ว แสดง popup แจ้งเตือน
        messagebox.showinfo(
            "✦ แจ้งเตือน",
            f"คุณเลือกครบ {max_picks} ใบแล้วค่ะ\nเลื่อนลงเพื่อดูคำทำนาย ✨"
        )
        return

    category = category_var.get()            # อ่านหมวดหมู่ปัจจุบัน
    pool = list(tarot_cards.keys())          # pool เริ่มต้น = ไพ่ทั้งหมด
    if category == "love":
        pool = [c for c in love_pool if c in tarot_cards]    # กรองเฉพาะไพ่ love
    elif category == "career":
        pool = [c for c in career_pool if c in tarot_cards]  # กรองเฉพาะไพ่ career

    # กรองไพ่ที่ยังไม่ถูกเลือก
    available = [c for c in pool if c not in selected_cards]
    if not available:  # ถ้า pool หมด ให้ใช้ไพ่ทั้งหมดที่ยังไม่ถูกเลือก
        available = [c for c in tarot_cards.keys() if c not in selected_cards]

    chosen_card = random.choice(available)   # สุ่มเลือกไพ่จาก pool ที่เหลือ
    selected_cards.append(chosen_card)       # เพิ่มไพ่ที่สุ่มได้เข้ารายการที่เลือก

    card_canvas.itemconfig(card_id, state="hidden")  # ซ่อนรูปไพ่ (เผยช่องว่างด้านหลัง)
    canvas_cards_map[card_id] = True                 # อัปเดตสถานะว่าไพ่ถูกเลือกแล้ว

    remaining = max_picks - len(selected_cards)      # คำนวณจำนวนที่เหลือ
    if remaining > 0:
        # อัปเดตข้อความแสดงความคืบหน้า
        card_label.config(
            text=f"✦  เลือกแล้ว {len(selected_cards)}/{max_picks} ใบ  —  เหลืออีก {remaining} ใบ  ✦",
            fg=COLORS["teal"]
        )
    else:
        # เลือกครบแล้ว → แสดงข้อความและเรียกแสดงคำทำนาย
        card_label.config(text="✦  ไพ่แห่งโชคชะตาถูกเปิดเผยแล้ว  ✦", fg=COLORS["gold_light"])
        predict()

# ==============================
# แสดงคำทำนาย
# ==============================
def predict():
    """สร้างและแสดงผลคำทำนายของไพ่ทุกใบที่เลือก"""
    category = category_var.get()  # อ่านหมวดหมู่ปัจจุบัน

    # ล้าง widget คำทำนายเก่า
    for widget in prediction_container.winfo_children():
        widget.destroy()
    image_refs.clear()  # ล้าง image reference เก่า

    # ─── หัวข้อส่วนคำทำนาย ───
    header_frame = tk.Frame(prediction_container, bg=COLORS["bg_dark"])
    header_frame.pack(fill="x", pady=(20, 5))

    tk.Label(
        header_frame,
        text="─── ✦ คำทำนายของคุณ ✦ ───",
        font=("Georgia", 16, "bold"),
        fg=COLORS["gold"],
        bg=COLORS["bg_dark"]
    ).pack()

    # map หมวดหมู่ → ชื่อภาษาไทยแสดงใต้หัวข้อ
    subtitle_map = {
        "daily":   "ดวงชะตาประจำวันนี้",
        "monthly": "ดวงชะตาประจำเดือน",
        "love":    "ดวงความรักและความสัมพันธ์",
        "career":  "ดวงการงานและความสำเร็จ",
    }
    tk.Label(
        header_frame,
        text=subtitle_map.get(category, ""),  # แสดงชื่อหมวดหมู่ภาษาไทย
        font=("Georgia", 11, "italic"),
        fg=COLORS["purple_light"],
        bg=COLORS["bg_dark"]
    ).pack(pady=(2, 10))

    for i, card_name in enumerate(selected_cards):  # วนลูปแสดงผลทุกใบที่เลือก
        # ─── กรอบนอกสีทอง (จำลอง glow ด้วย nested frames) ───
        outer = tk.Frame(prediction_container, bg=COLORS["gold_dim"], padx=1, pady=1)
        outer.pack(pady=12, padx=25, fill="x")

        # กรอบกลางสีม่วง
        inner = tk.Frame(outer, bg=COLORS["purple"], padx=1, pady=1)
        inner.pack(fill="both", expand=True)

        # กรอบในสุดสีพื้นหลังการ์ด
        card_frame = tk.Frame(inner, bg=COLORS["bg_card"], padx=15, pady=15)
        card_frame.pack(fill="both", expand=True)

        prediction_text = get_prediction_from_server(card_name, category)  # ดึงข้อความทำนายของไพ่ใบนี้

        # ─── ส่วนรูปภาพไพ่ (ซ้ายมือ) ───
        img_frame = tk.Frame(card_frame, bg=COLORS["bg_card"])
        img_frame.pack(side="left", padx=(0, 15))

        # สร้าง path ของไฟล์รูป (ชื่อไพ่ lowercase แทนช่องว่างด้วย _ + .jpg)
        filename = card_name.lower().replace(" ", "_") + ".jpg"
        image_path = os.path.join(image_folder, filename)

        if os.path.exists(image_path):  # ถ้ามีไฟล์รูปจริง
            img = Image.open(image_path).resize((90, 140), Image.LANCZOS)  # เปิดและย่อรูป
            # เพิ่มกรอบทองรอบรูปไพ่
            bordered = Image.new("RGB", (96, 146), (212, 175, 55))  # พื้นสีทองขนาดใหญ่กว่าเล็กน้อย
            bordered.paste(img, (3, 3))                              # วางรูปไพ่ตรงกลาง
            photo = ImageTk.PhotoImage(bordered)                     # แปลงเป็น PhotoImage
            img_label = tk.Label(img_frame, image=photo, bg=COLORS["bg_card"], cursor="hand2")
            img_label.config(image=photo)
            image_refs.append(photo)  # เก็บ reference กัน GC เก็บไป
        else:  # ถ้าไม่มีไฟล์รูป → สร้างรูปตัวแทน
            ph = make_gradient_image(90, 140, COLORS["bg_mid"], COLORS["purple"])  # gradient placeholder
            ph_draw = ImageDraw.Draw(ph)
            ph_draw.rectangle([0, 0, 89, 139], outline=(212, 175, 55), width=2)   # กรอบทอง
            ph_draw.text((45, 70), "☽", fill=(212, 175, 55))                      # ไอคอนพระจันทร์
            photo = ImageTk.PhotoImage(ph)
            img_label = tk.Label(img_frame, image=photo, bg=COLORS["bg_card"])
            image_refs.append(photo)  # เก็บ reference

        img_label.pack()  # แสดงรูปไพ่

        # ป้ายระบุหมายเลขใบ
        badge_text = f"ใบที่ {i+1}" if max_picks > 1 else "ไพ่แห่งโชคชะตา"
        tk.Label(
            img_frame,
            text=badge_text,
            font=("Georgia", 8, "italic"),
            fg=COLORS["gold"],
            bg=COLORS["bg_card"]
        ).pack(pady=(4, 0))

        # ─── ส่วนข้อความคำทำนาย (ขวามือ) ───
        text_frame = tk.Frame(card_frame, bg=COLORS["bg_card"])
        text_frame.pack(side="left", fill="both", expand=True)

        # Frame ชื่อไพ่พร้อมเส้นคั่น
        name_frame = tk.Frame(text_frame, bg=COLORS["bg_card"])
        name_frame.pack(fill="x", pady=(0, 8))

        # Label ชื่อไพ่สีทอง
        tk.Label(
            name_frame,
            text=f"✦  {card_name}  ✦",
            font=("Georgia", 13, "bold"),
            fg=COLORS["gold_light"],
            bg=COLORS["bg_card"]
        ).pack(anchor="w")

        # เส้นคั่นใต้ชื่อไพ่
        separator = tk.Frame(name_frame, bg=COLORS["gold_dim"], height=1)
        separator.pack(fill="x", pady=3)

        # Label ข้อความคำทำนาย
        tk.Label(
            text_frame,
            text=prediction_text,
            font=("Georgia", 10),
            fg=COLORS["white"],
            bg=COLORS["bg_card"],
            justify="left",
            wraplength=290  # ตัดบรรทัดที่ 290 px
        ).pack(anchor="w", fill="both", expand=True)

    # ─── เส้นคั่นปิดท้าย ───
    tk.Label(
        prediction_container,
        text="─── ✦ ───",
        font=("Georgia", 12),
        fg=COLORS["gold_dim"],
        bg=COLORS["bg_dark"]
    ).pack(pady=(10, 20))

    # อัปเดต scroll region ให้ครอบคลุมเนื้อหาใหม่
    scrollable_frame.update_idletasks()
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))
    # เลื่อน scroll ลงมาดูผลทำนายอัตโนมัติหลัง 100ms
    root.after(100, lambda: main_canvas.yview_moveto(0.25))

# ==============================
# ตั้งค่า GUI หลัก
# ==============================
root = tk.Tk()                              # สร้างหน้าต่างหลัก
root.title("✦ Fortune — Tarot Reading ✦")  # ตั้งชื่อหน้าต่าง
root.geometry("560x820")                   # ขนาดหน้าต่าง 560x820 px
root.configure(bg=COLORS["bg_dark"])       # สีพื้นหลังหน้าต่าง
root.resizable(False, True)                # ปรับกว้างไม่ได้ แต่ปรับสูงได้

# พยายามตั้ง icon หน้าต่าง (อาจล้มเหลวถ้าไม่มีไฟล์ .ico)
try:
    root.iconbitmap("")
except Exception:
    pass

# ── Layout แบบ Scrollable ──
# Canvas หลักที่รองรับ scroll
main_canvas = tk.Canvas(root, bg=COLORS["bg_dark"], highlightthickness=0)
# Scrollbar แนวตั้ง
main_scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview,
                               bg=COLORS["bg_mid"], troughcolor=COLORS["bg_dark"],
                               activebackground=COLORS["gold_dim"])
# Frame ที่จะเลื่อนได้ (วางอยู่ใน canvas)
scrollable_frame = tk.Frame(main_canvas, bg=COLORS["bg_dark"])

# ผูก event: เมื่อขนาด scrollable_frame เปลี่ยน → อัปเดต scroll region
scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)
# วาง scrollable_frame เป็น window บน canvas
canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

# ผูก event: เมื่อขนาด canvas เปลี่ยน → ขยาย scrollable_frame ให้เท่ากัน
main_canvas.bind("<Configure>", lambda e: main_canvas.itemconfig(canvas_window, width=e.width))
main_canvas.configure(yscrollcommand=main_scrollbar.set)  # เชื่อม scrollbar กับ canvas
main_canvas.pack(side="left", fill="both", expand=True)   # วาง canvas ด้านซ้ายเต็มพื้นที่
main_scrollbar.pack(side="right", fill="y")               # วาง scrollbar ด้านขวา

# ผูก MouseWheel สำหรับ scroll ด้วยเมาส์
root.bind_all("<MouseWheel>", lambda e: main_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

# ── ส่วนหัว (Header) ──
header_bg = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
header_bg.pack(fill="x", pady=0)

# แถบสีทองบาง ๆ ที่ด้านบนสุด
top_bar = tk.Frame(header_bg, bg=COLORS["gold_dim"], height=2)
top_bar.pack(fill="x")

# Frame โลโก้และชื่อแอป
logo_frame = tk.Frame(header_bg, bg=COLORS["bg_dark"], pady=20)
logo_frame.pack(fill="x")

# สัญลักษณ์พระจันทร์ตกแต่ง
tk.Label(
    logo_frame,
    text="☽  ✦  ☾",
    font=("Georgia", 18),
    fg=COLORS["gold"],
    bg=COLORS["bg_dark"]
).pack()

# ชื่อแอปหลัก "FORTUNE"
tk.Label(
    logo_frame,
    text="FORTUNE",
    font=("Georgia", 30, "bold"),
    fg=COLORS["gold_light"],
    bg=COLORS["bg_dark"]
).pack()

# ชื่อรอง "TAROT READING" แบบ letter-spacing
tk.Label(
    logo_frame,
    text="T A R O T   R E A D I N G",
    font=("Georgia", 10),
    fg=COLORS["purple_light"],
    bg=COLORS["bg_dark"]
).pack(pady=(2, 0))

# เส้นคั่นทองด้านล่างหัว
tk.Frame(header_bg, bg=COLORS["gold_dim"], height=1).pack(fill="x", padx=40)

# ── ตัวเลือกหมวดหมู่ (Category Selector) ──
cat_frame = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"], pady=18)
cat_frame.pack()

category_var = tk.StringVar(value="daily")  # ตัวแปรเก็บหมวดหมู่ที่เลือก (default: daily)

# รายการหมวดหมู่: (ค่า, ข้อความปุ่ม)
CAT_OPTIONS = [
    ("daily",   "☀  รายวัน"),
    ("monthly", "🌙  รายเดือน"),
    ("love",    "♡  ความรัก"),
    ("career",  "⚡  การงาน"),
]

# style พื้นฐานของปุ่มหมวดหมู่
btn_style = {
    "font": ("Georgia", 10),
    "relief": "flat",
    "cursor": "hand2",
    "padx": 14,
    "pady": 7,
    "bd": 0,
}

def update_category_buttons():
    """อัปเดตสีปุ่มหมวดหมู่ให้ปุ่มที่เลือกอยู่เด่นกว่า"""
    for btn, val in cat_buttons:
        if category_var.get() == val:  # ปุ่มที่ active
            btn.config(bg=COLORS["gold"], fg=COLORS["bg_dark"], font=("Georgia", 10, "bold"))
        else:                          # ปุ่มที่ไม่ active
            btn.config(bg=COLORS["bg_mid"], fg=COLORS["gray"], font=("Georgia", 10))

def select_category(val):
    """เรียกเมื่อผู้ใช้กดเปลี่ยนหมวดหมู่"""
    category_var.set(val)         # อัปเดตค่าหมวดหมู่
    update_category_buttons()     # อัปเดตหน้าตาปุ่ม
    reset_prediction()            # รีเซ็ตและเริ่มใหม่

cat_buttons = []  # เก็บ tuple (widget, value) ของปุ่มทุกอัน
for val, label in CAT_OPTIONS:
    btn = tk.Button(
        cat_frame, text=label,
        command=lambda v=val: select_category(v),  # เรียก select_category พร้อมค่าหมวดหมู่
        bg=COLORS["bg_mid"], fg=COLORS["gray"],
        **btn_style
    )
    btn.pack(side="left", padx=4)  # วางปุ่มแนวนอน
    cat_buttons.append((btn, val)) # เพิ่มเข้ารายการ

update_category_buttons()  # ไฮไลต์ปุ่ม default ครั้งแรก

# ── ปุ่มรีเซ็ต ──
reset_btn = tk.Button(
    scrollable_frame,
    text="🔄  เริ่มทำนายใหม่",
    command=reset_prediction,
    bg=COLORS["purple"],
    fg=COLORS["white"],
    font=("Georgia", 11, "bold"),
    relief="flat",
    cursor="hand2",
    padx=20, pady=8,
    activebackground=COLORS["purple_light"],
    activeforeground=COLORS["white"],
    bd=0
)
reset_btn.pack(pady=(0, 6))

# Hover effect: เปลี่ยนสีเมื่อ mouse เข้า/ออก
reset_btn.bind("<Enter>", lambda e: reset_btn.config(bg=COLORS["purple_light"]))
reset_btn.bind("<Leave>", lambda e: reset_btn.config(bg=COLORS["purple"]))

# ── Canvas สำหรับวงไพ่ ──
canvas_container = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
canvas_container.pack(pady=5)

card_canvas = tk.Canvas(
    canvas_container,
    width=520, height=340,      # ขนาด canvas วงไพ่
    bg=COLORS["bg_dark"],
    highlightthickness=0        # ไม่แสดงขอบ highlight
)
card_canvas.pack()

# ── Label คำแนะนำการเลือกไพ่ ──
card_label = tk.Label(
    scrollable_frame,
    text="✦  สัมผัสไพ่ที่คุณรู้สึกดึงดูด  1 ใบ  ✦",
    font=("Georgia", 12, "italic"),
    fg=COLORS["gold_light"],
    bg=COLORS["bg_dark"]
)
card_label.pack(pady=(5, 3))

# เส้นคั่นบาง ๆ
tk.Frame(scrollable_frame, bg=COLORS["gold_dim"], height=1).pack(fill="x", padx=60, pady=8)

# ── Container สำหรับแสดงผลคำทำนาย ──
prediction_container = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
prediction_container.pack(fill="both", expand=True, pady=5)

# ── Footer ──
footer = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"], pady=15)
footer.pack(fill="x")
tk.Label(
    footer,
    text="✦   The stars guide, the cards reveal   ✦",
    font=("Georgia", 9, "italic"),
    fg=COLORS["gray"],
    bg=COLORS["bg_dark"]
).pack()
# แถบทองที่ด้านล่างสุด
tk.Frame(footer, bg=COLORS["gold_dim"], height=2).pack(fill="x", padx=0, pady=(10, 0))

# ── เริ่มต้นโปรแกรม ──
reset_prediction()  # วาดวงไพ่และตั้งค่าเริ่มต้น
root.mainloop()     # เข้าสู่ event loop หลักของ tkinter
