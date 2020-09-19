import argparse
import configparser
import datetime
import os
import pickle

from requests_oauthlib import OAuth1Session


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


def fetch_tweets(oauth_tokens, latest=None):
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
    if latest is not None:
        params["since_id"] = str(latest)
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


def process_tweet(tweet):
    text = tweet["text"]
    dt_utc = datetime.datetime.strptime(tweet["created_at"],
                                        "%a %b %d %H:%M:%S %z %Y")
    tz_jst = datetime.timezone(datetime.timedelta(hours=9))
    dt_jst = dt_utc.astimezone(tz_jst)
    time_str = dt_jst.strftime("%H:%M")
    return generate_output(text, time_str)


def process_tweets(tweets):
    events = map(lambda t: process_tweet(t), reversed(tweets))
    return "\n".join(events)


def add_indent(line, line_number):
    indent = "  " if line_number > 0 else " "
    return indent + line


def generate_output(text, time):
    lines = text.split("\n")
    lines[0] = "{}（{}）".format(lines[0], time)
    return "\n".join([add_indent(li, i) for i, li in enumerate(lines)])


def convert_to_scrapbox(output):
    return


def get_history():
    home = os.path.expanduser("~")
    history_path = os.path.join(home, ".config/scrap-journal/history.pickle")
    if os.path.exists(history_path):
        with open(history_path, "rb") as hist:
            history = pickle.load(hist)
        return history
    else:
        return None


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-a", "--all",
                           help="display as many tweets as possible.",
                           action="store_true")
    argparser.add_argument("-r", "--raw",
                           help="display to stdout.",
                           action="store_true")
    args = argparser.parse_args()

    oauth_tokens = get_oauth_tokens()
    history = get_history()
    if history is not None and not args.all:
        tweets = fetch_tweets(oauth_tokens, latest=history)
    else:
        tweets = fetch_tweets(oauth_tokens)
    if len(tweets) == 0:
        print("No new tweets")
        return
    output = process_tweets(tweets)

    latest = tweets[0]["id"]
    home = os.path.expanduser("~")
    history_path = os.path.join(home, ".config/scrap-journal/history.pickle")
    if not args.all:
        with open(history_path, "wb") as hist:
            pickle.dump(latest, hist)

    if args.raw:
        print(output)
    else:
        convert_to_scrapbox(output)
