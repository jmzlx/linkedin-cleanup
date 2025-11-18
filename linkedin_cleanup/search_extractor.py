"""
Search Extractor - Utilities for extracting profiles from LinkedIn search results.
"""
from typing import List, Optional, Tuple

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient


def normalize_linkedin_url(href: str) -> Optional[str]:
    """
    Normalize a LinkedIn profile URL.
    Returns the normalized URL or None if invalid.
    """
    if not href or "/in/" not in href:
        return None
    
    # Clean up URL (remove query parameters, ensure full URL)
    if href.startswith("/"):
        return f"https://www.linkedin.com{href.split('?')[0]}"
    elif href.startswith("http"):
        return href.split("?")[0]
    else:
        return None


def clean_profile_name(text: str) -> str:
    """
    Clean and extract profile name from text.
    Removes common suffixes like "• 1st" or job titles.
    """
    if not text:
        return ""
    
    # Take first line, remove extra whitespace
    name = text.split('\n')[0].strip()
    # Remove common suffixes like "• 1st" or job titles
    if '•' in name:
        name = name.split('•')[0].strip()
    return name


async def extract_location_from_card(container_element) -> Optional[str]:
    """
    Extract location information from a search result card container.
    Location appears in the card text, typically after the job title.
    """
    try:
        location_text = await container_element.evaluate("""
            (container) => {
                if (!container) return null;
                
                // Get all text from the container
                let fullText = container.innerText || '';
                
                // Location typically appears after job title, before "Message" button
                // Pattern: "Name\nJob Title\nLocation\nMessage"
                let lines = fullText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                // Look for location pattern: typically a line with city, state/country format
                // or just country name
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    // Skip if it's the name, connection indicator, or action buttons
                    if (line.includes('•') || 
                        line.toLowerCase().includes('message') ||
                        line.toLowerCase().includes('mutual connection') ||
                        line.length < 3) {
                        continue;
                    }
                    
                    // Check if this looks like a location (contains comma or common location words)
                    if (line.includes(',') || 
                        /^[A-Z][a-z]+,\s*[A-Z]/.test(line) ||  // "City, State" or "City, Country"
                        line.toLowerCase().includes('india') ||
                        line.toLowerCase().includes('usa') ||
                        line.toLowerCase().includes('uk') ||
                        /^[A-Z][a-z]+\s+[A-Z][a-z]+$/.test(line)) {  // "City Country"
                        return line;
                    }
                }
                
                return null;
            }
        """)
        if location_text and location_text.strip():
            return location_text.strip()
    except Exception:
        pass
    
    return None


