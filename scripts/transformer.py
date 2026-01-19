import os
import json
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
EXTRACTED_FILE = PROCESSED_DIR / "extracted.json"
STANDARDIZED_FILE = PROCESSED_DIR / "standardized.json"
METADATA_FILE = DATA_DIR / "metadata.json"
LOG_FILE = BASE_DIR / "transformer.log"

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

def load_extracted_data():
    """Load extracted text data."""
    if not EXTRACTED_FILE.exists():
        logger.error(f"Extracted data file not found: {EXTRACTED_FILE}")
        return None
    
    try:
        with open(EXTRACTED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading extracted data: {e}")
        return None

def load_metadata():
    """Load crawler metadata to get original URLs and timestamps."""
    if not METADATA_FILE.exists():
        logger.warning(f"Metadata file not found: {METADATA_FILE}")
        return {}
    
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading metadata: {e}")
        return {}

def find_website_url_by_domain(domain, metadata):
    """Find the original website URL for a given domain."""
    for url, data in metadata.items():
        if data.get('domain') == domain:
            return url
    
    # Fallback: construct URL from domain
    if domain:
        return f"https://www.{domain}" if not domain.startswith('www.') else f"https://{domain}"
    
    return ""

def get_crawl_timestamp(domain, metadata):
    """Get the crawl timestamp for a domain."""
    for url, data in metadata.items():
        if data.get('domain') == domain:
            return data.get('crawl_time', '')
    
    return ""

def create_standardized_record(website_url, section, content, crawl_timestamp):
    """Create a standardized record."""
    return {
        "website": website_url,
        "section": section,
        "content": content.strip() if content else "",
        "crawl_timestamp": crawl_timestamp,
        "isActive": True
    }

def transform_domain_data(domain_name, domain_data, metadata):
    """Transform data for a single domain into standardized records."""
    records = []
    
    # Get website URL and crawl timestamp
    website_url = find_website_url_by_domain(domain_name, metadata)
    crawl_timestamp = get_crawl_timestamp(domain_name, metadata)
    
    logger.info(f"Transforming domain: {domain_name} -> {website_url}")
    
    # Define sections to process
    sections = ['navbar', 'homepage', 'footer', 'case_study']
    
    for section in sections:
        content = domain_data.get(section, "")
        
        # Create record even if content is empty (as per requirements)
        record = create_standardized_record(
            website_url=website_url,
            section=section,
            content=content,
            crawl_timestamp=crawl_timestamp
        )
        
        records.append(record)
        
        # Log content statistics
        content_length = len(content) if content else 0
        if content_length > 0:
            logger.info(f"  {section}: {content_length} characters")
        else:
            logger.info(f"  {section}: empty content")
    
    return records

def validate_record(record):
    """Validate a standardized record."""
    required_fields = ['website', 'section', 'content', 'crawl_timestamp', 'isActive']
    
    for field in required_fields:
        if field not in record:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Validate section values
    valid_sections = ['navbar', 'homepage', 'footer', 'case_study']
    if record['section'] not in valid_sections:
        logger.error(f"Invalid section: {record['section']}")
        return False
    
    # Validate isActive is boolean
    if not isinstance(record['isActive'], bool):
        logger.error(f"isActive must be boolean, got: {type(record['isActive'])}")
        return False
    
    return True

def main():
    """Main transformation function."""
    logger.info("Starting data transformation to standardized format...")
    setup_directories()
    
    # Load input data
    extracted_data = load_extracted_data()
    if not extracted_data:
        logger.error("Failed to load extracted data. Exiting.")
        return
    
    metadata = load_metadata()
    
    # Initialize output structure
    standardized_data = {
        "transformation_time": datetime.now().isoformat(),
        "source_file": str(EXTRACTED_FILE.relative_to(BASE_DIR)),
        "records": [],
        "summary": {
            "total_domains": 0,
            "total_records": 0,
            "records_by_section": {
                "navbar": 0,
                "homepage": 0,
                "footer": 0,
                "case_study": 0
            },
            "domains_processed": [],
            "validation_errors": 0
        }
    }
    
    try:
        domains_data = extracted_data.get('domains', {})
        standardized_data['summary']['total_domains'] = len(domains_data)
        
        # Process each domain
        for domain_name, domain_data in domains_data.items():
            logger.info(f"Processing domain: {domain_name}")
            
            # Transform domain data to standardized records
            domain_records = transform_domain_data(domain_name, domain_data, metadata)
            
            # Validate and add records
            for record in domain_records:
                if validate_record(record):
                    standardized_data['records'].append(record)
                    standardized_data['summary']['total_records'] += 1
                    standardized_data['summary']['records_by_section'][record['section']] += 1
                else:
                    standardized_data['summary']['validation_errors'] += 1
                    logger.error(f"Validation failed for record: {record}")
            
            standardized_data['summary']['domains_processed'].append(domain_name)
        
        # Save standardized data
        with open(STANDARDIZED_FILE, 'w', encoding='utf-8') as f:
            json.dump(standardized_data, f, indent=2, ensure_ascii=False)
        
        # Log summary
        summary = standardized_data['summary']
        logger.info("Transformation completed successfully!")
        logger.info(f"Domains processed: {summary['total_domains']}")
        logger.info(f"Total records created: {summary['total_records']}")
        logger.info(f"Records by section:")
        for section, count in summary['records_by_section'].items():
            logger.info(f"  {section}: {count}")
        
        if summary['validation_errors'] > 0:
            logger.warning(f"Validation errors: {summary['validation_errors']}")
        
        logger.info(f"Results saved to: {STANDARDIZED_FILE}")
        
        # Show sample records
        if standardized_data['records']:
            logger.info("Sample records:")
            for i, record in enumerate(standardized_data['records'][:3]):  # Show first 3
                logger.info(f"  Record {i+1}: {record['website']} - {record['section']} ({len(record['content'])} chars)")
        
    except Exception as e:
        logger.error(f"Unexpected error during transformation: {e}")
        
        # Save partial results with error information
        standardized_data['error'] = str(e)
        try:
            with open(STANDARDIZED_FILE, 'w', encoding='utf-8') as f:
                json.dump(standardized_data, f, indent=2, ensure_ascii=False)
            logger.info("Partial results saved despite error")
        except Exception as save_error:
            logger.error(f"Failed to save partial results: {save_error}")

if __name__ == "__main__":
    main()