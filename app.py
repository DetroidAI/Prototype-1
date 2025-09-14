# app.py - Appointment Assistant Backend
import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import openai

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Set your OpenAI API key (you'll set this as environment variable on Render)
openai.api_key = os.getenv('OPENAI_API_KEY')

# In-memory "database" to simulate appointment calendar
# In a real app, this would be a proper database
APPOINTMENTS = {
    # Format: "YYYY-MM-DD HH:MM": {"service": "", "name": "", "booked": True}
    "2024-09-20 10:00": {"service": "dentist", "name": "John Doe", "booked": True},
    "2024-09-20 14:00": {"service": "haircut", "name": "Jane Smith", "booked": True},
}

# Available time slots (simplified - in reality you'd generate these dynamically)
AVAILABLE_SLOTS = [
    "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"
]

def parse_date_time(user_message):
    """
    Use OpenAI to extract appointment details from user message
    """
    try:
        # Craft a specific prompt for OpenAI to extract appointment information
        system_prompt = """
You are an appointment extraction assistant. Extract appointment information from user messages.
Return a JSON object with these fields:
- service_type: type of appointment (dentist, haircut, meeting, etc.)
- date: date in YYYY-MM-DD format (if relative like "tomorrow", convert to actual date)
- time: time in HH:MM format (24-hour)
- user_name: user's name if mentioned
- intent: "book_appointment" if they want to book, "greeting" if just saying hi, "unclear" if unclear

If any field is not clear or missing, use null for that field.
Today's date is """ + datetime.now().strftime("%Y-%m-%d") + """

Examples:
User: "Hi, I want to book a dentist appointment for tomorrow at 2 PM"
Response: {"service_type": "dentist", "date": "2024-09-21", "time": "14:00", "user_name": null, "intent": "book_appointment"}

User: "Hello"
Response: {"service_type": null, "date": null, "time": null, "user_name": null, "intent": "greeting"}
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        # Parse the JSON response
        extracted_info = json.loads(response.choices[0].message.content.strip())
        return extracted_info
    
    except Exception as e:
        print(f"Error parsing with OpenAI: {e}")
        # Fallback response
        return {
            "service_type": None,
            "date": None,
            "time": None,
            "user_name": None,
            "intent": "unclear"
        }

def check_availability(date, time):
    """
    Check if a specific date and time slot is available
    """
    appointment_key = f"{date} {time}"
    return appointment_key not in APPOINTMENTS

def book_appointment(date, time, service, name):
    """
    Book an appointment by adding it to our in-memory database
    """
    appointment_key = f"{date} {time}"
    APPOINTMENTS[appointment_key] = {
        "service": service,
        "name": name,
        "booked": True
    }
    return True

def generate_response(user_message, extracted_info):
    """
    Generate appropriate response based on extracted information
    """
    intent = extracted_info.get('intent')
    
    if intent == 'greeting':
        return "Hello! I'm your appointment assistant. I can help you book appointments. What kind of appointment would you like to schedule?"
    
    elif intent == 'book_appointment':
        service = extracted_info.get('service_type')
        date = extracted_info.get('date')
        time = extracted_info.get('time')
        name = extracted_info.get('user_name')
        
        # Check if we have all required information
        missing_info = []
        if not service:
            missing_info.append("type of appointment")
        if not date:
            missing_info.append("date")
        if not time:
            missing_info.append("time")
        
        if missing_info:
            missing_str = ", ".join(missing_info)
            return f"I need a bit more information. Could you please provide the {missing_str}?"
        
        # Check availability
        if check_availability(date, time):
            if name:
                # We have all info, book the appointment
                book_appointment(date, time, service, name)
                return f"Perfect! Your {service} appointment for {date} at {time} is confirmed, {name}. Is there anything else I can help you with?"
            else:
                # Ask for name before confirming
                # Store the pending appointment info in the response
                return f"Great! I have a {service} appointment available on {date} at {time}. What's your name so I can confirm the booking?"
        else:
            return f"I'm sorry, but {time} on {date} is already booked. Here are some available times: {', '.join(AVAILABLE_SLOTS[:3])}. Would any of these work?"
    
    else:
        return "I'm here to help you book appointments. Could you please tell me what kind of appointment you need and when you'd like to schedule it?"

# Routes
@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages from the frontend"""
    try:
        # Get user message from request
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message.strip():
            return jsonify({'response': 'Please enter a message.'})
        
        # Extract information using OpenAI
        extracted_info = parse_date_time(user_message)
        
        # Generate response
        bot_response = generate_response(user_message, extracted_info)
        
        return jsonify({
            'response': bot_response,
            'extracted_info': extracted_info  # For debugging (remove in production)
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'response': 'Sorry, I encountered an error. Please try again.'})

@app.route('/appointments', methods=['GET'])
def view_appointments():
    """View all booked appointments (for testing)"""
    return jsonify(APPOINTMENTS)

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
