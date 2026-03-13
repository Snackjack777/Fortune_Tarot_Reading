import tkinter as tk
from tkinter import messagebox
import random
import os
import math
from PIL import Image, ImageTk, ImageDraw
import requests
import socket
import json

# ------------------------------
# การตั้งค่าเซิร์ฟเวอร์และ Firebase
# ------------------------------
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
FIREBASE_URL = "https://fortunetarot888-default-rtdb.asia-southeast1.firebasedatabase.app"

tarot_cards = {}

def load_tarot_from_firebase():
    global tarot_cards
    try:
        url = FIREBASE_URL + "/.json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            tarot_cards = res.json()
            print("โหลดข้อมูลไพ่จาก Firebase สำเร็จ :", len(tarot_cards), "ใบ")
        else:
            print("โหลดข้อมูลไม่สำเร็จ (status code:", res.status_code, ")")
            tarot_cards = {}
            messagebox.showwarning("✦ การเชื่อมต่อ", "ไม่สามารถโหลดข้อมูลไพ่จากเซิร์ฟเวอร์ได้\nใช้ข้อมูลสำรองแทน")
    except Exception as e:
        print("Firebase error:", e)
        tarot_cards = {}
        messagebox.showwarning("✦ การเชื่อมต่อ", "ไม่สามารถโหลดข้อมูลไพ่จากเซิร์ฟเวอร์ได้\nใช้ข้อมูลสำรองแทน")

