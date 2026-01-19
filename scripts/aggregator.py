import os
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
AGGREGATED_DIR = DATA_DIR / "aggregated"
STANDARDIZED_FILE = PROCESSED_DIR / "standardized.json"
METRICS_FILE = AGGREGATED_DIR / "metrics.json"
LOG_FILE = BASE_DIR / "aggregator.log"

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
    AGGREGATED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Aggregated directory ready at {AGGREGATED_DIR}")

def load_standardized_data():
    """Load standardized data."""
    if not STANDARDIZED_FILE.exists():
        logger.error(f"Standardized data file not found: {STANDARDIZED_FILE}")
        return None
    
    try:
        with open(STANDARDIZED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading standardized data: {e}")
        return None

def compute_case_study_metrics(records):
    """Compute metrics related to case studies."""
    logger.info("Computing case study metrics...")
    
    # Group records by website
    websites_data = defaultdict(dict)
    for record in records:
        website = record['website']
        section = record['section']
        websites_data[website][section] = record
    
    # Count websites with case studies
    websites_with_case_studies = 0
    websites_without_case_studies = 0
    case_study_content_lengths = []
    
    for website, sections in websites_data.items():
        case_study_record = sections.get('case_study', {})
        case_study_content = case_study_record.get('content', '')
        
        if case_study_content and case_study_content.strip():
            websites_with_case_studies += 1
            case_study_content_lengths.append(len(case_study_content))
            logger.debug(f"Website with case study: {website} ({len(case_study_content)} chars)")
        else:
            websites_without_case_studies += 1
            logger.debug(f"Website without case study: {website}")
    
    total_websites = len(websites_data)
    case_study_percentage = (websites_with_case_studies / total_websites * 100) if total_websites > 0 else 0
    
    avg_case_study_length = sum(case_study_content_lengths) / len(case_study_content_lengths) if case_study_content_lengths else 0
    
    logger.info(f"Case study analysis: {websites_with_case_studies}/{total_websites} websites have case studies ({case_study_percentage:.1f}%)")
    
    return {
        'total_websites': total_websites,
        'websites_with_case_studies': websites_with_case_studies,
        'websites_without_case_studies': websites_without_case_studies,
        'case_study_percentage': round(case_study_percentage, 2),
        'average_case_study_length': round(avg_case_study_length, 2) if avg_case_study_length > 0 else 0
    }

def compute_activity_metrics(records):
    """Compute active vs inactive website metrics."""
    logger.info("Computing activity metrics...")
    
    # Group by website and check if any record is inactive
    websites_activity = defaultdict(list)
    for record in records:
        website = record['website']
        is_active = record.get('isActive', True)
        websites_activity[website].append(is_active)
    
    active_websites = 0
    inactive_websites = 0
    
    for website, activity_list in websites_activity.items():
        # Website is considered active if ALL its records are active
        is_website_active = all(activity_list)
        
        if is_website_active:
            active_websites += 1
            logger.debug(f"Active website: {website}")
        else:
            inactive_websites += 1
            logger.debug(f"Inactive website: {website}")
    
    total_websites = len(websites_activity)
    active_percentage = (active_websites / total_websites * 100) if total_websites > 0 else 0
    
    logger.info(f"Activity analysis: {active_websites}/{total_websites} websites are active ({active_percentage:.1f}%)")
    
    return {
        'total_websites': total_websites,
        'active_websites': active_websites,
        'inactive_websites': inactive_websites,
        'active_percentage': round(active_percentage, 2)
    }

def compute_content_length_metrics(records):
    """Compute average content length by section."""
    logger.info("Computing content length metrics...")
    
    # Group content lengths by section
    section_lengths = defaultdict(list)
    section_counts = Counter()
    
    for record in records:
        section = record['section']
        content = record.get('content', '')
        content_length = len(content) if content else 0
        
        section_lengths[section].append(content_length)
        section_counts[section] += 1
    
    # Calculate averages and statistics
    section_metrics = {}
    for section, lengths in section_lengths.items():
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            min_length = min(lengths)
            max_length = max(lengths)
            non_empty_count = sum(1 for length in lengths if length > 0)
            empty_count = len(lengths) - non_empty_count
            
            section_metrics[section] = {
                'average_length': round(avg_length, 2),
                'min_length': min_length,
                'max_length': max_length,
                'total_records': len(lengths),
                'non_empty_records': non_empty_count,
                'empty_records': empty_count,
                'non_empty_percentage': round((non_empty_count / len(lengths) * 100), 2) if len(lengths) > 0 else 0
            }
            
            logger.info(f"Section '{section}': avg={avg_length:.1f} chars, {non_empty_count}/{len(lengths)} non-empty")
        else:
            section_metrics[section] = {
                'average_length': 0,
                'min_length': 0,
                'max_length': 0,
                'total_records': 0,
                'non_empty_records': 0,
                'empty_records': 0,
                'non_empty_percentage': 0
            }
    
    return section_metrics

def compute_additional_metrics(records):
    """Compute additional useful metrics."""
    logger.info("Computing additional metrics...")
    
    total_records = len(records)
    total_content_length = sum(len(record.get('content', '')) for record in records)
    
    # Website distribution
    website_counts = Counter(record['website'] for record in records)
    unique_websites = len(website_counts)
    
    # Section distribution
    section_counts = Counter(record['section'] for record in records)
    
    # Timestamp analysis
    timestamps = [record.get('crawl_timestamp', '') for record in records if record.get('crawl_timestamp')]
    earliest_crawl = min(timestamps) if timestamps else None
    latest_crawl = max(timestamps) if timestamps else None
    
    # Content statistics
    non_empty_records = sum(1 for record in records if record.get('content', '').strip())
    empty_records = total_records - non_empty_records
    
    return {
        'total_records': total_records,
        'unique_websites': unique_websites,
        'total_content_length': total_content_length,
        'average_content_length_overall': round(total_content_length / total_records, 2) if total_records > 0 else 0,
        'non_empty_records': non_empty_records,
        'empty_records': empty_records,
        'content_fill_rate': round((non_empty_records / total_records * 100), 2) if total_records > 0 else 0,
        'section_distribution': dict(section_counts),
        'website_distribution': dict(website_counts),
        'crawl_period': {
            'earliest': earliest_crawl,
            'latest': latest_crawl,
            'total_timestamps': len(timestamps)
        }
    }

def validate_metrics(metrics):
    """Validate computed metrics for consistency."""
    logger.info("Validating computed metrics...")
    
    validation_errors = []
    
    # Check case study metrics consistency
    case_study = metrics.get('case_study_analysis', {})
    if case_study:
        total = case_study.get('websites_with_case_studies', 0) + case_study.get('websites_without_case_studies', 0)
        if total != case_study.get('total_websites', 0):
            validation_errors.append("Case study totals don't match")
    
    # Check activity metrics consistency
    activity = metrics.get('activity_analysis', {})
    if activity:
        total = activity.get('active_websites', 0) + activity.get('inactive_websites', 0)
        if total != activity.get('total_websites', 0):
            validation_errors.append("Activity totals don't match")
    
    # Check section metrics
    content_metrics = metrics.get('content_length_by_section', {})
    expected_sections = ['navbar', 'homepage', 'footer', 'case_study']
    for section in expected_sections:
        if section not in content_metrics:
            validation_errors.append(f"Missing section metrics: {section}")
    
    if validation_errors:
        for error in validation_errors:
            logger.warning(f"Validation error: {error}")
        return False
    
    logger.info("✅ All metrics validation passed")
    return True

def main():
    """Main aggregation function."""
    logger.info("Starting data aggregation and metrics computation...")
    setup_directories()
    
    # Load standardized data
    standardized_data = load_standardized_data()
    if not standardized_data:
        logger.error("Failed to load standardized data. Exiting.")
        return
    
    records = standardized_data.get('records', [])
    if not records:
        logger.error("No records found in standardized data. Exiting.")
        return
    
    logger.info(f"Processing {len(records)} records...")
    
    # Initialize metrics structure
    metrics = {
        'computation_time': datetime.now().isoformat(),
        'source_file': str(STANDARDIZED_FILE.relative_to(BASE_DIR)),
        'input_summary': standardized_data.get('summary', {}),
        'case_study_analysis': {},
        'activity_analysis': {},
        'content_length_by_section': {},
        'additional_metrics': {},
        'validation_passed': False
    }
    
    try:
        # Compute all metrics
        logger.info("Computing case study metrics...")
        metrics['case_study_analysis'] = compute_case_study_metrics(records)
        
        logger.info("Computing activity metrics...")
        metrics['activity_analysis'] = compute_activity_metrics(records)
        
        logger.info("Computing content length metrics...")
        metrics['content_length_by_section'] = compute_content_length_metrics(records)
        
        logger.info("Computing additional metrics...")
        metrics['additional_metrics'] = compute_additional_metrics(records)
        
        # Validate metrics
        metrics['validation_passed'] = validate_metrics(metrics)
        
        # Save metrics
        with open(METRICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        # Log summary
        logger.info("Aggregation completed successfully!")
        logger.info(f"Results saved to: {METRICS_FILE}")
        
        # Print key findings
        case_study = metrics['case_study_analysis']
        activity = metrics['activity_analysis']
        additional = metrics['additional_metrics']
        
        logger.info("=== KEY FINDINGS ===")
        logger.info(f"📊 Total websites analyzed: {additional['unique_websites']}")
        logger.info(f"📝 Total records processed: {additional['total_records']}")
        logger.info(f"📚 Websites with case studies: {case_study['websites_with_case_studies']}/{case_study['total_websites']} ({case_study['case_study_percentage']}%)")
        logger.info(f"✅ Active websites: {activity['active_websites']}/{activity['total_websites']} ({activity['active_percentage']}%)")
        logger.info(f"📄 Content fill rate: {additional['content_fill_rate']}%")
        
        # Show section averages
        logger.info("📏 Average content length by section:")
        for section, data in metrics['content_length_by_section'].items():
            logger.info(f"  {section}: {data['average_length']} chars ({data['non_empty_percentage']}% non-empty)")
        
    except Exception as e:
        logger.error(f"Unexpected error during aggregation: {e}")
        
        # Save partial results with error information
        metrics['error'] = str(e)
        try:
            with open(METRICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)
            logger.info("Partial results saved despite error")
        except Exception as save_error:
            logger.error(f"Failed to save partial results: {save_error}")

if __name__ == "__main__":
    main()