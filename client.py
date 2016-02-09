#Generic client for connecting to multiple servers and send commands
import socket, sys, time, datetime, signal, threading
from connection import CustomSocket
from requests import ConnectionError

cc = None	#client object is global to pass it to signal Handler

def int_handler(sig, frame):
	"""
	Ctrl+C handler, for when we exit the client forcefully
	"""
	cc.save_contacts()
	cc.sock.close()
	sys.exit(0)

class ChatClient:
	"""
	Client object for connecting with TCP or UDP server
	"""
	def __init__(self):
		"""
		Construct an uninitialized client object
		"""
		self.server_hostname = None
		self.server_port = 36699
		self.sock = None
		self.timeout = 1.0	#secs
		self.debug = False
		self.auto = False
		self.socket_lock = None
		self.contacts = {}
		self.messages = []
		self.prompt = "chat"

	def options(self):
		"""
		Parse command line options, sets all the options used by this client object
		"""
		import argparse
		parser = argparse.ArgumentParser()
		parser.add_argument("-p", "--port", help="Port on server to connect to.", type=int)
		parser.add_argument("server", help="Server host name")
		parser.add_argument("-t", "--timeout", help="Set timeout for socket (default 1.0 sec)", type=float)
		parser.add_argument("-c", "--contacts", help="Use this contacts file")
		parser.add_argument("-v", "--verbose", help="Turn on verbosity", action='store_true')
		parser.add_argument("-a", "--automated", help="Turn on automated message checking", action='store_true')

		args = parser.parse_args()

		if args.server is not None:
			self.server_hostname = args.server
		if args.port is not None and args.port > 1024 and args.port < 65536:
			self.server_port = args.port
		if args.timeout is not None and args.timeout > 0:
			self.timeout = args.timeout

	def restore_contacts(self, filename):
		pass

	def save_contacts(self, filename):
		pass

	def print_help(self):
		print "Chat client commads and syntax:"
		print "-   @<user/group> \"<message>\" : Send message to user or group"
		print "-   ? : Get number of unread messags from server (if any) and read them"
		print "-   read : Read all unread messages"
		print "-   +<user> \"<keyword>\" : Add mapping to contacts list"
		print "-   <group>=<user1>+<user2>+... : Create multicast group"
		print "-   help : Print this help message"
		print "-   quit : Quit from chat"

	def parse_command(self, command):
		"""
		parse input string for chat syntax, return json string for server
		"""
		pass

	def parse_reply(self, reply):
		"""
		parse json reply from server, return printable string for user
		"""
		pass
	def unread_check(self):
		"""
		This will run as a seperate thread, do a check request and retreive messages
		update the prompt string if in auto mode else show unread number
		equivalent to ? in both modes
		"""
		pass

	def show_unread(self):
		"""
		This will show the retrieved unread messages
		equivalent to read in both modes
		"""
		pass

	def sendmsg(self, to, from, timestamp, body):
		pass

	def mkgroup(self, grpname, *members):
		pass

	def add_contact(self, user, keyword):
		pass

	def connect_socket(self):
		"""
		Connect the client to a server.
		Create a socket, set the timeout value, connect to the server
		"""
		self.sock = CustomSocket.newCustomSocket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.settimeout(self.timeout)
		self.sock.connect((self.server_hostname, self.server_port))
		if self.debug:
			print "Connected to {} on {} port {}".format(self.server_hostname, self.conntype, self.server_port)

	def chat(self):
		"""
		i/o main loop
		"""
		pass

if __name__ == "__main__":
	signal.signal(signal.SIGINT, int_handler)
	cc = ChatClient()
	cc.options()
	cc.connect_socket()
