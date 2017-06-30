import json
import logging
import re
import os
from slackclient import SlackClient

logger = logging.getLogger(__name__)


class RtmEventHandler(object):
    def __init__(self, slack_clients, msg_writer, config_file):
        self.clients = slack_clients
        self.msg_writer = msg_writer
        self.bot_data = ""
        self.persona_clients = {}
        self.messages = []
        self.config_file = config_file

        self.load_config(config_file)


        #need to use the built in slack_clients stuff for this!
        for i in self.bot_data['tokens']:
            self.persona_clients[i['name']] = SlackClient(i['token'])

    def handle(self, event):

        if 'type' in event:
            self._handle_by_type(event['type'], event)

    def _handle_by_type(self, event_type, event):
        # See https://api.slack.com/rtm for a full list of events
        if event_type == 'error':
            # error
            self.msg_writer.write_error(event['channel'], json.dumps(event))
        elif event_type == 'message':
            # message was sent to channel
            self._handle_message(event)
        else:
            pass


    def _handle_message(self, event):
        # Filter out messages from the bot itself, and from non-users (eg. webhooks)
        if ('user' in event) and (not self.clients.is_message_from_me(event['user'])):

            msg_txt = event['text']

            # @ mention or DM commands 
            if self.clients.is_bot_mention(msg_txt) or self._is_direct_message(event['channel']):
                # e.g. user typed: "@pybot tell me a joke!"
                if 'help' in msg_txt:
                    self.msg_writer.write_help_message(event['channel'])
                elif re.search('hi|hey|hello|howdy', msg_txt):
                    self.msg_writer.write_greeting(event['channel'], event['user'])
                #cleanup with an argument
                elif 'cleanup ' in msg_txt:
                    path = 'logs/' + re.split('cleanup ',msg_txt)[1]
                    with open(path,'r') as f:
                        messages_loaded = json.load(f)
                        self.msg_writer.cleanup(event['channel'], self.persona_clients, messages_loaded)
                        os.remove(path)
                #cleanup with no args uses current session messages list
                elif 'cleanup' in msg_txt:
                    self.msg_writer.cleanup(event['channel'], self.persona_clients, self.messages)
                    self.messages = []
                elif 'reload' in msg_txt:
                  #  self.bot_data = self.msg_writer.reload_config()
                  self.load_config(self.config_file)
                elif 'message list' in msg_txt:
                    print self.messages
                    self.msg_writer.write_message_list(event['channel'],self.messages)
                elif re.search('playback', msg_txt):
                    if msg_txt in self.bot_data['responses']:
                        self.messages = self.msg_writer.send_complex_message(event['channel'], self.bot_data['responses'][msg_txt], self.persona_clients)
         #       elif re.search('playback', msg_txt):
         #           phrase = re.split('playback ', msg_txt)[1]
         #           if phrase in self.bot_data['responses']:
         #               self.messages = self.msg_writer.send_complex_message(event['channel'], self.bot_data['responses'][phrase], self.persona_clients)
                else:
                    self.msg_writer.write_prompt(event['channel'])

            #Channel trigger commands
            elif msg_txt in self.bot_data['responses']:
                self.messages = self.msg_writer.send_complex_message(event['channel'], self.bot_data['responses'][msg_txt], self.persona_clients)

    def _is_direct_message(self, channel):
        """Check if channel is a direct message channel
        Args:
            channel (str): Channel in which a message was received
        """
        return channel.startswith('D')

    def load_config (self, config_file):
      #  print "[Re]loading config file!"
        logger.info("Loading config file %s",config_file)
        with open(config_file, 'r') as f:
            self.bot_data = json.load(f)
