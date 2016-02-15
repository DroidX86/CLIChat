#Generic client for connecting to multiple servers and send commands
import socket, sys, time, datetime, signal, threading
from connection import CustomSocket
from requests import ConnectionError
from base64 import b64decode, b64encode

import simplejson as json

cc = None	#client object is global to pass it to signal Handler

def int_handler(sig, frame):
	"""
	Ctrl+C handler, for when we exit the client forcefully
	"""
	cc.save_contacts()
	if cc.auto:
		cc.timer.cancel()
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
		self.user = None
		self.sock = None
		self.timeout = 60.0	#secs
		self.debug = False
		self.auto = False
		self.interval = 30
		self.timer = None
		self.socket_lock = threading.Lock()
		self.contacts_file = 'contacts'
		self.first = False
		self.contacts = {}
		self.messages = []
		self.prompt = "chat>"
		self.read_config()

	def options(self):
		"""
		Parse command line options, sets all the options used by this client object
		"""
		import argparse
		parser = argparse.ArgumentParser()
		parser.add_argument("-p", "--port", help="Port on server to connect to.", type=int)
		parser.add_argument("-s", "--server", help="Server host name")
		parser.add_argument("-t", "--timeout", help="Set timeout for socket (default 60.0 sec)", type=float)
		parser.add_argument("-c", "--contacts", help="Use this contacts file")
		parser.add_argument("-v", "--verbose", help="Turn on verbosity", action='store_true')
		parser.add_argument("-a", "--automated", help="Turn on automated message checking", action='store_true')
		parser.add_argument("-i", "--interval", help="Interval for checking messages", type=int)
		parser.add_argument("-u", "--user", help="Login as this user (will be prompted for password)")
		parser.add_argument("-f", "--first", help="Sign up instead of logging in", action='store_true')

		args = parser.parse_args()

		if args.server is not None:
			self.server_hostname = args.server
		if args.port is not None and args.port > 1024 and args.port < 65536:
			self.server_port = args.port
		if args.timeout is not None and args.timeout > 0:
			self.timeout = args.timeout
		if args.contacts is not None:
			self.contacts_file = args.contacts
		if args.verbose:
			self.debug = True
		if args.automated:
			self.auto = True
		if args.interval is not None and args.interval > 10:
			self.interval = args.interval
		if args.user is not None:
			self.user = args.user
		if args.first:
			self.first = True

	def read_config(self):
		"""
		Read default configuration from config file
		"""
		with open("chat.cfg", 'r') as cf:
			for line in cf:
				if line == "\n" or line[0] == '#':
					continue
				parts = line.split('=')
				if len(parts) > 2:
					print >> sys.stderr, "Bad config option \"{}\"".format(line)
					continue
				name, value = parts[0], parts[1].rstrip()
				if name == 'server':
					self.server_hostname = value
				elif name == 'port':
					self.server_port = int(value)
				elif name == 'timeout':
					self.timeout = float(value)
				elif name == 'contacts':
					self.contacts = value
				elif name == 'user':
					self.user = value
				elif name == 'interval':
					self.interval = float(value)
				else:
					print >> sys.stderr, "Unrecognized config option \"{}\"".format(name)
					continue

	def restore_contacts(self):
		"""
		Restore contacts from contacts_file
		"""
		with open(self.contacts_file, 'r') as cf:
			jstr = cf.read()
			if jstr:
				self.contacts = json.loads(jstr)
			else:
				self.contacts = {}

	def save_contacts(self):
		"""
		Save contacts to contacts_file
		"""
		with open(self.contacts_file, 'w') as cf:
			jstr = json.dumps(self.contacts)
			if jstr:
				cf.write(jstr)

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
		parse input string for chat syntax, return json string for server, or None if parsing error
		"""
		req = {}
		req["timestamp"] = time.time()
		req["from"] = self.user
		if command.startswith("@"):
			#send
			req["do"] = 'send'
			parts = command.split(None, 1)
			if len(parts) < 2:
				print >> sys.stderr, "Badly formed send command\n@<user> <message>"
				return None
			req["to"] = parts[0][1:]
			req["msg"] = parts[1]
			return req
		elif command == "?":
			#check unread number
			req["do"] = 'unread_count'
			return req
		elif command.startswith("+"):
			#add contact
			parts = command.split(None, 1)
			if len(parts) < 2:
				print >> sys.stderr, "Badly formed contact command\n+<user> <keyword>"
				return None
			self.contacts[parts[1]] = parts[0]
			return None
		elif command == "read":
			#retrieve unread
			req["do"] = 'unread_retrieve'
			return req
		elif command == "help":
			#help
			self.print_help()
			return None
		elif command == "quit":
			#exit
			self.save_contacts()
			if self.auto:
				self.timer.cancel()
			self.sock.close()
			sys.exit(0)
		else:
			#check for group definition
			import re
			if re.match('[a-zA-Z0-9_]+=.*', command):
				req["do"] = 'mkgroup'
				parts = command.split("=")
				if len(parts) > 2:
					print >> sys.stderr, "Badly formed group command\n<group>=<user>+<user>...1"
					return None
				req["name"] = parts[0]
				people = parts[1].split('+')
				print "people={}".format(people)
				if len(people) <= 1:
					print >> sys.stderr, "Badly formed group command\n<group>=<user>+<user>...2"
					return None
				req["members"] = people
				req["members"].append(self.user)
				return req
			elif re.match('[a-zA-Z0-9_]+\+=.*', command):
				req["do"] = 'addgroup'
				parts = command.split("+=")
				if len(parts) > 2:
					print >> sys.stderr, "Badly formed group-add command\n<group>+=<user>+<user>..."
					return None
				req["name"] = parts[0]
				req["member"] = parts[1]
				return req
			else:
				print >> sys.stderr, "Badly formed command\nType \'help\' for command syntax"
				return None


	def parse_reply(self, reply):
		"""
		parse json reply from server, print string for user
		"""
		if not reply["status"]:
			print >> sys.stderr, "Mangled response from server (no status)"
			return
		print "Server response status: {}".format(reply["status"])
		if reply["status"] != "OK":
			print >> sys.stderr, "Server error esponse\nError description: {}".format(reply["body"])
			return
		if not reply["done"]:
			print >> sys.stderr, "Mangled response from server (no operation)"
			return
		if reply["done"] in ['addgroup', 'mkgroup', 'send']:
			print reply["body"]
		elif reply["done"] == "unread_retrieve":
			print "Messages: \n"
			for msg in reply["msgs"]:
				print msg + "\n"
			self.prompt = "chat>"
		elif reply["done"] == "unread_count":
			if reply["count"] > 0:
				self.prompt = "chat[{} unread messages]>".format(reply["count"])
		else:
			print >> sys.stderr, "Unrecognized operation {}".format(reply["done"])

	def unread_check_auto(self):
		"""
		This will run as a seperate thread, do a check request and retreive messages
		update the prompt string if in auto mode else show unread number
		equivalent to ? periodically
		"""
		req = {}
		req["from"] = self.user
		req["timestamp"] = time.time()
		req["do"] = "unread_count"
		self.socket_lock.acquire()
		self.sock.sendln(b64encode(json.dumps(req)))
		rep = json.loads(b64decode(self.sock.recvln()))
		self.socket_lock.release()
		if rep["status"] == "OK" and rep["count"] > 0:
			self.prompt = "chat[{} unread messages]>".format(rep["count"])
		self.timer = threading.Timer(self.interval, self.unread_check_auto)
		self.timer.start()

	def login(self, password):
		"""
		Do login request and parse response
		"""
		req = {}
		req["from"] = self.user
		req["timestamp"] = time.time()
		req["do"] = "login"
		req["password"] = password
		self.sock.sendln(b64encode(json.dumps(req)))
		resp = json.loads(b64decode(self.sock.recvln()))
		if resp["status"] == "OK":	#user found and correct pw
			return True
		elif resp["status"] == "ERR":
			print "User not found in system. Error: {}".format(resp["body"])
		return False

	def signup(self):
		from getpass import getpass
		req = {}
		u = raw_input("Enter new username: ")
		pw = getpass("Enter your password: ")
		pw_check = getpass("Enter your password again: ")
		if pw != pw_check:
			print "Passwords do not match!"
			return
		req["from"] = u
		req["timestamp"] = time.time()
		req["do"] = 'signup'
		req["password"] = pw
		self.sock.sendln(b64encode(json.dumps(req)))
		resp = json.loads(b64decode(self.sock.recvln()))
		if resp["status"] == "OK": #done
			print "Signed up, restart the client to login"
		else:
			print "Could not sign up user"

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
		if self.first:
			self.signup()
			sys.exit(0)
		if not self.user:
			self.user = raw_input("Enter username: ")
		from getpass import getpass
		up = getpass("Logging in as {}....Enter password: ".format(self.user))
		logged_in = self.login(up)
		if not logged_in:
			print >> sys.stderr, "Could not log in"
			sys.exit(1)
		if self.auto:
			self.unread_check_auto()
		while True:
			comstr = raw_input(self.prompt)
			if not comstr:
				continue
			com = self.parse_command(comstr)
			if com is None:
				continue
			if self.debug:
				print "Sending: {}".format(com)
			self.socket_lock.acquire()
			self.sock.sendln(b64encode(json.dumps(com)))
			rep = json.loads(b64decode(self.sock.recvln()))
			self.socket_lock.release()
			if self.debug:
				print "Received: {}".format(rep)
			self.parse_reply(rep)


if __name__ == "__main__":
	signal.signal(signal.SIGINT, int_handler)
	cc = ChatClient()
	cc.options()
	cc.connect_socket()
	cc.chat()
