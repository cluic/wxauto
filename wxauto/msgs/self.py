from .type import *
from .mattr import SelfMessage
from typing import List

class SelfTextMessage(SelfMessage, TextMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfQuoteMessage(SelfMessage, QuoteMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfImageMessage(SelfMessage, ImageMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfFileMessage(SelfMessage, FileMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfVideoMessage(SelfMessage, VideoMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfVoiceMessage(SelfMessage, VoiceMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfLocationMessage(SelfMessage, LocationMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfLinkMessage(SelfMessage, LinkMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfEmotionMessage(SelfMessage, EmotionMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfMergeMessage(SelfMessage, MergeMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)
    
class SelfPersonalCardMessage(SelfMessage, PersonalCardMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfNoteMessage(SelfMessage, NoteMessage):
    def __init__(
            self,
            control: uia.Control,
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)

class SelfOtherMessage(SelfMessage, OtherMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
            sub_controls: List[uia.Control] = None,
        ):
        super().__init__(control, parent, sub_controls)