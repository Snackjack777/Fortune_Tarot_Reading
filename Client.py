# server.py
"""
UDP Server สำหรับให้บริการข้อมูลไพ่ทาโรต์
รับคำขอจาก client และส่งข้อมูลไพ่กลับไป
"""

import socket
import json
import threading
from cards import get_all_cards, get_card_prediction, get_cards_by_category

# การตั้งค่าเซิร์ฟเวอร์
UDP_IP = "127.0.0.1"  # localhost
UDP_PORT = 5005
BUFFER_SIZE = 65536  # เพิ่ม buffer size สำหรับข้อมูลขนาดใหญ่

# สร้าง UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(1.0)  # timeout 1 วินาที เพื่อให้สามารถตรวจสอบการปิดโปรแกรมได้

print(f"✨ Tarot Card Server กำลังทำงานที่ {UDP_IP}:{UDP_PORT}")
print("รอรับคำขอจาก client...")

running = True

def handle_request(data, addr):
    """จัดการคำขอจาก client"""
    try:
        # แปลงข้อมูล JSON ที่ได้รับ
        request = json.loads(data.decode('utf-8'))
        command = request.get('command', '')
        
        print(f"📨 ได้รับคำขอ: {command} จาก {addr}")
        
        response = {"status": "error", "message": "ไม่พบคำสั่งที่ระบุ"}
        
        if command == 'get_all_cards':
            # ส่งรายชื่อไพ่ทั้งหมด
            cards = get_all_cards()
            response = {
                "status": "success",
                "command": command,
                "data": cards,
                "count": len(cards)
            }
            
        elif command == 'get_card_prediction':
            # ส่งคำทำนายของไพ่เฉพาะ
            card_name = request.get('card_name', '')
            category = request.get('category', 'daily')
            
            if card_name:
                prediction = get_card_prediction(card_name, category)
                response = {
                    "status": "success",
                    "command": command,
                    "card_name": card_name,
                    "category": category,
                    "prediction": prediction
                }
            else:
                response = {"status": "error", "message": "ไม่พบชื่อไพ่"}
                
        elif command == 'get_cards_by_category':
            # ส่งรายชื่อไพ่ที่มีคำทำนายสำหรับหมวดหมู่ที่กำหนด
            category = request.get('category', 'daily')
            cards = get_cards_by_category(category)
            response = {
                "status": "success",
                "command": command,
                "category": category,
                "data": cards,
                "count": len(cards)
            }
            
        elif command == 'shuffle_deck':
            # สับไพ่ (server-side shuffling)
            category = request.get('category', None)
            if category:
                cards = get_cards_by_category(category)
            else:
                cards = get_all_cards()
                
            # สับไพ่ (server-side)
            import random
            shuffled = cards.copy()
            random.shuffle(shuffled)
            
            response = {
                "status": "success",
                "command": command,
                "category": category,
                "data": shuffled,
                "count": len(shuffled)
            }
            
        elif command == 'ping':
            # ทดสอบการเชื่อมต่อ
            response = {
                "status": "success",
                "command": command,
                "message": "pong"
            }
            
        elif command == 'shutdown':
            # ปิดเซิร์ฟเวอร์
            global running
            running = False
            response = {
                "status": "success",
                "command": command,
                "message": "เซิร์ฟเวอร์กำลังจะปิดตัวลง"
            }
            
        # ส่ง response กลับไปยัง client
        sock.sendto(json.dumps(response, ensure_ascii=False).encode('utf-8'), addr)
        print(f"📤 ส่งข้อมูลกลับไปยัง {addr} เรียบร้อย")
        
    except json.JSONDecodeError:
        error_msg = {"status": "error", "message": "ข้อมูล JSON ไม่ถูกต้อง"}
        sock.sendto(json.dumps(error_msg).encode('utf-8'), addr)
        print(f"⚠️ ข้อผิดพลาด: JSON ไม่ถูกต้องจาก {addr}")
        
    except Exception as e:
        error_msg = {"status": "error", "message": f"เกิดข้อผิดพลาด: {str(e)}"}
        sock.sendto(json.dumps(error_msg).encode('utf-8'), addr)
        print(f"❌ ข้อผิดพลาด: {str(e)}")

# รันเซิร์ฟเวอร์
try:
    while running:
        try:
            # รับข้อมูลจาก client
            data, addr = sock.recvfrom(BUFFER_SIZE)
            
            # จัดการคำขอใน thread แยก เพื่อไม่ให้ blocking
            thread = threading.Thread(target=handle_request, args=(data, addr))
            thread.daemon = True
            thread.start()
            
        except socket.timeout:
            # timeout เพื่อให้สามารถตรวจสอบ running flag ได้
            continue
            
except KeyboardInterrupt:
    print("\n👋 กำลังปิดเซิร์ฟเวอร์...")
    
finally:
    sock.close()
    print("✅ เซิร์ฟเวอร์ปิดการทำงานเรียบร้อย")