async def extract_profiles_from_page(client: LinkedInClient) -> List[Tuple[str, str, str]]:
    """
    Extract profile names, URLs, and locations from the current search results page.
    Returns list of (name, url, location) tuples.
    Only extracts the main profile from each search result card, skipping mutual connections.
    """
    page = client.page
    profiles = []
    seen_urls = set()
    
    # Verify we're on a people search results page, not jobs
    try:
        current_url = page.url
        if '/search/results/people/' not in current_url:
            print(f"Warning: URL doesn't appear to be a people search page: {current_url}")
    except Exception:
        pass
    
    try:
        # Wait for people search results to load (not job results)
        # Look for the specific container that indicates people search results
        await page.wait_for_selector(
            'div[data-view-name="people-search-result"]',
            timeout=config.SELECTOR_TIMEOUT
        )
    except Exception:
        print("Warning: Could not find people search result containers. Page might not have loaded or might be showing job results.")
        pass
    
    # Scroll down to load all content (LinkedIn may use lazy loading)
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await client.random_delay(2, 3)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.8)")
        await client.random_delay(1, 2)
    except Exception:
        pass
    
    # Extract profiles using the new LinkedIn structure
    # LinkedIn search results are in: main > div[data-view-name="people-search-result"]
    # Each container has one main profile link (plus potentially mutual connection links)
    try:
        # Extract all profile data in one pass - more efficient and reliable
        profile_data = await page.evaluate("""
            () => {
                let main = document.querySelector('main');
                if (!main) return {error: 'No main element', stats: {}};
                
                // Find all search result containers
                let resultContainers = Array.from(main.querySelectorAll('div[data-view-name="people-search-result"]'));
                
                let stats = {
                    totalContainers: resultContainers.length,
                    finalCount: 0
                };
                
                let profiles = [];
                
                // For each search result container, extract the main profile
                for (let container of resultContainers) {
                    // Get all profile links in this container
                    let allLinks = Array.from(container.querySelectorAll('a[href*="/in/"]'));
                    if (allLinks.length === 0) continue;
                    
                    // Find the main profile link
                    // The main link is usually:
                    // 1. The first link in the container (by DOM order)
                    // 2. Has more text content (name + title)
                    // 3. Is not in a mutual connections list
                    let mainLink = null;
                    
                    for (let link of allLinks) {
                        let href = link.getAttribute('href');
                        if (!href) continue;
                        
                        // Check if this link is in a mutual connections section
                        let parent = link.parentElement;
                        let isMutualConnection = false;
                        let depth = 0;
                        
                        while (parent && parent !== container && depth < 8) {
                            let parentText = (parent.innerText || '').toLowerCase();
                            if (parentText.includes('mutual connection') || 
                                parentText.includes('mutual connections')) {
                                isMutualConnection = true;
                                break;
                            }
                            parent = parent.parentElement;
                            depth++;
                        }
                        
                        // Skip mutual connection links
                        if (isMutualConnection) continue;
                        
                        // This is likely the main profile link
                        // Prefer the first one, or one with more text
                        if (!mainLink || (link.innerText || '').length > (mainLink.innerText || '').length) {
                            mainLink = link;
                        }
                    }
                    
                    if (!mainLink) continue;
                    
                    let href = mainLink.getAttribute('href');
                    if (!href) continue;
                    
                    // Normalize URL
                    let url = href.split('?')[0];
                    if (url.startsWith('/')) {
                        url = 'https://www.linkedin.com' + url;
                    }
                    
                    // Extract name from link text
                    let name = mainLink.innerText || '';
                    if (name.includes('•')) {
                        name = name.split('•')[0].trim();
                    }
                    name = name.trim();
                    
                    // Extract location from container text
                    // Location appears after job title, before "Message" button
                    let location = null;
                    let containerText = container.innerText || '';
                    let lines = containerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                    
                    for (let i = 0; i < lines.length; i++) {
                        let line = lines[i];
                        // Skip if it's the name, connection indicator, or action buttons
                        if (line.includes('•') || 
                            line.toLowerCase().includes('message') ||
                            line.toLowerCase().includes('mutual connection') ||
                            line.length < 3) {
                            continue;
                        }
                        
                        // Check if this looks like a location
                        if (line.includes(',') || 
                            /^[A-Z][a-z]+,\s*[A-Z]/.test(line) ||
                            /^[A-Z][a-z]+\s+[A-Z][a-z]+$/.test(line)) {
                            location = line;
                            break;
                        }
                    }
                    
                    profiles.push({
                        url: url,
                        name: name,
                        location: location || 'Unknown'
                    });
                    stats.finalCount++;
                }
                
                return {profiles: profiles, stats: stats};
            }
        """)
        
        # Handle result structure
        if isinstance(profile_data, dict) and 'error' in profile_data:
            print(f"Error: {profile_data['error']}")
            if 'stats' in profile_data:
                print(f"Stats: {profile_data['stats']}")
            return profiles
        
        if isinstance(profile_data, dict) and 'profiles' in profile_data:
            stats = profile_data.get('stats', {})
            print(f"Stats: {stats.get('totalContainers', 0)} search result containers found, "
                  f"{stats.get('finalCount', 0)} profiles extracted")
            profile_data = profile_data['profiles']
        
        print(f"Found {len(profile_data)} search result cards on page")
        
        if len(profile_data) == 0:
            print("Warning: No search result cards found")
            return profiles
        
        # Process the extracted data
        for profile in profile_data:
            try:
                url = normalize_linkedin_url(profile['url'])
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                
                name = clean_profile_name(profile['name'])
                location = profile['location'] or "Unknown"
                
                profiles.append((name, url, location))
            except Exception as e:
                print(f"  Error processing profile: {e}")
                continue
    
    except Exception as e:
        print(f"Warning: Error extracting profiles: {e}")
        return profiles
    
    print(f"  Extracted {len(profiles)} profiles with location information")
    return profiles


async def has_next_page(client: LinkedInClient) -> bool:
    """
    Check if there's a next page available by looking for enabled Next button.
    
    Uses multiple selectors because LinkedIn uses different button structures:
    - Different aria-label formats (e.g., "Next", "next", "Next page")
    - Different button implementations across page variations
    """
    page = client.page
    try:
        # Try each selector until we find an enabled Next button
        for selector in config.NEXT_BUTTON_SELECTORS:
            try:
                next_button = page.locator(selector).first
                if await next_button.count() > 0:
                    if await next_button.is_enabled():
                        return True
            except Exception:
                continue
        return False
    except Exception:
        return False


async def go_to_next_page(client: LinkedInClient) -> bool:
    """
    Navigate to the next page by clicking the Next button. Returns True if successful.
    
    Uses multiple selectors because LinkedIn uses different button structures:
    - Different aria-label formats (e.g., "Next", "next", "Next page")
    - Different button implementations across page variations
    """
    page = client.page
    try:
        # Try each selector until we find and click an enabled Next button
        for selector in config.NEXT_BUTTON_SELECTORS:
            try:
                next_button = page.locator(selector).first
                if await next_button.count() > 0:
                    if not await next_button.is_enabled():
                        continue
                    
                    await next_button.scroll_into_view_if_needed()
                    await client.random_delay(0.5, 1)
                    await next_button.click()
                    await client.random_delay(config.PAGE_DELAY_MIN, config.PAGE_DELAY_MAX)
                    return True
            except Exception:
                continue
        return False
    except Exception as e:
        print(f"Error navigating to next page: {e}")
        return False

