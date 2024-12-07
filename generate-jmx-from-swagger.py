import json
import xml.etree.ElementTree as ET
import sys
import os

def generate_jmx_from_swagger(swagger_json, output_file="generated_test_plan.jmx"):
    """
    Generate a JMeter JMX file from Swagger JSON.

    :param swagger_json: The parsed Swagger JSON object
    :param output_file: The name of the output JMX file
    """
    try:
        # Validate Swagger JSON
        if "paths" not in swagger_json:
            raise ValueError("Invalid Swagger JSON: 'paths' section missing.")
        
        # Create the root Test Plan element
        jmeter_test_plan = ET.Element("jmeterTestPlan", attrib={
            "version": "1.2", "properties": "5.0", "jmeter": "5.5"
        })
        hash_tree = ET.SubElement(jmeter_test_plan, "hashTree")

        # Test Plan setup
        test_plan = ET.SubElement(hash_tree, "TestPlan", attrib={
            "guiclass": "TestPlanGui", "testclass": "TestPlan", "testname": "Test Plan", "enabled": "true"
        })
        ET.SubElement(test_plan, "stringProp", name="TestPlan.comments").text = ""
        ET.SubElement(test_plan, "boolProp", name="TestPlan.functional_mode").text = "false"
        ET.SubElement(test_plan, "elementProp", name="TestPlan.user_defined_variables", elementType="Arguments")
        ET.SubElement(test_plan, "boolProp", name="TestPlan.serialize_threadgroups").text = "false"
        test_plan_hash_tree = ET.SubElement(hash_tree, "hashTree")

        # Thread Group setup
        thread_group = ET.SubElement(test_plan_hash_tree, "ThreadGroup", attrib={
            "guiclass": "ThreadGroupGui", "testclass": "ThreadGroup", "testname": "Thread Group", "enabled": "true"
        })
        ET.SubElement(thread_group, "intProp", name="ThreadGroup.num_threads").text = "1"
        ET.SubElement(thread_group, "intProp", name="ThreadGroup.ramp_time").text = "1"
        ET.SubElement(thread_group, "longProp", name="ThreadGroup.duration").text = "0"
        ET.SubElement(thread_group, "boolProp", name="ThreadGroup.scheduler").text = "false"
        main_controller = ET.SubElement(thread_group, "elementProp", name="ThreadGroup.main_controller",
                                        elementType="LoopController", guiclass="LoopControlPanel", testclass="LoopController")
        ET.SubElement(main_controller, "stringProp", name="LoopController.loops").text = "1"
        ET.SubElement(main_controller, "boolProp", name="LoopController.continue_forever").text = "false"
        thread_group_hash_tree = ET.SubElement(test_plan_hash_tree, "hashTree")

        # Generate HTTP Samplers from Swagger paths
        for path, methods in swagger_json["paths"].items():
            for method, details in methods.items():
                sampler_name = f"{method.upper()} {path}"
                sampler = ET.SubElement(thread_group_hash_tree, "HTTPSamplerProxy", attrib={
                    "guiclass": "HttpTestSampleGui", "testclass": "HTTPSamplerProxy", "testname": sampler_name, "enabled": "true"
                })
                ET.SubElement(sampler, "stringProp", name="HTTPSampler.protocol").text = "HTTPS"
                ET.SubElement(sampler, "stringProp", name="HTTPSampler.domain").text = "${HOSTNAME}"
                ET.SubElement(sampler, "stringProp", name="HTTPSampler.port").text = "443"
                ET.SubElement(sampler, "stringProp", name="HTTPSampler.path").text = path
                ET.SubElement(sampler, "stringProp", name="HTTPSampler.method").text = method.upper()
                arguments = ET.SubElement(sampler, "elementProp", name="HTTPsampler.Arguments", elementType="Arguments")
                collection_prop = ET.SubElement(arguments, "collectionProp", name="Arguments.arguments")

                # Add query parameters or body parameters as arguments
                parameters = details.get("parameters", [])
                for param in parameters:
                    param_name = param.get("name", "parameter")
                    param_type = param.get("in", "query")  # 'query', 'body', etc.
                    if param_type == "query":
                        argument = ET.SubElement(collection_prop, "elementProp", name=param_name, elementType="HTTPArgument")
                        ET.SubElement(argument, "boolProp", name="HTTPArgument.always_encode").text = "true"
                        ET.SubElement(argument, "stringProp", name="Argument.name").text = param_name
                        ET.SubElement(argument, "stringProp", name="Argument.value").text = f"${{{param_name}}}"
                        ET.SubElement(argument, "stringProp", name="Argument.metadata").text = "="

                sampler_hash_tree = ET.SubElement(thread_group_hash_tree, "hashTree")

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


if __name__ == "__main__":
    # Ensure the script is run with a valid JSON file as an argument
    if len(sys.argv) != 2:
        print("Usage: python generate-jmx-from-swagger.py <swagger_json_file>")
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
