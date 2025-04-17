import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
import itertools

# --- Configuration ---
DATA_DIR = 'data'
DATA_FILE = os.path.join(DATA_DIR, 'results.json')
X_AXIS_KPIS = ['analysisCapability', 'antiEvasionTechnology']
Y_AXIS_KPIS = ['speedThroughputScale', 'securityDeploymentMaintenance']
AXIS_LABELS = {
    'x': 'Detection & Evasion Capability (%)',
    'y': 'Speed & Operational Efficiency (%)'
}
# Define the order and display names for KPIs (used in both charts)
KPI_DEFINITIONS = {
    "analysisCapability": "Analysis",
    "antiEvasionTechnology": "Anti-Evasion",
    "speedThroughputScale": "Speed/Scale",
    "reportingThreatIntelligence": "Reporting/TI",
    "integrationsAutomation": "Integration",
    "securityDeploymentMaintenance": "Security/Deploy"
}
# Ordered list of keys for radar chart axes
RADAR_KPI_ORDER = list(KPI_DEFINITIONS.keys())
RADAR_LABELS = [KPI_DEFINITIONS[k] for k in RADAR_KPI_ORDER]


WEIGHT_PROFILES = {
    "Large-Scale Processing": {"analysisCapability": 8, "antiEvasionTechnology": 6, "speedThroughputScale": 9, "reportingThreatIntelligence": 3, "integrationsAutomation": 3, "securityDeploymentMaintenance": 6},
    "Zero-Day Detection": {"analysisCapability": 9, "antiEvasionTechnology": 9, "speedThroughputScale": 4, "reportingThreatIntelligence": 8, "integrationsAutomation": 6, "securityDeploymentMaintenance": 6},
    "Air-Gapped / Critical Infra": {"analysisCapability": 6, "antiEvasionTechnology": 6, "speedThroughputScale": 7, "reportingThreatIntelligence": 5, "integrationsAutomation": 2, "securityDeploymentMaintenance": 9},
    "Malware/Phishing Triage": {"analysisCapability": 6, "antiEvasionTechnology": 8, "speedThroughputScale": 5, "reportingThreatIntelligence": 9, "integrationsAutomation": 9, "securityDeploymentMaintenance": 5},
    "Threat Intel Generation": {"analysisCapability": 9, "antiEvasionTechnology": 9, "speedThroughputScale": 3, "reportingThreatIntelligence": 9, "integrationsAutomation": 7, "securityDeploymentMaintenance": 5},
    "Balanced (Equal Weight)": {k: 5 for k in KPI_DEFINITIONS.keys()}
}
DEFAULT_WEIGHTS = WEIGHT_PROFILES["Balanced (Equal Weight)"]

VENDOR_COLORS = ['rgba(255, 99, 132, 0.6)', 'rgba(54, 162, 235, 0.6)', 'rgba(255, 206, 86, 0.6)', 'rgba(75, 192, 192, 0.6)', 'rgba(153, 102, 255, 0.6)', 'rgba(255, 159, 64, 0.6)', 'rgba(46, 204, 113, 0.6)', 'rgba(231, 76, 60, 0.6)', 'rgba(41, 128, 185, 0.6)', 'rgba(241, 196, 15, 0.6)']
VENDOR_BORDERS = ['rgb(255, 99, 132)', 'rgb(54, 162, 235)', 'rgb(255, 206, 86)', 'rgb(75, 192, 192)', 'rgb(153, 102, 255)', 'rgb(255, 159, 64)', 'rgb(46, 204, 113)', 'rgb(231, 76, 60)', 'rgb(41, 128, 185)', 'rgb(241, 196, 15)']

color_cycler = itertools.cycle(zip(VENDOR_COLORS, VENDOR_BORDERS)) # Cycle through pairs
vendor_color_map = {} # Stores {'vendor': {'background': 'rgba', 'border': 'rgb'}}

# --- Flask App Setup ---
app = Flask(__name__)

