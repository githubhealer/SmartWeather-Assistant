import requests
import os
from dotenv import load_dotenv
from flask import Flask, request, render_template
import pycountry
import difflib
import json
import pyttsx3 as speaker
try:
    load_dotenv()
    gemini_description = "" # Initialize a variable to hold the description from Gemini API
except Exception as e:
    print(f"Error loading environment variables: {e}")
    exit(1)
def speak(text):
    try:
        start = speaker.init() # Initialize the speaker
        if start is None:
            raise Exception("Failed to initialize text-to-speech engine")
        
        voices = start.getProperty('voices') # Get the available voices
        if voices and len(voices) > 1:
            start.setProperty('voice', voices[1].id) # Set the voice to the female voice
        elif voices and len(voices) > 0:
            start.setProperty('voice', voices[0].id) # Use first available voice
        
        start.say(text) # Convert text to speech
        start.runAndWait() # Wait for the speech to finish
        start.stop() # Clean up
        
    except ImportError:
        raise Exception("pyttsx3 module not properly installed")
    except Exception as e:
        raise Exception(f"Text-to-speech error: {str(e)}")
try:
    country_code_dict = {} # Dictionary to hold country names and their codes
    for i in pycountry.countries: # Loop through all countries in pycountry
        country_code_dict[i.alpha_2] = i.name # form a dictionary with country codes and names
except Exception as e:
    print(f"Error loading country data: {e}")
    country_code_dict = {} # Use empty dict as fallback
key = os.getenv('key') # Get the API key from the environment variable
GEMINI_API_KEY = os.getenv('google') # Get the Google API key from the environment variable
if not GEMINI_API_KEY: # Check if the Google API key is set
    print("Google API key not found. Please set the 'google' environment variable.")
    exit(1) # Exit if the key is not found
if not key: # Check if the API key is set
    print("API key not found. Please set the 'key' environment variable.")
    exit(1) # Exit if the key is not found
app = Flask(__name__) # Create a Flask application instance

# Global error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('weather.html', description=[
        "Page not found.",
        "Please check the URL and try again."
    ]), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('weather.html', description=[
        "An internal server error occurred.",
        "Please try again later or contact support."
    ]), 500

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"Unhandled exception: {e}")
    return render_template('weather.html', description=[
        "An unexpected error occurred.",
        "Please try again later."
    ]), 500

@app.route('/') # Define the route for the home page
def index(): # Function to render the index page
    return render_template('index.html') # Render the index.html template
@app.route('/weather') # Define the route for the weather page
def weather(): # Function to fetch and display weather information
    global gemini_description # Use the global variable to store the description
    
    try:
        city = request.args.get('city') # Get the city from the request
        if not city: # Check if the city is provided
            return render_template('weather.html', description=["Please provide a city name."]), 400
        
        city = city.strip().capitalize() # Clean and capitalize the city name
        if not city: # Check if city is empty after stripping
            return render_template('weather.html', description=["City name cannot be empty."]), 400
        
        # Getting country from city
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={key}"
        try:
            response = requests.get(url, timeout=10) # Add timeout
            response.raise_for_status() # Raise an exception for bad status codes
        except requests.exceptions.Timeout:
            return render_template('weather.html', description=["Request timed out. Please try again."]), 408
        except requests.exceptions.ConnectionError:
            return render_template('weather.html', description=["Unable to connect to weather service. Please check your internet connection."]), 503
        except requests.exceptions.RequestException as e:
            return render_template('weather.html', description=[f"Error fetching location data: {str(e)}"]), 500
        
        try:
            data = response.json() # Parse the JSON response
        except json.JSONDecodeError:
            return render_template('weather.html', description=["Invalid response from weather service."]), 500
        
        if not data or len(data) == 0: # Check if city was found
            return render_template('weather.html', description=[f"City '{city}' not found. Please check the spelling and try again."]), 404
        
        try:
            code = data[0]['country'] # Extract the country code from the response
            if code in country_code_dict: # Check if the country code is in the dictionary
                country = country_code_dict[code] # Get the country name from the dictionary
            else:
                country = code # Use country code if name not found
            country = country.capitalize() # Capitalize the country name for consistency
        except (KeyError, IndexError):
            return render_template('weather.html', description=["Invalid location data received."]), 500
        
        # Getting weather data for the city
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},{code}&appid={key}"
        try:
            response = requests.get(url, timeout=10) # Add timeout
            response.raise_for_status() # Raise an exception for bad status codes
        except requests.exceptions.Timeout:
            return render_template('weather.html', description=["Weather request timed out. Please try again."]), 408
        except requests.exceptions.ConnectionError:
            return render_template('weather.html', description=["Unable to connect to weather service. Please check your internet connection."]), 503
        except requests.exceptions.RequestException as e:
            return render_template('weather.html', description=[f"Error fetching weather data: {str(e)}"]), 500
        
        try:
            data = response.json() # Parse the JSON response for weather data
        except json.JSONDecodeError:
            return render_template('weather.html', description=["Invalid weather data received."]), 500
        
        # Check if weather data is valid
        if 'main' not in data or 'weather' not in data or 'name' not in data:
            return render_template('weather.html', description=["Incomplete weather data received."]), 500
        
        try:
            city = data['name'] # Extract the city name from the weather data
            temperature = round(data['main']['temp'] - 273, 2) # Convert temperature from Kelvin to Celsius and round it
            weather_condition = data['weather'][0]['description'] # Extract the weather description from the data
        except (KeyError, IndexError, TypeError):
            return render_template('weather.html', description=["Error processing weather data."]), 500
        
        # Google Gemini API call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"""I want you to act like a smart weather-based lifestyle assistant. Based on the following weather conditions, suggest:
