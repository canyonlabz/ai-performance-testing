import xml.etree.ElementTree as ET
import json
import re

def jmeter_path_to_swagger_style(path):
    """
    Convert /api/v1/engagement/${engagementId} 
    to /api/v1/engagement/{engagementId}
    for easier comparison with Swagger.
    """
    return re.sub(r'\$\{([^\}]+)\}', r'{\1}', path)

def parse_jmeter_endpoints(jmx_file_path):
    """
    Parses the JMeter .jmx file and returns a list of dictionaries.
    Each dict contains:
      - method: e.g. "POST"
      - path: e.g. "/api/v1/engagement/${engagementId}"
      - label: e.g. "Create Engagement" (if found)
    Preserves duplicates if the same endpoint is repeated.
    """
    tree = ET.parse(jmx_file_path)
    root = tree.getroot()
    
    jmeter_endpoints = []
    
    # Each HTTPSamplerProxy typically represents one request
    for sampler in root.iter('HTTPSamplerProxy'):
        method_element = sampler.find("./stringProp[@name='HTTPSampler.method']")
        path_element = sampler.find("./stringProp[@name='HTTPSampler.path']")
        
        # Optional: Sampler name or label
        label_element = sampler.find("./stringProp[@name='TestElement.name']")
        
        if method_element is not None and path_element is not None:
            jmeter_endpoints.append({
                "method": method_element.text.strip(),
                "path": path_element.text.strip(),
                "label": label_element.text.strip() if label_element is not None else "No Label"
            })
    
    return jmeter_endpoints

def parse_swagger_endpoints(swagger_file_path):
    """
    Parses the Swagger JSON file and returns a set of (method, path).
    Each path is e.g. "/api/v2/engagement/{engagementId}" 
    and method is uppercase ("POST", "GET", etc.)
    """
    with open(swagger_file_path, "r") as f:
        swagger_data = json.load(f)
    
    swagger_set = set()
    paths = swagger_data.get("paths", {})
    
    for path, operations in paths.items():
        # operations might be {"get": {...}, "post": {...}, ...}
        for method in operations.keys():
            method_upper = method.upper()
            swagger_set.add((method_upper, path))
    
    return swagger_set

def compare_endpoints(jmeter_endpoints, swagger_endpoints_set):
    """
    Compare JMeter endpoints (list) to Swagger endpoints (set).
    Also detect duplicates in JMeter.

    Returns:
      - matched_in_jmeter (list): All JMeter items that match something in Swagger
      - missing_in_swagger (list): JMeter items NOT in Swagger
      - missing_in_jmeter (list): Swagger endpoints missing in JMeter
      - duplicates (list): Each (method, normalized_path) that appears more than once
                           in JMeter, reported once with a count.
    """
    
    # We'll keep track of normalized combos for each JMeter endpoint
    jmeter_combos = []  # e.g., [("POST", "/api/v1/engagement/{engagementId}"), ...]
    
    matched_in_jmeter = []
    missing_in_swagger = []
    
    for ep in jmeter_endpoints:
        norm_path = jmeter_path_to_swagger_style(ep["path"])
        combo = (ep["method"], norm_path)
        jmeter_combos.append(combo)
        
        # Check if this combo is in Swagger
        if combo in swagger_endpoints_set:
            matched_in_jmeter.append(ep)  # Keep original detail
        else:
            missing_in_swagger.append(ep)
    
    # Identify what's missing in JMeter from Swagger
    jmeter_set = set(jmeter_combos)
    missing_in_jmeter = []
    for (method, path) in swagger_endpoints_set:
        if (method, path) not in jmeter_set:
            missing_in_jmeter.append({"method": method, "path": path})
    
    # Detect duplicates
    # We'll count how many times each combo appears in jmeter_combos.
    combo_count = {}
    for combo in jmeter_combos:
        combo_count[combo] = combo_count.get(combo, 0) + 1
    
    duplicates = []
    for combo, cnt in combo_count.items():
        if cnt > 1:
            # Just list each duplicate once
            duplicates.append({
                "method": combo[0],
                "path": combo[1],
                "count": cnt
            })
    
    return matched_in_jmeter, missing_in_swagger, missing_in_jmeter, duplicates

if __name__ == "__main__":
    # Example usage
    jmeter_file = "example.jmx"
    swagger_file = "swagger.json"
    
    # Step 1: Parse JMeter
    jmeter_endpoints = parse_jmeter_endpoints(jmeter_file)
    
    # Step 2: Parse Swagger (returns a set)
    swagger_endpoints_set = parse_swagger_endpoints(swagger_file)
    
    # Step 3: Compare (also get duplicates)
    matched_in_jmeter, missing_in_swagger, missing_in_jmeter, duplicates = compare_endpoints(jmeter_endpoints, swagger_endpoints_set)
    
    print("\n=== MATCHED IN JMETER ===")
    for ep in matched_in_jmeter:
        print(f"- Label: {ep['label']}, Method: {ep['method']}, Path: {ep['path']}")
    
    print("\n=== MISSING IN SWAGGER (Present in JMeter but not in Swagger) ===")
    for ep in missing_in_swagger:
        print(f"- Label: {ep['label']}, Method: {ep['method']}, Path: {ep['path']}")
    
    print("\n=== MISSING IN JMETER (Present in Swagger but not in JMeter) ===")
    for ep in missing_in_jmeter:
        print(f"- Method: {ep['method']}, Path: {ep['path']}")
    
    print("\n=== DUPLICATES (Appear more than once in JMeter) ===")
    for d in duplicates:
        print(f"- Method: {d['method']}, Path: {d['path']}, Count: {d['count']}")
