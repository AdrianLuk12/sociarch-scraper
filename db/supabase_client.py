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
    
    def upsert_movie(self, movie_data: Dict[str, Any]) -> Optional[str]:
        """
        Insert or update movie data.
        
        Args:
            movie_data: Dictionary containing movie information
            
        Returns:
            Movie ID if successful, None otherwise
        """
        try:
            # Check if movie exists
            existing_movie = self.get_movie_by_name(movie_data['name'])
            
            if existing_movie:
                # Update existing movie
                movie_data['id'] = existing_movie['id']
                movie_data['last_updated'] = datetime.now().isoformat()
                response = self._get_table('movies').update(movie_data).eq('id', existing_movie['id']).execute()
            else:
                # Insert new movie
                movie_data['created_at'] = datetime.now().isoformat()
                response = self._get_table('movies').insert(movie_data).execute()
            
            if response.data:
                return response.data[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error upserting movie {movie_data.get('name')}: {e}")
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
    
    def upsert_cinema(self, cinema_data: Dict[str, Any]) -> Optional[str]:
        """
        Insert or update cinema data.
        
        Args:
            cinema_data: Dictionary containing cinema information
            
        Returns:
            Cinema ID if successful, None otherwise
        """
        try:
            # Check if cinema exists
            existing_cinema = self.get_cinema_by_name(cinema_data['name'])
            
            if existing_cinema:
                # Update existing cinema
                cinema_data['id'] = existing_cinema['id']
                response = self._get_table('cinemas').update(cinema_data).eq('id', existing_cinema['id']).execute()
            else:
                # Insert new cinema
                cinema_data['created_at'] = datetime.now().isoformat()
                response = self._get_table('cinemas').insert(cinema_data).execute()
            
            if response.data:
                return response.data[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error upserting cinema {cinema_data.get('name')}: {e}")
            return None
    
    def clear_movie_showtimes(self, movie_id: str) -> bool:
        """
        Clear all showtimes for a specific movie.
        
        Args:
            movie_id: Movie ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._get_table('showtimes').delete().eq('movie_id', movie_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error clearing showtimes for movie {movie_id}: {e}")
            return False
    
    def insert_showtimes(self, showtimes: List[Dict[str, Any]]) -> bool:
        """
        Insert multiple showtimes.
        
        Args:
            showtimes: List of showtime dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not showtimes:
                return True
                
            # Add created_at timestamp
            for showtime in showtimes:
                showtime['created_at'] = datetime.now().isoformat()
            
            response = self._get_table('showtimes').insert(showtimes).execute()
            return len(response.data) == len(showtimes)
            
        except Exception as e:
            logger.error(f"Error inserting showtimes: {e}")
            return False
    
    def mark_inactive_movies(self, active_movie_names: List[str]) -> bool:
        """
        Mark movies as inactive if they're not in the active list.
        
        Args:
            active_movie_names: List of currently active movie names
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Mark all movies as inactive first
            self._get_table('movies').update({'is_active': False}).neq('name', 'dummy').execute()
            
            # Then mark the active ones as active
            if active_movie_names:
                self._get_table('movies').update({'is_active': True}).in_('name', active_movie_names).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error updating movie active status: {e}")
            return False
    
    def get_all_active_movies(self) -> List[Dict[str, Any]]:
        """
        Get all active movies from database.
        
        Returns:
            List of active movie dictionaries
        """
        try:
            response = self._get_table('movies').select('*').eq('is_active', True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching active movies: {e}")
            return [] 