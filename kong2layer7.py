import yaml
import json
import logging
import requests
import urllib3

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def save_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

urllib3.disable_warnings()
logging.captureWarnings(True)



# Define the GraphQL query
query = '''
mutation setWebApiServices ($input: [L7ServiceInput!]!){
    setServices (input: $input) {
        detailedStatus {
            status
            description
            source { name value }
            target { name value }
        }
    }
}
'''
# Define the headers for the request
headers = {
    "Content-Type": "application/json"
}

# Define the URL for the GraphQL endpoint
#url = "https://localhost:7443/graphman"
url = sys.argv[1]

def extract_service_data(config):
    services = config.get('services', [])

    service_data_list = []
    for service in services:
        service_data = {}
        service_data['name'] = service.get('name', None)

        routes = service.get('routes', [])
        if routes:
            route = routes[0]
            service_data['paths'] = route.get('paths', [])
            service_data['methods'] = route.get('methods', [])

        plugins = service.get('plugins', [])
        if plugins:
            plugin = plugins[0]
            plugin_config = plugin.get('config', {})
            service_data['limit'] = plugin_config.get('limit', [None])[0]
            service_data['window_size'] = plugin_config.get('window_size', [None])[0]

        service_data['protocol'] = service.get('protocol', None)
        service_data['host'] = service.get('host', None)
        service_data['port'] = service.get('port', None)

        service_data_list.append(service_data)

    return service_data_list


def update_json_with_service_data(json_data, service_data_list):
    for service_data in service_data_list:

        json_data['input'][0]['name'] = service_data['name']
        json_data['input'][0]['resolutionPath'] = service_data['paths'][0]
        json_data['input'][0]['serviceType'] = 'WEB_API'
        json_data['input'][0]['folderPath'] = '/Kong2L7'
        json_data['input'][0]['methodsAllowed'] = service_data['methods'][0]

        json_data['input'][0]['policy']['code']['All'][0]['RateLimit']['counterName'] = 'MODIFIED_COUNTER_NAME'
        json_data['input'][0]['policy']['code']['All'][0]['RateLimit']['maxRequestsPerSecond'] = str(service_data['limit'])
        json_data['input'][0]['policy']['code']['All'][0]['RateLimit']['windowSizeInSeconds'] = str(service_data['window_size'])
        json_data['input'][0]['policy']['code']['All'][1]['HttpRouting']['httpMethod'] = service_data['methods'][0]


        protocol = service_data['protocol']
        host = service_data['host']
        port = service_data['port']
        if protocol and host and port:
            #json_data['protectedServiceUrl'] = f"{protocol}://{host}:{port}"
            json_data['input'][0]['policy']['code']['All'][1]['HttpRouting'][
                'protectedServiceUrl'] = f"{protocol}://{host}:{port}"
        else:
            json_data['input'][0]['policy']['code']['All'][1]['HttpRouting'][
                'protectedServiceUrl'] = None
        print("JSON Data",json_data)
        variable = json_data
        # Prepare the request payload
        payload = {
            "query": query,
            "variables": variable
        }

        # Make the POST request to the GraphQL endpoint with basic authentication
        response = requests.post(url, headers=headers, json=payload, auth=('admin', '7layer'), verify=False)

        # Check for errors
        if response.status_code == 200:
            print("Response:")
            print(json.dumps(response.json(), indent=4))
        else:
            print(f"Query failed to run by returning code of {response.status_code}. {response.text}")

    return json_data


def main():
    # File paths
    yaml_file_path = 'kongdump.yaml'
    json_file_path = 'createServiceRatelimitRoute.json'
    output_json_file_path = 'updated_createServiceRatelimitRoute.json'

    # Load YAML data
    yaml_data = load_yaml(yaml_file_path)

    # Load JSON data
    json_data = load_json(json_file_path)

    # Extract service data from YAML
    service_data_list = extract_service_data(yaml_data)

    # Update JSON data with service data
    updated_json_data = update_json_with_service_data(json_data, service_data_list)

    # Save updated JSON data
    save_json(updated_json_data, output_json_file_path)

    print("JSON file has been updated and saved to", output_json_file_path)


if __name__ == "__main__":
    main()
