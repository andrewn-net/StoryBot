# -*- coding: utf-8 -*-

import logging
import random
import time
import json
import os
import numpy as np

logger = logging.getLogger(__name__)

class Messenger(object):
    def __init__(self, slack_clients):
        self.clients = slack_clients

    def send_message(self, channel_id, msg):
        # in the case of Group and Private channels, RTM channel payload is a complex dictionary
        if isinstance(channel_id, dict):
            channel_id = channel_id['id']
        logger.debug('Sending msg: %s to channel: %s' % (msg, channel_id))
        channel = self.clients.rtm.server.channels.find(channel_id)
        channel.send_message(msg)

    def write_help_message(self, channel_id):
        bot_uid = self.clients.bot_user_id()
        txt = '{}\n{}\n{}\n{}'.format(
            "I'm your friendly Slack bot written in Python.  I'll *_respond_* to the following commands:",
            "> `hi <@" + bot_uid + ">` - I'll respond with a randomized greeting mentioning your user. :wave:",
            "> `<@" + bot_uid + "> joke` - I'll tell you one of my finest jokes, with a typing pause for effect. :laughing:",
            "> `<@" + bot_uid + "> attachment` - I'll demo a post with an attachment using the Web API. :paperclip:")
        self.send_message(channel_id, txt)

    def write_greeting(self, channel_id, user_id):
        greetings = ['Hi', 'Hello', 'Nice to meet you', 'Howdy', 'Salutations']
        txt = '{}, <@{}>!'.format(random.choice(greetings), user_id)
        self.send_message(channel_id, txt)

    def write_prompt(self, channel_id):
        bot_uid = self.clients.bot_user_id()
        txt = "I'm sorry, I didn't quite understand... Can I help you? (e.g. `<@" + bot_uid + "> help`)"
        self.send_message(channel_id, txt)

    def write_error(self, channel_id, err_msg):
        txt = ":face_with_head_bandage: my maker didn't handle this error very well:\n>```{}```".format(err_msg)
        self.send_message(channel_id, txt)

    def write_message_list(self, channel_id, message_list):
        bot_uid = self.clients.bot_user_id()
        self.send_message(channel_id,message_list)

    #wait, how do I kill this thing again?
    def goodnight(self, channel_id):     
        txt = ":sleeping: Daisy, Daisy, give me your answer do. I'm half crazy all for the love of you. It won't be a stylish marriage, I can't afford a carriage. But you'll look sweet upon the seat of a bicycle built for two. :sleeping:"
        self.send_message(channel_id, txt)
   #     exit()

    #
    #here there be dragons!!
    #


    #Get list of all channels from team
    def get_channel_list(self,sc):
        channel_list = sc.api_call("channels.list")
        channel_list = json.dumps(channel_list)
        channel_list = json.loads(str(channel_list))
        return channel_list

    #Get list of all groups from team
    def get_group_list(self,sc):
        group_list = sc.api_call("groups.list")
        group_list = json.dumps(group_list)
        group_list = json.loads(str(group_list))
        return group_list

    #Looks up channel ID from a name
    #Opportunity to cache the channel list to avoid calling it so much?
    def get_channel_id_from_name(self,sc,name,channel_list):
        for i in channel_list['channels']:
            if (i['name'] == name):
                return i['id']
        return False

    def reload_config (self):
        print "Reloading config file!"
        with open("bot.json", 'r') as f:
            bot_data = json.load(f)
        return bot_data

    def send_complex_message(self, channel_id, bot_data, persona_clients):

     #   if isinstance(channel_id, dict):
     #       channel_id = channel_id['id']
     #   logger.debug('COMPLEX Sending msg: %s to channel: %s' % (msg, channel_id))
     #   channel = self.clients.rtm.server.channels.find(channel_id)


        #just change the args if this works
        channel_id=0        


        #Blank message history
        messages = []

        #Pull channel & group lists once to reduce API calls - use these to go from name to ID where needed
        channel_list = self.get_channel_list(self.clients.rtm)
        group_list = self.get_group_list(self.clients.rtm)

        #Go through each item in the trigger - set some defaults in case they aren't provided
        for i in bot_data:
            delay=0
            item=i['item']  
            type=i['type']
            target_item=0
            channel=i['channel']
            username=i['username']
            attachments =""
            text=""
            reaction=""
            icon_emoji=""

            if 'target_item' in i:
                if np.isnan(i['target_item']): #oddness check due to DataFrame float conversions - fix this
                    target_item=0
                else:
                    target_item= int(i['target_item'])
            if 'text' in i:
                text = i['text']
            if 'reaction' in i:
                reaction = i['reaction']
            if 'delay' in i:
                if np.isnan(i['delay']): #oddness check due to DataFrame float conversions - fix this
                    delay = 0
                else:
                    delay = int(i['delay'])
            if 'attachments' in i:
                attachments = i['attachments']
            if 'icon_emoji' in i:
                icon_emoji=i['icon_emoji'] 

            ##Easier way to detect if this is a channel or group than these loops?
            for j in channel_list['channels']:
                if (j['name'] == channel):
                    channel_id = j['id']
            if channel_id == 0:
                for j in group_list['groups']:
                    if (j['name'] == channel):
                        channel_id = j['id']

            #artificial delay, default is 0
            time.sleep(delay)   
            
            #Now for the actual actioning via API!!
            if type == "message":
                result = persona_clients[username].api_call(
                    "chat.postMessage",
                    username=username, 
                    channel=channel_id,
                    text=text,
                    attachments=attachments,
                    as_user="true",
                    link_names=1,
                    unfurl_links="true")
            
            if type == "bot":
                result = self.clients.rtm.api_call(
                    "chat.postMessage",
                    username=username,
                    channel=channel_id,
                    text=text,
                    attachments=attachments, 
                    icon_emoji=icon_emoji, 
                    as_user="false", 
                    link_names=1,
                    unfurl_links="true")
            
            if type == "reply":
                result = persona_clients[username].api_call(
                    "chat.postMessage",
                    channel=messages[target_item][3],
                    text=text,
                    as_user="true",
                    thread_ts=messages[target_item][2],
                    attachments=attachments,
                    link_names=1,
                    unfurl_links="true")
            
            #Reactions use different args if against a message or post/file
            if type == "reaction":
                if (messages[target_item][1] == "post"):
                    result = persona_clients[username].api_call(
                        "reactions.add",
                        channel=messages[target_item][3],
                        name=reaction,
                        file=messages[target_item][2])
                else:
                    result = persona_clients[username].api_call(
                        "reactions.add",
                        channel=messages[target_item][3],
                        name=reaction,
                        timestamp=messages[target_item][2])  

            if type == "post":
                result = persona_clients[username].api_call(
                    "files.upload", 
                    channels=channel_id,
                    filetype="post",
                    initial_comment=text,
                    content=i['content'],
                    title=i['title'])

            #This probabily needs another look! It's tough anyway, need to specificy specific timestamps
            if type == "share":
                if 'target_item' in i:
                    target_ts=messages[target_item][2]
                    target_channel=messages[target_item][3]
                else:
                    if 'target_ts' in i:
                        target_ts = i['target_ts']
                    if 'target_channel' in i:
                        target_channel = i['target_channel']
                result = persona_clients[username].api_call("chat.shareMessage",channel=target_channel,timestamp=target_ts,text=text,share_channel=channel_id)

            #Message list consists of (item_id, type, timestamp or file id, channel) for recall.  Build it up here for references and cleanup
            if result.get('ok'):
                if type == "post":
                    messages.append((item,type,result.get('file')['id'],result.get('file')['channels']))
                else:
                    messages.append((item, type, result.get('ts'), result.get('channel')))
            else:
                logger.error("Playback Error: %s for #%s from %s",result.get('error'),channel,username)
                messages.append((item,type,result.get('error')))

            #Pin needs to happen after all this so we have a timestamp to use
            if 'pin' in i:
                result = persona_clients[username].api_call(
                    "pins.add",
                    channel=channel_id,
                    timestamp=messages[item][2])


        #Write the message history to disk for future cleanup - this needs some work! Let's make this more user friendly to do!!!!
        filename = time.strftime("%Y%m%d_%H%M%S")
    #    with open('/Users/dsmock/Documents/StoryBot/logs/' + channel + '-' + filename, 'w') as f:
        with open('./logs/' + channel + '-' + filename, 'w') as f:
            json.dump(messages, f)
        logger.info("Story Complete - %s-%s",channel,filename)
        return messages

    #Use this to go through a message list and delete everthing
    def cleanup (self, channel_id, persona_clients, messages):
        logger.info("CLEANING UP %s", messages)

        for i in messages:
            if i[1] == "post":
                result = persona_clients['dsmock'].api_call("files.delete",file=i[2])
            else:
                result = persona_clients['dsmock'].api_call("chat.delete",ts=i[2],channel=i[3])

            if not result.get('ok'):
                logger.error("Error cleaning up: %s",result.get('errors'))


