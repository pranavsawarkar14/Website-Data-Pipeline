# Deployment Guide

## 📁 Clean Project Structure
```
├── dags/                          # Apache Airflow DAGs
│   ├── website_pipeline_dag.py    # Main pipeline orchestration
│   └── dag_config.py             # DAG configuration settings
├── scripts/                       # Core processing scripts
│   ├── crawler.py                # Website crawling and HTML extraction
│   ├── extractor.py              # Text extraction from HTML
│   ├── transformer.py            # Data standardization
│   └── aggregator.py             # Metrics computation
├── data/                         # Data storage (sample outputs included)
│   ├── raw/                      # Raw HTML files by domain
│   ├── processed/                # Cleaned and standardized data
│   └── aggregated/               # Final metrics and insights
├── .gitignore                    # Git ignore patterns
├── requirements.txt              # Python dependencies
└── README.md                     # Complete documentation
```

## 🚀 Quick Deployment

### Local Deployment
```bash
# 1. Clone/download the project
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the pipeline
python scripts/crawler.py
python scripts/extractor.py
python scripts/transformer.py
python scripts/aggregator.py

# 4. Check results
ls data/aggregated/
```

### Airflow Deployment
```bash
# 1. Set up Airflow environment
export AIRFLOW_HOME=~/airflow
airflow db init

# 2. Copy DAG to Airflow
cp dags/website_pipeline_dag.py $AIRFLOW_HOME/dags/
cp dags/dag_config.py $AIRFLOW_HOME/dags/

# 3. Start Airflow
airflow webserver --port 8080 &
airflow scheduler &

# 4. Access UI and trigger DAG
# http://localhost:8080
```

### Cloud Deployment (AWS/GCP)
```bash
# 1. Upload to cloud storage
aws s3 sync . s3://your-bucket/website-pipeline/

# 2. Set up managed Airflow (MWAA/Cloud Composer)
# 3. Configure DAG with cloud paths
# 4. Schedule execution
```

## 🔧 Configuration

### Website List
Edit `scripts/crawler.py` line 12-21 to modify target websites:
```python
URLS_TO_CRAWL = [
    "https://your-website1.com",
    "https://your-website2.com",
    # Add more websites here
]
```

### Schedule
Edit `dags/dag_config.py` to change execution schedule:
```python
DAG_CONFIG = {
    'schedule_interval': '@daily',  # Change to '@weekly', '@hourly', etc.
}
```

## 📊 Expected Outputs

After successful execution:
- **Raw Data**: 30-40 HTML files in `data/raw/`
- **Processed Data**: JSON files in `data/processed/`
- **Metrics**: Business insights in `data/aggregated/metrics.json`
- **Logs**: Execution logs (auto-generated)

## 🔍 Monitoring

Check pipeline health:
```bash
# View latest metrics
cat data/aggregated/metrics.json | jq '.case_study_analysis'

# Check logs
tail -f *.log

# Validate data quality
python -c "
import json
with open('data/aggregated/metrics.json') as f:
    data = json.load(f)
    print(f'Websites processed: {data[\"case_study_analysis\"][\"total_websites\"]}')
    print(f'Success rate: {data[\"additional_metrics\"][\"content_fill_rate\"]}%')
"
```

## 🛠 Troubleshooting

### Common Issues
1. **Import Errors**: Ensure `pip install -r requirements.txt`
2. **Network Issues**: Check internet connection and website accessibility
3. **Permission Errors**: Ensure write permissions to `data/` directory
4. **Airflow Issues**: Verify Airflow installation and DAG syntax

### Support
- Check README.md for detailed documentation
- Review log files for specific error messages
- Ensure all dependencies are installed correctly