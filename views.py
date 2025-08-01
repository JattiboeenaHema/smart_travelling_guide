from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
import requests
import re
import time
import json


# ----------------- API KEYS -----------------
GEMINI_API_KEY = settings.GEMINI_API_KEY
OPENWEATHER_API_KEY = settings.OPENWEATHER_API_KEY

# ----------------- GEMINI HELPER FUNCTION -----------------
def get_gemini_response(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    data = { "contents": [ { "parts": [ { "text": prompt } ] } ] }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, params=params, json=data, timeout=30)
            result = response.json()
            if 'candidates' in result:
                return result['candidates'][0]['content']['parts'][0]['text']
            elif 'error' in result:
                return f"Gemini API Error: {result['error']['message']}"
            else:
                return "No response found."
        except requests.exceptions.Timeout:
            print(f"Timeout attempt {attempt+1}. Retrying...")
            time.sleep(2)
    return "Request timed out after multiple attempts."

# ----------------- REGISTER -----------------
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'register.html', {'error': "Passwords do not match."})
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': "Username already exists."})

        User.objects.create_user(username=username, email=email, password=password)
        return redirect('login')
    return render(request, 'register.html')

# ----------------- LOGIN -----------------
def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {'error': "Invalid username or password."})
    return render(request, 'login.html')

# ----------------- LOGOUT -----------------
def user_logout(request):
    logout(request)
    return redirect('login')

# ----------------- HOME -----------------
@login_required
def home(request):
    if request.method == 'POST':
        source = request.POST.get('source')
        destination = request.POST.get('destination')
        request.session['source'] = source
        request.session['destination'] = destination
        return render(request, 'home.html', {'show_options': True, 'source': source, 'destination': destination})
    return render(request, 'home.html')

# ----------------- HOTELS -----------------
@login_required
def hotels(request):
    destination = request.session.get('destination')
    hotels = []

    if destination:
        prompt = f"""
List top 5 staying hotels in and around {destination}, India.
For each hotel, provide:
- Hotel Name
- Address
- Cost per night
- Rating
Strictly in this format.
        """

        response = get_gemini_response(prompt)
        entries = response.strip().split('\n\n')
        
        for entry in entries:
            lines = entry.strip().split('\n')
            if len(lines) >= 4:
                try:
                    hotels.append({
                        'name': lines[0].split(':',1)[1].strip() if ':' in lines[0] else 'N/A',
                        'address': lines[1].split(':',1)[1].strip() if ':' in lines[1] else 'N/A',
                        'cost': lines[2].split(':',1)[1].strip() if ':' in lines[2] else 'N/A',
                        'rating': lines[3].split(':',1)[1].strip() if ':' in lines[3] else 'N/A',
                    })
                except Exception as e:
                    print("Parsing error:", e, "Entry:", entry)
            else:
                print("Invalid hotel entry format:", entry)

    return render(request, 'hotels.html', {'destination': destination, 'hotels': hotels})



# ----------------- RESTAURANTS -----------------
@login_required
def restaurants(request):
    destination = request.session.get('destination')
    restaurants = []

    if destination:
        prompt = f"""
List top 5 popular restaurants in and around {destination}, India.
For each, provide:
- Restaurant Name
- Address
- Distance from city center
        """
        response = get_gemini_response(prompt)
        entries = response.strip().split('\n\n')
        for entry in entries:
            lines = entry.split('\n')
            if len(lines) >= 3:
                restaurants.append({
                    'name': lines[0].split(':',1)[1].strip(),
                    'address': lines[1].split(':',1)[1].strip(),
                    'distance': lines[2].split(':',1)[1].strip()
                })
    return render(request, 'restaurants.html', {'destination': destination, 'restaurants': restaurants})

# ----------------- POPULAR PLACES -----------------
@login_required
def popularplaces(request):
    destination = request.session.get('destination')
    places = []

    if destination:
        prompt = f"""
List top 5 tourist places in and around {destination}, India.
For each place, provide:
- Place Name
- Address
- Distance
        """
        response = get_gemini_response(prompt)
        entries = response.strip().split('\n\n')
        for entry in entries:
            lines = entry.split('\n')
            if len(lines) >= 3:
                places.append({
                    'name': lines[0].split(':',1)[1].strip(),
                    'address': lines[1].split(':',1)[1].strip(),
                    'distance': lines[2].split(':',1)[1].strip()
                })
    return render(request, 'popularplaces.html', {'destination': destination, 'places': places})

# ----------------- WEATHER -----------------
@login_required
def weather(request):
    destination = request.session.get('destination')
    if destination:
        url = f"http://api.weatherapi.com/v1/current.json?key={OPENWEATHER_API_KEY}&q={destination}&aqi=no"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            weather_desc = data['current']['condition']['text']
            temp = data['current']['temp_c']
            return render(request, 'weather.html', {'destination': destination, 'weather': weather_desc, 'temp': temp})
        else:
            return render(request, 'weather.html', {'error': "Weather data not found.", 'destination': destination})
    return redirect('home')

