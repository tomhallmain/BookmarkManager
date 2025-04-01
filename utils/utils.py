from urllib.parse import urlparse, urlunparse
import re

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
    """
    # Normalize both URLs
    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)
    
    # If normalized URLs are identical, return 1.0
    if norm1 == norm2:
        return 1.0
    
    # Split URLs into parts for comparison
    parts1 = norm1.split('/')
    parts2 = norm2.split('/')
    
    # Compare domain parts
    if parts1[0] != parts2[0]:
        return 0.0
    
    # Compare path parts
    min_len = min(len(parts1), len(parts2))
    if min_len < 2:  # Only domain matches
        return 0.5
    
    # Count matching path segments
    matches = 0
    for i in range(1, min_len):
        if parts1[i] == parts2[i]:
            matches += 1
    
    # Calculate similarity based on matching path segments
    return 0.5 + (0.5 * (matches / (max(len(parts1), len(parts2)) - 1)))

def are_urls_similar(url1: str, url2: str, threshold: float = 0.8) -> bool:
    """
    Determine if two URLs are similar enough to be considered the same resource.
    Args:
        url1: First URL to compare
        url2: Second URL to compare
        threshold: Similarity threshold (0.0 to 1.0) above which URLs are considered similar
    Returns:
        bool: True if URLs are similar enough, False otherwise
    """
    return url_similarity(url1, url2) >= threshold 