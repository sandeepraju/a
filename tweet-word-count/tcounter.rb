require "./config"
require "json"
require "tweetstream"

module TCounter  
  # Define persistence modes
  module Persistence
    NONE = 0
    FILE = 1
    LAZY = 2
  end
  
  # Configure the TweetStream module
  TweetStream.configure do |config|
    config.consumer_key       = Config::CONSUMER_KEY
    config.consumer_secret    = Config::CONSUMER_SECRET
    config.oauth_token        = Config::OAUTH_TOKEN
    config.oauth_token_secret = Config::OAUTH_SECRET
    config.auth_method        = Config::AUTH_METHOD
  end  

  # Define the Counter class
  class Counter
    attr_accessor :duration
    attr_accessor :persistence
    
    def initialize()
      # Initialize the required variables
      @counter = Hash.new(0)
      @is_save_scheduled = false
      @is_shutdown_scheduled = false
      @client = TweetStream::Client.new()
      
      # Build stop words regex
      @stop_word_regex = Config::STOP_WORDS.join('\b|\b').prepend('\b').concat('\b')
      
      # Configure the client
      @client.on_error do |message|
        puts "[client-error] #{message}"
        # the steam has stopped. save it here.
        puts "[client-error] saving data..."
        save()
        
        # initiate a shutdown.
        puts "[client-error] shutting down..."
        shutdown()
      end
      
      # Configure shutdown signal handlers
      Config::SHUTDOWN_SIGNALS.each do |signal|
        Signal.trap(signal) do
          puts "[handling-signal] scheduling process for shutdown"
          @is_save_scheduled = true
          @is_shutdown_scheduled = true
        end
      end
      
      yield(self) if block_given?
    end

    def start()
      # load from dump file if exists
      load_from_dump()
      
      # compute the end time based on duration
      @end_time = Time.now + @duration
      
      # start fetching the tweets
      @client.sample(language: Config::LANGUAGE) do |status|
        if Time.now >= @end_time
          # time up. initiate a shutdown.
          @is_save_scheduled = true
          @is_shutdown_scheduled = true
        else
          # process the tweet
          process(status.text)
        end
      
        if @is_save_scheduled == true
          save()
        end
        if @is_shutdown_scheduled == true
          shutdown()
        end
      end
    end
    
    def process(tweet)
      puts "[processing-tweet] #{tweet}"

      # duplicate the string for easier processing
      text = tweet.dup

      # NOTE: the below preprocessing is split into
      # multiple lines for better readability
      words = text.gsub(/[^a-zA-Z\n\t ]/, " ")  # step 0 - remove everything that is not alphabets & newline
        .downcase  # step 1 - convert everything to lower case
        .gsub(/\b[a-z]\b/, " ")  # step 2 - remove all single characters
        .gsub(/#{@stop_word_regex}/, " ")  # step 3 - remove all stopwords in one step
        .split()  # step 4 - finally convert the string into a list of words
  
      # update the counter using the words
      words.each do |word|
        @counter[word] += 1
      end
    end
    
    def load_from_dump()
      begin
        puts "[loading-dump] attempting to load from dump file"
        File.open("./dump.json", "r" ) do |f|
          @counter = JSON.load(f)
          @counter.default = 0  # retaining the default of hash as 0
        end
        puts "[loading-dump] dump loaded successfully"
      rescue Exception
        puts "[loading-dump] there is no file to load from"
      end
    end
    
    def save()
      # save the data if a persistence type is selected
      if @persistence != Persistence::NONE
        puts "[saving-data] please wait..."
        File.open("./dump.json","w") do |f|
          f.write(@counter.to_json)
        end
      end
      
      # display the top 10 words
      puts "[displaying-data] top 10 word counts..."
      
      # do a reverse sort and print top 10
      @counter.sort_by { |word, count| -count }[0, 10].each do |word, count|
        puts "[displaying-data] #{word} --> #{count}"
      end
    end
    
    def shutdown()
      puts "[shutting-down] bye.. bye.."
      exit
    end
  end
end
