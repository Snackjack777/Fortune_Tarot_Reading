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
        ref = db.reference("/")
        all_data = ref.get()

        if not all_data:
            return "ไม่พบข้อมูลในฐานข้อมูล"

        # ปรับรูปแบบการค้นหาให้รองรับทั้งชื่อแบบมีช่องว่างและไม่มีช่องว่าง
        # และชื่อแบบต่างๆ ที่อาจมีใน Firebase
        
        # กรณีที่ 1: ค้นหาชื่อตรงๆ
        if card_name in all_data:
            card_data = all_data[card_name]
            if category in card_data:
                return card_data[category]
        
        # กรณีที่ 2: ลองแทนที่ underscore ด้วยช่องว่าง
        card_name_with_space = card_name.replace("_", " ")
        if card_name_with_space in all_data:
            card_data = all_data[card_name_with_space]
            if category in card_data:
                return card_data[category]
        
        # กรณีที่ 3: ลองแทนที่ช่องว่างด้วย underscore
        card_name_with_underscore = card_name.replace(" ", "_")
        if card_name_with_underscore in all_data:
            card_data = all_data[card_name_with_underscore]
            if category in card_data:
                return card_data[category]
        
        # กรณีที่ 4: ค้นหาแบบ case-insensitive
        for key in all_data.keys():
            if key.lower() == card_name.lower() or key.lower() == card_name_with_space.lower() or key.lower() == card_name_with_underscore.lower():
                card_data = all_data[key]
                if category in card_data:
                    return card_data[category]
                break
        
        # ถ้าไม่พบข้อมูล
        return f"ไม่พบคำทำนายสำหรับ {card_name} หมวด {category}"

    except Exception as e:
        return f"เกิดข้อผิดพลาด: {str(e)}"

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
            print(f"Sent response to {addr}: {prediction_result}")
        else:
            error_msg = "รูปแบบข้อมูลไม่ถูกต้อง ต้องเป็น 'ชื่อไพ่,หมวดหมู่'"
            server.sendto(error_msg.encode('utf-8'), addr)
            
    except Exception as e:
        print(f"Server Error: {e}")
        try:
            server.sendto(f"Server error: {str(e)}".encode('utf-8'), addr)
        except:
            pass