def get_prediction_from_server(card, category):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(5.0)
        message = f"{card},{category}"
        client.sendto(message.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        data, _ = client.recvfrom(4096)
        response = data.decode('utf-8')
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        return response
    except socket.timeout:
        return "เซิร์ฟเวอร์ไม่ตอบสนอง (timeout)"
    except Exception as e:
        return f"เชื่อมต่อผิดพลาด: {e}"

# โหลดข้อมูลไพ่ตั้งแต่เริ่ม
load_tarot_from_firebase()

# ------------------------------
# รายชื่อไพ่ทั้งหมด (fallback)
# ------------------------------
ALL_CARD_NAMES = [
    "ACE_of_Wands", "Cups01", "Cups02", "Cups03", "Cups04", "Cups05", "Cups06",
    "Cups07", "Cups08", "Cups09", "Cups10", "Cups11", "Cups12", "Cups13", "Cups14",
    "Pents01", "Pents02", "Pents03", "Pents04", "Pents05", "Pents06", "Pents07",
    "Pents08", "Pents09", "Pents10", "Pents11", "Pents12", "Pents13", "Pents14",
    "Swords01", "Swords02", "Swords03", "Swords04", "Swords05", "Swords06", "Swords07",
    "Swords08", "Swords09", "Swords10", "Swords11", "Swords12", "Swords13", "Swords14",
    "Tarot_Nine_of_Wands", "The_Chariot", "The_Death", "The_Devil", "The_Emperor",
    "The_Empress", "The_Fool", "The_Hanged_Man", "The_Hermit", "The_Hierophant",
    "The_High_Priestess", "The_Judgement", "The_Justice", "The_Lovers", "The_Moon",
    "The_Star", "The_Strength", "The_Sun", "The_Temperance", "The_Tower",
    "The_Wheel_of_Fortune", "The_World", "Wands02", "Wands03", "Wands04", "Wands05",
    "Wands06", "Wands07", "Wands08", "Wands10", "Wands11", "Wands12", "Wands13",
    "Wands14", "the_magician"
]

# ------------------------------
# กำหนดชุดไพ่สำหรับแต่ละหมวดหมู่ (ขนาดไม่เท่ากัน)
# ------------------------------
if tarot_cards:
    all_keys = list(tarot_cards.keys())
else:
    all_keys = ALL_CARD_NAMES

# หมวด daily: ใช้ไพ่ดอกไม้และไพ่สำคัญ 10 ใบ (เผื่อเลือก 2)
daily_candidates = [c for c in all_keys if "Wands" in c or "Cups" in c]
if len(daily_candidates) < 10:
    daily_candidates.extend([c for c in all_keys if "The" in c][:10-len(daily_candidates)])

CATEGORY_CARDS = {
    "daily": daily_candidates[:10],
    "monthly": [c for c in all_keys if "The" in c or "Wheel" in c or "World" in c][:15],  # 15 ใบ
    "love": [c for c in ["The_Lovers","The_Sun","The_Star","The_Empress","The_Wheel_of_Fortune","The_Fool","The_Moon","The_Strength"] if c in all_keys],  # 8 ใบ
    "career": [c for c in ["The_Emperor","The_Chariot","the_magician","The_Sun","The_Wheel_of_Fortune","The_Hierophant","The_Justice","The_Hermit","The_Empress","The_World"] if c in all_keys]  # 10 ใบ
}

# ------------------------------
# ตัวแปรสถานะของโปรแกรม
# ------------------------------
base_path = os.path.dirname(__file__)
image_folder = os.path.join(base_path, "images")

selected_cards = []          # รายชื่อไพ่ที่เลือกแล้ว
max_picks = 1                # จำนวนที่เลือกได้ (ขึ้นกับหมวด)
card_items = []              # รายการ ID ของไพ่บน canvas
canvas_cards_map = {}        # สถานะการเลือกของแต่ละ card_id (True=เลือกแล้ว)
card_id_to_name = {}         # แมป card_id -> ชื่อไพ่ (สำหรับตำแหน่งคงที่)
image_refs = []              # เก็บ reference รูปภาพ
back_card_image = None       # รูปหลังไพ่
glow_animation_id = None     # animation ของลูกโลก
current_card_list = []       # รายชื่อไพ่ที่ใช้ในหมวดปัจจุบัน (อาจถูกสับเปลี่ยน)

# ------------------------------
# สีธีม
# ------------------------------
COLORS = {
    "bg_dark":       "#0A0A1A",
    "bg_mid":        "#10102A",
    "bg_card":       "#14142E",
    "gold":          "#D4AF37",
    "gold_light":    "#F0D060",
    "gold_dim":      "#8B7520",
    "purple":        "#6B3FA0",
    "purple_light":  "#9B6FD0",
    "teal":          "#2DD4BF",
    "white":         "#F5F0FF",
    "gray":          "#5A5A7A",
    "selected":      "#2A2A4A",
}

# ------------------------------
# ฟังก์ชันช่วยสร้างภาพ
# ------------------------------
def make_gradient_image(w, h, color1, color2, vertical=True):
    img = Image.new("RGB", (w, h))
    c1 = tuple(int(color1.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    c2 = tuple(int(color2.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    for i in range(h if vertical else w):
        t = i / (h - 1 if vertical else w - 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        if vertical:
            img.paste((r, g, b), (0, i, w, i+1))
        else:
            img.paste((r, g, b), (i, 0, i+1, h))
    return img

def make_card_back(w=44, h=66):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        t = y / (h - 1)
        r = int(0x1E + (0x2A - 0x1E) * t)
        g = int(0x1E + (0x10 - 0x1E) * t)
        b = int(0x3F + (0x50 - 0x3F) * t)
        draw.rectangle([0, y, w, y+1], fill=(r, g, b, 255))

    draw.rectangle([0, 0, w-1, h-1], outline=(212, 175, 55, 255), width=2)
    draw.rectangle([3, 3, w-4, h-4], outline=(155, 111, 208, 180), width=1)

    cx, cy = w//2, h//2
    gold = (212, 175, 55, 255)
    for angle_deg in range(0, 360, 60):
        angle = math.radians(angle_deg)
        x1 = cx + int(4 * math.cos(angle))
        y1 = cy + int(4 * math.sin(angle))
        x2 = cx + int(10 * math.cos(angle))
        y2 = cy + int(10 * math.sin(angle))
        draw.line([x1, y1, x2, y2], fill=gold, width=1)
    draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill=gold)

    for (ox, oy) in [(3,3), (w-4,3), (3, h-4), (w-4, h-4)]:
        draw.ellipse([ox-2, oy-2, ox+2, oy+2], fill=(155, 111, 208, 220))

    return img

def draw_stars(canvas, width, height, count=120):
    for _ in range(count):
        x = random.randint(0, width)
        y = random.randint(0, height)
        size = random.choice([1,1,1,2,2,3])
        brightness = random.randint(140, 255)
        color = f"#{brightness:02x}{brightness:02x}{int(brightness*0.9):02x}"
        canvas.create_oval(x, y, x+size, y+size, fill=color, outline="")

glow_phase = 0
def animate_orb():
    global glow_phase, glow_animation_id
    glow_phase = (glow_phase + 1) % 100
    t = (math.sin(glow_phase * 0.063) + 1) / 2
    color = f"#{int(0x6B + 0x30*t):02x}{int(0x3F + 0x10*t):02x}{int(0xA0 + 0x30*t):02x}"
    try:
        card_canvas.itemconfig("orb_glow", fill=color)
        glow_animation_id = root.after(50, animate_orb)
    except Exception:
        pass

# ------------------------------
# ฟังก์ชันจัดการหมวดหมู่และไพ่
# ------------------------------
def load_category_cards(category):
    """โหลดชุดไพ่ของหมวดที่กำหนด (ยังไม่ shuffle)"""
    global current_card_list
    if category in CATEGORY_CARDS:
        current_card_list = CATEGORY_CARDS[category].copy()
    else:
        current_card_list = CATEGORY_CARDS["daily"].copy()

def reset_prediction():
    global selected_cards, max_picks, card_id_to_name
    selected_cards.clear()
    card_id_to_name.clear()

    cat = category_var.get()
    # กำหนดจำนวนไพ่ที่เลือกได้ตามหมวดหมู่
    if cat == "monthly":
        max_picks = 10
    elif cat == "daily":
        max_picks = 2
    elif cat == "love":
        max_picks = 3
    elif cat == "career":
        max_picks = 4
    else:
        max_picks = 1

    load_category_cards(cat)

    card_label.config(
        text=f"✦  สัมผัสไพ่ที่คุณรู้สึกดึงดูด  {max_picks} ใบ  ✦",
        fg=COLORS["gold_light"]
    )

    for widget in prediction_container.winfo_children():
        widget.destroy()
    image_refs.clear()

    draw_card_circle()
    main_canvas.yview_moveto(0)

def draw_card_circle():
    global back_card_image, card_id_to_name
    card_canvas.delete("all")
    card_items.clear()
    canvas_cards_map.clear()
    card_id_to_name.clear()

    cw, ch = 520, 340
    center_x, center_y = cw // 2, ch // 2
    radius = 130
    num_cards = len(current_card_list)

    draw_stars(card_canvas, cw, ch, count=150)

    for r_offset, ring_color in [(145, "#3C3420"), (135, "#615227"), (125, "#8F782D")]:
        card_canvas.create_oval(
            center_x - r_offset, center_y - r_offset,
            center_x + r_offset, center_y + r_offset,
            outline=ring_color, width=1
        )

    for r_size, fill in [
        (45, "#3D2060"), (35, "#4B2880"), (25, "#6B3FA0"), (15, "#8B5FC0"), (8, "#B07FE0")
    ]:
        card_canvas.create_oval(
            center_x - r_size, center_y - r_size,
            center_x + r_size, center_y + r_size,
            fill=fill, outline="",
            tags="orb_glow" if r_size == 35 else ""
        )

    card_canvas.create_text(
        center_x, center_y,
        text="☽", font=("Georgia", 16), fill=COLORS["gold_light"]
    )

    card_back_pil = make_card_back(44, 66)
    back_card_image = ImageTk.PhotoImage(card_back_pil)

    for i in range(num_cards):
        angle = i * (2 * math.pi / num_cards) - (math.pi / 2)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)

        card_canvas.create_rectangle(
            x - 22, y - 33, x + 22, y + 33,
            fill=COLORS["selected"], outline=COLORS["gold_dim"], width=1
        )

        card_id = card_canvas.create_image(x, y, image=back_card_image)
        card_canvas.tag_bind(card_id, "<Button-1>", lambda e, cid=card_id: pick_card(cid))

        card_items.append(card_id)
        canvas_cards_map[card_id] = False
        card_id_to_name[card_id] = current_card_list[i]

    animate_orb()

# ------------------------------
# ฟังก์ชันสับไพ่พร้อมแอนิเมชันกระพริบ
# ------------------------------
def shuffle_cards():
    if len(selected_cards) > 0:
        if not messagebox.askyesno("สับไพ่", "การสับไพ่จะรีเซ็ตการเลือกปัจจุบัน ดำเนินการต่อ?"):
            return
        reset_prediction()   # reset แล้วจะมีการโหลด current_card_list ใหม่และสับอยู่แล้ว
    else:
        animate_shuffle_and_redraw()

def animate_shuffle_and_redraw():
    # ทำให้ไพ่กระพริบ (เปลี่ยนความโปร่งแสง) หลายครั้ง
    original_state = {}
    for card_id in card_items:
        original_state[card_id] = card_canvas.itemcget(card_id, "state")

    blink_count = 6  # จำนวนครั้งที่กระพริบ
    delay = 150      # ระยะห่างแต่ละครั้ง (ms)

    def blink_step(step):
        if step >= blink_count:
            # จบการกระพริบ: สับไพ่จริงและวาดใหม่
            random.shuffle(current_card_list)
            draw_card_circle()
            return
        # สลับสถานะแสดง/ซ่อนของไพ่ทุกใบ
        hide = (step % 2 == 0)  # เริ่มจากซ่อนก่อน
        for card_id in card_items:
            if canvas_cards_map.get(card_id, False):
                continue  # ข้ามไพ่ที่ถูกเลือกไปแล้ว (ถ้ามี)
            card_canvas.itemconfig(card_id, state="hidden" if hide else "normal")
        root.after(delay, lambda: blink_step(step + 1))

    # เริ่มขั้นตอนการกระพริบ
    blink_step(0)

# ------------------------------
# ฟังก์ชันเลือกไพ่
# ------------------------------
def pick_card(card_id):
    global selected_cards, max_picks

    if canvas_cards_map.get(card_id, True):
        return

    if len(selected_cards) >= max_picks:
        messagebox.showinfo(
            "✦ แจ้งเตือน",
            f"คุณเลือกครบ {max_picks} ใบแล้วค่ะ\nเลื่อนลงเพื่อดูคำทำนาย ✨"
        )
        return

    chosen_card = card_id_to_name.get(card_id)
    if not chosen_card:
        messagebox.showerror("ข้อผิดพลาด", "ไม่พบข้อมูลไพ่")
        return

    if chosen_card in selected_cards:
        return

    # แอนิเมชันเลือกไพ่ (วงเรืองแสง)
    x, y = card_canvas.coords(card_id)
    glow = card_canvas.create_oval(x-25, y-35, x+25, y+35,
                                    outline=COLORS["gold_light"], width=3, dash=(5,2))
    root.after(150, lambda: card_canvas.delete(glow))

    selected_cards.append(chosen_card)

    card_canvas.itemconfig(card_id, state="hidden")
    canvas_cards_map[card_id] = True

    remaining = max_picks - len(selected_cards)
    if remaining > 0:
        card_label.config(
            text=f"✦  เลือกแล้ว {len(selected_cards)}/{max_picks} ใบ  —  เหลืออีก {remaining} ใบ  ✦",
            fg=COLORS["teal"]
        )
    else:
        card_label.config(text="✦  ไพ่แห่งโชคชะตาถูกเปิดเผยแล้ว  ✦", fg=COLORS["gold_light"])
        reveal_cards()
        # เมื่อเลือกครบแล้ว ให้แสดงคำทำนายทั้งหมด
        show_all_predictions()

def show_all_predictions():
    """แสดงคำทำนายของไพ่ทุกใบที่เลือก (เรียกเมื่อเลือกครบ)"""
    category = category_var.get()

    # ล้าง container (แต่ header จะถูกสร้างใหม่)
    for widget in prediction_container.winfo_children():
        widget.destroy()
    image_refs.clear()

    # สร้าง header
    header_frame = tk.Frame(prediction_container, bg=COLORS["bg_dark"])
    header_frame.pack(fill="x", pady=(20, 5))
    tk.Label(
        header_frame,
        text="─── ✦ คำทำนายของคุณ ✦ ───",
        font=("Georgia", 16, "bold"),
        fg=COLORS["gold"],
        bg=COLORS["bg_dark"]
    ).pack()

    subtitle_map = {
        "daily":   "ดวงชะตาประจำวันนี้",
        "monthly": "ดวงชะตาประจำเดือน",
        "love":    "ดวงความรักและความสัมพันธ์",
        "career":  "ดวงการงานและความสำเร็จ",
    }
    tk.Label(
        header_frame,
        text=subtitle_map.get(category, ""),
        font=("Georgia", 11, "italic"),
        fg=COLORS["purple_light"],
        bg=COLORS["bg_dark"]
    ).pack(pady=(2, 10))

    # ขอคำทำนายทีละใบและสร้างการ์ด
    for i, card_name in enumerate(selected_cards, 1):
        prediction_text = get_prediction_from_server(card_name, category)
        create_prediction_card(card_name, prediction_text, i)

    # เส้นปิดท้าย
    tk.Label(
        prediction_container,
        text="─── ✦ ───",
        font=("Georgia", 12),
        fg=COLORS["gold_dim"],
        bg=COLORS["bg_dark"]
    ).pack(pady=(10, 20))

    # อัปเดต scroll region และเลื่อนลงมา
    scrollable_frame.update_idletasks()
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))
    root.after(100, lambda: main_canvas.yview_moveto(0.25))

def create_prediction_card(card_name, prediction_text, index):
    global image_refs
    outer = tk.Frame(prediction_container, bg=COLORS["gold_dim"], padx=1, pady=1)
    outer.pack(pady=12, padx=25, fill="x")

    inner = tk.Frame(outer, bg=COLORS["purple"], padx=1, pady=1)
    inner.pack(fill="both", expand=True)

    card_frame = tk.Frame(inner, bg=COLORS["bg_card"], padx=15, pady=15)
    card_frame.pack(fill="both", expand=True)

    # รูปไพ่
    img_frame = tk.Frame(card_frame, bg=COLORS["bg_card"])
    img_frame.pack(side="left", padx=(0, 15))

    filename = card_name.lower().replace(" ", "_") + ".jpg"
    if "_" in card_name:
        filename = card_name.lower() + ".jpg"
    image_path = os.path.join(image_folder, filename)

    if os.path.exists(image_path):
        img = Image.open(image_path).resize((90, 140), Image.LANCZOS)
        bordered = Image.new("RGB", (96, 146), (212, 175, 55))
        bordered.paste(img, (3, 3))
        photo = ImageTk.PhotoImage(bordered)
        img_label = tk.Label(img_frame, image=photo, bg=COLORS["bg_card"])
        img_label.config(image=photo)
        image_refs.append(photo)
    else:
        ph = make_gradient_image(90, 140, COLORS["bg_mid"], COLORS["purple"])
        ph_draw = ImageDraw.Draw(ph)
        ph_draw.rectangle([0, 0, 89, 139], outline=(212, 175, 55), width=2)
        ph_draw.text((45, 70), "☽", fill=(212, 175, 55), anchor="mm")
        photo = ImageTk.PhotoImage(ph)
        img_label = tk.Label(img_frame, image=photo, bg=COLORS["bg_card"])
        image_refs.append(photo)

    img_label.pack()

    badge_text = f"ใบที่ {index}" if max_picks > 1 else "ไพ่แห่งโชคชะตา"
    tk.Label(
        img_frame,
        text=badge_text,
        font=("Georgia", 8, "italic"),
        fg=COLORS["gold"],
        bg=COLORS["bg_card"]
    ).pack(pady=(4, 0))

    # ข้อความ
    text_frame = tk.Frame(card_frame, bg=COLORS["bg_card"])
    text_frame.pack(side="left", fill="both", expand=True)

    name_frame = tk.Frame(text_frame, bg=COLORS["bg_card"])
    name_frame.pack(fill="x", pady=(0, 8))

    display_name = card_name.replace("_", " ")
    tk.Label(
        name_frame,
        text=f"✦  {display_name}  ✦",
        font=("Georgia", 13, "bold"),
        fg=COLORS["gold_light"],
        bg=COLORS["bg_card"]
    ).pack(anchor="w")

    separator = tk.Frame(name_frame, bg=COLORS["gold_dim"], height=1)
    separator.pack(fill="x", pady=3)

    tk.Label(
        text_frame,
        text=prediction_text,
        font=("Georgia", 10),
        fg=COLORS["white"],
        bg=COLORS["bg_card"],
        justify="left",
        wraplength=290
    ).pack(anchor="w", fill="both", expand=True)

def reveal_cards():
    """แอนิเมชันเมื่อเลือกไพ่ครบ"""
    reveal_text = card_canvas.create_text(260, 170, text="✨ REVEALED ✨",
                                          font=("Georgia", 22, "bold"), fill=COLORS["gold"])
    root.after(1500, lambda: card_canvas.delete(reveal_text))

# ------------------------------
# GUI หลัก
# ------------------------------
root = tk.Tk()
root.title("✦ Fortune — Tarot Reading ✦")
root.geometry("560x820")
root.configure(bg=COLORS["bg_dark"])
root.resizable(False, True)

# Scrollable Frame
main_canvas = tk.Canvas(root, bg=COLORS["bg_dark"], highlightthickness=0)
main_scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview,
                               bg=COLORS["bg_mid"], troughcolor=COLORS["bg_dark"],
                               activebackground=COLORS["gold_dim"])
scrollable_frame = tk.Frame(main_canvas, bg=COLORS["bg_dark"])

scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)
canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

