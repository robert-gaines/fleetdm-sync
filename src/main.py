from argparse import ArgumentParser
from queries import Queries
import requests
import logging
import urllib3
import yaml
import sys
import re
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)

class FleetDM():

    def __init__(self, token:str) -> None:
        self.filename = 'configuration.yaml'
        if self.check_file_presence(self.filename):
            logging.info("Found configuration file")
            self.fqdn = ""
            self.port = ""
            self.token = token
            self.parse_config()
            self.url = "https://{0}:{1}/api/v1/fleet/".format(self.fqdn, self.port)
            self.headers = {"Authorization": "Bearer {0}".
                            format(self.token),
                            'Content-Type': 'application/json'}
            self.Session = requests.Session()
            self.Session.headers.update(self.headers)
            self.get_host_count()
            self.query = Queries(self.Session, self.url)

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
        
    def parse_config(self) -> None:
        try:
            with open(self.filename, 'r') as file_handle:
                self.configuration = yaml.safe_load(file_handle)
                self.configuration = self.configuration['configuration']
                self.fqdn = self.configuration['fqdn']
                self.port = self.configuration['port']
        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))

def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("-phq", "--push-queries", action='store_true')
    parser.add_argument("-plq", "--pull-queries", action='store_true')
    parser.add_argument("-snq", "--sync-queries", action='store_true')
    parser.add_argument("-gqi", "--generate-query-id", action='store_true')
    parser.add_argument("-dq", "--delete-query")
    parser.add_argument("-t", "--token")
    args = parser.parse_args()
    token = args.token
    push_queries = args.push_queries
    pull_queries = args.pull_queries
    sync_queries = args.sync_queries
    gen_query_id = args.generate_query_id
    query_to_be_deleted = args.delete_query
    if token:
        session = FleetDM(token)
        session.get_host_count()
        if query_to_be_deleted:
            logging.info("Pulling queries into local repository")
            session.query.delete_query(query_to_be_deleted)
        if push_queries:
            logging.info("Pushing local queries to the application")
            current_queries = session.query.retrieve_queries()
            session.query.delete_all_queries(current_queries)
            current_queries = session.query.retrieve_queries()
            updates = session.query.identify_query_deltas(current_queries)
            if updates:
                session.query.push_query_updates(updates)
            candidates = session.query.identify_new_queries(current_queries)
            if candidates:
                session.query.create_new_queries(candidates)
        if pull_queries:
            session.query.export_queries()
        if sync_queries:
            logging.info("Synchronizing queries")
            current_queries = session.query.retrieve_queries()
            session.query.remove_nonexistent_queries(current_queries)
            updates = session.query.identify_query_deltas(current_queries)
            if updates:
                session.query.push_query_updates(updates)
            candidates = session.query.identify_new_queries(current_queries)
            if candidates:
                session.query.create_new_queries(candidates)
        if gen_query_id:
            logging.info("Generating a new query ID")
            current_queries = session.query.retrieve_queries()
            id = session.query.generate_new_query_id(current_queries)
            logging.info("New query ID: {0}".format(id))

    else:
        logging.error("Failed to supply an API token")
        return

if __name__ == '__main__':
    main()
