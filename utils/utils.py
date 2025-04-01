from urllib.parse import urlparse, urlunparse
import re
from difflib import SequenceMatcher

def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison by:
    1. Removing protocol (http/https)
    2. Removing www.
    3. Removing trailing slashes
    4. Converting to lowercase
    5. Removing query parameters and fragments
    """
    try:
        # Parse the URL
        parsed = urlparse(url.lower())
        
        # Remove www. from netloc if present
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Reconstruct URL without protocol, query, and fragment
        normalized = urlunparse(('', netloc, parsed.path.rstrip('/'), '', '', ''))
        return normalized
    except:
        # If URL parsing fails, return the original URL in lowercase
        return url.lower()

def url_similarity(url1: str, url2: str) -> float:
    """
    Calculate similarity between two URLs.
    Returns a float between 0 and 1, where 1 means identical and 0 means completely different.
    
    The similarity score is calculated in tiers:
    1.0: Exact match after normalization
    0.9: Match at start or after URL word boundary (/, -, _)
    0.8: One URL is a substring of the other
    0.0-0.7: String similarity ratio
    """
    # Use normalized URLs for comparison
    norm1 = url1 if isinstance(url1, str) else url1.normalized_url
    norm2 = url2 if isinstance(url2, str) else url2.normalized_url
    
    # Tier 1: Exact match
    if norm1 == norm2:
        return 1.0
    
    # Tier 2: Word boundary match
    # Check both directions for word boundary matches
    for (test_str, target_str) in [(norm1, norm2), (norm2, norm1)]:
        if test_str in target_str:
            idx = target_str.find(test_str)
            # Check if it's at the start
            if idx == 0:
                return 0.9
            # Check if it's after a word boundary
            if idx > 0 and target_str[idx-1] in ['/', '-', '_']:
                return 0.9
    # Tier 3: General substring match
            else:
                return 0.8 # No need to check further
    
    # Tier 4: String similarity
    # Use SequenceMatcher for string distance
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    return 0.7 * ratio  # Cap at 0.7 to maintain tier separation

def are_urls_similar(url1: str, url2: str, threshold: float = 0.8) -> bool:
    """
    Determine if two URLs are similar enough to be considered the same resource.
    Args:
        url1: First URL to compare (str or Bookmark)
        url2: Second URL to compare (str or Bookmark)
        threshold: Similarity threshold (0.0 to 1.0) above which URLs are considered similar
    Returns:
        bool: True if URLs are similar enough, False otherwise
    """
    return url_similarity(url1, url2) >= threshold 