main_canvas.bind("<Configure>", lambda e: main_canvas.itemconfig(canvas_window, width=e.width))
main_canvas.configure(yscrollcommand=main_scrollbar.set)
main_canvas.pack(side="left", fill="both", expand=True)
main_scrollbar.pack(side="right", fill="y")

root.bind_all("<MouseWheel>", lambda e: main_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

# Header
header_bg = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
header_bg.pack(fill="x", pady=0)

top_bar = tk.Frame(header_bg, bg=COLORS["gold_dim"], height=2)
top_bar.pack(fill="x")

logo_frame = tk.Frame(header_bg, bg=COLORS["bg_dark"], pady=20)
logo_frame.pack(fill="x")

tk.Label(logo_frame, text="☽  ✦  ☾", font=("Georgia", 18),
         fg=COLORS["gold"], bg=COLORS["bg_dark"]).pack()
tk.Label(logo_frame, text="FORTUNE", font=("Georgia", 30, "bold"),
         fg=COLORS["gold_light"], bg=COLORS["bg_dark"]).pack()
tk.Label(logo_frame, text="T A R O T   R E A D I N G", font=("Georgia", 10),
         fg=COLORS["purple_light"], bg=COLORS["bg_dark"]).pack(pady=(2,0))
tk.Frame(header_bg, bg=COLORS["gold_dim"], height=1).pack(fill="x", padx=40)

# Category selector
cat_frame = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"], pady=18)
cat_frame.pack()

category_var = tk.StringVar(value="daily")

CAT_OPTIONS = [
    ("daily",   "☀  รายวัน"),
    ("monthly", "🌙  รายเดือน"),
    ("love",    "♡  ความรัก"),
    ("career",  "⚡  การงาน"),
]

btn_style = {
    "font": ("Georgia", 10),
    "relief": "flat",
    "cursor": "hand2",
    "padx": 14,
    "pady": 7,
    "bd": 0,
}

def update_category_buttons():
    for btn, val in cat_buttons:
        if category_var.get() == val:
            btn.config(bg=COLORS["gold"], fg=COLORS["bg_dark"], font=("Georgia", 10, "bold"))
        else:
            btn.config(bg=COLORS["bg_mid"], fg=COLORS["gray"], font=("Georgia", 10))

def select_category(val):
    category_var.set(val)
    update_category_buttons()
    reset_prediction()

cat_buttons = []
for val, label in CAT_OPTIONS:
    btn = tk.Button(cat_frame, text=label, command=lambda v=val: select_category(v),
                    bg=COLORS["bg_mid"], fg=COLORS["gray"], **btn_style)
    btn.pack(side="left", padx=4)
    cat_buttons.append((btn, val))

update_category_buttons()

# ปุ่มรีเซ็ตและปุ่มสับไพ่
btn_frame = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
btn_frame.pack(pady=5)

reset_btn = tk.Button(btn_frame, text="🔄  เริ่มทำนายใหม่", command=reset_prediction,
                      bg=COLORS["purple"], fg=COLORS["white"],
                      font=("Georgia", 11, "bold"), relief="flat", cursor="hand2",
                      padx=15, pady=8, activebackground=COLORS["purple_light"])
reset_btn.pack(side="left", padx=5)

shuffle_btn = tk.Button(btn_frame, text="♠  สับไพ่", command=shuffle_cards,
                        bg=COLORS["purple"], fg=COLORS["white"],
                        font=("Georgia", 11, "bold"), relief="flat", cursor="hand2",
                        padx=15, pady=8, activebackground=COLORS["purple_light"])
shuffle_btn.pack(side="left", padx=5)

# Hover effects
reset_btn.bind("<Enter>", lambda e: reset_btn.config(bg=COLORS["purple_light"]))
reset_btn.bind("<Leave>", lambda e: reset_btn.config(bg=COLORS["purple"]))
shuffle_btn.bind("<Enter>", lambda e: shuffle_btn.config(bg=COLORS["purple_light"]))
shuffle_btn.bind("<Leave>", lambda e: shuffle_btn.config(bg=COLORS["purple"]))

# Canvas สำหรับวงไพ่
canvas_container = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
canvas_container.pack(pady=5)

card_canvas = tk.Canvas(canvas_container, width=520, height=340,
                        bg=COLORS["bg_dark"], highlightthickness=0)
card_canvas.pack()

card_label = tk.Label(scrollable_frame,
                      text="✦  สัมผัสไพ่ที่คุณรู้สึกดึงดูด  1 ใบ  ✦",  # จะถูกอัปเดตใน reset_prediction
                      font=("Georgia", 12, "italic"),
                      fg=COLORS["gold_light"], bg=COLORS["bg_dark"])
card_label.pack(pady=(5,3))

tk.Frame(scrollable_frame, bg=COLORS["gold_dim"], height=1).pack(fill="x", padx=60, pady=8)

# Container สำหรับคำทำนาย
prediction_container = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"])
prediction_container.pack(fill="both", expand=True, pady=5)

# Footer
footer = tk.Frame(scrollable_frame, bg=COLORS["bg_dark"], pady=15)
footer.pack(fill="x")
tk.Label(footer, text="✦   The stars guide, the cards reveal   ✦",
         font=("Georgia", 9, "italic"), fg=COLORS["gray"], bg=COLORS["bg_dark"]).pack()
tk.Frame(footer, bg=COLORS["gold_dim"], height=2).pack(fill="x", padx=0, pady=(10,0))

# เริ่มต้นโปรแกรม
reset_prediction()
root.mainloop()
