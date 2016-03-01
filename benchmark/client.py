#Generic client for connecting to multiple servers and send commands
import socket, sys, os, time, datetime, signal, base64
from connection import CustomSocket
from requests import ConnectionError
import simplejson as json

cc = None	#client object is global to pass it to signal Handler

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
		self.timeout = 10.0	#secs
		self.user = None


	def options(self):
		"""
		Parse command line options, sets all the options used by this client object
		"""
		import argparse
		parser = argparse.ArgumentParser(description="Custom Chat client")
		parser.add_argument("-p", "--port", help="Port on server to connect to.", type=int)
		parser.add_argument("server", help="Server host name")
		parser.add_argument("-t", "--timeout", help="Default timeout for connection", type=float)
		parser.add_argument("-u", "--user", help="Username for chat")

		args = parser.parse_args()

		if args.server:
			self.server_hostname = args.server
		if args.port is not None and args.port > 1024:
			self.server_port = args.port
		if args.timeout is not None and args.timeout > 0:
			self.timeout = args.timeout
		if args.user:
			self.user = args.user



	def connect_socket(self):
		"""
		Connect the client to a server.
		Create a socket, set the timeout value, connect to the server
		"""
		self.sock = CustomSocket.newCustomSocket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.settimeout(self.timeout)
		self.sock.connect((self.server_hostname, self.server_port))
		print "Connected to {} on port {}".format(self.server_hostname, self.server_port)

	def parse_and_send(self, reqstr):
		req = {}
		parts = reqstr.split(None, 2)
		if parts[0] == 'read':
			req["name"] = 'read'
		elif parts[0] == 'send' and len(parts) > 1:
			req["name"] = 'send'
			if parts[1].startswith('to:'):
				req["dest"] = parts[1][3:].split(',')
				req["body"] = "@{}\tfrom:{} \"{}\"".format(datetime.datetime.now(), self.user, " ".join(parts[2:]))
			else:
				req["dest"] = []
				req["body"] = "@{}\tfrom:{} \"{}\"".format(datetime.datetime.now(), self.user, " ".join(parts[1:]))
		else:
			req["name"] = reqstr
		self.sock.sendln(json.dumps(req))

	def parse_and_show(self, resp):
		resp = json.loads(base64.b64decode(resp))
		retval = "Response status: {}\n".format(resp["status"])
		retval += "[Response Body]\n"
		retval += resp["body"]
		return retval

	def chat(self):
		"""
		Send commands to server and await Response
		"""
		if self.user is None:
			self.user = raw_input("Please provide username: ")
		self.sock.sendln(self.user)
		while True:
			req = raw_input("Chat>")
			if req == 'quit':
				self.sock.close()
				sys.exit(0)
			self.parse_and_send(req)
			resp = self.sock.recvln()
			print self.parse_and_show(resp)

	def chat_from_file(self, ifile, delay=0.1):
		self.sock.sendln(self.user)
		if not os.path.isfile(ifile):
			return
		with open(ifile, 'r') as f:
			for line in f:
				time.sleep(delay)
				self.parse_and_send(line.rstrip())
				resp = self.sock.recvln()
				print self.parse_and_show(resp)
		self.sock.close()


def int_handler(sig, frame):
	"""
	Ctrl+C handler, for when we exit the client forcefully
	close socket before exiting
	"""
	global cc
	cc.sock.close()
	sys.exit(0)

if __name__ == "__main__":
	signal.signal(signal.SIGINT, int_handler)
	cc = ChatClient()
	cc.options()
	cc.connect_socket()
	cc.chat()
