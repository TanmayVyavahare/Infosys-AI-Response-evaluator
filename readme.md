# AI Response Quality Evaluator

**Aegis** is an automated, reference-grounded AI Response Quality Evaluator designed to audit LLM responses based on **relevance, accuracy, groundedness, and completeness**.

It evaluates AI responses using four main criteria:

- **Relevance:** Did the AI actually answer the user's question?
- **Accuracy:** Is the information factually correct?
- **Groundedness:** Did the AI stick to the provided source documents, or did it hallucinate?
- **Completeness:** Did the AI address all parts of the question?

---
## 🛠️ Technology Stack
* **Frontend**: React, TypeScript, Vite, Tailwind CSS
* **Backend**: FastAPI, LangChain, FAISS (Vector DB), SQL, Sentence Transformers (`all-MiniLM-L6-v2`)
---


## ⚡ Quick Start

 Local Installation

#### 1. Backend Service (Python 3.10+)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### 2. Frontend Client (Node.js 18+)
```bash
cd frontend
npm install
npm run dev
```

---

## 📡 Core API Reference

### 1. Evaluate Response
* **Route**: `POST /api/evaluate`
* **Request Payload**:
  ```json
  {
    "question": "What is the speed of light?",
    "ai_response": "The speed of light is 299,792,458 meters per second in a vacuum.",
    "reference_answer": "Light travels at exactly 299,792,458 m/s in a vacuum.",
    "source_document": "Standard physical constants state that light speed (c) is 299,792,458 m/s."
  }
  ```

### 2. Upload Custom Document
* **Route**: `POST /api/upload-document` (multipart/form-data)
* **Payload**: `file` field.

---

## 📁 Repository Structure
* [backend/](file:///C:/Users/ACER/Desktop/ai%20evaluate/backend/) - Python FastAPI application, database schemas, and multi-agent evaluator engines.
* [frontend/](file:///C:/Users/ACER/Desktop/ai%20evaluate/frontend/) - React dashboard build with Vite, TypeScript, and Tailwind CSS.
*[readme.md]
