import requests
import yaml
import os
from bs4 import BeautifulSoup
import time
from pathlib import Path
import sys

# Configuration
DATA_DIR = 'data'
# Ensure data directory exists
Path(DATA_DIR).mkdir(exist_ok=True)

# Maximum number of retries for failed requests
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# API base URL
API_BASE_URL = 'http://localhost:3000/api'

def _validate_data(file_path):
    """
    Validates the data in the given YAML file to ensure all entries have the required fields.
    This function is intended for internal use and should not be documented publicly.
    """
    try:
        required_fields = {
            'restaurants': {'Name', 'Description'},
            'shops': {'Name', 'Description'},
            'events': {'Name', 'Description'},
            'parks_recreation': {'Name', 'Description'},
            'cultural_landmarks': {'Name', 'Description'}
        }
        
        source_name = os.path.basename(file_path).rsplit('.', 1)[0]
        if source_name not in required_fields:
            print(f"No validation requirements defined for {source_name}")
            return True
            
        data = load_existing_data(file_path)
        entries = data.get('Entries', [])
        for entry in entries:
            if not required_fields[source_name].issubset(entry.keys()):
                raise ValueError(f"Entry in {file_path} is missing required fields: {required_fields[source_name] - entry.keys()}")
        print(f"Data in {file_path} is valid")
        return True
    except Exception as e:
        print(f"Error validating data in {file_path}: {e}")
        return False

