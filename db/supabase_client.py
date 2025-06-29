"""
Supabase client for movie data storage and retrieval.
"""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for interacting with Supabase database."""
    
    def __init__(self):
        """Initialize Supabase client with environment variables."""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.schema = os.getenv('SUPABASE_SCHEMA', 'public')  # Default to public
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(self.url, self.key)
    
    def _get_table(self, table_name: str):
        """Get table reference with schema."""
        return self.client.schema(self.schema).table(table_name)
    
    def movie_exists(self, name: str) -> bool:
        """
        Check if a movie exists in the database using exact name match.
        
        Args:
            name: Movie name to check
            
        Returns:
            True if movie exists, False otherwise
        """
        try:
            response = self._get_table('movies').select('id').eq('name', name).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking if movie exists {name}: {e}")
            return False
    
    def cinema_exists(self, name: str) -> bool:
        """
        Check if a cinema exists in the database using exact name match.
        
        Args:
            name: Cinema name to check
            
        Returns:
            True if cinema exists, False otherwise
        """
        try:
            response = self._get_table('cinemas').select('id').eq('name', name).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking if cinema exists {name}: {e}")
            return False
    
    def showtime_exists(self, movie_id: str, cinema_id: str, showtime: str, language: str) -> bool:
        """
        Check if a showtime exists in the database using exact match on all criteria.
        
        Args:
            movie_id: Movie ID to check
            cinema_id: Cinema ID to check
            showtime: Showtime timestamp to check
            language: Language to check
            
        Returns:
            True if showtime exists with exact match, False otherwise
        """
        try:
            response = (self._get_table('showtimes')
                       .select('id')
                       .eq('movie_id', movie_id)
                       .eq('cinema_id', cinema_id)
                       .eq('showtime', showtime)
                       .eq('language', language)
                       .execute())
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking if showtime exists (movie: {movie_id}, cinema: {cinema_id}, time: {showtime}, lang: {language}): {e}")
            return False
    
    def get_movie_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get movie by name from database.
        
        Args:
            name: Movie name
            
        Returns:
            Movie data dictionary or None if not found
        """
        try:
            response = self._get_table('movies').select('*').eq('name', name).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching movie {name}: {e}")
            return None
    
    def get_cinema_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get cinema by name from database.
        
        Args:
            name: Cinema name
            
        Returns:
            Cinema data dictionary or None if not found
        """
        try:
            response = self._get_table('cinemas').select('*').eq('name', name).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching cinema {name}: {e}")
            return None
    
    def add_movie(self, movie_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new movie to the database.
        
        Args:
            movie_data: Dictionary containing movie information
            
        Returns:
            Movie ID if successful, None otherwise
        """
        try:
            # Add timestamp
            movie_data['created_at'] = datetime.now().isoformat()
            
            response = self._get_table('movies').insert(movie_data).execute()
            
            if response.data:
                movie_id = response.data[0]['id']
                logger.info(f"Successfully added movie: {movie_data.get('name')} (ID: {movie_id})")
                return movie_id
            return None
            
        except Exception as e:
            logger.error(f"Error adding movie {movie_data.get('name')}: {e}")
            return None
    
    def add_cinema(self, cinema_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new cinema to the database.
        
        Args:
            cinema_data: Dictionary containing cinema information
            
        Returns:
            Cinema ID if successful, None otherwise
        """
        try:
            # Add timestamp
            cinema_data['created_at'] = datetime.now().isoformat()
            
            response = self._get_table('cinemas').insert(cinema_data).execute()
            
            if response.data:
                cinema_id = response.data[0]['id']
                logger.info(f"Successfully added cinema: {cinema_data.get('name')} (ID: {cinema_id})")
                return cinema_id
            return None
            
        except Exception as e:
            logger.error(f"Error adding cinema {cinema_data.get('name')}: {e}")
            return None
    
    def add_showtime(self, showtime_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new showtime to the database.
        
        Args:
            showtime_data: Dictionary containing showtime information
            
        Returns:
            Showtime ID if successful, None otherwise
        """
        try:
            # Add timestamp
            showtime_data['created_at'] = datetime.now().isoformat()
            
            response = self._get_table('showtimes').insert(showtime_data).execute()
            
            if response.data:
                showtime_id = response.data[0]['id']
                logger.info(f"Successfully added showtime (ID: {showtime_id})")
                return showtime_id
            return None
            
        except Exception as e:
            logger.error(f"Error adding showtime: {e}")
            return None