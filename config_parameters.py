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

ALPHA_CHANNEL_ID = 1072962447578763332
ALPHA_ROLE_CHANNEL_ID = 1072963459681103996
TWITTER_CHANNEL_ID = 1072624102268993576
INFLUENCER_TWITTER_CHANNEL_ID = 1090059193165303838
NSFWAVEY_CHANNEL_ID = 1080986943946502235

NSFWAVEY_ROLE_ID = 1082372937434271855
ALPHA_ROLE_ID = 1073331675397898281

NSFWAVEY_OPT_IN_MESSAGE_ID = 1082324075826905121
ALPHA_OPT_IN_MESSAGE_ID = 1074408946762268763


CHANNELS_TO_CHECK = [1072543132429864982]

### Alpha react ID the bot will check for
# ALPHA_REACT_ID = 'peepo_likes'
ALPHA_REACT_IDS = ['ALPHA', 'ALPHA_static']
NSFWAVEY_REACT_IDS = ['✅']

### Number of hours a message has to obtain 
### `LAYER_1_ALPHA_THRESHOLD` alpha reacts
### If it gets that many, its added to layer 2
TRAILING_ALPHA_PERIOD = 6

### Message will need this many alpha reacts in the first 
### `TRAILING_ALPHA_PERIOD` hours

ALPHA_REACT_THRESHOLD = 5

CHECK_TWITTER_INTERVAL = 60

FOLLOWED_INFLUENCER_ACCOUNTS = [
    "elonmusk",
    "VitalikButerin",
    "cz_binance",
    "Jason",
    "paulg",
    "DegenerateNews", 
    "itscrypto_news", 
    "News1Airdrop",
    "NFT_World_News",
    "nftnewspro",
    "NFToNEWS",
    "LuckyNFTNews",
    "NftDropsCal",
    "TodayNft",
    "NFTInsider_io",
    "CryptoBoomNews",
    "NFTPlazas",
    "LuckyTraderHQ",
    "blockhead_co",
    "NFTInsider_io",
    "esatoshiclub",
    "AltCoinAll",
    "nftlately",
]