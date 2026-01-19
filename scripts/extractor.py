import os
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_FILE = PROCESSED_DIR / "extracted.json"
METADATA_FILE = DATA_DIR / "metadata.json"
LOG_FILE = BASE_DIR / "extractor.log"

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
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Processed directory ready at {PROCESSED_DIR}")

def load_metadata():
    """Load crawler metadata to understand file structure."""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading metadata: {e}")
            return {}
    return {}

def clean_text(text):
    """Clean and normalize extracted text."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common unwanted characters
    text = re.sub(r'[\r\n\t]+', ' ', text)
    
    # Remove multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()

def extract_text_from_soup(soup):
    """Extract clean text from BeautifulSoup object."""
    if not soup:
        return ""
    
    # Remove script and style elements
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
    
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # Get text and clean it
    text = soup.get_text()
    return clean_text(text)

def read_html_file(file_path):
    """Read and parse HTML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return BeautifulSoup(content, 'html.parser')
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None

def extract_navbar_text(soup):
    """Extract navbar text using heuristics."""
    if not soup:
        return ""
    
    # Try multiple navbar selectors
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
            return extract_text_from_soup(navbar)
    
    return ""

def extract_footer_text(soup):
    """Extract footer text using heuristics."""
    if not soup:
        return ""
    
    # Try multiple footer selectors
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
            return extract_text_from_soup(footer)
    
    return ""

def extract_main_content_text(soup):
    """Extract main content text using heuristics."""
    if not soup:
        return ""
    
    # Try multiple main content selectors in order of preference
    main_selectors = [
        'main',
        '[role="main"]',
        '.main-content',
        '.content',
        '#main',
        '#content'
    ]
    
    # First try specific main content areas
    for selector in main_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            return extract_text_from_soup(main_content)
    
    # Fallback: extract from body but exclude nav and footer
    body = soup.find('body')
    if body:
        # Clone the body to avoid modifying original
        body_copy = BeautifulSoup(str(body), 'html.parser')
        
        # Remove navigation and footer elements
        for nav in body_copy(['nav', 'header', 'footer']):
            nav.decompose()
        
        # Remove elements with navigation/footer classes
        for elem in body_copy.find_all(class_=re.compile(r'nav|footer|sidebar', re.I)):
            elem.decompose()
        
        return extract_text_from_soup(body_copy)
    
    # Last resort: get all text
    return extract_text_from_soup(soup)

def is_case_study_url(url):
    """Check if URL indicates a case study page."""
    if not url:
        return False
    
    url_lower = url.lower()
    case_study_keywords = ['case', 'success', 'story', 'customer', 'testimonial']
    
    return any(keyword in url_lower for keyword in case_study_keywords)

def extract_from_html_file(file_path, content_type, url=None):
    """Extract text from a single HTML file based on content type."""
    soup = read_html_file(file_path)
    if not soup:
        return ""
    
    if content_type == 'navbar':
        return extract_navbar_text(soup)
    elif content_type == 'footer':
        return extract_footer_text(soup)
    elif content_type == 'homepage' or content_type == 'main':
        return extract_main_content_text(soup)
    elif content_type == 'case_study':
        # For case study, extract main content
        return extract_main_content_text(soup)
    else:
        # Default: extract main content
        return extract_main_content_text(soup)

