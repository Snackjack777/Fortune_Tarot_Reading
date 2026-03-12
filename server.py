import socket
import json
import firebase_admin
from firebase_admin import credentials, db
import sys

# บังคับ stdout ให้เป็น UTF-8 เพื่อดู Log ภาษาไทยได้
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# --- 1. การตั้งค่า Firebase Admin SDK ---
cred = credentials.Certificate(r"D:\python69\FT2\FTR.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://fortunetarot888-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

def get_prediction(card_name, category):
    try:
        # แก้ไข: ตรวจสอบโครงสร้างข้อมูลใน Firebase ก่อน
        ref = db.reference("tarot")
        all_data = ref.get()
        
        if not all_data:
            return "ไม่พบข้อมูลในฐานข้อมูล"
        
        print(f"Data structure: {type(all_data)}")  # debug
        
        # กรณีที่ 1: โครงสร้างเป็น /tarot/{card_name}/{category}
        if isinstance(all_data, dict) and card_name in all_data:
            card_data = all_data[card_name]
            if isinstance(card_data, dict) and category in card_data:
                return card_data[category]
        
        # กรณีที่ 2: โครงสร้างเป็น /tarot/{category}/{card_name}
        if isinstance(all_data, dict) and category in all_data:
            category_data = all_data[category]
            if isinstance(category_data, dict) and card_name in category_data:
                return category_data[card_name]
        
        # กรณีที่ 3: โครงสร้างเป็น list ของไพ่
        if isinstance(all_data, list):
            for card in all_data:
                if isinstance(card, dict):
                    if card.get('name') == card_name:
                        return card.get(category, "ไม่พบคำทำนาย")
        
        # กรณีที่ 4: ลองค้นหาแบบ case-insensitive
        card_name_lower = card_name.lower()
        for key in all_data.keys():
            if key.lower() == card_name_lower:
                card_data = all_data[key]
                if isinstance(card_data, dict) and category in card_data:
                    return card_data[category]
        
        return f"ไม่พบคำทำนายสำหรับไพ่ '{card_name}' ในหมวดหมู่ '{category}'"
        
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการดึงข้อมูล: {str(e)}"

# --- 2. การตั้งค่า UDP Server ---
HOST = "0.0.0.0"
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((HOST, PORT))

print(f"Tarot UDP Server Started on {HOST}:{PORT}")
print("Waiting for clients...")

while True:
    try:
        # รับข้อมูลจาก Client
        data, addr = server.recvfrom(4096)
        message = data.decode('utf-8')
        
        print(f"Received from {addr}: {message}")
        
        if "," in message:
            card, category = message.split(",", 1)  # split only first comma
            card = card.strip()
            category = category.strip()
            
            print(f"Processing: Card='{card}', Category='{category}'")
            
            # ดึงคำทำนายจาก Firebase
            prediction_result = get_prediction(card, category)
            
            # ส่งข้อมูลกลับ (แปลงเป็น JSON string เพื่อรองรับภาษาไทย)
            response = json.dumps(prediction_result, ensure_ascii=False)
            server.sendto(response.encode('utf-8'), addr)
            print(f"Sent response to {addr}")
        else:
            error_msg = "รูปแบบข้อมูลไม่ถูกต้อง ต้องเป็น 'ชื่อไพ่,หมวดหมู่'"
            server.sendto(error_msg.encode('utf-8'), addr)
            
    except Exception as e:
        print(f"Server Error: {e}")
        try:
            server.sendto(f"Server error: {str(e)}".encode('utf-8'), addr)
        except:
            pass
