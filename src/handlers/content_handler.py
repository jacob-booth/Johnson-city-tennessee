"""
Content management handler for the Johnson City Guide update system.
"""
import os
import re
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

    def update_weather_section(self, content: str) -> str:
        """
        Update the weather section in README.md.
        
        Args:
            content: Current README content
            
        Returns:
            str: Updated README content
        """
        # Example weather data (in production this would come from an API)
        weather_data = {
            'temp': 45,
            'high': 52,
            'low': 38,
            'condition': 'Partly Cloudy',
            'humidity': 65
        }

        # Format weather section
        weather_section = f"""## 🌤️ Today's Weather in Johnson City

**Current Weather:** 🌦️ {weather_data['temp']}°F, {weather_data['condition']}
**Forecast:** 🌞 High: {weather_data['high']}°F | 🌙 Low: {weather_data['low']}°F
**Humidity:** {weather_data['humidity']}%
**Source:** [WJHL Weather Center](https://www.wjhl.com/weather/)

_"A crisp winter day perfect for exploring Johnson City's cozy cafes and indoor attractions!"_
"""

        # Check if weather section exists
        weather_pattern = r'## 🌤️ Today\'s Weather in Johnson City.*?(?=\n\n|$)'
        if re.search(weather_pattern, content, re.DOTALL):
            # Update existing weather section
            return re.sub(weather_pattern, weather_section.strip(), content, flags=re.DOTALL)
        else:
            # Add weather section after title
            title_pattern = r'(# .+?\n)'
            return re.sub(title_pattern, f"\\1\n{weather_section}", content, count=1)

    def update_readme_timestamp(self) -> bool:
        """
        Update the timestamp and weather in README.md.
        
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

            # Update weather section
            content = self.update_weather_section(content)

            # Look for existing timestamp section
            timestamp_pattern = r'(Last Updated: ).*'
            new_timestamp = f"Last Updated: {self.config.format_timestamp()}"

            if re.search(timestamp_pattern, content):
                # Update existing timestamp
                updated_content = re.sub(timestamp_pattern, new_timestamp, content)
            else:
                # Add timestamp after the title
                title_pattern = r'(# .+?\n)'
                updated_content = re.sub(
                    title_pattern,
                    f"\\1\n{new_timestamp}\n",
                    content,
                    count=1
                )

            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            self.logger.logger.info("Updated README.md timestamp and weather")
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

            # Basic structure validation
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