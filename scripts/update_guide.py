#!/usr/bin/env python3
"""
Automated update system for the Johnson City Guide.
"""
import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.updater_config import UpdaterConfig
from handlers.git_handler import GitHandler
from handlers.content_handler import ContentHandler
from monitoring.logger import UpdateLogger

class GuideUpdater:
    """Main orchestrator for the update process."""

    def __init__(self):
        """Initialize the update system components."""
        self.config = UpdaterConfig()
        self.logger = UpdateLogger(self.config)
        self.git_handler = GitHandler(self.config, self.logger)
        self.content_handler = ContentHandler(self.config, self.logger)
        self.changes = {
            'restaurants': 0,
            'shops': 0,
            'events': 0,
            'parks': 0,
            'almanac': 0
        }
        self.weather_data = None
        self.moon_data = None

    async def validate_environment(self) -> bool:
        """
        Validate the environment setup.
        
        Returns:
            bool: True if environment is valid
        """
        # Check environment variables
        is_valid, missing_keys = self.config.validate_environment()
        if not missing_keys:
            self.logger.logger.info("Environment validation successful")
            return True
        
        for key in missing_keys:
            self.logger.log_error(ValueError(f"Missing environment variable: {key}"))
        return False

    async def fetch_data_from_api(self, endpoint: str, service: str = None, **params) -> Optional[dict]:
        """
        Fetch data from the API.
        
        Args:
            endpoint: API endpoint to call
            service: Optional service name for API key
            params: Additional parameters for the API call
            
        Returns:
            Optional[dict]: Fetched data or None on error
        """
        import aiohttp
        import time

        url = f"{self.config.api_config['base_url']}{endpoint}"
        start_time = time.time()
        success = False

        try:
            headers = {}
            if service:
                api_key = self.config.get_api_key(service)
                headers['Authorization'] = f'Bearer {api_key}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    success = True
                    return data
        except Exception as e:
            self.logger.log_error(e, {
                'action': 'fetch_data',
                'endpoint': endpoint,
                'params': params
            })
            return None
        finally:
            duration = time.time() - start_time
            self.logger.log_api_call(endpoint, success, duration)

    async def update_category(self, category: str) -> int:
        """
        Update a specific category of data.
        
        Args:
            category: Category to update
            
        Returns:
            int: Number of entries updated
        """
        try:
            # Fetch new data
            data = await self.fetch_data_from_api(
                self.config.api_config['endpoints'][category]
            )
            
            if not data:
                self.logger.log_warning(f"No data received for {category}")
                return 0

            # Update data file
            file_path = self.config.get_data_file_path(category)
            
            # Validate data before saving
            is_valid, errors = self.content_handler.validate_data_file(file_path)
            if not is_valid:
                self.logger.log_warning(
                    f"Validation failed for {category}",
                    {'errors': errors}
                )
                return 0

            # Count the number of entries
            entry_count = len(data)
            self.logger.log_change(category, entry_count)
            
            return entry_count

        except Exception as e:
            self.logger.log_error(e, {'action': 'update_category', 'category': category})
            return 0

    async def update_weather(self) -> bool:
        """
        Update weather data.
        
        Returns:
            bool: True if update was successful
        """
        try:
            self.weather_data = await self.fetch_data_from_api(
                self.config.api_config['endpoints']['weather'],
                service='weather',
                city='Johnson City,TN,US',
                units='imperial'
            )
            return bool(self.weather_data)
        except Exception as e:
            self.logger.log_error(e, {'action': 'update_weather'})
            return False

    async def update_moon_phase(self) -> bool:
        """
        Update moon phase data.
        
        Returns:
            bool: True if update was successful
        """
        try:
            self.moon_data = await self.fetch_data_from_api(
                self.config.api_config['endpoints']['moon'],
                service='astronomy'
            )
            return bool(self.moon_data)
        except Exception as e:
            self.logger.log_error(e, {'action': 'update_moon_phase'})
            return False

    async def update_almanac(self) -> bool:
        """
        Update almanac data including weather and moon phases.
        
        Returns:
            bool: True if update was successful
        """
        try:
            weather_success = await self.update_weather()
            moon_success = await self.update_moon_phase()

            if weather_success and moon_success:
                self.changes['almanac'] = 1
                return True
            return False

        except Exception as e:
            self.logger.log_error(e, {'action': 'update_almanac'})
            return False

    async def update_all_categories(self):
        """Update all data categories."""
        # Update standard categories
        for category in ['restaurants', 'shops', 'events', 'parks']:
            self.changes[category] = await self.update_category(category)

        # Update almanac data
        await self.update_almanac()

    async def run(self):
        """Run the complete update process."""
        self.logger.start_update()

        try:
            # Validate environment
            if not await self.validate_environment():
                return False

            # Create backup before updates
            if not self.content_handler.backup_data_files():
                return False

            # Update all categories
            await self.update_all_categories()

            # Update documentation with weather and moon data
            self.content_handler.update_readme_timestamp(
                weather_data=self.weather_data,
                moon_data=self.moon_data
            )
            self.content_handler.update_changelog(self.changes)

            # Validate all data files
            validation_results = self.content_handler.validate_all_data_files()
            if validation_results:
                self.logger.log_warning(
                    "Validation issues found",
                    {'validation_results': validation_results}
                )

            # Handle Git operations
            if any(count > 0 for count in self.changes.values()):
                if not self.git_handler.handle_update_cycle(self.changes):
                    self.logger.log_warning("Git operations failed")
                    return False

            return True

        except Exception as e:
            self.logger.log_error(e, {'action': 'run'})
            return False

        finally:
            self.logger.end_update()
            self.logger.save_metrics()

def main():
    """Main entry point for the update script."""
    # Ensure we're in the correct directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    updater = GuideUpdater()
    success = asyncio.run(updater.run())
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()