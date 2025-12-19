# 🧠 Multi-Step Reasoning Agent (Planner → Executor → Verifier) with Streamlit + Self-Correction

## 📋 Project Overview
This project implements a **local multi-step reasoning agent** that solves structured questions (math, time, and simple logic) using a robust **Planner → Executor → Verifier** loop.

The system is designed to:
- produce a **clean final answer**
- **self-check** correctness using an independent verifier pass
- **retry with feedback** when incorrect
- provide a **user-safe explanation** (no raw step-by-step chain-of-thought shown to end users)
- expose **debug metadata** for engineers (plan + verification logs)

It runs fully locally using **Ollama** (default model: `llama3.1:8b`) and includes:
- a CLI test runner (`main.py`)
- a Streamlit UI (`streamlit_app.py`)

---

## 💡 The Problem
When an LLM answers multi-step questions, it often:
- makes arithmetic mistakes (especially time subtraction / borrowing),
- produces an answer with confident but wrong reasoning,
- or fails silently without a reliable correctness check.

This project solves that by enforcing a structured pipeline:

1. **Plan**: break the problem into a short step-by-step plan (no solving).
2. **Execute**: follow the plan and compute the answer.
3. **Verify**: independently re-solve, check constraints, and compare results.
4. **Retry**: if verification fails, re-plan using verifier feedback and try again.

---

## 🧱 Architecture
### ✅ Planner → Executor → Verifier
The agent is implemented as a loop with retries:

- **Planner**
  - Outputs a concise numbered plan.
  - Must *not* solve the problem (prevents early anchoring and hallucinated intermediate values).

- **Executor**
  - Executes the plan step-by-step.
  - Must end with the exact output marker:
    ```
    FINAL ANSWER: <short answer>
    ```
  - Includes special guardrails for time arithmetic.

- **Verifier**
  - Independently re-solves the question.
  - Checks constraints.
  - Compares with the executor’s proposed solution.
  - Returns strict JSON:
    ```json
    {
      "passed": true,
      "feedback": "Concise explanation (max 2 sentences).",
      "corrected_answer": null
    }
    ```

### 🔁 Self-Correction Loop
If the verifier fails, the agent retries up to `max_retries` times:
- The **verifier’s feedback** is injected into a corrected planner prompt.
- The executor runs again with the updated plan.

---

## 🧾 Prompt System (Why it’s designed this way)
All prompts live in `prompts.py` and are intentionally separated by role:

### 1) `PLANNER_PROMPT`
**Goal:** produce a plan only (no solving).
- This reduces early mistakes and prevents the planner from anchoring the executor with wrong calculations.

### 2) `PLANNER_WITH_FEEDBACK_PROMPT`
**Goal:** generate a *new corrected plan* using verifier feedback.
- This is the core “self-healing” mechanism: failed attempts become training signal for replanning.

### 3) `EXECUTOR_PROMPT`
**Goal:** execute the plan and compute the answer.
- Enforces deterministic extraction using:
  - `FINAL ANSWER:` marker (regex-extracted in code)
- Includes **time calculation rules**:
  - Convert both times to **minutes-from-midnight**
  - Subtract in minutes
  - Convert back to hours/minutes only at the end

### 4) `VERIFIER_PROMPT`
**Goal:** independently re-solve and validate.
- Also enforces minutes-from-midnight for time problems.
- Outputs strict JSON so the code can reliably gate success/failure.

### 5) `FINAL_FORMATTER_PROMPT`
**Goal:** produce user-facing explanation **without** exposing raw chain-of-thought.
- Explicitly forbids:
  - “Step 1 / Step 2”
  - raw calculations
  - internal scratch reasoning

### 6) `FAILURE_SUMMARIZER_PROMPT`
**Goal:** if all retries fail, generate a user-friendly explanation of why.
- Keeps the user experience clean while engineering logs remain in metadata.

---

## ✨ Key Features

### ✅ Deterministic Answer Extraction (anti-hallucination)
The final answer is extracted using a regex from:

Fallbacks (in order):
1. Regex extraction from executor output (most reliable)
2. Verifier’s `corrected_answer` (if provided)
3. Formatter’s extracted answer (last resort)

### ✅ Robust Time Arithmetic
Time subtraction is a frequent failure mode.
Both executor and verifier are instructed to use:
- minutes-from-midnight conversion
- subtraction in minutes
- convert back at the end

### ✅ Clear User vs Engineer Views (Streamlit)
- **Result tab:** final answer + safe explanation
- **Debug Logic tab:** plan + verification attempts + raw JSON response

### ✅ Test Suite Included
The provided `main.py` runs:
- **5 easy questions**
- **3 tricky questions**
and prints a full JSON result for each run.

---

## 📦 Repository Structure
```text
.
├── prompts.py          # All prompts (Planner/Executor/Verifier/Formatter/Failure)
├── agent.py            # ReasoningAgent orchestration + retries + parsing logic
├── main.py             # CLI test suite runner (prints JSON output)
├── streamlit_app.py    # Streamlit UI (Result + Debug tabs)
└── README.md
