import json
import re
from typing import Dict, Any

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
import prompts

class ReasoningAgent:
    def __init__(self, model_name="llama3.1:8b"):
        self.model_name = model_name
        self.max_retries = 2
        
        # 1. Standard LLM
        self.llm_text = ChatOllama(
            model=model_name,
            temperature=0.2
        )
        
        # 2. JSON-Enforced LLM
        self.llm_json = ChatOllama(
            model=model_name,
            temperature=0.1,
            format="json"
        )

    def _call_llm(self, system_content: str, user_content: str, json_mode=False) -> str:
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content)
        ]
        try:
            model = self.llm_json if json_mode else self.llm_text
            response = model.invoke(messages)
            return response.content
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def _clean_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        return text.strip()

    def _extract_answer_regex(self, text: str) -> str:
        """Deterministic extraction to prevent hallucinations."""
        match = re.search(r"FINAL ANSWER:\s*(.*)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def _plan(self, question: str, feedback: str = None) -> str:
        """Phase 1: Planner - using .format() for prompt variables."""
        if feedback:
            # Properly formatting the system prompt with variables
            sys_msg = prompts.PLANNER_WITH_FEEDBACK_PROMPT.format(
                question=question, 
                feedback=feedback
            )
            return self._call_llm(sys_msg, "Please provide a corrected plan.", json_mode=False)
        else:
            return self._call_llm(prompts.PLANNER_PROMPT, f"Question: {question}", json_mode=False)

    def _execute(self, question: str, plan: str) -> str:
        """Phase 2: Executor"""
        content = f"Question: {question}\n\nPlan:\n{plan}"
        return self._call_llm(prompts.EXECUTOR_PROMPT, content, json_mode=False)

    def _verify(self, question: str, plan: str, solution: str) -> Dict:
        """Phase 3: Verifier"""
        content = f"Question: {question}\n\nPlan:\n{plan}\n\nProposed Solution:\n{solution}"
        response_str = self._call_llm(prompts.VERIFIER_PROMPT, content, json_mode=True)
        try:
            return json.loads(self._clean_json(response_str))
        except json.JSONDecodeError:
            return {"passed": False, "feedback": "Verifier JSON Error", "corrected_answer": None}

    def solve(self, question: str) -> Dict[str, Any]:
        retries = 0
        checks_log = []
        current_plan = ""
        last_solution_text = ""
        feedback_context = None
        status = "failed"
        # We need to keep the last verification object to access 'corrected_answer'
        last_verification = {} 
        
        # Loop: Initial + Retries
        for attempt in range(self.max_retries + 1):
            retries = attempt
            
            # 1. Plan
            current_plan = self._plan(question, feedback=feedback_context)
            
            # 2. Execute
            solution_text = self._execute(question, current_plan)
            last_solution_text = solution_text
            
            # 3. Verify
            last_verification = self._verify(question, current_plan, solution_text)
            
            checks_log.append({
                "check_name": f"Attempt {attempt + 1} Verification",
                "passed": last_verification.get("passed", False),
                "details": last_verification.get("feedback", "No details")
            })

            if last_verification.get("passed"):
                status = "success"
                break
            else:
                feedback_context = last_verification.get("feedback", "Incorrect solution.")

        # 4. Final Formatting
        final_answer = ""
        reasoning_user = ""

        if status == "success":
            # A. Try Regex Extraction first (Most Reliable)
            final_answer = self._extract_answer_regex(last_solution_text)
            
            # Fallback 1 - Use the Verifier's corrected answer if Regex failed
            if not final_answer and last_verification.get("corrected_answer"):
                final_answer = last_verification["corrected_answer"]
            
            # Use Formatter to generate user reasoning
            fmt_resp = self._call_llm(
                prompts.FINAL_FORMATTER_PROMPT.replace("{solution_text}", last_solution_text), 
                "Generate user output.", 
                json_mode=True
            )
            try:
                fmt_data = json.loads(self._clean_json(fmt_resp))
                reasoning_user = fmt_data.get("reasoning_visible_to_user", "Success")
                
                # Fallback 2 - If Regex AND Verifier failed, use Formatter result
                if not final_answer: 
                    final_answer = fmt_data.get("answer", "Answer found")
            except:
                reasoning_user = "Solved, but formatter failed."
                if not final_answer: final_answer = "Check logs."

        else:
            # FAILURE PATH: Use Failure Summarizer
            final_answer = "Unable to verify solution."
            
            # Ensure the human message contains the log details if the replace() fails
            fail_prompt = prompts.FAILURE_SUMMARIZER_PROMPT
            user_msg = f"Summarize why the agent failed. Context: {str(checks_log)}"
            fail_resp = self._call_llm(fail_prompt, user_msg, json_mode=True)
            
            try:
                fail_data = json.loads(self._clean_json(fail_resp))
                reasoning_user = fail_data.get("reasoning_visible_to_user", "Verification failed multiple times.")
            except:
                reasoning_user = "Verification failed multiple times."

        return {
            "answer": final_answer,
            "status": status,
            "reasoning_visible_to_user": reasoning_user,
            "metadata": {
                "plan": current_plan,
                "checks": checks_log,
                "retries": retries
            }
        }