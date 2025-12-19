import streamlit as st
import json
from agent import ReasoningAgent

# Page Configuration
st.set_page_config(
    page_title="Reasoning Agent",
    page_icon="🧠",
    layout="wide"
)

# Title - Minimal and Clean
st.title("🧠 Reasoning Agent")
st.caption("Planner → Executor → Verifier Architecture")

# Sidebar 
with st.sidebar:
    st.header("Settings")
    model_name = st.text_input("Model", value="llama3.1:8b")
    
    st.markdown("---")
    st.subheader("Quick Tests")
    if st.button("Time Difference (Train)"):
        st.session_state.input_text = "If a train leaves at 14:30 and arrives at 18:05, how long is the journey?"
    if st.button("Logic Puzzle (Apples)"):
        st.session_state.input_text = "Alice has 3 red apples and twice as many green apples as red. How many apples total?"

# Main Input
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

question = st.text_area("Question:", height=100, key="input_text")

if st.button("Solve", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        # Initialize Agent
        agent = ReasoningAgent(model_name=model_name)
        
        # Minimal Status Bar
        status_text = st.empty()
        status_text.info("Thinking... (Planning & Verifying)")
        
        try:
            result = agent.solve(question)
            status_text.empty() # Remove status message when done

            # --- RESULT DISPLAY ---
            
            # Tabs for a cleaner look 
            tab1, tab2 = st.tabs(["Result", "Debug Logic"])

            with tab1:
                if result['status'] == 'success':
                    st.success(f"**Answer:** {result['answer']}")
                    st.markdown(f"**Reasoning:**\n{result['reasoning_visible_to_user']}")
                else:
                    st.error(f"❌ **Failed:** {result['answer']}")
                    st.markdown(f"**Why:** {result['reasoning_visible_to_user']}")

            with tab2:
                st.info("Technical details for the Engineer")
                
                # 1. Plan
                st.markdown("**1. Final Plan**")
                st.code(result['metadata']['plan'], language="markdown")

                # 2. Verification Loops
                st.markdown("**2. Self-Correction Logs**")
                for i, check in enumerate(result['metadata']['checks']):
                    icon = "✅" if check['passed'] else "❌"
                    with st.expander(f"Attempt {i+1} {icon}"):
                        st.write(f"Feedback: {check['details']}")
                
                # 3. Raw Data
                with st.expander("Full JSON Response"):
                    st.json(result)

        except Exception as e:
            status_text.error(f"Error: {str(e)}")