def fetch_data_with_retry(url, fetch_func, max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Helper function to retry failed requests"""
    for attempt in range(max_retries):
        try:
            return fetch_func(url)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)

# Default data templates for when API calls fail
DEFAULT_DATA = {
    'restaurants': [],
    'shops': [],
    'events': [],
    'parks_recreation': [],
    'cultural_landmarks': []
}

def fetch_data_from_api(source):
    """Fetch data from API"""
    try:
        if source == 'restaurants':
            response = requests.get(f'{API_BASE_URL}/restaurants', params={'term': '', 'limit': 20})
            response.raise_for_status()
            data = response.json()
            return [{'Name': r['name'],
                    'Description': f"{r.get('categories', [{'title': ''}])[0]['title']} restaurant. {r.get('rating', '')} stars. {r.get('price', '')}. {r.get('location', {}).get('address1', '')}"}
                    for r in data]
        
        elif source == 'shops':
            response = requests.get(f'{API_BASE_URL}/shops', params={'term': 'retail', 'limit': 20})
            response.raise_for_status()
            data = response.json()
            return [{'Name': s['name'],
                    'Description': f"{s.get('categories', [{'title': ''}])[0]['title']} shop. {s.get('rating', '')} stars. {s.get('price', '')}. {s.get('location', {}).get('address1', '')}"}
                    for s in data]
        
        elif source == 'events':
            response = requests.get(f'{API_BASE_URL}/events', params={'q': '', 'start_date': time.strftime("%Y-%m-%d")})
            response.raise_for_status()
            data = response.json()
            return [{'Name': e['name'],
                    'Description': e.get('description', '')}
                    for e in data]
        
        elif source in ['parks_recreation', 'cultural_landmarks']:
            response = requests.get(f'{API_BASE_URL}/parks', params={'limit': 10})
            response.raise_for_status()
            data = response.json()
            parks = data
            if source == 'cultural_landmarks':
                # Filter for historic sites
                parks = [p for p in parks if 'Historic' in p.get('designation', '')]
            return [{'Name': p['fullName'],
                    'Description': p.get('description', '')}
                    for p in parks]
        
        return []
    except Exception as e:
        print(f"Error fetching {source} data: {e}")
        return DEFAULT_DATA[source]

def fetch_data_from_web(source_url):
    def _fetch(url):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        entries = []
        
        # Look for Wix rich text elements that might contain event information
        rich_text_elements = soup.find_all(class_=['wixui-rich-text__text'])
        
        print(f"Found {len(rich_text_elements)} rich text elements")
        
        current_event = {}
        for elem in rich_text_elements:
            try:
                text = elem.text.strip()
                if not text:
                    continue
                    
                # If the text is short, it might be a title
                if len(text) < 100 and not current_event.get('Name'):
                    current_event['Name'] = text
                # If we have a name and this is longer text, it might be a description
                elif current_event.get('Name') and not current_event.get('Description'):
                    current_event['Description'] = text
                    # We have both name and description, add to entries
                    if current_event.get('Name') and current_event.get('Description'):
                        print(f"Found event: {current_event['Name']}")
                        entries.append(current_event.copy())
                        current_event = {}
                
            except Exception as e:
                print(f"Error parsing rich text element: {e}")
        
        # Also try to find events in sections
        sections = soup.find_all(class_='wixui-section')
        print(f"Found {len(sections)} sections")
        
        for section in sections:
            try:
                # Look for headings and paragraphs within sections
                heading = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                paragraphs = section.find_all('p')
                
                if heading and paragraphs:
                    name = heading.text.strip()
                    description = ' '.join(p.text.strip() for p in paragraphs)
                    
                    if name and description:
                        print(f"Found event from section: {name}")
                        entries.append({
                            'Name': name,
                            'Description': description
                        })
            except Exception as e:
                print(f"Error parsing section: {e}")
        
        if not entries:
            print("No events found in rich text elements or sections.")
            # Try to find any text content that might be useful for debugging
            all_text = soup.get_text()
            print(f"Total text content length: {len(all_text)} characters")
            print("First 200 characters of content:", all_text[:200])
        
        return entries
    
    return fetch_data_with_retry(source_url, _fetch)

def load_existing_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file) or {}
    return {}

def save_data(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        yaml.safe_dump(data, file, allow_unicode=True)

def update_data(source, data, source_type='json'):
    try:
        file_path = os.path.join(DATA_DIR, f'{source}.yml')
        existing_data = load_existing_data(file_path)
        
        # Initialize with default structure if empty
        if not existing_data:
            existing_data = {'Entries': [], 'last_updated': None}
        
        existing_entries = {entry.get('Name', ''): entry for entry in existing_data.get('Entries', [])}
        new_entries = {}

        # Use default data if no data is provided
        if not data:
            data = DEFAULT_DATA.get(source, [])

        if source_type == 'json':
            for entry in data:
                name = entry.get('Name', entry.get('name', ''))
                description = entry.get('Description', entry.get('description', ''))
                if name:  # Only add entries with a name
                    new_entries[name] = {
                        'Name': name,
                        'Description': description,
                        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
        elif source_type == 'geojson':
            for feature in data.get('features', []):
                properties = feature.get('properties', {})
                name = properties.get('NAME', properties.get('name', ''))
                description = properties.get('DESCRIPTION', properties.get('description', ''))
                if name:  # Only add entries with a name
                    new_entries[name] = {
                        'Name': name,
                        'Description': description or f"Location in {source}",
                        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
        elif source_type == 'html':
            for entry in data:
                name = entry.get('Name', '')
                description = entry.get('Description', '')
                if name:  # Only add entries with a name
                    new_entries[name] = {
                        'Name': name,
                        'Description': description,
                        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
                    }

        # Update existing entries and add new ones
        updated_entries = []
        for name, entry in {**existing_entries, **new_entries}.items():
            if name in new_entries:
                updated_entry = {**existing_entries.get(name, {}), **new_entries[name]}
            else:
                updated_entry = existing_entries[name]
            updated_entries.append(updated_entry)

        # Sort entries by name for consistency
        updated_entries.sort(key=lambda x: x.get('Name', ''))
        
        existing_data['Entries'] = updated_entries
        existing_data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')

        if _validate_data(file_path):  # Only save if validation passes
            save_data(file_path, existing_data)
            print(f"Successfully updated {source} data with {len(updated_entries)} entries")
            return True
        return False
    except Exception as e:
        print(f"Error updating {source} data: {e}")
        # Save current state to prevent data loss
        try:
            backup_path = os.path.join(DATA_DIR, f'{source}_backup_{int(time.time())}.yml')
            save_data(backup_path, existing_data)
            print(f"Backup saved to {backup_path}")
        except Exception as backup_error:
            print(f"Failed to create backup: {backup_error}")
        return False

def main():
    sources = [
        'restaurants',
        'shops',
        'events',
        'parks_recreation',
        'cultural_landmarks'
    ]

    success_count = 0
    total_sources = len(sources)

    for source in sources:
        try:
            data = fetch_data_from_api(source)
            if update_data(source, data, source_type='json'):
                success_count += 1
        except Exception as e:
            print(f"Failed to update {source}: {e}")

    print(f"\nUpdate complete: {success_count}/{total_sources} sources updated successfully")

if __name__ == '__main__':
    main()