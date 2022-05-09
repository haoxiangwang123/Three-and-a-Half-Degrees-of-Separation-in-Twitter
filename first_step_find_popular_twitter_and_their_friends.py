import requests
import re
import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
import twitter
from functools import partial
import os

def most_popular_twitter_account_1(page_limit = 40):
    # Use requests and re to find the most popular twitter accounts from 
    # https://www.trackalytics.com/the-most-followed-twitter-profiles/page/1/
    # One page has 25 accounts. Forty pages have 1000 accounts.
    popular_accounts = []
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE'}
    for page_number in range(page_limit):
        url = 'https://www.trackalytics.com/the-most-followed-twitter-profiles/page/' + str(page_number) + '/'
        html = requests.get(url, headers = headers)
        html_text = html.text
        results = re.findall(r'<td><a title=', html_text)
        for result in results:
            popular_accounts += result[14:-1]
    return popular_accounts

def most_popular_twitter_account_2(page_limit = 40, path = '/Users/haoxiangwang/Desktop/Courses/DataMining/Term Project/htmls/'):
    # Due to access restrictions, use re to find the most popular  
    # twitter accounts from the pre-downloaded html documents.
    # One page has 25 accounts. Forty pages have 1000 accounts.
    popular_accounts = []
    for page_number in range(1, page_limit + 1):
        f = open(path + 'page_' + str(page_number) + '.html', 'r', encoding = 'ISO-8859-1')
        for line in f.readlines():
            obj = re.search(r'href=\"https://www.trackalytics.com/twitter/profile/.*/\"', line)
            if obj != None:
                popular_accounts.append(line[obj.span()[0] + 51 : obj.span()[1] - 2])
        f.close()
    return popular_accounts

#Python code from Chapter 9 of Mining the Social Web, 3rd Ed.
def oauth_login():
    # XXX: Go to http://twitter.com/apps/new to create an app and get values
    # for these credentials that you'll need to provide in place of these
    # empty string values that are defined as placeholders.
    # See https://developer.twitter.com/en/docs/basics/authentication/overview/oauth
    # for more information on Twitter's OAuth implementation.
    
    CONSUMER_KEY = 'IHk7dQvEG7vkbLfDCC8EO7inz'
    CONSUMER_SECRET = '6nyXtofsflGLnx4njMKRQjPg5pqapklJYolYdAJ1Tt7TouibkW'
    OAUTH_TOKEN = '1487077364018339843-DYtli6994rJl8ngt44dZvl7H1glVfO'
    OAUTH_TOKEN_SECRET = '3WH4HzjU4hXvOtPxJTKYrox54kr8tQe0HIwy1pxtYaTiJ'
    
    auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                               CONSUMER_KEY, CONSUMER_SECRET)
    
    twitter_api = twitter.Twitter(auth=auth)
    return twitter_api


#Python code from Chapter 9 of Mining the Social Web, 3rd Ed.
def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw): 
    
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
    
        if wait_period > 3600: # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e
    
        # See https://developer.twitter.com/en/docs/basics/response-codes
        # for common codes
    
        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429: 
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...ZzZ...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print('...ZzZ...Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'                  .format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    # End of nested helper function
    
    wait_period = 2 
    error_count = 0 

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0 
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("BadStatusLine encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise

# Python code from Chapter 9 of Mining the Social Web, 3rd Ed.
def get_friends_followers_ids(twitter_api, screen_name = None, user_id = None,
                              friends_limit = 5000, followers_limit = 5000):
    
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None),     "Must have screen_name or user_id, but not both"
    
    # See http://bit.ly/2GcjKJP and http://bit.ly/2rFz90N for details
    # on API parameters
    
    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, 
                              count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, 
                                count=5000)

    friends_ids, followers_ids = [], []
    
    for twitter_api_func, limit, ids, label in [
                    [get_friends_ids, friends_limit, friends_ids, "friends"], 
                    [get_followers_ids, followers_limit, followers_ids, "followers"]
                ]:
        
        if limit == 0: continue
        
        cursor = -1
        while cursor != 0:
        
            # Use make_twitter_request via the partially bound callable...
            if screen_name: 
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else: # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']
        
            print('Fetched {0} total {1} ids for {2}'.format(len(ids), label, (user_id or screen_name)),file=sys.stderr)
        
            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances
        
            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]

if __name__ == '__main__':
    twitter_api = oauth_login()

    # Get the most popular 1000 twitter accounts name
    most_popular_twitter_accounts = most_popular_twitter_account_2()

    # Get the most popular 1000 twitter accounts id
    most_popular_twitter_ids = []
    for account in most_popular_twitter_accounts:
        try:
            most_popular_twitter_ids.append(str(twitter_api.users.show(screen_name = account)['id']))
        except:
            continue
    print(most_popular_twitter_ids)
    
    # Find the popular friends of these popular twitter
    current_path = os.path.dirname(__file__)
    file_name = current_path + '/data/popular_twitter_friends.txt'
    f = open(file_name, 'w')

    for id in most_popular_twitter_ids[1:]:
        f.write(str(id) + ': ')
        friends, _ = get_friends_followers_ids(twitter_api, user_id = id, friends_limit = 1000000, followers_limit = 0)
        for friend in friends:
            if str(friend) in most_popular_twitter_ids:
                f.write(str(friend) + ' ')
        print('')
    
    f.close()
