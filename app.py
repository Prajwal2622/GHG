from flask import Flask, request, jsonify, render_template
import requests
import time

app = Flask(__name__)

ORS_API_KEY = "5b3ce3597851110001cf62482abb106bbd0b4f778c430ead48caf2e3"

# Device data
devices = {
    "Laptop": {"weight": 1.5, "co2e": 3.75},
    "Desktop": {"weight": 3, "co2e": 7.5},
    "Server": {"weight": 15, "co2e": 37.5},
    "Mobile/Tablet": {"weight": 0.3, "co2e": 0.75},
    "Printer": {"weight": 6, "co2e": 15.69},
    "TV": {"weight": 5, "co2e": 12.5},
    "Microwave": {"weight": 13.6, "co2e": 15.03},
    "LCD TV/Monitor": {"weight": 18.13, "co2e": 20.04},
    "Washing Machine": {"weight": 65.7, "co2e": 156},
    "Refrigerator": {"weight": 45, "co2e": 51},
    "Air Conditioners": {"weight": 36.82, "co2e": 68},
    "Li-ion batteries": {"weight": 0.015, "co2e": 0.073},
    "Routers": {"weight": 0.6, "co2e": 1.5},
    "Cables": {"weight": 0.1, "co2e": 0.25},
    "Water Boilers": {"weight": 22.3, "co2e": 24.65}
}

# Emission factors for vehicles
vehicle_emission_factors = {
    "LDV": 0.307,  # Light Duty Vehicle (<3.5T)
    "MDV": 0.5928, # Medium Duty Vehicle (<12T)
    "HDV": 0.7375  # Heavy Duty Vehicle (>12T)
}

# Function to get coordinates using Nominatim
def get_coordinates(location):
    query = location.split(",")[0]  # Use only the city name
    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json"
    headers = {"User-Agent": "GHG Emission Calculator (your-email@example.com)"}  # Replace with your email
    response = requests.get(url, headers=headers)
    time.sleep(1)  # Add a delay to avoid rate-limiting
    if response.status_code == 200 and response.json():
        data = response.json()[0]
        lat = float(data['lat'])
        lon = float(data['lon'])
        print(f"Coordinates for {location}: Latitude = {lat}, Longitude = {lon}")
        return lat, lon
    print(f"Could not fetch coordinates for {location}")
    return None, None

# Function to calculate distance using OpenRouteService API
def calculate_distance(origin_coords, destination_coords):
    if not origin_coords or not destination_coords:
        print("Invalid coordinates provided")
        return 0

    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [
            [origin_coords[1], origin_coords[0]],  # [lon, lat]
            [destination_coords[1], destination_coords[0]]  # [lon, lat]
        ]
    }
    try:
        response = requests.post(url, json=body, headers=headers)
        if response.status_code == 200:
            data = response.json()
            distance = data['routes'][0]['summary']['distance'] / 1000  # Convert meters to kilometers
            print(f"Distance: {distance} km")
            return distance
        else:
            print(f"Error fetching distance: {response.status_code}, {response.text}")
            return 0
    except Exception as e:
        print(f"Exception occurred while fetching distance: {e}")
        return 0

@app.route('/')
def index():
    return render_template('index.html', devices=devices, vehicles=vehicle_emission_factors)

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    e_waste_co2e = 0
    transport_co2e = 0

    # Calculate CO2e for devices (e-waste)
    for item in data['items']:
        device = item['device']
        quantity = item.get('quantity', 0)
        weight = item.get('weight', 0)

        if quantity > 0:
            e_waste_co2e += quantity * devices[device]['co2e']
        if weight > 0:
            co2_per_kg = devices[device]['co2e'] / devices[device]['weight']
            e_waste_co2e += weight * co2_per_kg

    # Calculate CO2e for transportation
    origin = data.get('origin')
    destination = data.get('destination')
    vehicle = data.get('vehicle')
    num_vehicles = data.get('num_vehicles', 0)

    if origin and destination and vehicle and num_vehicles > 0:
        origin_coords = get_coordinates(origin)
        destination_coords = get_coordinates(destination)
        if origin_coords and destination_coords:
            distance = calculate_distance(origin_coords, destination_coords)
            emission_factor = vehicle_emission_factors.get(vehicle, 0)
            transport_co2e += distance * emission_factor * num_vehicles
            print(f"Distance: {distance} km, Emission Factor: {emission_factor}, Vehicles: {num_vehicles}, Transport CO2e: {transport_co2e}")
        else:
            print("Could not fetch coordinates for origin or destination")
    else:
        print("Missing origin, destination, vehicle, or number of vehicles")

    return jsonify({
        "e_waste_co2e": round(e_waste_co2e, 2),
        "transport_co2e": round(transport_co2e, 2)
    })

if __name__ == '__main__':
    app.run(debug=True)