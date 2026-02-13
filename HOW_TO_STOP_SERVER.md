# วิธีหยุด Server ที่รันค้างอยู่

## 🛑 ปัญหา: Server ยังรันอยู่แม้ปิด Antigravity

เมื่อรัน server ด้วย background command มันจะรันต่อไปเรื่อยๆ แม้ปิดโปรแกรม

## 🔍 วิธีตรวจสอบว่า Server ยังรันอยู่หรือไม่

### วิธีที่ 1: เช็ค Port
```powershell
netstat -ano | findstr :8000
```

จะเห็น:
```
TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    24136
                                                  ^^^^^ PID
```

### วิธีที่ 2: เช็ค Python Process
```powershell
Get-Process python | Where-Object {$_.Path -like '*landslide_env*'}
```

## 🛑 วิธีหยุด Server

### วิธีที่ 1: ใช้ PID จาก netstat
```powershell
# หา PID
netstat -ano | findstr :8000

# หยุด process (เปลี่ยน 24136 เป็น PID ที่เจอ)
taskkill /PID 24136 /F
```

### วิธีที่ 2: หยุดทุก Python process ใน landslide_env
```powershell
Get-Process python | Where-Object {$_.Path -like '*landslide_env*'} | Stop-Process -Force
```

### วิธีที่ 3: ใช้ Task Manager
1. เปิด Task Manager (`Ctrl+Shift+Esc`)
2. ไปที่แท็บ "Details"
3. หา `python.exe` ที่มี PID ตรงกับที่เจอ
4. Right-click → End Task

## ✅ ตรวจสอบว่าหยุดสำเร็จ

ลองเปิด http://localhost:8000/dashboard

- ถ้าหยุดสำเร็จ: จะขึ้น "This site can't be reached"
- ถ้ายังรันอยู่: จะเห็นหน้า dashboard

## 🚀 วิธีรัน Server ใหม่

```powershell
cd C:\Users\nongt\OneDrive\Desktop\AI-study\cola\model
.\landslide_env\Scripts\python.exe run.py
```

หรือ

```powershell
.\landslide_env\Scripts\python.exe test_manual.py
```

## 💡 Tips

- ใช้ `Ctrl+C` เพื่อหยุด server ที่รันใน terminal
- ถ้ารันแบบ background จะต้องใช้ `taskkill` เท่านั้น
- ตรวจสอบ port ก่อนรันใหม่เสมอ
