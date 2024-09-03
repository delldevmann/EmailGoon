# Streamlit Cloud Email Harvester ⚒️

A powerful tool for scraping and harvesting email addresses from multiple websites, with support for batch processing, scheduled scraping, and export options.

## Features

- **Batch Processing**: Input multiple URLs at once and scrape them sequentially.
- **Scheduled Scraping**: Schedule scraping tasks to run automatically at a specified time (e.g., daily at 9 AM).
- **Real-Time Progress Tracking**: Visual progress bar to monitor scraping progress.
- **Export Options**: Download scraped emails as CSV or Excel files.
- **Feedback Form**: Submit feedback or report issues directly within the app.
- **Logging**: Detailed logs of scraping activities, including successes and failures.

## Installation

### Prerequisites

- Python 3.7 or later
- `pip` package manager

### Install Dependencies

First, ensure you have all required Python packages installed. You can do this by using the `requirements.txt` file provided:

```bash
pip install -r requirements.txt
```

### Requirements

Ensure your `requirements.txt` file includes the following:

```plaintext
altair==4.2.2
apscheduler==3.10.1
attrs==23.1.0
beautifulsoup4==4.12.2
blinker==1.6.2
cachetools==5.3.0
certifi==2023.5.7
charset-normalizer==3.1.0
click==8.1.3
decorator==5.1.1
entrypoints==0.4
gitdb==4.0.10
GitPython==3.1.31
idna==3.4
importlib-metadata==6.6.0
Jinja2==3.1.2
jsonschema==4.17.3
markdown-it-py==2.2.0
MarkupSafe==2.1.2
mdurl==0.1.2
numpy==1.24.3
packaging==23.1
pandas==2.0.1
Pillow==9.5.0
protobuf==3.20.3
pyarrow==12.0.0
pydeck==0.8.1b0
Pygments==2.15.1
Pympler==1.0.1
pyrsistent==0.19.3
python-dateutil==2.8.2
pytz==2023.3
requests==2.30.0
rich==13.3.5
six==1.16.0
smmap==5.0.0
soupsieve==2.4.1
streamlit==1.22.0
tenacity==8.2.2
toml==0.10.2
toolz==0.12.0
tornado==6.3.2
typing_extensions==4.5.0
tzdata==2023.3
tzlocal==5.0.1
urllib3==2.0.2
validators==0.20.0
zipp==3.15.0
openpyxl
```

## Usage

### Running the App

To start the Streamlit app, run the following command:

```bash
streamlit run app.py
```

### User Interface Overview

- **URL Input**: Enter multiple URLs in the text area, one URL per line.
- **Start Scraping**: Click the "Start Scraping" button to begin harvesting emails from the entered URLs. The progress bar will indicate the progress.
- **Export Data**: After scraping, download the found email addresses as a CSV or Excel file.
- **View Logs**: Use the sidebar to view logs of the scraping process.
- **Submit Feedback**: Provide feedback or report issues directly from the sidebar.
- **Schedule Scraping**: Schedule scraping tasks to run automatically at 9 AM daily.

### Feedback and Logging

- **Feedback Form**: Available in the sidebar for submitting feedback or reporting issues.
- **Logging**: Logs are automatically created and stored in `scraper.log` in the working directory, recording all scraping activities.

## Security and Legal Considerations

- **Respect Website Terms of Service**: Ensure that your scraping activities comply with the terms of service of the websites you are scraping.
- **Rate Limiting and Captchas**: Implement appropriate measures if you encounter rate limiting or Captchas on target websites.

## Troubleshooting

### Common Issues

- **ModuleNotFoundError**: Ensure all dependencies are installed using the provided `requirements.txt`.
- **Scheduler Not Working**: Verify that `apscheduler` is installed and correctly configured.

### Logs

If you encounter issues, refer to `scraper.log` for detailed logs of the scraping process.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

---

Happy scraping! ⚒️
