# Quick Start Guide

## 🚀 เริ่มใช้งานระบบ

### วิธีที่ 1: ใช้ Batch Script (แนะนำ)
1. Double-click ไฟล์ `start.bat`
2. รอระบบเริ่มต้น
3. เปิดเบราว์เซอร์ไปที่ http://localhost:8000/dashboard

### วิธีที่ 2: ใช้ Command Line
```bash
# 1. Activate environment
landslide_env\Scripts\activate

# 2. Run system
python run.py
```

---

## 🔧 ตั้งค่าครั้งแรก

### 1. ติดตั้ง Dependencies (ครั้งแรกเท่านั้น)
```bash
landslide_env\Scripts\activate
pip install -r requirements.txt
```

### 2. Authenticate Google Earth Engine (ครั้งแรกเท่านั้น)
```bash
earthengine authenticate
```
- เปิดเบราว์เซอร์ตาม link ที่แสดง
- Login ด้วย Google Account
- Copy code กลับมาใส่ใน terminal

---

## 📊 การใช้งาน Dashboard

### หน้าจอหลัก
- **แผนที่**: แสดงจุดติดตาม 2,728 จุด
- **สถิติ**: จำนวนจุดแต่ละระดับความเสี่ยง
- **ฟิลเตอร์**: กรองแสดงเฉพาะระดับที่ต้องการ
- **ค้นหา**: ค้นหาตามอำเภอ, ตำบล

### สีหมุด
- 🔴 **แดง**: อันตราย (≥60%)
- 🟡 **เหลือง**: เฝ้าระวัง (30-60%)
- 🟢 **เขียว**: ปกติ (<30%)

### การดูรายละเอียด
- Click ที่หมุดบนแผนที่
- จะแสดง popup ข้อมูล:
  - ความน่าจะเป็น
  - ความชัน
  - ความสูง
  - NDVI (พืชพรรณ)
  - ปริมาณฝน

---

## ⏰ การอัปเดตข้อมูล

### อัตโนมัติ (Auto-update)
ระบบจะอัปเดตทุก 6 ชั่วโมง:
- 00:00 น.
- 06:00 น.
- 12:00 น.
- 18:00 น.

### ด้วยตนเอง (Manual)
1. กดปุ่ม "Manual Update" ใน dashboard
2. รอ 5-10 นาที (ขึ้นอยู่กับจำนวนจุด)
3. Dashboard จะ refresh อัตโนมัติ

---

## 🐛 แก้ปัญหา

### ปัญหา: ไม่สามารถเข้า Dashboard ได้
**วิธีแก้**:
1. ตรวจสอบว่า server รันอยู่หรือไม่
2. ลองเปลี่ยน port ใน `.env`:
   ```
   API_PORT=8080
   ```
3. เปิดเบราว์เซอร์ใหม่ไปที่ http://localhost:8080/dashboard

### ปัญหา: GEE Authentication Error
**วิธีแก้**:
```bash
earthengine authenticate
```

### ปัญหา: Model file not found
**วิธีแก้**:
- ตรวจสอบว่าไฟล์ `Northern_Landslide_Model_Final.pkl` อยู่ในโฟลเดอร์เดียวกับ `run.py`

### ปัญหา: Dependencies ไม่ครบ
**วิธีแก้**:
```bash
landslide_env\Scripts\activate
pip install -r requirements.txt
```

---

## 📖 API Documentation

เปิดเบราว์เซอร์ไปที่: http://localhost:8000/docs

จะเห็น API endpoints ทั้งหมดพร้อมทดสอบได้เลย

---

## 🔒 Security Notes

- ระบบนี้ออกแบบสำหรับใช้ภายใน (localhost)
- ถ้าต้องการเปิดให้เข้าถึงจากภายนอก:
  1. เปลี่ยน `API_HOST` ใน `.env` เป็น `0.0.0.0`
  2. ตั้งค่า firewall
  3. พิจารณาเพิ่ม authentication

---

## 📞 ติดต่อ

หากมีปัญหาหรือข้อสงสัย กรุณาติดต่อทีมพัฒนา
