# 📚 Vector Store Explanation

> **คำถาม:** Vector Store ใช้ทำอะไร? ต้องเก็บข้อมูลเป็น vector หรือไม่?

---

## 🎯 สรุปสั้นๆ

**Vector Store ใช้สำหรับ Document RAG เท่านั้น**  
**ไม่ใช่สำหรับข้อมูล business (leads, customers, sales, etc.)**

---

## 📊 สองระบบแยกกัน

### 1. **Database RPC Functions** (สำหรับข้อมูล Business)
- ✅ ใช้สำหรับข้อมูล business: leads, customers, sales, inventory, etc.
- ✅ เก็บในตารางปกติ (ไม่ใช่ vector)
- ✅ Query ผ่าน RPC functions (15 functions)
- ✅ ใช้ SQL queries ตามปกติ

**ตัวอย่าง:**
- "สถานะ lead A" → ใช้ `ai_get_lead_status()`
- "ยอด lead วันนี้" → ใช้ `ai_get_daily_summary()`
- "ข้อมูลลูกค้า B" → ใช้ `ai_get_customer_info()`

### 2. **Vector Store (RAG)** (สำหรับเอกสาร/ความรู้)
- ✅ ใช้สำหรับเอกสาร/ความรู้: SOPs, manuals, documents, policies
- ✅ เก็บเป็น vector embeddings
- ✅ ใช้ semantic search (ค้นหาความหมาย)
- ✅ ใช้สำหรับตอบคำถามเกี่ยวกับเอกสาร

**ตัวอย่าง:**
- "ขั้นตอนขออนุมัติ X" → ใช้ RAG search ในเอกสาร
- "นโยบายการลา" → ใช้ RAG search ในเอกสาร
- "วิธีใช้งานระบบ Y" → ใช้ RAG search ในเอกสาร

---

## 🔄 ระบบทำงานอย่างไร

### Intent Router จะตัดสินใจ:

```
User Question
    ↓
Intent Router
    ↓
    ├─→ ถามข้อมูล Business? → Database RPC Functions
    │   (leads, customers, sales, etc.)
    │
    ├─→ ถามเอกสาร/ความรู้? → Vector Store (RAG)
    │   (SOPs, manuals, policies)
    │
    └─→ ไม่ชัดเจน? → Clarify
```

---

## 📁 Database Schema

### ตาราง Business (ไม่ใช่ Vector)
```sql
-- ข้อมูล business เก็บในตารางปกติ
leads, customers, sales_docs, quotations, etc.
-- Query ผ่าน RPC functions
```

### ตาราง Vector Store (สำหรับ RAG)
```sql
-- kb_documents: เก็บ metadata ของเอกสาร
CREATE TABLE kb_documents (
    id UUID PRIMARY KEY,
    title TEXT,
    file_path TEXT,
    file_type TEXT,
    ...
);

-- kb_chunks: เก็บ chunks ของเอกสาร + vector embeddings
CREATE TABLE kb_chunks (
    id UUID PRIMARY KEY,
    document_id UUID,
    content TEXT,              -- เนื้อหาข้อความ
    embedding vector(1536),    -- Vector embedding (OpenAI)
    chunk_index INTEGER,
    metadata JSONB,
    ...
);
```

---

## 🔍 Vector Store ทำงานอย่างไร

### 1. Document Ingestion (อัปโหลดเอกสาร)
```
เอกสาร PDF/DOCX
    ↓
Chunk (แบ่งเป็นส่วนๆ)
    ↓
Generate Embeddings (แปลงเป็น vector)
    ↓
Store in kb_chunks (เก็บ vector + content)
```

### 2. Search (ค้นหาเอกสาร)
```
User Question: "ขั้นตอนขออนุมัติ"
    ↓
Generate Query Embedding (แปลงคำถามเป็น vector)
    ↓
Vector Similarity Search (ค้นหา chunks ที่คล้ายกัน)
    ↓
Return Relevant Chunks + Citations
```

---

## 💡 ตัวอย่างการใช้งาน

### Use Case 1: ถามข้อมูล Business
```
User: "สถานะ lead A"
    ↓
Intent: db_query
    ↓
Tool: ai_get_lead_status("A", user_id)
    ↓
Result: ข้อมูลจากตาราง leads (ไม่ใช่ vector)
```

### Use Case 2: ถามเอกสาร
```
User: "ขั้นตอนขออนุมัติ X"
    ↓
Intent: rag_query
    ↓
Vector Search: search_similar("ขั้นตอนขออนุมัติ X")
    ↓
Result: Chunks จากเอกสารที่เกี่ยวข้อง + citations
```

---

## ✅ สรุป

### ข้อมูล Business
- ❌ **ไม่ต้อง** เก็บเป็น vector
- ✅ เก็บในตารางปกติ
- ✅ Query ผ่าน RPC functions
- ✅ ใช้ SQL queries

### เอกสาร/ความรู้
- ✅ **ต้อง** เก็บเป็น vector
- ✅ เก็บใน `kb_chunks` table
- ✅ ใช้ semantic search
- ✅ ใช้สำหรับ RAG

---

## 🎯 คำตอบ

**Q: ต้องเก็บข้อมูลเป็น vector หรือไม่?**  
**A:** 
- ❌ **ข้อมูล business ไม่ต้อง** (leads, customers, sales, etc.)
- ✅ **เอกสาร/ความรู้ต้อง** (SOPs, manuals, documents)

**Q: Vector Store ช่วย search อย่างไร?**  
**A:**
- ช่วยค้นหาเอกสารที่เกี่ยวข้องกับคำถาม
- ใช้ semantic search (ค้นหาความหมาย ไม่ใช่แค่ keyword)
- ใช้สำหรับ RAG (Retrieval-Augmented Generation)

---

**Last Updated:** 2025-01-16
