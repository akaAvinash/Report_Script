 # Jira QMR Report Generator

This Python script generates a QMR  report based on JQL queries defined in a JSON file. 

## Installation

To install the required dependencies, run:

```
pip install -r requirements.txt
```

## Usage

1. Create a JSON file with the following structure:

```json
{
    "api_credentials": {
        "api_username": "your_username",
        "api_password": "your_password",
        "api_url": "https://your_jira_instance/rest/api/latest/search"
    },
    "Regression": {
        "BugsRaised": "labels in (vega-ta) AND labels in (vega-ta-stability) AND type = Bug AND project != \"Lab Management Services (LMS)\" AND labels in (vega-ta-reg) AND created > \"{{start_date}}\" AND created <= \"{{end_date}}\" ORDER BY priority DESC",
        "Resolved": "issuetype = Bug AND status in (Closed, Resolved) AND labels in (vega-ta) AND labels in (vega-ta-stability) AND type = Bug AND project != \"Lab Management Services (LMS)\" AND labels in (vega-ta-reg) AND created > \"{{start_date}}\" AND created <= \"{{end_date}}\"",
        "Fixed": "issuetype = Bug AND project != \"Lab Management Services (LMS)\" AND created >= \"{{start_date}}\" AND created <= \"{{end_date}}\" AND labels = \"vega-ta\" AND labels in (vega-ta-stability) AND resolution = \"Fixed\"",
        "GerritFix": "issuetype = Bug AND labels in (vega-ta) AND labels in (vega-ta-stability) AND labels in (\"dosta-gerrit\", \"Dosta-gerrit\") AND type = Bug AND project != \"Lab Management Services (LMS)\" AND labels in (vega-ta-reg) AND created > \"{{start_date}}\" AND created <= \"{{end_date}}\"",
        "Noise": "issuetype = Bug AND labels in (vega-ta) AND labels in (vega-ta-stability) AND type = Bug AND project != \"Lab Management Services (LMS)\" AND labels in (vega-ta-reg)
