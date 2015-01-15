import socket
import time

class IrcClient(object):
    """ A simple IRC client to send a message and then leave.
    the calls to `time.sleep` are so the socket has time to recognize
    responses from the IRC protocol
    """
    def __init__(self, target, nick="rust-highfive", should_join=False):
        self.target = target
        self.nick = nick
        self.should_join = should_join
        self.ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ircsock.connect(("irc.mozilla.org", 6667))
        self.ircsock.send("USER {0} {0} {0} :alert bot!\r\n".format(self.nick))
        self.ircsock.send("NICK {}\r\n".format(self.nick))
        time.sleep(2)

    def join(self):
        self.ircsock.send("JOIN {}\r\n".format(self.target))

    def send(self, msg):
        start = time.time()
        while True:
            if time.time() - start > 5:
                print("Timeout! EXITING")
                return
            ircmsg = self.ircsock.recv(2048).strip()
            #if ircmsg: print(ircmsg)

            if ircmsg.find(self.nick + " +x") != -1:
                self.ircsock.send("PRIVMSG {} :{}\r\n".format(self.target, msg))
                return

    def quit(self):
        self.ircsock.send("QUIT :bot out\r\n")

    def send_then_quit(self, msg):
        if self.should_join:
            self.join()
        time.sleep(2)
        self.send(msg)
        time.sleep(3)
        self.quit()
