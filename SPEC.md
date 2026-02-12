# Problem

- Students have notes scattered across PDFs/DOCX and don’t know how to practice effectively.
- They want fast practice questions that match their material.

# Target user

- High school / college students studying from teacher PDFs and their own notes.

# MVP: What it does

- Import PDF + DOCX into a local library.
- Build a local index (chunks).
- Generate a set of practice questions (MCQ first).
- Practice mode: answer → show correct answer + evidence snippet + source (doc + page).
- Track results and allow retry missed.

# MVP: What it does NOT do (non-goals)

- No cloud upload.
- No public doc bank.
- No OCR (scanned PDFs unsupported).
- No free-form grading (MCQ/cloze only in MVP).
- No macOS/Linux support initially (Windows only).
- Trust rule (non-negotiable)
- Every question must include an evidence quote from the imported text.
- If evidence cannot be verified in the extracted text, discard/regenerate.
- Success metrics (pick numbers you can measure)
- Import time: import a 30-page PDF in under ___ seconds on my laptop.
- Generation time: generate 30 questions in under ___ minutes.
- Reliability: 95%+ of questions are valid JSON (parseable).
- Evidence validation: 80%+ of questions contain verifiable evidence (Week 6 goal; write it now anyway).
- User outcome: student can finish a 20-question session and review misses.

# Risks

- PDF extraction noise (headers/footers, broken lines).
- LLM hallucination → wrong answers.
- Low-end PCs → slow generation.

# First release platform

- Windows 10/11.