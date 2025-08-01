from flask import Flask, send_from_directory, jsonify
import os
import json

app = Flask(__name__)

# Serve the main HTML
@app.route('/')
def index():
    return send_from_directory('.', 'working_multi_view.html')

# Serve the enhanced network JSON
@app.route('/data')
def data():
    with open('concept_network/complete_enhanced_network.json', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

# Serve concept network files
@app.route('/concept_network/<path:filename>')
def concept_network_files(filename):
    return send_from_directory('concept_network', filename)

# Serve vis.js library files
@app.route('/lib/vis-9.1.2/<path:filename>')
def vis_library_files(filename):
    return send_from_directory('lib/vis-9.1.2', filename)

# Serve tom-select library files
@app.route('/lib/tom-select/<path:filename>')
def tom_select_files(filename):
    return send_from_directory('lib/tom-select', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001) 