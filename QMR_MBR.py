import json
import requests
import pandas as pd
import logging
from datetime import datetime , timezone
import os
from path_handler import adjust_path_for_os

class JiraReportGenerator:

    # Specify your download path and output Excel file path here
    download_path = "/home/ANT.AMAZON.COM/avinaks/Downloads"
    output_excel_file = os.path.join(download_path, "report", "output.xlsx")

    def __init__(self, api_url, auth, json_file_path):

        self.api_url = api_url
        self.auth = auth
        self.json_file_path = json_file_path
        self.regression_data = []

    def  calculate_overall_metrics(self, report_layout):
        priorities = ['Blocker', 'Critical', 'Others']

        # Initialize overall values
        overall_resolved = 0
        overall_bugs_raised = 0
        overall_noise_issues = 0
        overall_fixed_issues = 0
        overall_gerrit_issues = 0

        for priority in priorities:
            # Calculate overall resolved issues and bugs raised
            overall_resolved += report_layout.loc['Resolved', ('Regression', priority)] + report_layout.loc['Resolved', ('Exploratory', priority)]
            overall_bugs_raised += report_layout.loc['BugsRaised', ('Regression', priority)] + report_layout.loc['BugsRaised', ('Exploratory', priority)]

            # Calculate overall noise issues
            overall_noise_issues += report_layout.loc['Noise', ('Regression', priority)] + report_layout.loc['Noise', ('Exploratory', priority)]

            # Calculate overall fixed issues and gerrit issues
            overall_fixed_issues += report_layout.loc['Fixed', ('Regression', priority)] + report_layout.loc['Fixed', ('Exploratory', priority)]
            overall_gerrit_issues += report_layout.loc['GerritFix', ('Regression', priority)] + report_layout.loc['GerritFix', ('Exploratory', priority)]

        # Calculate overall percentages using overall values
        overall_noise_percentage = (overall_noise_issues / overall_resolved) * 100
        overall_fixed_percentage = (overall_fixed_issues / overall_resolved) * 100
        overall_gerrit_percentage = (overall_gerrit_issues / overall_resolved) * 100

        # Calculate overall resolution percentage using overall values
        overall_resolution_percentage = (overall_resolved / overall_bugs_raised) * 100

        # Set the overall percentages in the report_layout under the "Overall" category for each priority
        for priority in priorities:
            report_layout.loc["Noise%", ('Overall')] = f"{overall_noise_percentage:.2f}%"
            report_layout.loc["Fixed%", ('Overall')] = f"{overall_fixed_percentage:.2f}%"
            report_layout.loc["Gerrit%", ('Overall')] = f"{overall_gerrit_percentage:.2f}%"
            report_layout.loc["Resolution%", ('Overall')] = f"{overall_resolution_percentage:.2f}%"

    def fetch_and_sort_data(self, jql_query):
        try:
            issues = []
            start_at = 0
            max_results = 100  # Set maxResults to your desired value
            total_issues = None

            while total_issues is None or start_at < total_issues:
                response = requests.get(
                    self.api_url,
                    auth=self.auth,
                    params={'jql': jql_query, 'startAt': start_at, 'maxResults': max_results}
                )
                response.raise_for_status()
                response_data = response.json()

                if total_issues is None:
                    total_issues = response_data.get('total', 0)

                issues.extend(response_data.get('issues', []))
                start_at += max_results

            return issues
        except requests.exceptions.RequestException as e:
            logging.error("Jira API request failed: %s", str(e))
            return []
        
    def fetch_resolution_data(self, jql_query):
        try:
            response = requests.get(
                self.api_url,
                auth=self.auth,
                params={'jql': jql_query}
            )
            response.raise_for_status()
            resolution_data = response.json().get('issues', [])
            return resolution_data
        except requests.exceptions.RequestException as e:
            logging.error("Jira API request failed for Resolution data: %s", str(e))
            return []

    def create_report_layout(self):
        columns = pd.MultiIndex.from_tuples([
            ('Regression', 'Blocker'),
            ('Regression', 'Critical'),
            ('Regression', 'Others'),
            ('Exploratory', 'Blocker'),
            ('Exploratory', 'Critical'),
            ('Exploratory', 'Others'),
            ('Overall', '')],
            names=['Metrics', 'Priority'])

        index = [
            'BugsRaised',
            'Resolved',
            'Fixed',
            'GerritFix',
            'Noise',
            #'Resolution',
            'Noise%',
            'Fixed%',
            'Gerrit%',
            'Resolution%',
            'Resolved-Defect',
            #'Un-resolved-Defect'
        ]

        data = [[0] * len(columns) for _ in range(len(index))]

        df = pd.DataFrame(data, columns=columns, index=index)

        return df

    def validate_report_data(self, report_layout, data, common_sub_queries, start_date, end_date):
        success = True

        for sub_query in common_sub_queries:
            regression_sub_query = data["Regression"].get(sub_query)
            exploratory_sub_query = data["Exploratory"].get(sub_query)

            if regression_sub_query is None:
                logging.error("Regression JQL query for '%s' not found in JSON data.", sub_query)
                success = False
            if exploratory_sub_query is None:
                logging.error("Exploratory JQL query for '%s' not found in JSON data.", sub_query)
                success = False

        return success
    
    def calculate_metrics(self, report_layout):


        priorities = ['Blocker', 'Critical', 'Others']
        possible_resolutions = [
            "Fixed", "Done", "Completed", "Resolved", "Verified", 
            "Implemented", "Closed", "Cannot Reproduce", "Duplicate"
        ]

        for priority in priorities:
            noise_issues = report_layout.loc['Noise', ('Regression', priority)]
            resolved_issues = report_layout.loc['Resolved', ('Regression', priority)]

            # Check if the denominator is not zero before calculating noise_percentage
            if resolved_issues != 0:
                noise_percentage = (noise_issues / resolved_issues) * 100
                report_layout.loc["Noise%", ('Regression', priority)] = f"{noise_percentage:.2f}%"
            else:
                report_layout.loc["Noise%", ('Regression', priority)] = '0.0%'  # Set to 0 if no resolved issues

            fixed_issues = report_layout.loc['Fixed', ('Regression', priority)]
            resolved_issues = report_layout.loc['Resolved', ('Regression', priority)]
            gerrit_issues = report_layout.loc['GerritFix', ('Regression', priority)]

            # Check if the denominator is not zero before calculating percentages
            if resolved_issues != 0:
                fixed_percentage = (fixed_issues / resolved_issues) * 100
                gerrit_percentage = (gerrit_issues / resolved_issues) * 100

                report_layout.loc["Fixed%", ('Regression', priority)] = f"{fixed_percentage:.2f}%"   # Fixed%
                report_layout.loc["Gerrit%", ('Regression', priority)] = f"{gerrit_percentage:.2f}%"  # Gerrit%
            else:
                report_layout.loc["Fixed%", ('Regression', priority)] = '0.0%'  # Set to '0%' if no resolved issues
                report_layout.loc["Gerrit%", ('Regression', priority)] = '0.0%'  # Set to '0%' if no resolved issues

            # Calculate Resolution% as Resolved / BugsRaised
            bugs_raised = report_layout.loc['BugsRaised', ('Regression', priority)]
            resolved_issues = report_layout.loc['Resolved', ('Regression', priority)]

            if bugs_raised > 0:
                resolution_percentage = (resolved_issues / bugs_raised) * 100
            else:
                resolution_percentage = 0

            report_layout.loc["Resolution%", ('Regression', priority)] = f"{resolution_percentage:.2f}%"


           
        # Calculate metrics for "Exploratory" category
        for priority in priorities:
            noise_issues = report_layout.loc['Noise', ('Exploratory', priority)]
            resolved_issues = report_layout.loc['Resolved', ('Exploratory', priority)]

            # Check if the denominator is not zero before calculating noise_percentage
            if resolved_issues != 0:
                noise_percentage = (noise_issues / resolved_issues) * 100
                report_layout.loc["Noise%", ('Exploratory', priority)] = f"{noise_percentage:.2f}%"
            else:
                report_layout.loc["Noise%", ('Exploratory', priority)] = '0.0%'  # Set to 0 if no resolved issues

            fixed_issues = report_layout.loc['Fixed', ('Exploratory', priority)]
            resolved_issues = report_layout.loc['Resolved', ('Exploratory', priority)]
            gerrit_issues = report_layout.loc['GerritFix', ('Exploratory', priority)]

            # Check if the denominator is not zero before calculating percentages
            if resolved_issues != 0:
                fixed_percentage = (fixed_issues / resolved_issues) * 100
                gerrit_percentage = (gerrit_issues / resolved_issues) * 100

                report_layout.loc["Fixed%", ('Exploratory', priority)] = f"{fixed_percentage:.2f}%"   # Fixed%
                report_layout.loc["Gerrit%", ('Exploratory', priority)] = f"{gerrit_percentage:.2f}%"  # Gerrit%
            else:
                report_layout.loc["Fixed%", ('Exploratory', priority)] = '0.0%'  # Set to '0%' if no resolved issues
                report_layout.loc["Gerrit%", ('Exploratory', priority)] = '0.0%'  # Set to '0%' if no resolved issues

            # Calculate Resolution% as Resolved / BugsRaised
            bugs_raised = report_layout.loc['BugsRaised', ('Exploratory', priority)]
            resolved_issues = report_layout.loc['Resolved', ('Exploratory', priority)]

            if bugs_raised > 0:
                resolution_percentage = (resolved_issues / bugs_raised) * 100
            else:
                resolution_percentage = 0

            report_layout.loc["Resolution%", ('Exploratory', priority)] = f"{resolution_percentage:.2f}%"


    def calculate_average_defect_age(self, report_layout, resolved_defect_data, unresolved_defect_data):
        priority_groups = {
            'Blocker': ['Blocker'],
            'Critical': ['Critical'],
            'Others': ['Major', 'Minor', 'Trivial']
        }

        # Initialize dictionaries to store sums and counts for each priority group
        resolved_defect_age_sums = {group: 0 for group in priority_groups}
        unresolved_defect_age_sums = {group: 0 for group in priority_groups}
        resolved_defect_counts = {group: 0 for group in priority_groups}
        unresolved_defect_counts = {group: 0 for group in priority_groups}

        for issue in resolved_defect_data:
            priority = issue['fields']['priority']['name']
            created_date = datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z")
            resolved_date = datetime.strptime(issue['fields']['resolutiondate'], "%Y-%m-%dT%H:%M:%S.%f%z")
            age = (resolved_date - created_date).days
            for group, group_priorities in priority_groups.items():
                if priority in group_priorities:
                    resolved_defect_age_sums[group] += age
                    resolved_defect_counts[group] += 1

        for issue in unresolved_defect_data:
            priority = issue['fields']['priority']['name']
            created_date = datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z")
            age = (datetime.now(timezone.utc) - created_date).days
            for group, group_priorities in priority_groups.items():
                if priority in group_priorities:
                    unresolved_defect_age_sums[group] += age
                    unresolved_defect_counts[group] += 1

        for group in priority_groups:
            resolved_defect_age_avg = resolved_defect_age_sums[group] / max(resolved_defect_counts[group], 1)
            unresolved_defect_age_avg = unresolved_defect_age_sums[group] / max(unresolved_defect_counts[group], 1)

            report_layout.loc["Resolved-Defect", ('Regression', group)] = f"{resolved_defect_age_avg:.2f} "
            report_layout.loc["Un-Resolved-Defect", ('Regression', group)] = f"{unresolved_defect_age_avg:.2f} "

            # Separate calculation and assignment for "Exploratory"
            report_layout.loc["Resolved-Defect", ('Exploratory', group)] = f"{resolved_defect_age_avg:.2f} "
            report_layout.loc["Un-Resolved-Defect", ('Exploratory', group)] = f"{unresolved_defect_age_avg:.2f} "

         # Calculate total averages for both "Regression" and "Exploratory"
        total_resolved_regression_age_sum = sum(resolved_defect_age_sums[group] for group in priority_groups)
        total_unresolved_regression_age_sum = sum(unresolved_defect_age_sums[group] for group in priority_groups)
        total_resolved_regression_count = sum(resolved_defect_counts[group] for group in priority_groups)
        total_unresolved_regression_count = sum(unresolved_defect_counts[group] for group in priority_groups)

        total_resolved_regression_age_avg = total_resolved_regression_age_sum / max(total_resolved_regression_count, 1)
        total_unresolved_regression_age_avg = total_unresolved_regression_age_sum / max(total_unresolved_regression_count, 1)

        # Assign total averages to "Overall" in your layout
        report_layout.loc["Resolved-Defect", ('Overall')] = f"{total_resolved_regression_age_avg:.2f}"
        report_layout.loc["Un-Resolved-Defect", ('Overall')] = f"{total_unresolved_regression_age_avg:.2f}"

        # Similarly, calculate and assign total averages for "Exploratory" in your layout
        total_resolved_exploratory_age_sum = sum(resolved_defect_age_sums[group] for group in priority_groups)
        total_unresolved_exploratory_age_sum = sum(unresolved_defect_age_sums[group] for group in priority_groups)
        total_resolved_exploratory_count = sum(resolved_defect_counts[group] for group in priority_groups)
        total_unresolved_exploratory_count = sum(unresolved_defect_counts[group] for group in priority_groups)

        total_resolved_exploratory_age_avg = total_resolved_exploratory_age_sum / max(total_resolved_exploratory_count, 1)
        total_unresolved_exploratory_age_avg = total_unresolved_exploratory_age_sum / max(total_unresolved_exploratory_count, 1)

        report_layout.loc["Resolved-Defect", ('Overall')] = f"{total_resolved_exploratory_age_avg:.2f}"
        report_layout.loc["Un-Resolved-Defect", ('Overall')] = f"{total_unresolved_exploratory_age_avg:.2f}"

    def calculate_age(self, issue):
        created_date_str = issue['fields']['created']
        resolved_date_str = issue['fields'].get('resolutiondate')  # Use .get() to handle None
        if resolved_date_str:
            created_date = datetime.strptime(created_date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            resolved_date = datetime.strptime(resolved_date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            age = (resolved_date - created_date).days
            return age
        else:
            # Handle the case where 'resolutiondate' is None (not resolved)
            return 0  # You can choose an appropriate value for unresolved issues


    

    
        return f"{age:.2f} days"

    def generate_report(self, start_date, end_date):
        try:
            with open(self.json_file_path, 'r') as json_file:
                data = json.load(json_file)
        except FileNotFoundError as e:
            logging.error("JSON file not found: %s", str(e))
            return

        api_credentials = data["api_credentials"]
        api_username = api_credentials["api_username"]
        api_password = api_credentials["api_password"]
        api_url = api_credentials["api_url"]
        auth = (api_username, api_password)

        common_sub_queries = ["BugsRaised", "Resolved", "Fixed", "GerritFix", "Noise", "Resolution"]

        # Create an empty DataFrame for JQL queries
        jql_queries_data = {
            "Regression": {},
            "Exploratory": {}
        }
        jql_queries_df = pd.DataFrame(jql_queries_data)

        report_layout = self.create_report_layout()

        # Fetch Resolved Defect and Un-Resolved Defect data
        resolved_defect_query = data["Regression"]["Resolved_Defect"].replace("{{start_date}}", start_date).replace("{{end_date}}", end_date)
        unresolved_defect_query = data["Regression"]["Un-Resolved_Defect"].replace("{{start_date}}", start_date).replace("{{end_date}}", end_date)

        resolved_defect_data = self.fetch_and_sort_data(resolved_defect_query)
        unresolved_defect_data = self.fetch_and_sort_data(unresolved_defect_query)

        # Sort the issues based on Priority
        resolved_defect_data.sort(key=lambda x: x['fields']['priority']['name'])
        unresolved_defect_data.sort(key=lambda x: x['fields']['priority']['name'])

        # Calculate defect age for Resolved Defect and Un-Resolved Defect
        for issue in resolved_defect_data:
            created_date = datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z")
            updated_date = datetime.strptime(issue['fields']['updated'], "%Y-%m-%dT%H:%M:%S.%f%z")
            age = (updated_date - created_date).days
            issue['defect_age'] = age

        today = datetime.now(timezone.utc)
        for issue in unresolved_defect_data:
            created_date = datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z")
            age = (today - created_date).days
            issue['defect_age'] = age

        if self.validate_report_data(report_layout, data, common_sub_queries, start_date, end_date):
            for sub_query in common_sub_queries:
                regression_sub_query = data["Regression"][sub_query].replace("{{start_date}}", start_date).replace("{{end_date}}", end_date)
                exploratory_sub_query = data["Exploratory"][sub_query].replace("{{start_date}}", start_date).replace("{{end_date}}", end_date)

                regression_data = self.fetch_and_sort_data(regression_sub_query)
                exploratory_data = self.fetch_and_sort_data(exploratory_sub_query)

                for priority in ['Blocker', 'Critical', 'Others']:
                    if priority == 'Others':
                        priority_issues = [issue for issue in regression_data if issue['fields']['priority']['name'] not in ['Blocker', 'Critical']]
                    else:
                        priority_issues = [issue for issue in regression_data if issue['fields']['priority']['name'] == priority]
                    report_layout.loc[sub_query, ('Regression', priority)] = len(priority_issues)

                    if priority == 'Others':
                        priority_issues = [issue for issue in exploratory_data if issue['fields']['priority']['name'] not in ['Blocker', 'Critical']]
                    else:
                        priority_issues = [issue for issue in exploratory_data if issue['fields']['priority']['name'] == priority]
                    report_layout.loc[sub_query, ('Exploratory', priority)] = len(priority_issues)

                overall_regression = sum(report_layout.loc[sub_query, ('Regression', priority)] for priority in ['Blocker', 'Critical', 'Others'])
                overall_exploratory = sum(report_layout.loc[sub_query, ('Exploratory', priority)] for priority in ['Blocker', 'Critical', 'Others'])
                report_layout.loc[sub_query, ('Overall', '')] = overall_regression + overall_exploratory

                # Fetch Resolution data
                resolution_sub_query = data["Regression"]["Resolution"].replace("{{start_date}}", start_date).replace("{{end_date}}", end_date)
                resolution_data = self.fetch_and_sort_data(resolution_sub_query)

                # Update report layout with Resolution data
                for priority in ['Blocker', 'Critical', 'Others']:
                    # Calculate Resolution%
                    bugs_raised = report_layout.loc['BugsRaised', ('Regression', priority)]
                    resolution_count = len(resolution_data)
                    resolution_percentage = (resolution_count / bugs_raised) * 100

                    # Update the corresponding cell in the DataFrame
                    report_layout.loc["Resolution%", ('Regression', priority)] = resolution_percentage

                    # Update JQL queries DataFrame with actual JQL queries
                    jql_queries_df.loc[sub_query, ('Regression')] = regression_sub_query
                    jql_queries_df.loc[sub_query, ('Exploratory')] = exploratory_sub_query
            
            # Remove the "Resolution" row from the report
            report_layout = report_layout.drop("Resolution", errors='ignore')

            resolved_defect_data = self.fetch_and_sort_data(resolved_defect_query)
            unresolved_defect_data = self.fetch_and_sort_data(unresolved_defect_query)

            # Calculate metrics (Fixed%, Gerrit%, etc.)
            self.calculate_metrics(report_layout)

            # Calculate average defect age for resolved issues
            self.calculate_average_defect_age(report_layout, resolved_defect_data, unresolved_defect_data)

            # Calculate average defect age for unresolved issues
            self.calculate_average_defect_age(report_layout, resolved_defect_data, unresolved_defect_data)

            # Calculate overall percentages for "Fixed%", "Gerrit%", and "Resolution%"
            self.calculate_overall_metrics(report_layout) 

            # Remove "days" from defect age values
            report_layout = report_layout.applymap(lambda x: str(x).rstrip("days"))

            # Handle "nan%" issue by replacing "nan" with an empty string
            report_layout = report_layout.fillna('')



            print(report_layout)
            

            # Save the report as an Excel file
            report_filename = "/home/ANT.AMAZON.COM/avinaks/Downloads/Report_Script/report.xlsx"
            report_layout.to_excel(report_filename)
            print(f"Report saved to {report_filename}")

            # Save JQL queries as an Excel file
            jql_queries = {
                "Regression": data["Regression"],
                "Exploratory": data["Exploratory"]
            }
            jql_queries_df = pd.DataFrame(jql_queries)
            jql_queries_filename = "/home/ANT.AMAZON.COM/avinaks/Downloads/Report_Script/jql_queries.xlsx"
            jql_queries_df.to_excel(jql_queries_filename, index=False)
            print(f"JQL queries saved to {jql_queries_filename}")

            

        else:
            logging.error("Validation failed. Please check the errors in the log.")

def main():
    logging.basicConfig(level=logging.ERROR)  # Configure logging
    #json_file_path = "/home/ANT.AMAZON.COM/avinaks/Downloads/Report_Script/queries.json"
    json_file_path = adjust_path_for_os("/home/ANT.AMAZON.COM/avinaks/Downloads/Report_Script/queries.json")

    api_credentials = None
    try:
        with open(adjust_path_for_os(json_file_path), 'r') as json_file:

            data = json.load(json_file)
            api_credentials = data["api_credentials"]
    except FileNotFoundError as e:
        logging.error("JSON file not found: %s", str(e))    
        return
    except KeyError:
        logging.error("API credentials not found in JSON data.")
        return

    api_username = api_credentials["api_username"]
    api_password = api_credentials["api_password"]
    api_url = api_credentials["api_url"]

    auth = (api_username, api_password)

    # Print the Username and Adjusted Path from the path_handler module
    print(f"Username: {os.getlogin()}")
    print(f"Adjusted Path: {json_file_path}")


    jira_report_generator = JiraReportGenerator(api_url, auth, json_file_path)
    start_date = input("Enter start date (YYYY-MM-DD): ")
    end_date = input("Enter end date (YYYY-MM-DD): ")

    jira_report_generator.generate_report(start_date, end_date)

if __name__ == "__main__":
    main()
