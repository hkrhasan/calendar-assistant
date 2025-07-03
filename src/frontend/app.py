import os
import streamlit as st
import requests
import uuid
from dotenv import load_dotenv



# Determine if we're in production
IS_PRODUCTION = os.getenv("IS_PRODUCTION", "false").lower() == "true"

# Set backend URL
if IS_PRODUCTION:
    BACKEND_HOST = os.getenv("BACKEND_HOST", "https://calendar-assistant-production-b9f1.up.railway.app")
else:
    BACKEND_HOST = "https://calendar-assistant-production-b9f1.up.railway.app"

API_URL = f"{BACKEND_HOST}/chat"
RESET_URL = f"{BACKEND_HOST}/reset/"

# Initialize session
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# UI Setup
st.title("📅 Calendar Assistant")
st.caption("Book appointments through natural conversation")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Reset button
if st.sidebar.button("Clear Conversation"):
    try:
        response = requests.post(RESET_URL + st.session_state.session_id)
        if response.status_code == 200:
            st.session_state.messages = []
            st.rerun() 
        else:
            st.error("Failed to clear conversation history")
    except Exception as e:
        st.error(f"Error clearing conversation: {str(e)}")

# User input
if prompt := st.chat_input("Ask about availability or book a meeting..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get assistant response
    with st.spinner("Thinking..."):
        try:
            payload = {
                "session_id": st.session_state.session_id,
                "message": prompt
            }
            response = requests.post(API_URL, json=payload)
            
            print("API >> ", API_URL) 
            print(response) 
            if response.status_code == 200:
                data = response.json()
                reply = data["response"]
            else:
                reply = f"⚠️ Error: Received status code {response.status_code}"
        except requests.exceptions.RequestException as e:
            reply = "⚠️ Sorry, I'm having trouble connecting to the assistant."
    
    # Display assistant response
    with st.chat_message("assistant"):
        st.write(reply)
    
    # Add to history
    st.session_state.messages.append({"role": "assistant", "content": reply})