# ----------------- ATMS -----------------
@login_required
def atms(request):
    destination = request.session.get('destination')
    atms = []

    if destination:
        prompt = f"""
List top 5 ATMs in and around {destination}, India.
For each ATM, provide:
- ATM Name
- Address
        """
        response = get_gemini_response(prompt)
        entries = response.strip().split('\n\n')
        for entry in entries:
            lines = entry.split('\n')
            if len(lines) >= 2:
                atms.append({
                    'name': lines[0].split(':',1)[1].strip(),
                    'address': lines[1].split(':',1)[1].strip()
                })
    return render(request, 'atms.html', {'destination': destination, 'atms': atms})
    # ----------------- HOSPITALS -----------------
@login_required
def hospitals(request):
    destination = request.session.get('destination')
    hospitals = []

    if destination:
        prompt = f"""
List top 5 hospitals in and around {destination}, India.
For each hospital, provide:
- Hospital Name
- Address
- Timings
- Specializations
        """
        response = get_gemini_response(prompt)
        entries = response.strip().split('\n\n')
        for entry in entries:
            lines = entry.split('\n')
            if len(lines) >= 4:
                hospitals.append({
                    'name': lines[0].split(':',1)[1].strip(),
                    'address': lines[1].split(':',1)[1].strip(),
                    'timings': lines[2].split(':',1)[1].strip(),
                    'specializations': lines[3].split(':',1)[1].strip()
                })
    return render(request, 'hospitals.html', {'destination': destination, 'hospitals': hospitals})
    # ----------------- POLICE STATIONS -----------------
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import google.generativeai as genai

# Configure Gemini API key
genai.configure(api_key="AIzaSyB2ga0UIPUPmZIkhMkF9bYd9EwAITx3FeA")  # Replace with your actual Gemini API key


@login_required
def policestations(request):
    destination = request.session.get('destination')
    stations = []

    if destination:
        prompt = f"""
List top 5 police stations in and around {destination}, India.
For each police station, provide:
- Police Station Name
- Address
- Timings (Working hours)
- Contact Number

Strictly follow this format:
Police Station Name: [name]
Address: [address]
Timings: [working hours]
Contact Number: [phone number]
        """
        model = genai.GenerativeModel('gemini-2.0-flash')  # Adjust model name as per your access
        response = model.generate_content(prompt)
        entries = response.text.strip().split('\n\n')

        for entry in entries:
            lines = entry.strip().split('\n')
            try:
                name = ""
                address = ""
                timings = ""
                phone = ""

                for line in lines:
                    if line.lower().startswith('police station name'):
                        name = line.split(':',1)[1].strip()
                    elif line.lower().startswith('address'):
                        address = line.split(':',1)[1].strip()
                    elif line.lower().startswith('timings'):
                        timings = line.split(':',1)[1].strip()
                    elif line.lower().startswith('contact number'):
                        phone = line.split(':',1)[1].strip()

                if name and address:
                    stations.append({
                        'name': name,
                        'address': address,
                        'timings': timings,
                        
                    })
            except IndexError:
                continue  # skip problematic entry

    return render(request, 'policestations.html', {'destination': destination, 'stations': stations})




# ----------------- BUDGET -----------------

@login_required
def budget(request):
    destination = request.session.get('destination')
    budget_text = ""
    places = []

    # Fetch places to visit using Gemini (or your logic)
    if destination:
        prompt_places = f"""
List top 5 popular tourist places to visit in {destination}, India. 
Return as plain list without numbering.
        """
        places_response = get_gemini_response(prompt_places)
        places = [place.strip() for place in places_response.strip().split('\n') if place.strip()]

    if request.method == "POST":
        days = request.POST.get('days')
        vehicle = request.POST.get('vehicle')
        hotel = request.POST.get('hotel')
        food = request.POST.get('food')
        selected_places = request.POST.getlist('places')

        prompt = f"""
Estimate travel budget for {destination}, India for {days} days.
Vehicle type: {vehicle}.
Hotel type: {hotel}.
Food preference: {food}.
Places to visit: {', '.join(selected_places)}.

Provide a detailed breakdown (travel, stay, food, entry tickets, miscellaneous) and a total estimate in INR.
        """
        budget_text = get_gemini_response(prompt)

    return render(request, 'budget.html', {
        'destination': destination,
        'places': places,
        'budget_text': budget_text
    })


# ----------------- DIRECTIONS -----------------
@login_required
def directions(request):
    source = request.session.get('source')
    destination = request.session.get('destination')
    return render(request, 'directions.html', {'source': source, 'destination': destination})

# ----------------- CHATBOT -----------------
@login_required
def travel_chatbot(request):
    destination = request.session.get('destination')
    response_text = ""

    if request.method == "POST":
        user_prompt = request.POST.get('user_prompt')
        prompt = f"User is travelling to {destination}. Question: {user_prompt}. Provide detailed, helpful answer."
        response_text = get_gemini_response(prompt)

    return render(request, 'travel_chatbot.html', {'destination': destination, 'response': response_text})
