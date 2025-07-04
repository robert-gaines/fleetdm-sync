from argparse import ArgumentParser
import requests
import logging
import urllib3
import json
import yaml
import sys
import re
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)

class FleetManager():

    def __init__(self, token:str) -> None:
        self.filename = 'configuration.yaml'
        if self.check_file_presence(self.filename):
            logging.info("Found configuration file")
            self.fqdn = ""
            self.port = ""
            self.token = token
            self.parse_config(self.filename)
            self.url = "https://{0}:{1}/api/v1/fleet/".format(self.fqdn, self.port)
            self.headers = {"Authorization": "Bearer {0}".
                            format(self.token),
                            'Content-Type': 'application/json'}
            self.Session = requests.Session()
            self.Session.headers.update(self.headers)
            self.get_host_count()

    def check_file_presence(self, filename: str) -> bool:
        if os.path.exists(filename):
            return True
        else:
            return False
        
    def remove_characters(self, input: str) -> str:
        try:
            res = re.sub(r'[^a-zA-Z0-9]', '_', input)
            return res
        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))
            return None
        
    def get_host_count(self) -> None:
        url = self.url + 'hosts/count'
        try:
            response = self.Session.get(url, verify=False)
            if response.status_code == 200:
                logging.info("Credentials are valid")
                logging.info("Currently managing {0} hosts".format(response.json()['count']))
            else:
                logging.info("Invalid API key")
                sys.exit()
        except requests.exceptions.RequestException as e:
            logging.exception("Request exception raised: {0}".format(e))

    def retrieve_queries(self) -> None:
        url = self.url + "queries"
        queries = {}
        try:
            response = self.Session.get(url, verify=False)
            if response.status_code == 200:
                logging.info("Succesfully retrieved {0} queries".format(
                    len(response.json()['queries'])))
                for query in response.json()['queries']:
                    queries[query['id']] = query
            else:
                logging.info("Failed to retrieve queries")
        except requests.exceptions.RequestException as e:
            logging.exception("Request exception raised: {0}".format(e))
        finally:
            return queries

    def export_queries(self) -> None:
        current_directory = os.getcwd()
        url = self.url + "queries"
        try:
            os.chdir("../queries")
            logging.info(os.getcwd())
            response = self.Session.get(url, verify=False)
            if response.status_code == 200:
                logging.info("Exporting {0} queries".format(
                    len(response.json()['queries'])))
                for query in response.json()['queries']:
                    sanitized = self.remove_characters(query['name']).lower()
                    filename = sanitized + '.yaml'
                    with open(filename, 'w') as fileobj:
                        yaml.dump(query, fileobj)
                logging.info("Finished query export")
            else:
                logging.info("Failed to retrieve queries")
        except requests.exceptions.RequestException as e:
            logging.exception("Request exception raised: {0}".format(e))
        finally:
            os.chdir(current_directory)

    def identify_query_deltas(self, queries: dict):
        current_directory = os.getcwd()
        updates = {}
        try:
            os.chdir('../queries')
            for file in os.listdir():
                with open(file, 'r') as file_obj:
                    convert_to_json = yaml.safe_load(file_obj)
                    if convert_to_json['id'] in queries.keys():
                        if convert_to_json == queries[convert_to_json['id']]:
                            logging.info("NO CHANGE")
                        else:
                            logging.info("QUERY {0} CHANGED ".format(convert_to_json['id']))

        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))
        finally:
            os.chdir(current_directory)
        
    def parse_config(self, filename: str) -> None:
        try:
            with open(self.filename, 'r') as file_handle:
                self.configuration = yaml.safe_load(file_handle)
                self.configuration = self.configuration['configuration']
                self.fqdn = self.configuration['fqdn']
                self.port = self.configuration['port']
        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))

def main():
    parser = ArgumentParser()
    parser.add_argument("-ph", "--push")
    parser.add_argument("-pl", "--pull")
    parser.add_argument("-t", "--token")
    args = parser.parse_args()
    token = args.token
    if token:
        session = FleetManager(token)
        # session.export_queries()
        queries = session.retrieve_queries()
        # for entry in queries.keys():
        #     logging.info(entry)
        #     logging.info(queries[entry])
        #     logging.info('\n')
        session.identify_query_deltas(queries)
    else:
        logging.error("Failed to supply an API token")
        return

if __name__ == '__main__':
    main()
