"""
Central configuration management for the Johnson City Guide update system.
"""
import os
from datetime import datetime
from typing import Dict, Any

class UpdaterConfig:
    """Manages configuration settings for the update system."""

    def __init__(self):
        """Initialize configuration with default values and environment variables."""
        # API Configuration
        self.api_config = {
            'base_url': 'http://localhost:3000/api',
            'timeout': 30,
            'max_retries': 3,
            'endpoints': {
                'restaurants': '/restaurants',
                'shops': '/shops',
                'events': '/events',
                'parks': '/parks',
                'weather': '/weather/forecast',
                'moon': '/astronomy/moon',
                'agriculture': '/agriculture'
            }
        }

        # Git Configuration
        self.git_config = {
            'commit_message_prefix': 'Daily Update:',
            'author_name': os.getenv('GIT_USERNAME', 'Cline'),
            'author_email': os.getenv('GIT_EMAIL', 'cline@example.com'),
            'branch': 'main'
        }

        # File Paths
        self.paths = {
            'readme': 'README.md',
            'changelog': 'CHANGELOG.md',
            'data_dir': 'data',
            'log_dir': 'logs',
            'metrics_dir': 'metrics',
            'schemas_dir': 'schemas'
        }

        # Update Settings
        self.update_settings = {
            'update_frequency': 'daily',
            'min_entries_per_category': 5,
            'max_entries_per_category': 50,
            'cache_duration': 3600,  # 1 hour in seconds
            'weather_update_interval': 3600,  # Update weather hourly
            'moon_update_interval': 86400  # Update moon phases daily
        }

        # Monitoring Configuration
        self.monitoring = {
            'log_file': os.path.join('logs', 'update.log'),
            'metrics_file': os.path.join('metrics', 'daily_stats.json'),
            'error_notification_email': os.getenv('NOTIFICATION_EMAIL')
        }

        # Required API Keys
        self.required_keys = [
            'YELP_API_KEY',
            'EVENTBRITE_API_KEY',
            'NPS_API_KEY',
            'OPENWEATHER_API_KEY',
            'ASTRONOMY_API_KEY'
        ]

    def validate_environment(self) -> tuple[bool, list[str]]:
        """
        Validate that all required environment variables are set.
        
        Returns:
            tuple: (is_valid, missing_keys)
        """
        missing_keys = [
            key for key in self.required_keys 
            if not os.getenv(key)
        ]
        return len(missing_keys) == 0, missing_keys

    def get_api_key(self, service: str) -> str:
        """
        Get API key for a specific service.
        
        Args:
            service: Service name (e.g., 'yelp', 'eventbrite', 'nps', 'weather', 'astronomy')
            
        Returns:
            str: API key for the service
        """
        key_map = {
            'yelp': 'YELP_API_KEY',
            'eventbrite': 'EVENTBRITE_API_KEY',
            'nps': 'NPS_API_KEY',
            'weather': 'OPENWEATHER_API_KEY',
            'astronomy': 'ASTRONOMY_API_KEY'
        }
        env_key = key_map.get(service.lower())
        if not env_key:
            raise ValueError(f"Unknown service: {service}")
        
        api_key = os.getenv(env_key)
        if not api_key:
            raise ValueError(f"API key not found for service: {service}")
        
        return api_key

    def get_data_file_path(self, category: str) -> str:
        """
        Get the full path for a data file.
        
        Args:
            category: Category name (e.g., 'restaurants', 'shops', 'agriculture')
            
        Returns:
            str: Full path to the data file
        """
        return os.path.join(self.paths['data_dir'], f"{category}.yml")

    def get_schema_file_path(self, category: str) -> str:
        """
        Get the full path for a schema file.
        
        Args:
            category: Category name (e.g., 'restaurants', 'shops', 'agriculture')
            
        Returns:
            str: Full path to the schema file
        """
        return os.path.join(self.paths['schemas_dir'], f"{category}.schema.json")

    def get_timestamp_format(self) -> str:
        """Get the standard timestamp format for the system."""
        return "%Y-%m-%d %H:%M:%S"

    def format_timestamp(self, dt: datetime = None) -> str:
        """
        Format a timestamp using the standard format.
        
        Args:
            dt: datetime object to format (defaults to current time)
            
        Returns:
            str: Formatted timestamp
        """
        if dt is None:
            dt = datetime.now()
        return dt.strftime(self.get_timestamp_format())

    def get_commit_message(self, changes: Dict[str, Any] = None) -> str:
        """
        Generate a commit message based on changes.
        
        Args:
            changes: Dictionary of changes made during update
            
        Returns:
            str: Formatted commit message
        """
        timestamp = self.format_timestamp()
        message = f"{self.git_config['commit_message_prefix']} {timestamp}"
        
        if changes:
            message += "\n\nChanges:"
            for category, count in changes.items():
                if count > 0:
                    message += f"\n- Updated {count} entries in {category}"
        
        return message