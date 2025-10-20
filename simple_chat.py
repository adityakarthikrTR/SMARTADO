"""
SUPER SIMPLE Chatbot - Guaranteed to Work
"""

import streamlit as st
import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

st.title("💬 Simple Working Chatbot")

# Initialize messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display all previous messages
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.write(f"**👤 You:** {msg['content']}")
    else:
        st.write(f"**🤖 AI:** {msg['content']}")
    st.write("---")

# Simple form for input
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Your question:", key="user_input")
    submitted = st.form_submit_button("Send Message")

if submitted and user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Show loading
    with st.spinner("AI is thinking..."):
        try:
            # Call LiteLLM
            response = completion(
                model="gpt-4",
                api_base="https://litellm.int.thomsonreuters.com",
                api_key="sk-zlR9TXis42IY0AuSRvU9Cw",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."}
                ] + st.session_state.messages,
                temperature=0.7,
                max_tokens=500
            )

            ai_message = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": ai_message})

            st.success("✅ Response received!")
            st.rerun()

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.rerun()

# Clear button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()
