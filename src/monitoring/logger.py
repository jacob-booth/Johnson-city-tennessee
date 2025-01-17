"""
Logging configuration for the Johnson City Guide update system.
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict

class UpdateLogger:
    """Handles logging for the update system."""

    def __init__(self, config):
        """
        Initialize the logger with configuration.
        
        Args:
            config: UpdaterConfig instance
        """
        self.config = config
        self.logger = self._setup_logger()
        self.update_stats = {
            'start_time': None,
            'end_time': None,
            'changes': {
                'restaurants': 0,
                'shops': 0,
                'events': 0,
                'parks': 0
            },
            'errors': [],
            'warnings': []
        }

    def _setup_logger(self) -> logging.Logger:
        """
        Set up the logging configuration.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config.monitoring['log_file']), exist_ok=True)

        # Create logger
        logger = logging.getLogger('JohnsonCityGuide')
        logger.setLevel(logging.INFO)

        # Create handlers
        file_handler = logging.FileHandler(self.config.monitoring['log_file'])
        console_handler = logging.StreamHandler()

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Set formatter for handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def start_update(self):
        """Record the start of an update operation."""
        self.update_stats['start_time'] = datetime.now()
        self.logger.info("Starting guide update process")

    def end_update(self):
        """Record the end of an update operation."""
        self.update_stats['end_time'] = datetime.now()
        duration = self.update_stats['end_time'] - self.update_stats['start_time']
        self.logger.info(f"Update process completed in {duration}")

    def log_change(self, category: str, count: int):
        """
        Log changes for a specific category.
        
        Args:
            category: Category being updated
            count: Number of items updated
        """
        self.update_stats['changes'][category] = count
        self.logger.info(f"Updated {count} entries in {category}")

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """
        Log an error with context.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
        """
        error_info = {
            'error': str(error),
            'type': type(error).__name__,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        self.update_stats['errors'].append(error_info)
        self.logger.error(f"Error: {error}", exc_info=True, extra=context or {})

    def log_warning(self, message: str, context: Dict[str, Any] = None):
        """
        Log a warning with context.
        
        Args:
            message: Warning message
            context: Additional context about the warning
        """
        warning_info = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        self.update_stats['warnings'].append(warning_info)
        self.logger.warning(message, extra=context or {})

    def log_api_call(self, endpoint: str, success: bool, duration: float):
        """
        Log API call metrics.
        
        Args:
            endpoint: API endpoint called
            success: Whether the call was successful
            duration: Time taken for the call in seconds
        """
        self.logger.info(
            f"API Call to {endpoint}: {'Success' if success else 'Failed'} "
            f"(Duration: {duration:.2f}s)"
        )

    def get_update_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the update operation.
        
        Returns:
            Dict containing update statistics
        """
        return {
            'duration': str(self.update_stats['end_time'] - self.update_stats['start_time'])
            if self.update_stats['end_time'] else None,
            'changes': self.update_stats['changes'],
            'error_count': len(self.update_stats['errors']),
            'warning_count': len(self.update_stats['warnings'])
        }

    def save_metrics(self):
        """Save metrics to the metrics file."""
        metrics_file = self.config.monitoring['metrics_file']
        os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
        
        summary = self.get_update_summary()
        # Add timestamp to metrics
        summary['timestamp'] = datetime.now().isoformat()
        
        import json
        with open(metrics_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Metrics saved to {metrics_file}")