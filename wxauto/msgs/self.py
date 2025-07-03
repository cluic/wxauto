from .type import *
from .attr import SelfMessage
import sys

class SelfTextMessage(SelfMessage, TextMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class SelfQuoteMessage(SelfMessage, QuoteMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox",
        ):
        super().__init__(control, parent)

class SelfImageMessage(SelfMessage, ImageMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class SelfFileMessage(SelfMessage, FileMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class SelfVideoMessage(SelfMessage, VideoMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class SelfVoiceMessage(SelfMessage, VoiceMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)

class SelfOtherMessage(SelfMessage, OtherMessage):
    def __init__(
            self, 
            control: uia.Control, 
            parent: "ChatBox"
        ):
        super().__init__(control, parent)