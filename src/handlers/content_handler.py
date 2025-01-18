"""
Content management handler for the Johnson City Guide update system.
"""
import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import yaml

class ContentHandler:
    """Manages content updates for documentation files."""

    def __init__(self, config, logger):
        """
        Initialize the content handler.
        
        Args:
            config: UpdaterConfig instance
            logger: UpdateLogger instance
        """
        self.config = config
        self.logger = logger

    def update_almanac_section(self, content: str, weather_data: dict, moon_data: dict) -> str:
        """
        Update the almanac section in README.md.
        
        Args:
            content: Current README content
            weather_data: Current weather data
            moon_data: Current moon phase data
            
        Returns:
            str: Updated README content
        """
        # Load agricultural data
        try:
            with open(self.config.get_data_file_path('agriculture'), 'r', encoding='utf-8') as f:
                ag_data = yaml.safe_load(f)
        except Exception as e:
            self.logger.log_error(e, {'action': 'load_agriculture_data'})
            ag_data = {}

        # Format current conditions
        current_temp = weather_data.get('main', {}).get('temp', 'N/A')
        current_condition = weather_data.get('weather', [{}])[0].get('description', 'N/A')
        
        # Get current moon phase
        moon_phase = moon_data.get('phase', 'N/A')
        planting_guide = ag_data.get('moon_planting_guide', {}).get(moon_phase.lower().replace(' ', '_'), [])

        # Get current season's planting info
        current_month = datetime.now().strftime('%B').lower()
        season = 'spring' if datetime.now().month < 7 else 'fall'
        current_plantings = ag_data.get('planting_calendar', {}).get(season, {}).get(current_month, [])

        # Format farmers market info
        markets_today = [
            market for market in ag_data.get('farmers_markets', [])
            if datetime.now().strftime('%A') in market.get('schedule', '')
        ]

        almanac_section = f"""## 🌱 Johnson City Almanac

### 🌤️ Current Weather
**Temperature:** {current_temp}°F
**Conditions:** {current_condition}
**Growing Zone:** {ag_data.get('growing_zone', {}).get('zone', '6b/7a')}

### 🌿 Today's Planting Guide
**Season:** {season.capitalize()}
**Current Plantings:**
{chr(10).join(f"- {plant['crop']}: {plant['plant_date']}" for plant in current_plantings) if current_plantings else "No plantings scheduled for today"}

### 🌙 Moon Phase Guide
**Current Phase:** {moon_phase}
**Planting Recommendations:**
{chr(10).join(f"- {guide}" for guide in planting_guide) if planting_guide else "No specific planting recommendations for current phase"}

### 👨‍🌾 Today's Farmers Markets
{chr(10).join(f"- {market['name']} at {market['location']}: {market['schedule']}" for market in markets_today) if markets_today else "No markets scheduled for today"}

### 🌾 Local Wisdom
{chr(10).join(f"- {wisdom}" for wisdom in ag_data.get('local_wisdom', [])[:3])}

_Last Updated: {self.config.format_timestamp()}_
"""

        # Check if almanac section exists
        almanac_pattern = r'## 🌱 Johnson City Almanac.*?(?=\n\n## |$)'
        if re.search(almanac_pattern, content, re.DOTALL):
            # Update existing almanac section
            return re.sub(almanac_pattern, almanac_section.strip(), content, flags=re.DOTALL)
        else:
            # Add almanac section after weather section or title
            weather_pattern = r'## 🌤️ Today\'s Weather.*?(?=\n\n## |$)'
            if re.search(weather_pattern, content, re.DOTALL):
                return re.sub(weather_pattern, lambda m: f"{m.group(0)}\n\n{almanac_section}", content, flags=re.DOTALL)
            else:
                title_pattern = r'(# .+?\n)'
                return re.sub(title_pattern, f"\\1\n{almanac_section}", content, count=1)

    def validate_agriculture_data(self, data: dict) -> Tuple[bool, List[str]]:
        """
        Validate agriculture data against its schema.
        
        Args:
            data: Agriculture data to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        try:
            schema_path = self.config.get_schema_file_path('agriculture')
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            errors = []
            
            # Check required sections
            for section in schema['required']:
                if section not in data:
                    errors.append(f"Missing required section: {section}")

            # Validate growing zone
            if 'growing_zone' in data:
                for field in ['zone', 'first_frost', 'last_frost', 'growing_season_days']:
                    if field not in data['growing_zone']:
                        errors.append(f"Missing field in growing_zone: {field}")

            # Validate farmers markets
            if 'farmers_markets' in data:
                for i, market in enumerate(data['farmers_markets']):
                    for field in ['name', 'location', 'schedule']:
                        if field not in market:
                            errors.append(f"Missing field in farmers_market {i}: {field}")

            return len(errors) == 0, errors

        except Exception as e:
            self.logger.log_error(e, {'action': 'validate_agriculture_data'})
            return False, [str(e)]

    def update_readme_timestamp(self, weather_data: dict = None, moon_data: dict = None) -> bool:
        """
        Update the timestamp and almanac section in README.md.
        
        Args:
            weather_data: Optional current weather data
            moon_data: Optional current moon phase data
            
        Returns:
            bool: True if update was successful
        """
        try:
            readme_path = self.config.paths['readme']
            if not os.path.exists(readme_path):
                self.logger.log_error(FileNotFoundError(f"README.md not found at {readme_path}"))
                return False

            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update almanac section if weather and moon data are provided
            if weather_data and moon_data:
                content = self.update_almanac_section(content, weather_data, moon_data)

            # Update timestamp
            timestamp_pattern = r'(Last Updated: ).*'
            new_timestamp = f"Last Updated: {self.config.format_timestamp()}"

            if re.search(timestamp_pattern, content):
                updated_content = re.sub(timestamp_pattern, new_timestamp, content)
            else:
                title_pattern = r'(# .+?\n)'
                updated_content = re.sub(
                    title_pattern,
                    f"\\1\n{new_timestamp}\n",
                    content,
                    count=1
                )

            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            self.logger.logger.info("Updated README.md timestamp and almanac section")
            return True

        except Exception as e:
            self.logger.log_error(e, {'action': 'update_readme_timestamp'})
            return False

    def update_changelog(self, changes: Dict[str, int]) -> bool:
        """
        Update CHANGELOG.md with new entries.
        
        Args:
            changes: Dictionary of changes made during update
            
        Returns:
            bool: True if update was successful
        """
        try:
            changelog_path = self.config.paths['changelog']
            if not os.path.exists(changelog_path):
                self.logger.log_error(FileNotFoundError(f"CHANGELOG.md not found at {changelog_path}"))
                return False

            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.readlines()

            # Find the [Unreleased] section
            unreleased_index = -1
            for i, line in enumerate(content):
                if line.strip() == '## [Unreleased]':
                    unreleased_index = i
                    break

            if unreleased_index == -1:
                self.logger.log_warning("No [Unreleased] section found in CHANGELOG.md")
                return False

            # Format the new entry
            date_str = datetime.now().strftime('%Y-%m-%d')
            new_entry = [
                f"\n## [{date_str}]\n\n",
                "### Changed\n"
            ]

            # Add change details
            for category, count in changes.items():
                if count > 0:
                    new_entry.append(f"- Updated {count} entries in {category}\n")

            # Insert the new entry after the [Unreleased] section
            content.insert(unreleased_index + 1, "".join(new_entry))

            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.writelines(content)

            self.logger.logger.info("Updated CHANGELOG.md")
            return True

        except Exception as e:
            self.logger.log_error(e, {'action': 'update_changelog'})
            return False

    def validate_data_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a data file against its schema.
        
        Args:
            file_path: Path to the data file
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return False, ["Empty data file"]

            # Special handling for agriculture.yml
            if file_path.endswith('agriculture.yml'):
                return self.validate_agriculture_data(data)

            # Basic structure validation for other files
            if 'Entries' not in data:
                return False, ["Missing 'Entries' section"]

            if not isinstance(data['Entries'], list):
                return False, ["'Entries' must be a list"]

            # Validate each entry
            errors = []
            for i, entry in enumerate(data['Entries']):
                if not isinstance(entry, dict):
                    errors.append(f"Entry {i} must be a dictionary")
                    continue

                if 'Name' not in entry:
                    errors.append(f"Entry {i} missing required field 'Name'")
                if 'Description' not in entry:
                    errors.append(f"Entry {i} missing required field 'Description'")

            return len(errors) == 0, errors

        except Exception as e:
            self.logger.log_error(e, {'action': 'validate_data_file', 'file': file_path})
            return False, [str(e)]

    def validate_all_data_files(self) -> Dict[str, List[str]]:
        """
        Validate all data files in the data directory.
        
        Returns:
            Dict[str, List[str]]: Dictionary of validation errors by file
        """
        validation_results = {}
        data_dir = self.config.paths['data_dir']

        for filename in os.listdir(data_dir):
            if filename.endswith('.yml'):
                file_path = os.path.join(data_dir, filename)
                is_valid, errors = self.validate_data_file(file_path)
                
                if not is_valid:
                    validation_results[filename] = errors
                    self.logger.log_warning(
                        f"Validation errors in {filename}",
                        {'errors': errors}
                    )

        return validation_results

    def backup_data_files(self) -> bool:
        """
        Create backups of all data files.
        
        Returns:
            bool: True if backup was successful
        """
        try:
            import shutil
            from datetime import datetime

            data_dir = self.config.paths['data_dir']
            backup_dir = os.path.join(
                data_dir,
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            os.makedirs(backup_dir, exist_ok=True)

            for filename in os.listdir(data_dir):
                if filename.endswith('.yml'):
                    src = os.path.join(data_dir, filename)
                    dst = os.path.join(backup_dir, filename)
                    shutil.copy2(src, dst)

            self.logger.logger.info(f"Created backup in {backup_dir}")
            return True

        except Exception as e:
            self.logger.log_error(e, {'action': 'backup_data_files'})
            return False