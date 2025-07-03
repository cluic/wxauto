from .type import *
from .attr import FriendMessage
import sys

class FriendTextMessage(FriendMessage, TextMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class FriendQuoteMessage(FriendMessage, QuoteMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
        ):
        super().__init__(control, parent)

class FriendImageMessage(FriendMessage, ImageMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",

        ):
        super().__init__(control, parent)

class FriendFileMessage(FriendMessage, FileMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",

        ):
        super().__init__(control, parent)

class FriendVideoMessage(FriendMessage, VideoMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",

        ):
        super().__init__(control, parent)

class FriendVoiceMessage(FriendMessage, VoiceMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",

        ):
        super().__init__(control, parent)

class FriendOtherMessage(FriendMessage, OtherMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",

        ):
        super().__init__(control, parent)