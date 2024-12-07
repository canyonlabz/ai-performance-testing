import json
import xml.etree.ElementTree as ET
import sys
import os

def generate_jmx_from_swagger(swagger_json, output_file="generated_test_plan.jmx"):
    """
    Generate a JMeter JMX file dynamically from Swagger JSON.

    :param swagger_json: The parsed Swagger JSON object
    :param output_file: The name of the output JMX file
    """
    try:
        # Validate Swagger JSON
        if "paths" not in swagger_json:
            raise ValueError("Invalid Swagger JSON: 'paths' section missing.")

        # Create the root Test Plan element
        jmeter_test_plan = ET.Element("jmeterTestPlan", attrib={
            "version": "1.2", "properties": "5.0", "jmeter": "5.6.3"
        })
        hash_tree = ET.SubElement(jmeter_test_plan, "hashTree")

        # Test Plan setup
        test_plan = ET.SubElement(hash_tree, "TestPlan", attrib={
            "guiclass": "TestPlanGui", "testclass": "TestPlan", "testname": "Test Plan"
        })
        user_defined_vars = ET.SubElement(test_plan, "elementProp", attrib={
            "name": "TestPlan.user_defined_variables", "elementType": "Arguments"
        })
        ET.SubElement(user_defined_vars, "collectionProp", attrib={"name": "Arguments.arguments"})
        ET.SubElement(test_plan, "stringProp", attrib={"name": "TestPlan.user_define_classpath"}).text = ""

        test_plan_hash_tree = ET.SubElement(hash_tree, "hashTree")

        # Dynamically Add User Defined Variables based on Swagger parameters
        arguments = ET.SubElement(test_plan_hash_tree, "Arguments", attrib={
            "guiclass": "ArgumentsPanel", "testclass": "Arguments", "testname": "User Defined Variables"
        })
        collection = ET.SubElement(arguments, "collectionProp", attrib={"name": "Arguments.arguments"})

        dynamic_vars = set()
        for path, methods in swagger_json["paths"].items():
            for method_details in methods.values():
                parameters = method_details.get("parameters", [])
                for param in parameters:
                    dynamic_vars.add(param["name"])

        for var in dynamic_vars:
            var_element = ET.SubElement(collection, "elementProp", attrib={
                "name": var, "elementType": "Argument"
            })
            ET.SubElement(var_element, "stringProp", attrib={"name": "Argument.name"}).text = var
            ET.SubElement(var_element, "stringProp", attrib={"name": "Argument.value"}).text = ""
            ET.SubElement(var_element, "stringProp", attrib={"name": "Argument.metadata"}).text = "="

        ET.SubElement(test_plan_hash_tree, "hashTree")

        # Get the server URL from the Swagger JSON
        server_url = extract_server_url(swagger_json)
        print(f"Using server URL as prefix to API endpoint: {server_url}")

        # Add Thread Group
        thread_group = ET.SubElement(test_plan_hash_tree, "ThreadGroup", attrib={
            "guiclass": "ThreadGroupGui", "testclass": "ThreadGroup", "testname": "Thread Group"
        })
        ET.SubElement(thread_group, "intProp", attrib={"name": "ThreadGroup.num_threads"}).text = "1"
        ET.SubElement(thread_group, "intProp", attrib={"name": "ThreadGroup.ramp_time"}).text = "1"
        ET.SubElement(thread_group, "longProp", attrib={"name": "ThreadGroup.duration"}).text = "0"
        ET.SubElement(thread_group, "boolProp", attrib={"name": "ThreadGroup.scheduler"}).text = "false"
        loop_controller = ET.SubElement(thread_group, "elementProp", attrib={
            "name": "ThreadGroup.main_controller", "elementType": "LoopController"
        })
        ET.SubElement(loop_controller, "stringProp", attrib={"name": "LoopController.loops"}).text = "1"
        ET.SubElement(loop_controller, "boolProp", attrib={"name": "LoopController.continue_forever"}).text = "false"

        thread_group_hash_tree = ET.SubElement(test_plan_hash_tree, "hashTree")

        # Add HTTP Samplers and Header Manager
        for path, methods in swagger_json["paths"].items():
            for method, details in methods.items():
                sampler = ET.SubElement(thread_group_hash_tree, "HTTPSamplerProxy", attrib={
                    "guiclass": "HttpTestSampleGui", "testclass": "HTTPSamplerProxy",
                    "testname": f"{method.upper()} {path}"
                })
                ET.SubElement(sampler, "stringProp", attrib={"name": "HTTPSampler.domain"}).text = "${HOSTNAME}"
                ET.SubElement(sampler, "stringProp", attrib={"name": "HTTPSampler.protocol"}).text = "https"
                ET.SubElement(sampler, "stringProp", attrib={"name": "HTTPSampler.port"}).text = "443"
                ET.SubElement(sampler, "stringProp", attrib={"name": "HTTPSampler.path"}).text = path
                ET.SubElement(sampler, "stringProp", attrib={"name": "HTTPSampler.method"}).text = method.upper()
                ET.SubElement(sampler, "boolProp", attrib={"name": "HTTPSampler.auto_redirects"}).text = "true"
                sampler_arguments = ET.SubElement(sampler, "elementProp", name="HTTPsampler.Arguments", elementType="Arguments")
                collection_prop = ET.SubElement(sampler_arguments, "collectionProp", name="Arguments.arguments")

                # Add query parameters or body parameters as arguments
                request_parameters = details.get("parameters", [])
                for request_param in request_parameters:
                    param_name = request_param.get("name", "parameter")
                    param_type = request_param.get("in", "query")  # 'query', 'body', etc.
                    if param_type == "query":
                        request_argument = ET.SubElement(collection_prop, "elementProp", name=param_name, elementType="HTTPArgument")
                        ET.SubElement(request_argument, "boolProp", name="HTTPArgument.always_encode").text = "true"
                        ET.SubElement(request_argument, "stringProp", name="Argument.name").text = param_name
                        ET.SubElement(request_argument, "stringProp", name="Argument.value").text = f"${{{param_name}}}"
                        ET.SubElement(request_argument, "stringProp", name="Argument.metadata").text = "="

                # Add Header Manager for Authorization
                sampler_hash_tree = ET.SubElement(thread_group_hash_tree, "hashTree")
                header_manager = ET.SubElement(sampler_hash_tree, "HeaderManager", attrib={
                    "guiclass": "HeaderPanel", "testclass": "HeaderManager", "testname": "HTTP Header Manager"
                })
                header_collection = ET.SubElement(header_manager, "collectionProp", attrib={"name": "HeaderManager.headers"})
                auth_header = ET.SubElement(header_collection, "elementProp", attrib={"name": "", "elementType": "Header"})
                ET.SubElement(auth_header, "stringProp", attrib={"name": "Header.name"}).text = "Authorization"
                ET.SubElement(auth_header, "stringProp", attrib={"name": "Header.value"}).text = "${auth_token}"

        # Add Listeners
        listeners = [
            ("View Results Tree", "ViewResultsFullVisualizer"),
            ("Summary Report", "SummaryReport")
        ] 
        for listener_name, guiclass in listeners:
            listener = ET.SubElement(hash_tree, "ResultCollector", attrib={
                "guiclass": guiclass, "testclass": "ResultCollector", "testname": listener_name, "enabled": "true"
            })
            ET.SubElement(listener, "boolProp", name="ResultCollector.error_logging").text = "false"
            listener_hash_tree = ET.SubElement(hash_tree, "hashTree")
                
        # Write the XML to a file
        tree = ET.ElementTree(jmeter_test_plan)
        tree.write(output_file, encoding="UTF-8", xml_declaration=True)
        print(f"JMX file generated successfully: {output_file}")

    except Exception as e:
        print(f"Error generating JMX file: {e}")

