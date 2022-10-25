from whatsapp_to_sqlite import utils
from whatsapp_to_sqlite import messages

import datetime
import random
import unittest
import pytest

@pytest.fixture
def test_timestamp():
    startts = datetime.datetime.fromisoformat("2022-01-01T23:11:00+01:00")
    return startts + datetime.timedelta(minutes = random.randrange(60))



class TestSanitizeUserMessage:
    @pytest.mark.skip
    def test_sanitize_multiline_message(self, test_timestamp: datetime.datetime):

        str1 = "testtext1\n"
        str2 = "testtext2\n"
        message = messages.RoomMessage(
            timestamp=test_timestamp,
            text=str1,
            continued_text=str2,
            full_text=str1 + str2,
            sender="Jane Doe",
        )
        
        sanitized_message = utils.sanitize_user_message(message)[0]
        
        assert sanitized_message.continued_text == None
        assert sanitized_message.text == (str1 + str2)

    def test_sanitize_media_attached_message(self):
        message = messages.RoomMessage()


if __name__ == '__main__':
    unittest.main()
