import requests
import logging
import urllib3
import random
import glob
import yaml
import os
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)

class Queries():

    def __init__(self, session: object, url: str):
        self.session = session
        self.url = url
    
    def remove_characters(self, input: str) -> str:
        try:
            res = re.sub(r'[^a-zA-Z0-9]', '_', input)
            return res
        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))
            return None
        
    def remove_current_queries(self) -> None:
        """ Remove current query files """
        for target in glob.glob("*.yaml"):
            os.remove(target)
        for target in glob.glob("*.yml"):
            os.remove(target)

    def retrieve_queries(self) -> None:
        url = self.url + "queries"
        queries = {}
        try:
            response = self.session.get(url, verify=False)
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
        
    def generate_new_query_id(self, queries: dict) -> int:
        id = list(queries.keys())[-1]
        id += 1
        if id not in queries.keys():
            return id
        else:
            while id in queries.keys():
                id = random.randint(1,1000000)
                if id not in queries.keys():
                    return id

    def export_queries(self) -> None:
        current_directory = os.getcwd()
        url = self.url + "queries"
        try:
            os.chdir("../queries")
            response = self.session.get(url, verify=False)
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

    def identify_query_deltas(self, queries: dict) -> dict:
        ''' Retrieve queries identify changes in the local definition files '''
        current_directory = os.getcwd()
        updates = {}
        try:
            os.chdir('../queries')
            for file in os.listdir():
                with open(file, 'r') as file_obj:
                    convert_to_json = yaml.safe_load(file_obj)
                    if convert_to_json['id'] in queries.keys():
                        if convert_to_json != queries[convert_to_json['id']]:
                            logging.info("Change detected in {0}".format(convert_to_json['id']))
                            updates[convert_to_json['id']] = convert_to_json
            if len(updates.keys()) < 1:
                logging.info("No query deltas identified")
        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))
        finally:
            os.chdir(current_directory)
            return updates
        
    def identify_new_queries(self, queries: dict) -> dict:
        ''' Identify queries that are not currently present within the application '''
        current_directory = os.getcwd()
        candidates = {}
        try:
            os.chdir('../queries')
            for file in os.listdir():
                with open(file, 'r') as file_obj:
                    convert_to_json = yaml.safe_load(file_obj)
                    if convert_to_json['id'] not in queries.keys():
                        logging.info("New query identified: {0}".format(convert_to_json['id']))
                        candidates[convert_to_json['id']] = convert_to_json
            if len(candidates.keys()) < 1:
                logging.info("No new queries identified")
        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))
        finally:
            os.chdir(current_directory)
            return candidates
        
    def remove_nonexistent_queries(self, queries: dict) -> dict:
        ''' Identify queries that are not currently present within the application '''
        current_directory = os.getcwd()
        local_queries = []
        try:
            os.chdir('../queries')
            for file in os.listdir():
                with open(file, 'r') as file_obj:
                    convert_to_json = yaml.safe_load(file_obj)
                    local_queries.append(convert_to_json['id'])
            for id in queries.keys():
                if id not in local_queries:
                    logging.info("Query {0} is no longer present locally".format(id))
                    self.delete_query(id)
        except Exception as e:
            logging.exception("Exception raised: {0}".format(e))
        finally:
            os.chdir(current_directory)
        
    def push_query_updates(self, updates: dict) -> None:
        ''' Push updated queries to FleetDM '''
        current_directory = os.getcwd()
        os.chdir('../queries')
        for id in updates.keys():
            query_id = id
            query_body = updates[id]
            url = self.url + "queries/{0}".format(query_id)
            try:
                response = self.session.patch(url=url,json=query_body)
                if response.status_code == 200:
                    logging.info("Successfully updated query ID: {0}".format(query_id))
                else:
                    logging.error("Failed to update query ID: {0}".format(query_id))
            except requests.exceptions.RequestException as e:
                logging.exception("Exception raised: {0}".format(e))
        self.remove_current_queries()
        self.export_queries()
        os.chdir(current_directory)

    def create_new_queries(self, candidates: dict) -> None:
        ''' Create new queries in FleetDM '''
        current_directory = os.getcwd()
        os.chdir('../queries')
        for id in candidates.keys():
            query_id = id
            query_body = candidates[id]
            logging.info("Removing placeholder query ID")
            query_body.pop('id')
            url = self.url + "queries"
            try:
                response = self.session.post(url=url,json=query_body)
                if response.status_code == 200:
                    new_id = response.json()['query']['id']
                    logging.info("Successfully created query ID: {0}".format(new_id))
                    self.remove_current_queries()
                    self.export_queries()
                else:
                    logging.error("Failed to create query ID: {0}".format(query_id))
                    logging.error(response.json()['message'])
            except requests.exceptions.RequestException as e:
                logging.exception("Exception raised: {0}".format(e))
        os.chdir(current_directory)

    def delete_query(self, query_id: int) -> None:
        ''' Delete query by ID '''
        url = self.url + "queries/id/{0}".format(query_id)
        try:
            response = self.session.delete(url=url)
            if response.status_code == 200:
                logging.info("Succesffully deleted: {0}".format(query_id))
            else:
                logging.error("Failed to delete query ID: {0}".format(query_id))
        except requests.exceptions.RequestException as e:
            logging.exception("Exception raised: {0}".format(e))

    def delete_all_queries(self, queries: dict) -> None:
        ''' Delete all queries within the application '''
        logging.info("Removing all existing queries")
        for query_id in queries.keys():
            self.delete_query(query_id)
        
