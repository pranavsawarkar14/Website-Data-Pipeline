"""
Configuration file for the Website Pipeline DAG.
Centralizes all configuration settings for easy management.
"""

from datetime import timedelta

# DAG Configuration
DAG_CONFIG = {
    'dag_id': 'website_pipeline_dag',
    'description': 'Complete website data processing pipeline',
    'schedule_interval': '@daily',  # Options: '@daily', '@weekly', '0 2 * * *', None
    'max_active_runs': 1,
    'catchup': False,
    'tags': ['website', 'data-processing', 'etl'],
}

# Task Configuration
TASK_CONFIG = {
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
    'email_on_failure': False,
    'email_on_retry': False,
}

# Pipeline Configuration
PIPELINE_CONFIG = {
    'websites_to_crawl': [
        "https://www.python.org",
        "https://www.apache.org", 
        "https://www.mozilla.org",
        "https://www.linux.org",
        "https://www.nginx.com",
        "https://www.github.com",
        "https://www.stackoverflow.com",
        "https://www.docker.com"
    ],
    'request_timeout': 10,
    'crawl_delay': 1,  # seconds between requests
    'max_internal_links': 2,
}

# File Paths (relative to project root)
PATHS = {
    'raw_data': 'data/raw',
    'processed_data': 'data/processed', 
    'aggregated_data': 'data/aggregated',
    'logs': 'logs',
    'scripts': 'scripts',
}

# Notification Configuration
NOTIFICATIONS = {
    'email_on_success': False,
    'email_on_failure': False,
    'slack_webhook': None,  # Set to Slack webhook URL if desired
    'teams_webhook': None,  # Set to Teams webhook URL if desired
}

# Data Quality Checks
QUALITY_CHECKS = {
    'min_websites_crawled': 5,  # Minimum number of websites that should be successfully crawled
    'min_content_fill_rate': 70,  # Minimum percentage of non-empty content
    'required_sections': ['navbar', 'homepage', 'footer', 'case_study'],
    'max_empty_case_studies': 0.8,  # Maximum percentage of empty case studies allowed
}

# Cleanup Configuration
CLEANUP_CONFIG = {
    'log_retention_days': 7,
    'archive_old_data': True,
    'data_retention_days': 30,
}