from requests_oauthlib import OAuth1Session
import os
import pickle
import configparser


def get_consumer_keys():
    config = get_config()
    return config["consumer_key"], config["consumer_secret"]


def get_config():
    config = configparser.ConfigParser()
    home = os.path.expanduser("~")
    config_path = os.path.join(home, ".config/scrap-journal/config.ini")
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        raise Exception("Config is not found.")
    res = {
        "consumer_key": config["consumer_keys"]["key"],
        "consumer_secret": config["consumer_keys"]["secret"],
        "twitter_name": config["twitter"]["user"],
        "scrapbox_proj": config["scrapbox"]["project"]
    }
    return res


def auth():
    consumer_key, consumer_secret = get_consumer_keys()
    request_token_url = "https://api.twitter.com/oauth/request_token"
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)

    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except ValueError:
        print(
            "There may have been an issue with "
            "the consumer_key or consumer_secret."
        )

    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    print("Got OAuth token: %s" % resource_owner_key)

    # Get authorization
    base_authorization_url = "https://api.twitter.com/oauth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print("Please go here and authorize: %s" % authorization_url)
    verifier = input("Paste the PIN here: ")

    # Get the access token
    access_token_url = "https://api.twitter.com/oauth/access_token"
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    oauth_tokens = oauth.fetch_access_token(access_token_url)
    return oauth_tokens


def get_oauth_tokens():
    oauth_tokens = None
    home = os.path.expanduser("~")
    token_path = os.path.join(home, ".config/scrap-journal/token.pickle")
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            oauth_tokens = pickle.load(token)
    if not oauth_tokens:
        oauth_tokens = auth()
        with open(token_path, "wb") as token:
            pickle.dump(oauth_tokens, token)
    return oauth_tokens


def connect_to_endpoint(oauth_tokens):
    consumer_key, consumer_secret = get_consumer_keys()
    access_token = oauth_tokens["oauth_token"]
    access_token_secret = oauth_tokens["oauth_token_secret"]

    # Make the request
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )
    config = get_config()
    params = {"screen_name": config["twitter_name"], "count": "200"}
    response = oauth.get(
        "https://api.twitter.com/1.1/statuses/user_timeline.json",
        params=params
    )

    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text)
        )

    # print("Response code: {}".format(response.status_code))
    return response.json()


def main():
    oauth_tokens = get_oauth_tokens()
    tweets = connect_to_endpoint(oauth_tokens)
    for tweet in tweets[::-1]:
        print(tweet["text"])
