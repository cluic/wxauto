from .type import *
from typing import (
    List
)
from .mattr import FriendMessage

class FriendTextMessage(FriendMessage, TextMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendQuoteMessage(FriendMessage, QuoteMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendImageMessage(FriendMessage, ImageMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendFileMessage(FriendMessage, FileMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendVideoMessage(FriendMessage, VideoMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendVoiceMessage(FriendMessage, VoiceMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendLocationMessage(FriendMessage, LocationMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendLinkMessage(FriendMessage, LinkMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendEmotionMessage(FriendMessage, EmotionMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendMergeMessage(FriendMessage, MergeMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendPersonalCardMessage(FriendMessage, PersonalCardMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendNoteMessage(FriendMessage, NoteMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class FriendOtherMessage(FriendMessage, OtherMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)