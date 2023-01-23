######## Task timing intervals

### Reload forms points once every 10 minutes
### Not used by the client yet so not necessary
RELOAD_FORMS_POINTS_INTERVAL = 600

### Number of seconds between checks for new alpha reacts on
### messages from the last `TRAILING_ALPHA_PERIOD` hours 
CHECK_RECENT_MESSAGES_INTERVAL = 15

### Number of seconds between checks of pending alpha
### the last `TRAILING_ALPHA_PERIOD` hours for new alpha reacts
CHECK_PENDING_ALPHA_INTERVAL = 30

######## Alpha bot parameters

### Channel the bot will ping for messages with enough alpha
ALPHA_CHANNEL_ID = 1045019403701461092

CHANNELS_TO_CHECK = [1045019403701461092]

### Alpha react ID the bot will check for
ALPHA_REACT_ID = 908989024021118986

### Number of hours a message has to obtain 
### `LAYER_1_ALPHA_THRESHOLD` alpha reacts
### If it gets that many, its added to layer 2
TRAILING_ALPHA_PERIOD = 6

### Message will need this many alpha reacts in the first 
### `TRAILING_ALPHA_PERIOD` hours
LAYER_1_ALPHA_THRESHOLD = 1

### Message will need this many alpha reacts eventually to be
### Quoted by the bot
LAYER_2_ALPHA_THRESHOLD = 1

