import logging
import threading
import os
import openai
from local_settings import OPENAI_API_KEY

from discord_client import _run_discord_client
from discord_bot import _run_discord_bot

if not os.path.exists('data'):
        os.mkdir('data')

if not os.path.exists('data/forms_points.json'):
    with open('data/forms_points.json', 'w') as f:
        f.write('{}')

if not os.path.exists('data/forms_points_trxns.json'):
    with open('data/forms_points_trxns.json', 'w') as f:
        f.write('[]')


FORMAT = '[%(levelname)s] (%(threadName)s) - %(asctime)s - %(message)s'

logging.basicConfig(format=FORMAT)
file_handler = logging.FileHandler('output.log')
file_handler.setFormatter(logging.Formatter(FORMAT))
logger = logging.getLogger('FORMS_BOT')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

openai.api_key = OPENAI_API_KEY

def main():
    # print ID of current process
    logger.debug("ID of process running main program: {}".format(os.getpid()))
 
    # print name of main thread
    logger.debug(f"Main thread name: {threading.current_thread().name}")

    t1 = threading.Thread(target=_run_discord_client, name='discord_client')
    t2 = threading.Thread(target=_run_discord_bot, name='discord_bot')
    t2.start()
    t1.start()
    t1.join()
    t2.join()

 
if __name__ == "__main__":
    main()