import json
import logging
import re
import os
from slackclient import SlackClient
import glob
import pandas

logger = logging.getLogger(__name__)


class RtmEventHandler(object):
    def __init__(self, slack_clients, msg_writer, config_file):
        self.clients = slack_clients
        self.msg_writer = msg_writer
        self.bot_data = ""
        self.persona_clients = {}
        self.messages = []
        self.config_file = config_file #storing so we can call a reload() at any point

        #load up the config
        self.load_config(config_file)

        #need to use the built in slack_clients stuff for this!!!!!!
        for i in self.bot_data['Tokens']:
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
                elif 'goodnight' in msg_txt:
                    self.msg_writer.goodnight(event['channel'])
                elif re.search('hi|hey|hello|howdy', msg_txt):
                    self.msg_writer.write_greeting(event['channel'], event['user'])
                #cleanup with an argument
                elif 'cleanup ' in msg_txt:
                 #   path = '/Users/dsmock/Documents/StoryBot/logs/' + re.split('cleanup ',msg_txt)[1].strip()  #needs to be modified, but subdirectory for logs is a good thing - or just overhaul logs!
                    
                    path = './logs/' + re.split('cleanup ',msg_txt)[1].strip()
                    with open(path,'r') as f:
                        messages_loaded = json.load(f)
                        self.msg_writer.cleanup(event['channel'], self.persona_clients, messages_loaded)
                        os.remove(path)
                #cleanup with no args uses current session messages list
                elif 'cleanup' in msg_txt:
                    self.msg_writer.cleanup(event['channel'], self.persona_clients, self.messages)
                    self.messages = []
                elif 'reload' in msg_txt:
                  self.load_config(self.config_file)
                elif 'message list' in msg_txt:
                    print self.messages
                    self.msg_writer.write_message_list(event['channel'],self.messages)
                elif re.search('playback', msg_txt):
                    if msg_txt in self.bot_data['Triggers']:
                        self.messages = self.msg_writer.send_complex_message(event['channel'], self.bot_data['Triggers'][msg_txt], self.persona_clients)
         #       elif re.search('playback', msg_txt):
         #           phrase = re.split('playback ', msg_txt)[1]
         #           if phrase in self.bot_data['responses']:
         #               self.messages = self.msg_writer.send_complex_message(event['channel'], self.bot_data['responses'][phrase], self.persona_clients)
                else:
                    self.msg_writer.write_prompt(event['channel'])

            #Channel trigger commands - need to strip any leading / because Excel sheet names can't contain that - but we still need a command trigger!
            elif msg_txt.strip('/') in self.bot_data['Triggers']:
                self.messages = self.msg_writer.send_complex_message(event['channel'], self.bot_data['Triggers'][msg_txt.strip('/')], self.persona_clients)

    def _is_direct_message(self, channel):
        """Check if channel is a direct message channel
        Args:
            channel (str): Channel in which a message was received
        """
        return channel.startswith('D')

    
    def load_config (self, config_file):
        
     #   Load all the XLS data files (will we have more than one? Or just multiple sheets in one XLS?)
     #   files_location = './data'
     #   if os.getcwd() != files_location:
     #   os.chdir(config_dir)
     #   files = glob.glob("*.xlsx")

        #Decided to just use one config file - can clean up this logic later
        files = glob.glob(config_file)

        #Initialize the bot_data container
        bot_data = {'Tokens':[],'Triggers':{}}
        #Create a new Data Frame to handle each sheet
        df = pandas.DataFrame()

        #Go through each XLS file, then each sheet within the XLS to build a DataFrame and load it
        for file in files:
            sheets = pandas.ExcelFile(file).sheet_names

            for sheet in sheets:
                logger.info("Now working on %s", sheet)

                df = pandas.read_excel(file, sheet)

                #Get rid of rows with only an Item (i.e. blank) and lower case the column headers for consistency
                df = df.dropna(axis='index',thresh=2)
                df.columns = map(unicode.lower,df.columns)

                if sheet == "Tokens":
                    bot_data[sheet] = df.to_dict(orient='record') #load the tokens in
                else:
                    bot_data['Triggers'][sheet] = df.to_dict(orient='record') #add the appropriate trigger entry

        self.bot_data = bot_data

    #deprecated direct JSON config load
    def load_config_old (self, config_file):
      #  print "[Re]loading config file!"
        logger.info("Loading config file %s",config_file)
        with open(config_file, 'r') as f:
            self.bot_data = json.load(f)