# --- Data Loading ---
vendor_data = []
def load_data():
    """Loads data from DATA_FILE and populates color map."""
    global vendor_data, vendor_color_map, color_cycler
    vendor_data = [] # Reset data
    vendor_color_map = {} # Reset colors
    try:
        if not os.path.exists(DATA_FILE):
             print(f"ERROR: Data file not found at {DATA_FILE}. Please create the 'data' directory and the file.")
             return False

        with open(DATA_FILE, 'r') as f: vendor_data = json.load(f)
        # Basic validation if data is a list
        if not isinstance(vendor_data, list):
            print(f"ERROR: Data in {DATA_FILE} is not a valid JSON list.")
            vendor_data = []
            return False

        print(f"Loaded {len(vendor_data)} vendor records from {DATA_FILE}")

        if vendor_data:
            # Filter for valid records before sorting/coloring
            valid_vendors = [
                v for v in vendor_data
                if isinstance(v, dict) and
                   'testMetadata' in v and isinstance(v['testMetadata'], dict) and
                   'vendorName' in v['testMetadata'] and 'kpiScores' in v # Ensure scores exist too
            ]
            vendor_names = sorted([v['testMetadata']['vendorName'] for v in valid_vendors])
            color_cycler = itertools.cycle(zip(VENDOR_COLORS, VENDOR_BORDERS)) # Reset cycler
            vendor_color_map = {name: {'background': bg, 'border': bd} for name, (bg, bd) in zip(vendor_names, color_cycler)}
            print("Populated vendor color map.")
            return True
        else:
             return False

    except FileNotFoundError:
        print(f"ERROR: Data file not found at {DATA_FILE}.")
        return False
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {DATA_FILE}. Check format.")
        return False
    except Exception as e:
        print(f"Error loading data file {DATA_FILE}: {e}")
        return False
    finally:
        # Ensure vendor_data and vendor_color_map are lists/dicts even on failure
        if not isinstance(vendor_data, list): vendor_data = []
        if not isinstance(vendor_color_map, dict): vendor_color_map = {}


# --- Helper Functions ---
def calculate_axis_score(scores, weights, axis_kpis):
    weighted_sum = 0
    max_possible_sum = 0
    for kpi in axis_kpis:
        score = scores.get(kpi, 0)
        weight = weights.get(kpi, 0)
        score = max(0, min(10, score))
        weight = max(0, min(10, weight))
        weighted_sum += score * weight
        max_possible_sum += 10 * weight
    return weighted_sum, max_possible_sum

def normalize_score(weighted_sum, max_possible_sum):
    if max_possible_sum == 0: return 0
    normalized = (weighted_sum / max_possible_sum) * 100
    return round(max(0, min(100, normalized)), 2)


# --- Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    if not vendor_data:
         if not load_data(): # Try to load data if empty
            message = f"Error: Could not load data from {os.path.abspath(DATA_FILE)}. Please ensure the file exists in a 'data' subdirectory and is valid JSON."
            return render_template('error.html', message=message)

    return render_template('index.html',
                           kpis=KPI_DEFINITIONS,
                           default_weights=DEFAULT_WEIGHTS,
                           weight_profiles=WEIGHT_PROFILES,
                           axis_labels=AXIS_LABELS,
                           radar_labels=RADAR_LABELS) # Pass radar labels

@app.route('/api/data') # For Scatter Plot
def get_scatter_data():
    global vendor_data, vendor_color_map
    custom_weights = {key: max(0, min(10, request.args.get(key, default=0, type=float))) for key in KPI_DEFINITIONS.keys()}

    if not vendor_data: return jsonify({"error": "No vendor data available"}), 500
    if not vendor_color_map: # Ensure colors loaded
        if not load_data():
             return jsonify({"error": "Failed to load data/colors"}), 500

    chart_data_by_vendor = {}
    for vendor in vendor_data:
        if not isinstance(vendor, dict) or not all(k in vendor for k in ['kpiScores', 'testMetadata']) or \
           'vendorName' not in vendor.get('testMetadata', {}):
            continue

        metadata = vendor['testMetadata']
        scores = vendor['kpiScores']
        vendor_name = metadata['vendorName']
        test_date = metadata.get('testDate', 'N/A')

        ws_x, max_ws_x = calculate_axis_score(scores, custom_weights, X_AXIS_KPIS)
        ws_y, max_ws_y = calculate_axis_score(scores, custom_weights, Y_AXIS_KPIS)
        norm_x = normalize_score(ws_x, max_ws_x)
        norm_y = normalize_score(ws_y, max_ws_y)
        colors = vendor_color_map.get(vendor_name, {'background': '#808080', 'border': '#606060'})

        nudge = 3.5 # How much to nudge away from edge
        if norm_x >= (100.0 - nudge / 2): norm_x = 100.0 - nudge
        if norm_x <= (0.0 + nudge / 2): norm_x = 0.0 + nudge
        if norm_y >= (100.0 - nudge / 2): norm_y = 100.0 - nudge
        if norm_y <= (0.0 + nudge / 2): norm_y = 0.0 + nudge
        norm_x = round(norm_x, 2)
        norm_y = round(norm_y, 2)

        if vendor_name not in chart_data_by_vendor:
            chart_data_by_vendor[vendor_name] = {
                'label': vendor_name, 'data': [],
                'backgroundColor': colors['background'], 'borderColor': colors['border'],
                'pointRadius': 7, 'pointHoverRadius': 9
            }
        chart_data_by_vendor[vendor_name]['data'].append({
            'x': norm_x, 'y': norm_y, 'vendor': vendor_name, 'test_date': test_date,
            'fp_rate': vendor.get('keyPerformanceMetrics', {}).get('falsePositiveRatePercent', 'N/A'),
            'fn_rate': vendor.get('keyPerformanceMetrics', {}).get('falseNegativeRatePercent', 'N/A'),
            'avg_speed': vendor.get('keyPerformanceMetrics', {}).get('averageProcessingTimeSeconds', 'N/A')
        })

    chart_datasets = list(chart_data_by_vendor.values())
    return jsonify(chart_datasets)

