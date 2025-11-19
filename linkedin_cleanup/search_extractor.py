"""
Search Extractor - Utilities for extracting profiles from LinkedIn search results.
"""
from typing import List, Optional, Tuple

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient
from linkedin_cleanup.random_actions import random_delay


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


class SearchExtractor:
    """Handles extraction of profiles from LinkedIn search results."""
    
    def __init__(self, client: LinkedInClient):
        """Initialize with a LinkedIn client."""
        self.client = client
    
    async def extract_profiles_from_page(self) -> List[Tuple[str, str, str]]:
        """Extract profile names, URLs, and locations from the current search results page."""
        page = self.client.page
        profiles = []
        seen_urls = set()
        
        try:
            await page.wait_for_selector(
                'div[data-view-name="people-search-result"]',
                timeout=config.SELECTOR_TIMEOUT
            )
        except Exception:
            pass
        
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await random_delay()
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.8)")
            await random_delay()
        except Exception:
            pass
        
        try:
            profile_data = await page.evaluate("""
            () => {
                let main = document.querySelector('main');
                if (!main) return {error: 'No main element', stats: {}};
                
                let resultContainers = Array.from(main.querySelectorAll('div[data-view-name="people-search-result"]'));
                let stats = {totalContainers: resultContainers.length, finalCount: 0};
                let profiles = [];
                
                for (let container of resultContainers) {
                    let allLinks = Array.from(container.querySelectorAll('a[href*="/in/"]'));
                    if (allLinks.length === 0) continue;
                    
                    let mainLink = null;
                    for (let link of allLinks) {
                        let href = link.getAttribute('href');
                        if (!href) continue;
                        
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
                        
                        if (isMutualConnection) continue;
                        
                        if (!mainLink || (link.innerText || '').length > (mainLink.innerText || '').length) {
                            mainLink = link;
                        }
                    }
                    
                    if (!mainLink) continue;
                    
                    let href = mainLink.getAttribute('href');
                    if (!href) continue;
                    
                    let url = href.split('?')[0];
                    if (url.startsWith('/')) {
                        url = 'https://www.linkedin.com' + url;
                    }
                    
                    let name = mainLink.innerText || '';
                    if (name.includes('•')) {
                        name = name.split('•')[0].trim();
                    }
                    name = name.trim();
                    
                    let location = 'Unknown';
                    let paragraphs = container.querySelectorAll('p');
                    if (paragraphs.length >= 3) {
                        location = paragraphs[2].innerText.trim().replace(/\\s+/g, ' ').trim();
                    }
                    
                    profiles.push({url: url, name: name, location: location || 'Unknown'});
                    stats.finalCount++;
                }
                
                return {profiles: profiles, stats: stats};
            }
        """)
        
            if not isinstance(profile_data, dict) or 'profiles' not in profile_data:
                return profiles
            
            if 'error' in profile_data:
                return profiles
            
            profile_list = profile_data['profiles']
            if not profile_list:
                return profiles
            
            for profile in profile_list:
                try:
                    url = normalize_linkedin_url(profile['url'])
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    profiles.append((
                        clean_profile_name(profile['name']),
                        url,
                        profile['location'] or "Unknown"
                    ))
                except Exception:
                    continue
        
        except Exception:
            return profiles
        
        return profiles


    async def has_next_page(self) -> bool:
        """Check if there's a next page available by looking for enabled Next button."""
        page = self.client.page
        try:
            for selector in config.NEXT_BUTTON_SELECTORS:
                try:
                    next_button = page.locator(selector).first
                    if await next_button.count() > 0 and await next_button.is_enabled():
                            return True
                except Exception:
                    continue
            return False
        except Exception:
            return False
    
    async def go_to_next_page(self) -> bool:
        """Navigate to the next page by clicking the Next button. Returns True if successful."""
        page = self.client.page
        try:
            for selector in config.NEXT_BUTTON_SELECTORS:
                try:
                    next_button = page.locator(selector).first
                    if await next_button.count() > 0 and await next_button.is_enabled():
                        await next_button.scroll_into_view_if_needed()
                        await random_delay()
                        await next_button.click()
                        await random_delay()
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

