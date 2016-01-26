Tweet Word Counter
==================

Tweet Word Counter is a simple word counting program which reads the Twitter tweet stream and keeps a count of the number occurences of each word.

## Getting started

Follow the steps below to try out the Tweet Word Counter:

* Get the source code by cloning this repository

```
git clone https://github.com/sandeepraju/a.git
```

* Navigate to the Tweet Word Counter directory

```
cd a/tweet-word-count/
```

* This program depends on the twitter streaming library called [tweetstream](https://github.com/tweetstream/tweetstream). To install this dependency, run the following command

```
bundle install
```

* Once the dependencies are installed, the program has to be configured. Open the [config file](https://github.com/sandeepraju/a/blob/master/tweet-word-count/config.rb) in your favorite editor. Then, fill in following values
  * `CONSUMER_KEY`
  * `CONSUMER_SECRET`
  * `OAUTH_TOKEN`
  * `OAUTH_SECRET`

* You can get the above values by logging in to your [Twitter developer account](https://dev.twitter.com/) and [creating an application](https://apps.twitter.com/) in their developer dashboard.

* Once the config is populated, the program can be run with the following command.

```
ruby main.rb
```

## How does it work

* As soon as the program is run, a new instance of the `Counter` class is created with the `duration` and `persistence` parameters.
* Once this is done, the couter is ready to be started. Call the `start()` method to start the counter.
* The `start()` method connects to the twitter streaming API and starts fetching tweets in real-time.
* Each time a tweet is received, it is pre-processed (case normalization, removing unwanted characters and stop words). The list of stop words can be configured in the `config.rb` file.
* After pre-processing, the tweet is split into words and a centralized hash map is updated with the count of each word's occurence.
* The program, left uninterrupted, runs for 5 minutes (configurable using the `duration` parameter) and finally shows the top 10 most frequently occured words.
* The program can be shutdown mid-way by issuing a `SIGINT` or `SIGTERM` (again, configurable). When one of these signals are issued, the program stops processing any further tweets and starts the saving process. The saving process involves converting the hash map to a JSON blob and dumping to a file (named `dump.json`) in the current working directory.
* If the program is restarted, it reads the `dump.json` and loads the JSON contents into it's counter hash map. 

## Assumptions made

* The program though saves the hash map of counters while shutting down and picks it back up when started, it runs for a total 5 minute interval regardless of the time it ran before shutting down (the time interval is not saved). This is a simple change and can be incorporated if required.
* The number of words in the hash map are small enough for the program to load from JSON when restarting, without much noticable delays. If the JSON file is pretty huge and the initial load time is bad, a strategy to lazy load the dump can be implemented where each word is stored in a different file and loaded only when required. Note that even though this will speeden up the startup process, calculating the top 10 occurences needs all the words to be loaded invariably.