What clothes to wear

What food or drinks are suitable

Any precautions or activity suggestions

The weather details are:

City: {city}

Country: {country}

Temperature: {temperature}°C

Weather condition: {weather_condition}

Give the suggestions in short, friendly sentences for a human user. Dont use any markdown or formatting, just plain text."""
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 1,
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30) # Longer timeout for AI
            response.raise_for_status()
        except requests.exceptions.Timeout:
            return render_template('weather.html', description=[
                f"Weather in {city}, {country}:",
                f"Temperature: {temperature}°C",
                f"Condition: {weather_condition}",
                "AI suggestions are temporarily unavailable due to timeout."
            ])
        except requests.exceptions.ConnectionError:
            return render_template('weather.html', description=[
                f"Weather in {city}, {country}:",
                f"Temperature: {temperature}°C", 
                f"Condition: {weather_condition}",
                "AI suggestions are temporarily unavailable. Please check your internet connection."
            ])
        except requests.exceptions.RequestException as e:
            return render_template('weather.html', description=[
                f"Weather in {city}, {country}:",
                f"Temperature: {temperature}°C",
                f"Condition: {weather_condition}",
                f"AI suggestions error: {str(e)}"
            ])
        
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            return render_template('weather.html', description=[
                f"Weather in {city}, {country}:",
                f"Temperature: {temperature}°C",
                f"Condition: {weather_condition}",
                "AI suggestions are temporarily unavailable due to invalid response."
            ])
        
        # Extract the generated text from the response
        gemini_description = ""
        try:
            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    gemini_description = candidate['content']['parts'][0]['text']
        except (KeyError, IndexError, TypeError):
            gemini_description = f"Basic weather info: {temperature}°C in {city}, {country}. Condition: {weather_condition}"
        
        # Fallback if no description generated
        if not gemini_description:
            gemini_description = f"Weather in {city}, {country}: {temperature}°C, {weather_condition}. AI suggestions temporarily unavailable."
        
        try:
            with open('weather.txt', 'w', encoding='utf-8') as f:
                f.write(gemini_description)
        except IOError as e:
            print(f"Warning: Could not save weather data to file: {e}")
        
        # Split description for display
        description_list = [item.strip() for item in gemini_description.split('.') if item.strip()]
        
        return render_template('weather.html', description=description_list)
        
    except Exception as e:
        # Catch any unexpected errors
        print(f"Unexpected error in weather route: {e}")
        return render_template('weather.html', description=[
            "An unexpected error occurred while fetching weather data.",
            "Please try again later or contact support if the problem persists."
        ]), 500

@app.route('/speak')
def speak_route():
    try:
        if os.path.exists('weather.txt'):
            try:
                with open('weather.txt', 'r', encoding='utf-8') as f:
                    gemini_description = f.read()
                
                if not gemini_description.strip():
                    return render_template('weather.html', description=["No weather description available to speak."]), 404
                
                try:
                    speak(gemini_description)
                    description_list = [item.strip() for item in gemini_description.split('.') if item.strip()]
                    return render_template('weather.html', description=description_list)
                except Exception as e:
                    print(f"Text-to-speech error: {e}")
                    return render_template('weather.html', description=[
                        "Weather description loaded but speech function failed.",
                        "This may be due to missing audio drivers or unsupported system.",
                        f"Error: {str(e)}"
                    ]), 500
                    
            except IOError as e:
                return render_template('weather.html', description=[
                    f"Error reading weather data file: {str(e)}"
                ]), 500
        else:
            return render_template('weather.html', description=[
                "No weather description available to speak.",
                "Please search for weather information first."
            ]), 404
            
    except Exception as e:
        print(f"Unexpected error in speak route: {e}")
        return render_template('weather.html', description=[
            "An unexpected error occurred while trying to speak.",
            "Please try again later."
        ]), 500
if __name__ == '__main__':  
    app.run(debug=True,port=5001) # Run the Flask application in debug mode on port 5000
    print(len(list(pycountry.countries)))  # Print all countries for debugging