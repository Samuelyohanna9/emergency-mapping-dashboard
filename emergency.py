from flask import Flask, jsonify, request
import psycopg2
from flask_cors import CORS
import json
import requests

app = Flask(__name__)
CORS(app)

# Database connection
conn = psycopg2.connect(
    dbname="emergency_db",
    user="postgres",
    password="password",  # Replace with your actual password
    host="localhost",
    port="35432"  # Default PostgreSQL port
)

@app.route('/')
def home():
    return "Welcome to the Emergency Response System!"

@app.route('/api/accidents')
def get_accidents():
    try:
        category = request.args.get('category', default=None, type=str)
        cur = conn.cursor()
        query = """
            SELECT id, ST_AsGeoJSON(geom) AS geometry, "UKATEGORIE" AS category
            FROM accidents
        """
        if category:
            query += f" WHERE \"UKATEGORIE\" = '{category}'"
        query += ";"
        cur.execute(query)
        results = cur.fetchall()
        cur.close()

        # Convert results to GeoJSON format
        features = []
        for id, geometry, category in results:
            geom = json.loads(geometry)
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {"id": id, "category": category}
            })

        return jsonify({"type": "FeatureCollection", "features": features})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/heatmap')
def get_heatmap():
    try:
        cur = conn.cursor()
        query = """
            SELECT ST_X(geom) AS longitude, ST_Y(geom) AS latitude
            FROM accidents;
        """
        cur.execute(query)
        results = cur.fetchall()
        cur.close()

        if not results:
            return jsonify({"error": "No accident data found"}), 404

        # Convert accident points into Leaflet heatmap format (latitude, longitude, intensity)
        heatmap_data = [[lat, lon, 1] for lon, lat in results]  # Intensity = 1 (each accident is 1 unit)

        print("Heatmap data:", heatmap_data)  # Log the data being returned

        return jsonify(heatmap_data)
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/accidents_by_landuse')
def get_accidents_by_landuse():
    try:
        cur = conn.cursor()
        query = """
            SELECT landuse_type, accident_count
            FROM precomputed_accidents_by_landuse;
        """
        cur.execute(query)
        results = cur.fetchall()
        cur.close()

        # Convert results to a list of dictionaries
        accidents_by_landuse = [{"landuse_type": landuse_type, "accident_count": count} for landuse_type, count in results]

        return jsonify(accidents_by_landuse)
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/optimal_locations')
def get_optimal_locations():
    try:
        cur = conn.cursor()
        query = """
            SELECT ST_AsGeoJSON(geom) AS geometry
            FROM precomputed_optimal_locations;
        """
        cur.execute(query)
        results = cur.fetchall()
        cur.close()

        # Convert results to GeoJSON format
        features = []
        for geometry in results:
            geom = json.loads(geometry[0])
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {}
            })

        return jsonify({"type": "FeatureCollection", "features": features})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/layers')
def get_layers():
    try:
        layer_type = request.args.get('type', default=None, type=str)
        cur = conn.cursor()
        if layer_type == 'roads':
            query = "SELECT id, ST_AsGeoJSON(geom) AS geometry FROM roads;"
        elif layer_type == 'population_density':
            query = "SELECT id, ST_AsGeoJSON(geom) AS geometry, density FROM population_density;"
        elif layer_type == 'landuse':
            query = "SELECT id, ST_AsGeoJSON(geom) AS geometry, fclass FROM landuse;"

        else:
            return jsonify({"error": "Invalid layer type"}), 400

        cur.execute(query)
        results = cur.fetchall()
        cur.close()

        features = []
        for result in results:
            geom = json.loads(result[1])
            properties = {"id": result[0]}
            if layer_type == 'population_density':
                properties["density"] = result[2]
            elif layer_type == 'landuse':
                properties["fclass"] = result[2]
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": properties
            })

        return jsonify({"type": "FeatureCollection", "features": features})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/route_to_nearest_optimal')
def get_route_to_nearest_optimal():
    try:
        start_lon = request.args.get('start_lon', type=float)
        start_lat = request.args.get('start_lat', type=float)

        # Validate inputs
        if None in [start_lon, start_lat]:
            return jsonify({"error": "Missing start coordinates"}), 400

        # Find the nearest optimal location
        cur = conn.cursor()
        query = f"""
            SELECT ST_AsGeoJSON(geom) AS geometry
            FROM precomputed_optimal_locations
            ORDER BY ST_Distance(geom, ST_SetSRID(ST_MakePoint({start_lon}, {start_lat}), 4326))
            LIMIT 1;
        """
        cur.execute(query)
        result = cur.fetchone()
        cur.close()

        if not result:
            return jsonify({"error": "No optimal location found"}), 404

        optimal_location = json.loads(result[0])
        end_lon, end_lat = optimal_location['coordinates']

        # OSRM API URL (public OSRM demo server)
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"

        # Fetch route from OSRM
        response = requests.get(osrm_url)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch route from OSRM"}), 500

        # Parse the route data
        route_data = response.json()
        route_geometry = route_data['routes'][0]['geometry']

        # Return the route geometry in GeoJSON format
        return jsonify({
            "type": "Feature",
            "geometry": route_geometry,
            "properties": {
                "distance": route_data['routes'][0]['distance'],  # Distance in meters
                "duration": route_data['routes'][0]['duration']   # Duration in seconds
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)