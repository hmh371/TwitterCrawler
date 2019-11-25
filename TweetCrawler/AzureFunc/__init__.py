"""
Created on Wed Sep 25 17:12:47 2019

@author: Hsia-Ming Hsu
"""

#import time
import tweepy
import pyodbc
import logging
import azure.functions as func
		
### connect to Azure dB
server = '<servername>'
database = '<database>'
username = '<username>'
password = '<password>'
driver= '{ODBC Driver 17 for SQL Server}'
cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)
cursor = cnxn.cursor()
sql = "Insert into twitterdata(twitter_id, follower_id, tweet_id, tweet_text) values(?, ?, ?, ?)"


### Twitter API setting for authorized
consumer_key = "<consumer_key>"
consumer_secret = "<consumer_secret>"
access_key = "<access_key>"
access_secret = "<access_secret>"


### Twitter Scripter main func
def get_all_tweets(cursor, screen_name):
	#Twitter only allows access most recent 3240 tweets from a user in this way
	
	#authorize twitter, initialize tweepy
	auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
	auth.set_access_token(access_key, access_secret)
	api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, compression=True)
        
	twitter_user_name = screen_name # test ID: 821551658970726400 username: ChristineNEvans
	Max_fid_num = 100 # max parsing followers number
	Max_tweet_num = 20 # max parsing tweets number 
    
	per_count_num = 10
	c = tweepy.Cursor(api.followers_ids, id = twitter_user_name)
	
	#initialize
	ids = [] # for followers ids
	outtweets = [] # initialize a list to hold all the tweepy Tweets
	fid_count = 0 # for counting
    
	for page in c.pages():
		ids.append(page)
		#time.sleep(60)
	
	for fids in ids:
	    # for follower number control        
		if fid_count > Max_fid_num :
			break
		
		for fid in fids:
			fid_count += 1
			if fid_count > Max_fid_num :
				break
			
			follower = api.get_user(fid)
			#print(fid_count, " follower id =", fid ," screen name =", follower.screen_name)

			alltweets = []	
        	
        	# make initial request for most recent tweets (Max_tweet_num is the maximum allowed count)
        	# and skip unauthorithized access followers
			try:
				new_tweets = api.user_timeline(screen_name = follower.screen_name, count = per_count_num)
			except tweepy.TweepError:
				print("This follower's tweets is not available. Skipping...")
				continue
        	
        	#save most recent tweets
			alltweets.extend(new_tweets)
        	
        	#save the size of tweets too large to access or not
			try:
				oldest = alltweets[-1].id - 1
			except:
				print("This follower's tweets is not available II. Skipping...")
				continue
        	
        	#keep grabbing tweets until there are no tweets left to grab
			tweet_count = 0
			Max_fid_num2 = (Max_tweet_num - per_count_num) / 10
            
			while len(new_tweets) > 0:
				tweet_count += 1
				if tweet_count > Max_fid_num2 :
					break
				print ("    getting tweets before %s" % oldest)
        		
        		#all subsiquent requests use the max_id param to prevent duplicates
				new_tweets = api.user_timeline(screen_name = follower.screen_name,count = per_count_num,max_id=oldest)
				alltweets.extend(new_tweets) #save most recent tweets
				oldest = alltweets[-1].id - 1 #update the id of the oldest tweet less one
				print ("    ...%s tweets downloaded so far" % len(alltweets))
        	
        	#transform the tweepy tweets into a 2D array that will populate the csv	
			outtweets_temp = [[twitter_user_name, tweet.user.id, tweet.id_str, tweet.text.encode("utf-8")] for tweet in alltweets]
			cursor.execute(sql, outtweets_temp[-1]);
			cnxn.commit()
			outtweets.extend(outtweets_temp)
        	pass

	return outtweets

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        # read from the output from get_all_tweets func & store into s 
        res = get_all_tweets(cursor, name)
        s = name + "\n"
        for row in res:
            for word in row:
                s = s + str(word) + ","
            s = s[:-1] + "\n"
        
        #return output through HTTPResponse to browser
        #return func.HttpResponse(f"Script twitter ID: {s}!")
        return func.HttpResponse(
             "The parsed results are stored into Azure database..." + "\n" + "\n" + 
             "And each tweet be shown in each row with the following format:" + "\n" +
             "twitter_id,follower_id,tweet_id,tweet_text" + "\n" +
             "@by Mike" + "\n" + "\n" +
             f"Script twitter ID: {s}!"
        )
    else:
        return func.HttpResponse(
             "Welcome to Twitter Scripter !!!" + "\n" + "\n" +
             "Please enter a twitter ID or user name on the query string (the end of the URL)" + "\n" +
             "from twitter name e.g.1: https://...==&name=ChristineNEvans" + "\n" +
             "from twitter ID   e.g.2: https://...==&name=92454905" + "\n" + "\n" +
             "After enter the query through URL HTTPtrigger, please wait 2~3 minutes and thanks for your time." + "\n" +
             "@by Mike"
        )
