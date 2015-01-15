import mock

from highfive import irc
from highfive.tests import base

class TestIrc(base.BaseTest):

    def test_send_and_join(self):
        with mock.patch('socket.socket') as mocked_socket:
            with mock.patch('time.sleep') as time:
                msocket = mock.MagicMock()
                mocked_socket.return_value = msocket

                client = irc.IrcClient('#rust-bots')
                msocket.connect.assert_called_once_with(("irc.mozilla.org", 6667))
                msocket.reset_mock()

                client.send_then_quit("test")
                msocket.send.assert_has_calls([mock.call("PRIVMSG #rust-bots :test\r\n"),
                                               mock.call("QUIT :bot out\r\n")])
