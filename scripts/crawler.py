import os
import json
import time
import logging
from urllib.parse import urlparse, urljoin
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# --- Configuration ---
URLS_TO_CRAWL = [
    "https://www.python.org",
    "https://www.apache.org", 
    "https://www.mozilla.org",
    "https://www.linux.org",
    "https://www.nginx.com",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.docker.com"
]

REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
METADATA_FILE = DATA_DIR / "metadata.json"
LOG_FILE = BASE_DIR / "crawler.log"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data directory ready at {RAW_DATA_DIR}")

def load_metadata():
    """Load existing metadata or return empty dict."""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading metadata: {e}. Starting fresh.")
            return {}
    return {}

def save_metadata(metadata):
    """Save metadata to JSON file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info("Metadata saved successfully")
    except Exception as e:
        logger.error(f"Failed to save metadata: {e}")

def get_domain_name(url):
    """Extract clean domain name from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc
    # Remove www. prefix for cleaner folder names
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def fetch_url(url, session=None):
    """Fetch URL with error handling and retries."""
    if session is None:
        session = requests.Session()
    
    headers = {'User-Agent': USER_AGENT}
    
    try:
        logger.info(f"Fetching: {url}")
        response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} fetching {url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None

def save_html_file(content, domain, filename):
    """Save HTML content to domain-specific directory."""
    try:
        domain_dir = RAW_DATA_DIR / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = domain_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved {filename} for {domain}")
        return str(filepath.relative_to(BASE_DIR))
    except Exception as e:
        logger.error(f"Error saving {filename} for {domain}: {e}")
        return None

def extract_navbar_html(html_content):
    """Extract navbar HTML from page content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try multiple selectors for navbar
        navbar_selectors = [
            'nav',
            'header nav',
            '[role="navigation"]',
            '.navbar',
            '.nav',
            '.navigation',
            'header'
        ]
        
        for selector in navbar_selectors:
            navbar = soup.select_one(selector)
            if navbar:
                return str(navbar)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting navbar: {e}")
        return None

def extract_footer_html(html_content):
    """Extract footer HTML from page content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try multiple selectors for footer
        footer_selectors = [
            'footer',
            '[role="contentinfo"]',
            '.footer',
            '.site-footer',
            '#footer'
        ]
        
        for selector in footer_selectors:
            footer = soup.select_one(selector)
            if footer:
                return str(footer)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting footer: {e}")
        return None

def find_case_study_url(base_url, html_content):
    """Find case study or success story URL using pattern matching."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(base_url).netloc
        
        # Keywords to look for in URLs and link text
        case_study_keywords = ['case', 'success', 'story', 'customer', 'testimonial']
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().lower().strip()
            href_lower = href.lower()
            
            # Check if URL or link text contains case study keywords
            if any(keyword in href_lower or keyword in link_text for keyword in case_study_keywords):
                full_url = urljoin(base_url, href)
                parsed_url = urlparse(full_url)
                
                # Ensure it's internal and valid
                if (parsed_url.netloc == base_domain and 
                    parsed_url.scheme in ('http', 'https') and
                    full_url != base_url):
                    return full_url
        
        return None
    except Exception as e:
        logger.error(f"Error finding case study URL: {e}")
        return None

def extract_internal_links(base_url, html_content, max_links=2):
    """Extract internal links from the same domain (reduced to 2 since we now have case study)."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(base_url).netloc
        internal_links = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            parsed_url = urlparse(full_url)
            
            # Check if it's internal and not just a fragment
            if (parsed_url.netloc == base_domain and 
                parsed_url.scheme in ('http', 'https') and
                parsed_url.path != '/' and  # Skip homepage
                not parsed_url.path.endswith(('.pdf', '.jpg', '.png', '.gif', '.zip')) and
                full_url != base_url):
                
                if full_url not in internal_links:
                    internal_links.append(full_url)
                    if len(internal_links) >= max_links:
                        break
        
        return internal_links[:max_links]
    except Exception as e:
        logger.error(f"Error extracting internal links from {base_url}: {e}")
        return []

def crawl_website(base_url, metadata, session):
    """Crawl a single website: homepage + navbar + footer + case study + 2 internal links."""
    domain = get_domain_name(base_url)
    
    # Check idempotency - skip if already crawled successfully
    if base_url in metadata and metadata[base_url].get('status') == 'completed':
        logger.info(f"Skipping {base_url} - already crawled successfully")
        return
    
    crawl_data = {
        'url': base_url,
        'domain': domain,
        'crawl_time': datetime.now().isoformat(),
        'timestamp': datetime.now().timestamp(),
        'status': 'failed',
        'pages': {},
        'components': {}
    }
    
    try:
        # Fetch homepage
        homepage_response = fetch_url(base_url, session)
        if not homepage_response:
            logger.error(f"Failed to fetch homepage for {base_url}")
            metadata[base_url] = crawl_data
            return
        
        # Save homepage
        homepage_path = save_html_file(homepage_response.text, domain, 'homepage.html')
        crawl_data['pages']['homepage'] = {
            'url': base_url,
            'http_status': homepage_response.status_code,
            'file_path': homepage_path,
            'content_length': len(homepage_response.text)
        }
        
        # Extract and save navbar
        navbar_html = extract_navbar_html(homepage_response.text)
        if navbar_html:
            navbar_path = save_html_file(navbar_html, domain, 'navbar.html')
            crawl_data['components']['navbar'] = {
                'file_path': navbar_path,
                'content_length': len(navbar_html)
            }
            logger.info(f"Extracted navbar for {domain}")
        else:
            logger.warning(f"No navbar found for {domain}")
        
        # Extract and save footer
        footer_html = extract_footer_html(homepage_response.text)
        if footer_html:
            footer_path = save_html_file(footer_html, domain, 'footer.html')
            crawl_data['components']['footer'] = {
                'file_path': footer_path,
                'content_length': len(footer_html)
            }
            logger.info(f"Extracted footer for {domain}")
        else:
            logger.warning(f"No footer found for {domain}")
        
        # Find and fetch case study page
        case_study_url = find_case_study_url(base_url, homepage_response.text)
        if case_study_url:
            logger.info(f"Found case study URL for {domain}: {case_study_url}")
            time.sleep(1)  # Polite delay
            
            case_study_response = fetch_url(case_study_url, session)
            if case_study_response:
                case_study_path = save_html_file(case_study_response.text, domain, 'case_study.html')
                crawl_data['pages']['case_study'] = {
                    'url': case_study_url,
                    'http_status': case_study_response.status_code,
                    'file_path': case_study_path,
                    'content_length': len(case_study_response.text)
                }
                logger.info(f"Successfully crawled case study for {domain}")
            else:
                logger.warning(f"Failed to fetch case study for {domain}: {case_study_url}")
        else:
            logger.info(f"No case study found for {domain}")
        
        # Extract and crawl internal links (reduced to 2 since we have case study)
        internal_links = extract_internal_links(base_url, homepage_response.text, max_links=2)
        logger.info(f"Found {len(internal_links)} internal links for {domain}")
        
        for i, link_url in enumerate(internal_links, 1):
            time.sleep(1)  # Be polite - 1 second delay between requests
            
            link_response = fetch_url(link_url, session)
            if link_response:
                filename = f'internal_page_{i}.html'
                file_path = save_html_file(link_response.text, domain, filename)
                
                crawl_data['pages'][f'internal_{i}'] = {
                    'url': link_url,
                    'http_status': link_response.status_code,
                    'file_path': file_path,
                    'content_length': len(link_response.text)
                }
                logger.info(f"Successfully crawled internal page {i} for {domain}")
            else:
                logger.warning(f"Failed to fetch internal link {i} for {domain}: {link_url}")
        
        crawl_data['status'] = 'completed'
        crawl_data['pages_crawled'] = len(crawl_data['pages'])
        crawl_data['components_extracted'] = len(crawl_data['components'])
        logger.info(f"Successfully completed crawling {domain} - {crawl_data['pages_crawled']} pages, {crawl_data['components_extracted']} components")
        
    except Exception as e:
        logger.error(f"Unexpected error crawling {base_url}: {e}")
        crawl_data['error'] = str(e)
    
    finally:
        metadata[base_url] = crawl_data

def main():
    """Main crawler function."""
    logger.info("Starting web crawler...")
    setup_directories()
    
    # Load existing metadata for idempotency
    metadata = load_metadata()
    
    # Create session for connection reuse
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    
    try:
        for base_url in URLS_TO_CRAWL:
            logger.info(f"Processing {base_url}")
            crawl_website(base_url, metadata, session)
            
            # Save metadata after each website (for crash recovery)
            save_metadata(metadata)
            
            # Polite delay between websites
            time.sleep(2)
        
        # Final summary
        completed = sum(1 for data in metadata.values() if data.get('status') == 'completed')
        total_pages = sum(data.get('pages_crawled', 0) for data in metadata.values())
        total_components = sum(data.get('components_extracted', 0) for data in metadata.values())
        
        logger.info(f"Crawling completed! {completed}/{len(URLS_TO_CRAWL)} websites successful")
        logger.info(f"Total content extracted: {total_pages} pages, {total_components} components")
        
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
    finally:
        session.close()
        save_metadata(metadata)

if __name__ == "__main__":
    main()
