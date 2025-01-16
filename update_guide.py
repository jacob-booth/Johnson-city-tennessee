import requests
import yaml
import os

# Configuration
DATA_DIR = 'data'
SOURCES = {
    'restaurants': 'https://api.example.com/restaurants',
    'shops': 'https://api.example.com/shops',
    'events': 'https://api.example.com/events',
    'local_tales': 'https://api.example.com/local_tales',
    'entertainment': 'https://api.example.com/entertainment'
}

def fetch_data(source_url):
    response = requests.get(source_url)
    response.raise_for_status()
    return response.json()

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

    save_data(os.path.join(DATA_DIR, f'{source}.yml'), existing_data)

def main():
    for source, url in SOURCES.items():
        try:
            data = fetch_data(url)
            update_data(source, data)
        except Exception as e:
            print(f"Failed to update {source}: {e}")

if __name__ == '__main__':
    main()