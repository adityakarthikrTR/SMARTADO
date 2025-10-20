"""
Simple Chatbot Test - Diagnose LiteLLM Issue
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

st.title("🧪 Chatbot Test")

st.write("**Environment Variables:**")
st.write(f"- LITELLM_API_BASE: {os.getenv('LITELLM_API_BASE')}")
st.write(f"- LITELLM_API_KEY: {os.getenv('LITELLM_API_KEY')[:20]}..." if os.getenv('LITELLM_API_KEY') else "NOT SET")
st.write(f"- LITELLM_MODEL: {os.getenv('LITELLM_MODEL')}")

st.markdown("---")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type a test message..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        try:
            from litellm import completion

            st.write("✅ LiteLLM imported successfully")

            # Try to call LiteLLM
            with st.spinner("Calling LiteLLM..."):
                response = completion(
                    model=os.getenv('LITELLM_MODEL', 'gpt-4'),
                    api_base=os.getenv('LITELLM_API_BASE'),
                    api_key=os.getenv('LITELLM_API_KEY'),
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200,
                    custom_llm_provider="openai"
                )

                ai_response = response.choices[0].message.content
                st.markdown(ai_response)

                # Add to history
                st.session_state.messages.append({"role": "assistant", "content": ai_response})

                st.success("✅ LiteLLM call successful!")

        except Exception as e:
            error_msg = f"""
❌ **ERROR DETAILS:**

{str(e)}

**Error Type:** {type(e).__name__}

**Full Traceback:**
"""
            st.error(error_msg)

            import traceback
            st.code(traceback.format_exc())

            st.warning("""
**Common Issues:**
1. Not connected to TR VPN
2. LiteLLM endpoint down
3. Invalid API key
4. Model not available
5. Network/firewall blocking request
""")

            # Add error to history
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
