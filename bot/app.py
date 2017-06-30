#!/usr/bin/env python

import logging
import os
import sys
import json

from beepboop import resourcer
from beepboop import bot_manager

from slack_bot import SlackBot
from slack_bot import spawn_bot

logger = logging.getLogger(__name__)


if __name__ == "__main__":

    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=log_level)

    if len (sys.argv) < 2:
        logging.critical("WOMP WOMP no config file set!")
        exit()
    elif not os.path.isfile(sys.argv[1]):
        logging.critical('WOMP WOMP config file {} doesn\'t exist'.format(sys.argv[1]))
        exit()
 #   elif os.path.isfile(sys.argv[1]):
 #       logging.info('Loading config file: {}'.format(sys.argv[1]))
 #       with open(sys.argv[1], 'r') as f:
 #           bot_data = json.load(f)
 #   else:
 #       logging.critical('WOMP WOMP config file {} doesn\'t exist'.format(sys.argv[1]))
 #       exit()


    slack_token = os.getenv("SLACK_TOKEN", "")
    logging.info("token: {}".format(slack_token))

    if slack_token == "":
        logging.info("SLACK_TOKEN env var not set, expecting token to be provided by Resourcer events")
        slack_token = None
        botManager = bot_manager.BotManager(spawn_bot)
        res = resourcer.Resourcer(botManager)
        res.start()
    else:
        # only want to run a single instance of the bot in dev mode
        bot = SlackBot(slack_token)
        bot.start({}, sys.argv[1])
