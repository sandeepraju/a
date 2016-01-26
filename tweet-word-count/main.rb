require "./tcounter"

# instantiate the counter
counter = TCounter::Counter.new do |config|
  config.duration = 300
  config.persistence = TCounter::Persistence::FILE
end

# start the counter
counter.start()