def process_domain_files(domain_dir, domain_name, metadata_entry):
    """Process all HTML files for a single domain."""
    logger.info(f"Processing domain: {domain_name}")
    
    domain_data = {
        'domain': domain_name,
        'processed_time': datetime.now().isoformat(),
        'navbar': "",
        'homepage': "",
        'footer': "",
        'case_study': "",
        'files_processed': []
    }
    
    try:
        # Process specific component files first
        component_files = {
            'navbar.html': 'navbar',
            'footer.html': 'footer',
            'homepage.html': 'homepage'
        }
        
        for filename, content_type in component_files.items():
            file_path = domain_dir / filename
            if file_path.exists():
                extracted_text = extract_from_html_file(file_path, content_type)
                domain_data[content_type] = extracted_text
                domain_data['files_processed'].append(filename)
                logger.info(f"Extracted {content_type} from {filename} for {domain_name}")
            else:
                logger.info(f"File {filename} not found for {domain_name}")
        
        # Look for case study file
        case_study_file = domain_dir / 'case_study.html'
        if case_study_file.exists():
            extracted_text = extract_from_html_file(case_study_file, 'case_study')
            domain_data['case_study'] = extracted_text
            domain_data['files_processed'].append('case_study.html')
            logger.info(f"Extracted case study from case_study.html for {domain_name}")
        else:
            # Check if any internal pages might be case studies based on URL
            if metadata_entry and 'pages' in metadata_entry:
                for page_key, page_info in metadata_entry['pages'].items():
                    if page_key.startswith('internal_') and is_case_study_url(page_info.get('url', '')):
                        # Find corresponding file
                        page_num = page_key.split('_')[1]
                        internal_file = domain_dir / f'internal_page_{page_num}.html'
                        if internal_file.exists():
                            extracted_text = extract_from_html_file(internal_file, 'case_study', page_info.get('url'))
                            domain_data['case_study'] = extracted_text
                            domain_data['files_processed'].append(f'internal_page_{page_num}.html')
                            logger.info(f"Found case study in internal page {page_num} for {domain_name}")
                            break
        
        # Add content statistics
        domain_data['stats'] = {
            'navbar_length': len(domain_data['navbar']),
            'homepage_length': len(domain_data['homepage']),
            'footer_length': len(domain_data['footer']),
            'case_study_length': len(domain_data['case_study']),
            'total_files': len(domain_data['files_processed'])
        }
        
        return domain_data
        
    except Exception as e:
        logger.error(f"Error processing domain {domain_name}: {e}")
        domain_data['error'] = str(e)
        return domain_data

def main():
    """Main extraction function."""
    logger.info("Starting text extraction from raw HTML files...")
    setup_directories()
    
    # Load metadata to understand file structure
    metadata = load_metadata()
    
    extracted_data = {
        'extraction_time': datetime.now().isoformat(),
        'domains': {},
        'summary': {
            'total_domains': 0,
            'successful_extractions': 0,
            'failed_extractions': 0
        }
    }
    
    try:
        # Process each domain directory
        if not RAW_DATA_DIR.exists():
            logger.error(f"Raw data directory not found: {RAW_DATA_DIR}")
            return
        
        for domain_dir in RAW_DATA_DIR.iterdir():
            if domain_dir.is_dir():
                domain_name = domain_dir.name
                extracted_data['summary']['total_domains'] += 1
                
                # Get metadata for this domain if available
                metadata_entry = None
                for url, data in metadata.items():
                    if data.get('domain') == domain_name:
                        metadata_entry = data
                        break
                
                # Process the domain
                domain_data = process_domain_files(domain_dir, domain_name, metadata_entry)
                extracted_data['domains'][domain_name] = domain_data
                
                if 'error' not in domain_data:
                    extracted_data['summary']['successful_extractions'] += 1
                else:
                    extracted_data['summary']['failed_extractions'] += 1
        
        # Save extracted data
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Extraction completed successfully!")
        logger.info(f"Processed {extracted_data['summary']['total_domains']} domains")
        logger.info(f"Successful: {extracted_data['summary']['successful_extractions']}")
        logger.info(f"Failed: {extracted_data['summary']['failed_extractions']}")
        logger.info(f"Results saved to: {OUTPUT_FILE}")
        
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        extracted_data['error'] = str(e)
        
        # Save partial results even if there was an error
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        except Exception as save_error:
            logger.error(f"Failed to save partial results: {save_error}")

if __name__ == "__main__":
    main()