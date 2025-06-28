import requests
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('key')

city = "Salem"
url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={key}"
response = requests.get(url)
data = response.json()
country = data[0]['country']
print(f"City: {city}, Country: {country}")
