import socket
import json
import random
# จากเดิม: from cards import tarot_cards
# แนะนำ: หากใช้ Database ออนไลน์ ให้ใช้ library เช่น firebase-admin หรือ mysql-connector-python
# ในที่นี้จะขอใช้ตัวแปร tarot_cards แทนข้อมูลที่ดึงมาจาก DB

import cards # ไฟล์ cards.py เดิม (จำลองเป็น Local DB)
tarot_data = cards.tarot_cards 

UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

all_card_keys = list(tarot_data.keys())
client_sessions = {} 

print(f"✅ Tarot Server Online (Ready for Database Integration)...")

while True:
    try:
        data, addr = sock.recvfrom(1024)
        msg = json.loads(data.decode('utf-8'))
        command = msg.get("command")

        # สร้าง Session หรือ Reset
        if addr not in client_sessions or command == "RESET":
            client_sessions[addr] = []
            print(f"[*] Session Reset for {addr}")
            if command == "RESET":
                sock.sendto(json.dumps({"status": "reset_ok"}).encode('utf-8'), addr)
                continue

        if command == "GET_SHUFFLE":
            used = client_sessions[addr]
            # กรองไพ่ที่ไม่ซ้ำกับที่เลือกไว้แล้ว
            available = [i for i in range(len(all_card_keys)) if i not in used]
            
            # สุ่ม 15 ใบ (ถ้าเหลือน้อยกว่า 15 ก็เอาเท่าที่มี)
            sample_count = min(15, len(available))
            shuffled = random.sample(available, sample_count)
            
            sock.sendto(json.dumps({"indices": shuffled}).encode('utf-8'), addr)

        elif command == "MARK_USED":
            idx = msg.get("index")
            if idx is not None and idx not in client_sessions[addr]:
                client_sessions[addr].append(idx)
                print(f"[+] Card {idx} saved to User Session at {addr}")
                
    except Exception as e:
        print(f"Error: {e}")