@app.route('/api/rawscores') # New endpoint for Radar Chart
def get_raw_scores():
    """Returns raw KPI scores for all vendors for the radar chart."""
    global vendor_data, vendor_color_map
    if not vendor_data: return jsonify({"error": "No vendor data available"}), 500
    if not vendor_color_map:
        if not load_data(): return jsonify({"error": "Failed to load data/colors"}), 500

    radar_datasets = []
    for vendor in vendor_data:
         if not isinstance(vendor, dict) or not all(k in vendor for k in ['kpiScores', 'testMetadata']) or \
            'vendorName' not in vendor.get('testMetadata', {}):
             continue

         vendor_name = vendor['testMetadata']['vendorName']
         scores = vendor['kpiScores']
         colors = vendor_color_map.get(vendor_name, {'background': '#808080', 'border': '#606060'})

         # Create data array in the order defined by RADAR_KPI_ORDER
         data_points = [max(0, min(10, scores.get(kpi, 0))) for kpi in RADAR_KPI_ORDER] # Ensure 0-10

         radar_datasets.append({
             'label': vendor_name,
             'data': data_points,
             'fill': True,
             'backgroundColor': colors['background'], # Use semi-transparent bg
             'borderColor': colors['border'],     # Use solid border
             'pointBackgroundColor': colors['border'],
             'pointBorderColor': '#fff',
             'pointHoverBackgroundColor': '#fff',
             'pointHoverBorderColor': colors['border']
         })

    return jsonify({'labels': RADAR_LABELS, 'datasets': radar_datasets})


@app.route('/api/rawdata') # For Download
def get_raw_data_file():
    """Serves the raw data JSON file for download."""
    try:
        data_dir_abs = os.path.abspath(DATA_DIR)
        file_path_abs = os.path.abspath(DATA_FILE)

        # Security check: ensure the file requested is inside the intended data directory
        if not file_path_abs.startswith(data_dir_abs):
             return jsonify({"error": "Access denied"}), 403

        if not os.path.exists(file_path_abs):
            return jsonify({"error": f"Data file not found: {DATA_FILE}"}), 404

        return send_from_directory(
            directory=data_dir_abs,
            path=os.path.basename(DATA_FILE),
            as_attachment=True,
            download_name='sandbox_landscape_raw_data.json' # Custom download name
        )
    except Exception as e:
        print(f"Error serving raw data file: {e}")
        return jsonify({"error": "Could not serve raw data file."}), 500

# --- Main Execution ---
if __name__ == '__main__':
    load_data() # Load data at startup
    print("\n--- Enhanced App v5 (Radar) Setup Complete ---")
    if not vendor_data:
        print(f"WARNING: No data loaded. Check {os.path.abspath(DATA_FILE)}")
    else:
        print(f"Expecting data file at: {os.path.abspath(DATA_FILE)}")
    print("To run: `python app.py`")
    print("Access at: http://127.0.0.1:5001")
    print("---")
    app.run(debug=True, host='0.0.0.0', port=5001)