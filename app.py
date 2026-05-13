from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory
from safety_filter import filter_response
from figure_classifier import is_public_figure_question, classify_figure, KNOWN_TIER1
from web_search import get_web_context
import ollama
import os
import re

app = Flask(__name__, static_folder='static')

with open('final_prompt.txt') as f:
    SYSTEM_PROMPT = f.read()

TIER1_RESPONSE = "That name comes up in some very grown-up news stories. Your parents are the best people to explain that one — they can decide what is right for you to know and when. Is there something else I can help you with today? 😊"

def get_tier2_response(name):
    return f"That is someone a lot of people have heard about! I can tell you that {name} is a well-known public figure, but for the full story your parents are a great person to ask — they can share what is right for you to know. Is there something else you are curious about today? 😊"

def detect_visual(message):
    msg = message.lower()
    triggers = {
        'ocean': 'ocean_salty', 'salty': 'ocean_salty',
        'dream': 'dreams', 'dreams': 'dreams',
        'bully': 'bullying', 'bullying': 'bullying', 'bullied': 'bullying',
    }
    for keyword, card in triggers.items():
        if keyword in msg:
            return card
    return None

def contains_tier1_name(message, tier1_names):
    msg = message.lower()
    for name in tier1_names:
        if name.lower() in msg:
            return True
    return False

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    demo_mode = data.get('demo_mode', False)
    tier1_seen = data.get('tier1_seen', [])
    history = data.get('history', [])

    msg_lower = user_message.lower()

    # Hardcoded appearance response — Gemma ignores prompt rule on this
    APPEARANCE_KEYWORDS = ['look like', 'profile picture', 'bunny', 'rabbit', 'mouse', 'bear', 'are you a']
    if any(k in msg_lower for k in APPEARANCE_KEYWORDS):
        return jsonify({
            'response': "That's my little face up there! I'm Biscuit — a brown dog with cookie-like spots, kind of like a chocolate chip biscuit! What would you like to learn about today? 🍪😊",
            'was_filtered': False,
            'visual': None,
            'tier1_seen': tier1_seen
        })

    # Check ALL Tier 1 known names in any message
    for name in KNOWN_TIER1:
        if name in msg_lower:
            if name not in tier1_seen:
                tier1_seen.append(name)
            return jsonify({
                'response': TIER1_RESPONSE,
                'was_filtered': True if demo_mode else False,
                'visual': None,
                'tier1_seen': tier1_seen
            })

    # Check if message mentions a previously seen Tier 1 name
    if contains_tier1_name(user_message, tier1_seen):
        return jsonify({
            'response': TIER1_RESPONSE,
            'was_filtered': True if demo_mode else False,
            'visual': None,
            'tier1_seen': tier1_seen
        })

    # Check if public figure question
    is_figure, name = is_public_figure_question(user_message)
    if is_figure:
        tier, reason = classify_figure(name)
        print(f'[Figure] {name} -> Tier {tier} ({reason})')
        if tier == 1:
            if name not in tier1_seen:
                tier1_seen.append(name)
            return jsonify({
                'response': TIER1_RESPONSE,
                'was_filtered': True if demo_mode else False,
                'visual': None,
                'tier1_seen': tier1_seen
            })
        elif tier == 2:
            return jsonify({
                'response': get_tier2_response(name),
                'was_filtered': False,
                'visual': None,
                'tier1_seen': tier1_seen
            })

    # Flag sensitive input topics for demo mode badge (input is handled by prompt, not filter)
    SENSITIVE_INPUT_PATTERNS = [
        'drug', 'weed', 'marijuana', 'cocaine', 'heroin', 'meth', 'alcohol',
        'beer', 'wine', 'cigarette', 'vape', 'smoke', 'narcotic'
    ]
    input_flagged = any(p in msg_lower for p in SENSITIVE_INPUT_PATTERNS)

    # Check if web search needed
    web_context = get_web_context(user_message)
    final_message = user_message
    if web_context:
        final_message = user_message + "\n\n[Web context for Biscuit only]: " + web_context

    # Build messages with conversation history (last 6 exchanges)
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    for h in history[-12:]:
        messages.append(h)
    messages.append({'role': 'user', 'content': final_message})

    # Send to Gemma
    response = ollama.chat(
        model='gemma4:e4b',
        messages=messages
    )
    raw_text = response['message']['content']
    filtered = filter_response(raw_text, verbose=False)
    final_text = filtered['text']
    was_filtered = not filtered['safe']
    visual = detect_visual(user_message)

    return jsonify({
        'response': final_text,
        'was_filtered': (was_filtered or input_flagged) if demo_mode else False,
        'visual': visual,
        'tier1_seen': tier1_seen
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