# Function to extract the server URL from the Swagger JSON
def extract_server_url(swagger_json):
    """
    Extract the server URL from the Swagger JSON file.

    :param swagger_json: Parsed Swagger JSON data
    :return: Server URL if found, else an empty string
    """
    try:
        # Look for 'servers' in the Swagger JSON
        servers = swagger_json.get("servers", [])
        if not servers:
            print("No 'servers' section found in the Swagger JSON. Returning an empty string.")
            return ""

        # Extract the first server URL
        server_url = servers[0].get("url", "")
        print(f"Extracted server URL: {server_url}")
        return server_url
    except Exception as e:
        print(f"Error extracting server URL: {e}")
        return ""

if __name__ == "__main__":
    # Ensure the script is run with a valid JSON file as an argument
    if len(sys.argv) != 2:
        print("Usage: python generate_jmx_from_swagger.py <swagger_json_file>")
        sys.exit(1)

    swagger_file = sys.argv[1]

    if not os.path.exists(swagger_file):
        print(f"Error: File '{swagger_file}' does not exist.")
        sys.exit(1)

    # Load the Swagger JSON file
    with open(swagger_file, "r", encoding="utf-8") as f:
        swagger_data = json.load(f)

    # Generate the JMX file
    generate_jmx_from_swagger(swagger_data)
