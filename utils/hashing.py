"""
Utility functions for hashing movie data to detect changes.
"""
import hashlib
import json
from typing import Dict, Any


def generate_content_hash(data: Dict[str, Any]) -> str:
    """
    Generate a hash for movie content to detect changes.
    
    Args:
        data: Dictionary containing movie data
        
    Returns:
        MD5 hash string of the normalized data
    """
    # Create a normalized version of the data for consistent hashing
    normalized_data = {
        'name': data.get('name', '').strip(),
        'category': data.get('category', '').strip(),
        'description': data.get('description', '').strip(),
    }
    
    # Convert to JSON string with sorted keys for consistent hashing
    json_string = json.dumps(normalized_data, sort_keys=True, ensure_ascii=False)
    
    # Generate MD5 hash
    return hashlib.md5(json_string.encode('utf-8')).hexdigest()


def generate_showtime_hash(showtimes_data: list) -> str:
    """
    Generate a hash for showtime data to detect changes.
    
    Args:
        showtimes_data: List of showtime dictionaries
        
    Returns:
        MD5 hash string of the normalized showtime data
    """
    # Normalize and sort showtime data
    normalized_showtimes = []
    for showtime in showtimes_data:
        normalized = {
            'cinema_name': showtime.get('cinema_name', '').strip(),
            'showtime': showtime.get('showtime', '').strip(),
    
            'language': showtime.get('language', '').strip()
        }
        normalized_showtimes.append(normalized)
    
    # Sort by cinema name and showtime for consistent ordering
    normalized_showtimes.sort(key=lambda x: (x['cinema_name'], x['showtime']))
    
    # Convert to JSON string
    json_string = json.dumps(normalized_showtimes, sort_keys=True, ensure_ascii=False)
    
    # Generate MD5 hash
    return hashlib.md5(json_string.encode('utf-8')).hexdigest()


def should_update_movie(current_hash: str, stored_hash: str = None) -> bool:
    """
    Determine if a movie should be updated based on hash comparison.
    
    Args:
        current_hash: Hash of current scraped data
        stored_hash: Hash stored in database (None if movie doesn't exist)
        
    Returns:
        True if movie should be updated, False otherwise
    """
    return stored_hash is None or current_hash != stored_hash 