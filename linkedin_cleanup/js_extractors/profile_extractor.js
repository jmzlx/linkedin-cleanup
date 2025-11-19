// Profile extraction JavaScript for LinkedIn search results
// This script extracts profile information from LinkedIn search result pages

(() => {
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
            location = paragraphs[2].innerText.trim().replace(/\s+/g, ' ').trim();
        }
        
        profiles.push({url: url, name: name, location: location || 'Unknown'});
        stats.finalCount++;
    }
    
    return {profiles: profiles, stats: stats};
})();

