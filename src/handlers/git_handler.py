"""
Git operations handler for the Johnson City Guide update system.
"""
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import git
from git import Repo, GitCommandError

class GitHandler:
    """Manages Git operations for the update system."""

    def __init__(self, config, logger):
        """
        Initialize the Git handler.
        
        Args:
            config: UpdaterConfig instance
            logger: UpdateLogger instance
        """
        self.config = config
        self.logger = logger
        self.repo = self._get_repo()

    def _get_repo(self) -> Repo:
        """
        Get or initialize the Git repository.
        
        Returns:
            git.Repo: Repository instance
        """
        try:
            return Repo('.')
        except git.InvalidGitRepositoryError:
            self.logger.log_error("Not a valid Git repository")
            raise

    def check_status(self) -> Tuple[bool, List[str]]:
        """
        Check the status of the repository.
        
        Returns:
            Tuple[bool, List[str]]: (is_clean, modified_files)
        """
        modified_files = [item.a_path for item in self.repo.index.diff(None)]
        untracked_files = self.repo.untracked_files
        is_clean = len(modified_files) == 0 and len(untracked_files) == 0
        return is_clean, modified_files + untracked_files

    def stage_changes(self, paths: List[str] = None) -> bool:
        """
        Stage specified files or all changes if no paths provided.
        
        Args:
            paths: List of file paths to stage
            
        Returns:
            bool: True if staging was successful
        """
        try:
            if paths:
                self.repo.index.add(paths)
            else:
                self.repo.git.add(A=True)
            return True
        except GitCommandError as e:
            self.logger.log_error(e, {'action': 'stage_changes', 'paths': paths})
            return False

    def commit_changes(self, changes: Dict[str, int]) -> bool:
        """
        Commit staged changes with a formatted message.
        
        Args:
            changes: Dictionary of changes made during update
            
        Returns:
            bool: True if commit was successful
        """
        try:
            # Configure the commit author
            with self.repo.config_writer() as git_config:
                git_config.set_value('user', 'name', self.config.git_config['author_name'])
                git_config.set_value('user', 'email', self.config.git_config['author_email'])

            # Create commit message
            commit_message = self.config.get_commit_message(changes)

            # Commit changes
            self.repo.index.commit(commit_message)
            self.logger.logger.info(f"Changes committed: {commit_message}")
            return True
        except GitCommandError as e:
            self.logger.log_error(e, {'action': 'commit_changes'})
            return False

    def push_changes(self) -> bool:
        """
        Push committed changes to remote repository.
        
        Returns:
            bool: True if push was successful
        """
        try:
            origin = self.repo.remote('origin')
            origin.push()
            self.logger.logger.info("Changes pushed to remote repository")
            return True
        except GitCommandError as e:
            self.logger.log_error(e, {'action': 'push_changes'})
            return False

    def create_tag(self, version: str, message: Optional[str] = None) -> bool:
        """
        Create a new version tag.
        
        Args:
            version: Version string for the tag
            message: Optional tag message
            
        Returns:
            bool: True if tag was created successfully
        """
        try:
            tag_message = message or f"Version {version}"
            new_tag = self.repo.create_tag(
                version,
                message=tag_message,
                force=True
            )
            self.logger.logger.info(f"Created tag: {version}")
            return True
        except GitCommandError as e:
            self.logger.log_error(e, {'action': 'create_tag', 'version': version})
            return False

    def get_latest_tag(self) -> Optional[str]:
        """
        Get the latest version tag.
        
        Returns:
            str: Latest version tag or None if no tags exist
        """
        try:
            tags = sorted(self.repo.tags, key=lambda t: t.commit.committed_datetime)
            return str(tags[-1]) if tags else None
        except IndexError:
            return None

    def create_daily_tag(self) -> Optional[str]:
        """
        Create a tag for the daily update.
        
        Returns:
            str: Created tag name or None if failed
        """
        date_str = datetime.now().strftime('%Y%m%d')
        tag_name = f"update-{date_str}"
        
        if self.create_tag(tag_name):
            return tag_name
        return None

    def handle_update_cycle(self, changes: Dict[str, int]) -> bool:
        """
        Handle the complete update cycle: stage, commit, tag, and push.
        
        Args:
            changes: Dictionary of changes made during update
            
        Returns:
            bool: True if all operations were successful
        """
        try:
            # Stage all changes
            if not self.stage_changes():
                return False

            # Commit changes
            if not self.commit_changes(changes):
                return False

            # Create daily tag
            tag_name = self.create_daily_tag()
            if not tag_name:
                return False

            # Push changes and tags
            if not self.push_changes():
                return False

            self.logger.logger.info("Update cycle completed successfully")
            return True

        except Exception as e:
            self.logger.log_error(e, {'action': 'handle_update_cycle'})
            return False