import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
import twitter
from functools import partial
import os
import random

# Python code from Chapter 9 of Mining the Social Web, 3rd Ed.
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
def get_user_profile(twitter_api, screen_names=None, user_ids=None):
   
    # Must have either screen_name or user_id (logical xor)
    assert (screen_names != None) != (user_ids != None),     "Must have screen_names or user_ids, but not both"
    
    items_to_info = {}

    items = screen_names or user_ids
    
    while len(items) > 0:

        # Process 100 items at a time per the API specifications for /users/lookup.
        # See http://bit.ly/2Gcjfzr for details.
        
        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, 
                                            screen_name=items_str)
        else: # user_ids
            response = make_twitter_request(twitter_api.users.lookup, 
                                            user_id=items_str)
    
        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else: # user_ids
                items_to_info[user_info['id']] = user_info

    return items_to_info


# Python code from Chapter 9 of Mining the Social Web, 3rd Ed.
def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=5000, followers_limit=5000):
    
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
        
            #print('Fetched {0} total {1} ids for {2}'.format(len(ids), label, (user_id or screen_name)),file=sys.stderr)
        
            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances
        
            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]

def crawl_popular_friends_followers(twitter_api, seed_id, popular_ids, neighbour_ids, limit = 3):
    
    # Use BFS to find popular twitter friends/followers of a twitter
    # To get the shorter distance, I find 3 popular twitter friends/followers of a twitter
    next_queue = [{"id" : str(id), "distance" : 1} for id in neighbour_ids]
    popular_friends_follows = [{"id": str(id), "distance": 1} for id in neighbour_ids if str(id) in popular_ids]
    
    while len(popular_friends_follows) < limit:
        (queue, next_queue) = (next_queue, [])
        for element in queue:
            friends_ids, followers_ids = get_friends_followers_ids(twitter_api, user_id = element["id"])
            next_queue += [{"id" : id, "distance" : element["distance"] + 1} for id in friends_ids + followers_ids]
            popular_friends_follows += [{"id" : str(id), "distance" : element["distance"] + 1} for id in friends_ids + followers_ids if str(id) in popular_ids]

            if len(popular_friends_follows) >= limit:
                return popular_friends_follows
    
    return popular_friends_follows

# Main function
if __name__ == '__main__':

    current_path = os.path.dirname(__file__)

    # Load the id of popular twitters
    file_name = current_path + '/data/popular_network_nodes.txt'
    f = open(file_name, 'r')
    line = f.readline()
    popular_ids = line.rstrip('\n').split(' ')
    if popular_ids[-1] == '':
        popular_ids.pop(-1)
    f.close()

    # Load the shortest distance between any two popular twitters
    file_name = current_path + '/data/popular_network_shortest_distance_matrix.txt'
    f = open(file_name, 'r')
    popular_network = []
    for line in f.readlines():
        row = line.rstrip('\n').split(' ')
        if row[-1] == '':
            row.pop(-1)
        row = [int(element) for element in row]
        popular_network.append(row)
    f.close()

    # Load some twitter ids in this world
    file_name = current_path + '/data/user_ids.txt'
    f = open(file_name, 'r')
    user_ids = []
    for line in f.readlines():
        line = line.rstrip('\n')
        user_ids.append(line)
    f.close()

    file_name = current_path + '/data/user_distance.txt'
    f = open(file_name, 'w')

    twitter_api = oauth_login()

    user_profile = get_user_profile(twitter_api, user_ids = user_ids)

    addUp = {}

    # Get the shortest distance between 300 random pairs of twitter
    for i in range(300):
        id_1 = user_ids[random.randint(0, len(user_ids) - 1)]
        friends_ids_1, followers_ids_1 = get_friends_followers_ids(twitter_api, user_id = id_1)
        # If the account is inactive remove it
        while len(friends_ids_1) + len(followers_ids_1) < 20:
            id_1 = user_ids[random.randint(0, len(user_ids))]
            friends_ids_1, followers_ids_1 = get_friends_followers_ids(twitter_api, user_id = id_1)

        id_2 = user_ids[random.randint(0, len(user_ids) - 1)]
        friends_ids_2, followers_ids_2 = get_friends_followers_ids(twitter_api, user_id = id_2)
        # If the account is inactive remove it
        while len(friends_ids_2) + len(followers_ids_2) < 20:
            id_2 = user_ids[random.randint(0, len(user_ids))]
            friends_ids_2, followers_ids_2 = get_friends_followers_ids(twitter_api, user_id = id_2)

        # Find their 3 popular twitter friends/followers
        id_1_popular_friends_followers = crawl_popular_friends_followers(twitter_api, id_1, popular_ids, neighbour_ids = friends_ids_1 + followers_ids_1, limit = 3)
        id_2_popular_friends_followers = crawl_popular_friends_followers(twitter_api, id_2, popular_ids, neighbour_ids = friends_ids_2 + followers_ids_2, limit = 3)

        # Find the shortest path between id_1 and id_2
        shortest_distance = 999999
        for id_1_popular in id_1_popular_friends_followers:
            for id_2_popular in id_2_popular_friends_followers:
                distance_1_to_popular_network = id_1_popular["distance"]
                distance_2_to_popular_network = id_2_popular["distance"]
                distance_in_popular_network = popular_network[popular_ids.index(id_1_popular["id"])][popular_ids.index(id_2_popular["id"])]
                distance = distance_1_to_popular_network + distance_2_to_popular_network + distance_in_popular_network
                if distance < shortest_distance:
                    shortest_distance = distance
    
        print('Distance between', id_1, 'and', id_2, 'is', shortest_distance)
        f.write('Distance between ' + id_1 + ' and ' + id_2 + ' is ' + str(shortest_distance) + '\n')
        if shortest_distance in addUp.keys():
            addUp[shortest_distance] += 1
        else:
            addUp[shortest_distance] = 1
    
        print(addUp)

    f.close()