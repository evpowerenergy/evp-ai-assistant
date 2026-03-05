# 🤖 How to Change LLM Model

## 📋 Overview

ระบบใช้ **OpenAI API** สำหรับ LLM มี **2 จุด** ที่ต้องเปลี่ยน model:

1. **LLM Router** - Intent analysis และ function calling
2. **Generate Response** - สร้าง response ตอบกลับ user

---

## 🎯 Locations to Change Model

### 1. **LLM Router** (Intent Analysis & Function Calling)

📁 `backend/app/orchestrator/llm_router.py`

**Line:** ~188

**Current:**
```python
response = await client.chat.completions.create(
    model="gpt-5-mini",  # ← Change this
    messages=openai_messages,
    tools=TOOL_SCHEMAS,
    tool_choice="auto",
    temperature=0.3
)
```

**Change to:**
```python
response = await client.chat.completions.create(
    model="gpt-5-mini",  # หรือ "gpt-3.5-turbo"
    messages=openai_messages,
    tools=TOOL_SCHEMAS,
    tool_choice="auto",
    temperature=0.3
)
```

---

### 2. **Generate Response** (Final Response Generation)

📁 `backend/app/services/llm.py`

**Line:** ~14

**Current:**
```python
def get_llm(temperature: float = 0.7, model: str = "gpt-4") -> ChatOpenAI:
    """
    Get or create OpenAI LLM instance
    """
    global _llm
    
    if _llm is None:
        try:
            _llm = ChatOpenAI(
                model=model,  # ← Default is "gpt-4"
                temperature=temperature,
                openai_api_key=settings.OPENAI_API_KEY
            )
```

**Change to:**
```python
def get_llm(temperature: float = 0.7, model: str = "gpt-4-turbo") -> ChatOpenAI:  # ← Change default here
    """
    Get or create OpenAI LLM instance
    """
    global _llm
    
    if _llm is None:
        try:
            _llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=settings.OPENAI_API_KEY
            )
```

---

## 🎯 Recommended Approach: Use Environment Variable

**แนะนำ:** ใช้ environment variable แทน hardcode เพื่อให้เปลี่ยนง่าย

### Step 1: Add to Config

📁 `backend/app/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"  # ← Add this (default: gpt-4)
```

### Step 2: Update LLM Router

📁 `backend/app/orchestrator/llm_router.py`

```python
from app.config import settings

response = await client.chat.completions.create(
    model=settings.OPENAI_MODEL,  # ← Use from settings
    messages=openai_messages,
    tools=TOOL_SCHEMAS,
    tool_choice="auto",
    temperature=0.3
)
```

### Step 3: Update LLM Service

📁 `backend/app/services/llm.py`

```python
from app.config import settings

def get_llm(temperature: float = 0.7, model: str = None) -> ChatOpenAI:
    """
    Get or create OpenAI LLM instance
    """
    global _llm
    
    # Use default from settings if not provided
    if model is None:
        model = settings.OPENAI_MODEL
    
    if _llm is None:
        try:
            _llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=settings.OPENAI_API_KEY
            )
```

### Step 4: Add to .env

📁 `backend/.env`

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo  # ← Add this
```

---

## 📋 Available Models

### OpenAI Models:

| Model | Description | Cost | Best For |
|-------|-------------|------|----------|
| `gpt-4` | GPT-4 (standard) | High | Best quality |
| `gpt-4-turbo` | GPT-4 Turbo | Medium | Faster, cheaper |
| `gpt-4-turbo-preview` | GPT-4 Turbo Preview | Medium | Latest features |
| `gpt-3.5-turbo` | GPT-3.5 Turbo | Low | Faster, cheaper |
| `gpt-3.5-turbo-16k` | GPT-3.5 Turbo (16k context) | Low | Longer context |

---

## 🔧 Quick Change (Manual)

### Option 1: Change Both Files Manually

1. **LLM Router:**
   - Open: `backend/app/orchestrator/llm_router.py`
   - Line ~188: Change `model="gpt-4"` to `model="gpt-4-turbo"`

2. **LLM Service:**
   - Open: `backend/app/services/llm.py`
   - Line ~14: Change `model: str = "gpt-4"` to `model: str = "gpt-4-turbo"`

### Option 2: Use Environment Variable (Recommended)

1. Add to `.env`:
   ```env
   OPENAI_MODEL=gpt-4-turbo
   ```

2. Update config (see above)

3. Update code to use `settings.OPENAI_MODEL`

---

## ⚠️ Important Notes

### 1. **Function Calling Support**

บาง model อาจไม่รองรับ function calling:
- ✅ `gpt-4` - รองรับ function calling
- ✅ `gpt-4-turbo` - รองรับ function calling
- ✅ `gpt-3.5-turbo` - รองรับ function calling
- ❌ `gpt-3.5-turbo-instruct` - **ไม่รองรับ** function calling (chat model only)

### 2. **Cost Consideration**

| Model | Cost (approx) | Speed |
|-------|---------------|-------|
| `gpt-4` | Highest | Slowest |
| `gpt-4-turbo` | Medium | Fast |
| `gpt-3.5-turbo` | Lowest | Fastest |

### 3. **Quality vs Speed**

- **Best Quality:** `gpt-4` or `gpt-4-turbo`
- **Best Speed:** `gpt-3.5-turbo`
- **Best Balance:** `gpt-4-turbo`

---

## 🚀 After Changing Model

1. **Restart Backend:**
   ```bash
   # Stop current backend
   # Start again
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. **Test:**
   - Test intent analysis (function calling)
   - Test response generation
   - Check if model supports function calling

---

## 📝 Example Changes

### Change to GPT-4 Turbo:

**Before:**
```python
model="gpt-4"
```

**After:**
```python
model="gpt-4-turbo"
```

### Change to GPT-3.5 Turbo:

**Before:**
```python
model="gpt-4"
```

**After:**
```python
model="gpt-3.5-turbo"
```

---

## 🔍 Verify Model Change

### Check Logs:

เมื่อเปลี่ยน model แล้ว ดู logs:

```bash
# LLM Router log
🔧 Calling OpenAI API with function calling...
   Model: gpt-4-turbo  # ← Check this

# LLM Service log
LLM initialized: gpt-4-turbo  # ← Check this
```

---

## 📝 Summary

**จุดที่ต้องเปลี่ยน model:**
1. `backend/app/orchestrator/llm_router.py` - line ~188
2. `backend/app/services/llm.py` - line ~14

**แนะนำ:**
- ใช้ environment variable (`OPENAI_MODEL`)
- Update config และ code ให้ใช้ `settings.OPENAI_MODEL`

**Models ที่แนะนำ:**
- `gpt-4-turbo` - Best balance (quality + speed)
- `gpt-4` - Best quality
- `gpt-3.5-turbo` - Best speed/cost
