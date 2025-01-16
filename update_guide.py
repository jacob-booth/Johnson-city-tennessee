import requests
import yaml
import os
from bs4 import BeautifulSoup

# Configuration
DATA_DIR = 'data'
SOURCES = {
    'restaurants': 'https://api.example.com/restaurants',
    'shops': 'https://api.example.com/shops',
    'events': 'https://api.example.com/events',
    'local_tales': 'https://api.example.com/local_tales',
    'entertainment': 'https://api.example.com/entertainment'
}

def fetch_data_from_api(source_url):
    response = requests.get(source_url)
    response.raise_for_status()
    return response.json()

def fetch_data_from_web(source_url):
    response = requests.get(source_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    # Parse the data from the web page
    # This is a placeholder for actual parsing logic
    entries = []
    for item in soup.find_all('div', class_='entry'):
        name = item.find('h2').text.strip()
        description = item.find('p').text.strip()
        entries.append({'Name': name, 'Description': description})
    return entries

def load_existing_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    return {}

def save_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        yaml.safe_dump(data, file, allow_unicode=True)

def update_data(source, data):
    existing_data = load_existing_data(os.path.join(DATA_DIR, f'{source}.yml'))
    existing_entries = {entry['Name']: entry for entry in existing_data.get('Entries', [])}
    new_entries = {entry['Name']: entry for entry in data}

    # Update existing entries and add new ones
    for name, entry in new_entries.items():
        if name not in existing_entries:
            existing_data.setdefault('Entries', []).append(entry)
        else:
            existing_entries[name].update(entry)

    file_path = os.path.join(DATA_DIR, f'{source}.yml')
    _validate_data(file_path)  # Validate data before saving
    save_data(file_path, existing_data)

def main():
    for source, url in SOURCES.items():
        try:
            if 'api' in url:
                data = fetch_data_from_api(url)
            else:
                data = fetch_data_from_web(url)
            update_data(source, data)
        except Exception as e:
            print(f"Failed to update {source}: {e}")

if __name__ == '__main__':
    main()

def _validate_data(file_path):
    """
    Validates the data in the given YAML file to ensure all entries have the required fields.
    This function is intended for internal use and should not be documented publicly.
    """
    required_fields = {'Name', 'Description'}
    data = load_existing_data(file_path)
    entries = data.get('Entries', [])
    for entry in entries:
        if not required_fields.issubset(entry.keys()):
            raise ValueError(f"Entry in {file_path} is missing required fields: {required_fields - entry.keys()}")
    print(f"Data in {file_path} is valid.")