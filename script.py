import time
import os

import requests
import requests.auth

from dotenv import load_dotenv

load_dotenv()

AGENT_NAME = f"personal-bot/0.1 by {os.environ['REDDIT_USERNAME']}"
BASE_URL = 'https://oauth.reddit.com'
USER = os.environ['REDDIT_USERNAME']


class Connection:
    def __init__(self):
        self.agent_name = f"personal-bot/0.1 by {os.environ['REDDIT_USERNAME']}"
        self.rate_limit_remaining = None
        self.rate_limit_used = None
        self.rate_limit_reset = None
        self.token = self.get_token()
        self.last_request_response = None
        self.headers = {"Authorization": f"bearer {self.token}", "User-Agent": AGENT_NAME}

    def __str__(self):
        try:
            return f"{self.agent_name=}, {self.token=}, {self.last_request_response=}, " \
                   f"{self.rate_limit_used=}, {self.rate_limit_remaining=}, {self.rate_limit_reset=}"
        except AttributeError as e:
            print(e)
            return f"{self.agent_name=}"

    def get_token(self):
        client_auth = requests.auth.HTTPBasicAuth(
            os.environ['CLIENT_ID'],
            os.environ['CLIENT_SECRET']
        )
        post_data = {
            "grant_type": "password",
            "username": os.environ['REDDIT_USERNAME'],
            "password": os.environ['REDDIT_PASSWORD']
        }
        headers = {"User-Agent": self.agent_name}
        response = self.post_request(
            url="https://www.reddit.com/api/v1/access_token",
            auth=client_auth,
            data=post_data,
            headers=headers,
        )
        return response.json().get('access_token')

    def update_connection(self):
        self.rate_limit_remaining = int(float(self.last_request_response.headers.get('x-ratelimit-remaining', -1)))
        self.rate_limit_reset = int(float(self.last_request_response.headers.get('x-ratelimit-reset', 600)))
        self.rate_limit_used = int(float(self.last_request_response.headers.get('x-ratelimit-used')))

    def is_request_allowed(self):
        if self.rate_limit_remaining is not None and self.rate_limit_remaining <= 0:
            sleep_time = self.rate_limit_reset
            print(f'{sleep_time=}')
            time.sleep(sleep_time)

    def before_request(self):
        self.is_request_allowed()

    def after_request(self, response):
        self.last_request_response = response
        self.update_connection()
        if self.last_request_response.status_code != 200:
            exit(f'ERROR: Status code != 200. {self.__str__()}. {self.last_request_response.headers}')
        print(self.__str__())

    def post_request(self, **kwargs):
        self.before_request()
        response = requests.post(**kwargs)
        self.after_request(response)
        return response

    def get_request(self, **kwargs):
        self.before_request()
        response = requests.get(**kwargs)
        self.after_request(response)
        return response


conn = Connection()


def get_ids_from_response(response):
    ids = list()
    children = response.json().get('data', {}).get('children', [])
    for child in children:
        id_ = child.get('data', {}).get('id')
        ids.append(id_)
    return ids


def get_comments(user):
    params = {
        "limit": 100,
    }
    url = f"{BASE_URL}/user/{user}/comments"
    response = conn.get_request(url=url, params=params, headers=conn.headers)
    return get_ids_from_response(response)


def editusertext(thing_id, new_text='.', is_post=False):
    data = {
        'thing_id': f't3_{thing_id}' if is_post else f't1_{thing_id}',
        'text': new_text,
    }
    url = f"{BASE_URL}/api/editusertext"
    print(f'EDIT: {thing_id=}')
    conn.post_request(url=url, data=data, headers=conn.headers)


def editusertexts(thing_ids, is_post=False):
    for thing_id in thing_ids:
        editusertext(thing_id=thing_id, is_post=is_post)


def delete_thing_id(thing_id, is_post=False):
    data = {
        'id': f't3_{thing_id}' if is_post else f't1_{thing_id}',
    }
    url = f"{BASE_URL}/api/del"
    print(f'DELETE: {thing_id=}')
    conn.post_request(url=url, data=data, headers=conn.headers)


def delete_thing_ids(thing_ids, is_post=False):
    for thing_id in thing_ids:
        delete_thing_id(thing_id=thing_id, is_post=is_post)


def get_posts(user):
    url = f"{BASE_URL}/user/{user}/submitted"
    response = conn.get_request(url=url, headers=conn.headers)
    return get_ids_from_response(response)


def main():
    comment_ids = get_comments(user=USER)
    while comment_ids:
        editusertexts(comment_ids)
        delete_thing_ids(comment_ids)
        comment_ids = get_comments(user=USER)

    post_ids = get_posts(user=USER)
    while post_ids:
        editusertexts(post_ids, is_post=True)
        delete_thing_ids(post_ids, is_post=True)
        post_ids = get_posts(user=USER)


if __name__ == '__main__':
    main()
