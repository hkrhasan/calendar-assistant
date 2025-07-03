import os, json, uuid, requests
import streamlit as st


# Determine if we're in production
IS_PRODUCTION = os.getenv("IS_PRODUCTION", "false").lower() == "true"

# Set backend URL
if IS_PRODUCTION:
    BACKEND_HOST = os.getenv("BACKEND_HOST", "http://192.168.1.7:8000")
else:
    BACKEND_HOST = "http://192.168.1.7:8000"

API_URL = f"{BACKEND_HOST}/chat"
RESET_URL = f"{BACKEND_HOST}/reset/"

# Initialize session
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_booking" not in st.session_state:
    st.session_state.pending_booking = None

# UI Setup
st.title("📅 Calendar Assistant")
st.caption("Book appointments through natural conversation")

# Display chat history
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    
    with st.chat_message(role):
        # Check if it's a booking confirmation request
        if role == "assistant" and isinstance(content, dict) and content.get("confirmation_required"):
            st.write(content["message"])
            
            # Show confirmation buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm", key=f"confirm_{msg['timestamp']}"):
                    # Handle confirmation
                    confirmation_payload = {
                        "confirmation": True,
                        "summary": content["proposed_summary"],
                        "start_iso": content["proposed_start"],
                        "end_iso": content["proposed_end"]
                    }
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": json.dumps(confirmation_payload),
                        "is_confirmation": True
                    })
                    st.session_state.pending_booking = None
                    st.rerun()
                    
            with col2:
                if st.button("❌ Cancel", key=f"cancel_{msg['timestamp']}"):
                    # Handle cancellation
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": "cancel_booking",
                        "is_cancellation": True
                    })
                    st.session_state.pending_booking = None
                    st.rerun()
        else:
            # Normal message display
            st.write(content)

# Reset button
if st.sidebar.button("Clear Conversation"):
    try:
        response = requests.post(RESET_URL + st.session_state.session_id)
        if response.status_code == 200:
            st.session_state.messages = []
            st.session_state.pending_booking = None
            st.rerun() 
        else:
            st.error("Failed to clear conversation history")
    except Exception as e:
        st.error(f"Error clearing conversation: {str(e)}")

# User input
if prompt := st.chat_input("Ask about availability or book a meeting..."):
    # Check if we have a pending booking confirmation
    if st.session_state.pending_booking:
        # Handle confirmation via text input
        if prompt.lower() in ["yes", "y", "confirm"]:
            confirmation_payload = {
                "confirmation": True,
                "summary": st.session_state.pending_booking["proposed_summary"],
                "start_iso": st.session_state.pending_booking["proposed_start"],
                "end_iso": st.session_state.pending_booking["proposed_end"]
            }
            prompt = json.dumps(confirmation_payload)
        elif prompt.lower() in ["no", "n", "cancel"]:
            prompt = "cancel_booking"
        st.session_state.pending_booking = None
    
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
            
            if response.status_code == 200:
                data = response.json()
                reply = data["response"]
                
                # Check if this is a booking confirmation request
                if isinstance(reply, dict) and reply.get("confirmation_required"):
                    # Store pending booking details
                    st.session_state.pending_booking = {
                        "proposed_summary": reply["proposed_summary"],
                        "proposed_start": reply["proposed_start"],
                        "proposed_end": reply["proposed_end"]
                    }
            else:
                reply = f"⚠️ Error: Received status code {response.status_code}"
        except requests.exceptions.RequestException as e:
            reply = "⚠️ Sorry, I'm having trouble connecting to the assistant."
    
    # Display assistant response
    with st.chat_message("assistant"):
        # For confirmation requests, we'll store the structured data
        if isinstance(reply, dict) and reply.get("confirmation_required"):
            # Add timestamp for unique keys
            reply["timestamp"] = str(uuid.uuid4())
            st.session_state.messages.append({
                "role": "assistant", 
                "content": reply
            })
        else:
            # Normal text response
            st.write(reply)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": reply
            })
    
    # Rerun to update UI
    st.rerun()