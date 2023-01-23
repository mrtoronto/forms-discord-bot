# forms-discord-bot

## How to run

Run the following commands to create a virtual environment, install the required packages and then start the processes.
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 main.py
```

## What's going on

`main.py` starts two processes, a client and a bot, on two threads. 

Together these two processes will handle forms points tipping, leaderboard checking, personal balance checking, an alpha react monitoring system and an alpha amplification system. 

All the UI needs to be improved. All messages from the bot could be cleaner and enabling application commands are the two highest priorities. 

### Client

The client will handle recurring, background tasks. Right now this includes both layers of the alpha check but more tasks could be added.

#### Client notes
- Client checks for alpha with a two layer system.
    - Layer 1 checks messages from the last `N` hours. Any with an alpha react are added to a pending alpha list.
    - Layer 2 checks all the messages in the pending alpha queue and sends a message when one of the messages in the queue exceeds the set threshold
- Alpha check is current setup to run with a custom emoji based on the emoji ID but can be changed to run on a non-custom emoji too.
- Alpha check only runs in a specific channel right now. Another channel could be added or all channels on the server could be checked. 
    - Minimizing the number of channels to check is probably good but can be compensated for by checking less frequently. 
- The client has a few parameters to configure. I moved them all to `config_parameters.py`. Can add details here too if helpful. 

### Bot

The bot will handle commands from users. Right now, this includes the forms points tipping mechanism and forms points leaderboard checks. 

#### Bot notes
- The bot will export and updated cache of the forms point data each time an update is made
- Commands are made with the hybrid_command decorator but the slash commands still aren't working. I think you have to sync the bot's commands with the server somehow but I didn't figure it out.
- Bot currently includes a `give` command which should be made admin-only or removed entirely.
- Leaderboard and personal check balance messages should be made prettier. 
- Right now, bot listens for commands prefixed with `/`. This can be changed to mentioning the bot instead of a slash. 
- Filelock is used to make sure the bot and client don't try to access the forms points file at the same time.
    - Not a problem now but just to be safu
    
