#Define the server connectivity, create threads, use protocol to serve.
import socket, time, threading, os, sys, time, datetime
from connection import CustomSocket
from base64 import b16decode, b64encode

########################################################################################################################

#server config
host = ""
port = 36699
server_sock = CustomSocket.newCustomSocket(socket.AF_INET, socket.SOCK_STREAM)
user_file = "userdb"
group_file = "groupdb"
userdb = None
groupdb = None
mdir = "mailbox/"

#locking
locks = {}	#for files
dblock = None	#for userdb and groupdb

#server
cs = None

########################################################################################################################

def sendmsg(from, to, msg, timestamp):
	global locks, mdir
	pass

def unread_retrieve(from):
	global locks, mdir
	pass

def unread_count(from):
	global locks, mdir
	pass

def login(user, passwd):
	global dblock
	pass

def signup(user, passwd):
	global dblock
	pass

def mkgroup(name, members):
	global dblock
	pass

def addgroup(name, members):
	global dblock
	pass

########################################################################################################################

def make_locks(folder):
	#make dict of file locks for files in folder
	global dblock, locks
	dblock = threading.Lock()
	for f in os.listdir(folder):
		locks[f] = threading.Lock()

def options():
	"""
	Parse command line arguments
	"""
	global port, user_file, group_file, mdir
	import argparse
	parser = argparse.ArgumentParser(description="Chat server")
	parser.add_argument("-p", "--port", help="Use given port instead of default (36699)", type=int)
	parser.add_argument("-m", "--mailbox", help="Set the server to use this folder as mailbox (default: mailbox)")
	parser.add_argument("-u", "--userdb", help="Set the server to use this file as user database (default: userdb)")
	parser.add_argument("-g", "--groupdb", help="Set the server to use this file as group database (default: groupdb)")

	args = parser.parse_args()

	if args.port is not None and args.port > 1024 and args.port < 65363:
		port = args.port
	if args.userdb:
		user_file = args.userdb
	if args.mailbox:
		mdir = args.mailbox
	if args.groupdb:
		group_file = args.groupdb

def print_server_settings():
	global port, user_file, group_file, mdir
	print "Server running on TCP port {} for all interfaces".format(port)
	print "Loaded users from {} and groups from {}.".format(user_file, group_file)
	print "Using mailbox folder {}".format(mdir)

def startup():
	"""
	Load users and group definitions
	"""
	global user_file, userdb, group_file, groupdb, mdir
	with open(user_file, 'r') as uf:
		jstr = uf.read()
		if jstr:
			userdb = json.loads(jstr)
		else:
			userdb = {}
	with open(group_file, 'r') as gf:
		jstr = gf.read()
		if jstr:
			groupdb = json.loads(jstr)
		else:
			groupdb = {}
	make_locks(mdir)

def shutdown():
	"""
	Save user and group, wait for threads to exit
	"""
	global cs, user_file, group_file, userdb, groupdb, server_threads
	#threads exit
	for t in cs.server_threads:
		t.join()
	#save users
	with open(user_file 'w') as uf:
		jstr = json.dumps(userdb)
		uf.write(jstr)
	#save groups
	with open(group_file, 'w') as gf:
		jstr = json.dumps(groupdb)
		gf.write(jstr)


########################################################################################################################

def int_handler(sig, frame):
	"""
	Ctrl+C handler, for when we exit the server
	"""
	global cs
	shutdown()
	cs.server_sock.close()
	print "User and Group info saved, exiting......."
	sys.exit(0)

########################################################################################################################

class ChatHandler(threading.Thread):
	def __init__(self, clientsocket):
		super(ChatHandler, self).__init__()
		self.clientsocket = clientsocket

	def run(self):
		while True:
			try:
				reqstr = self.clientsocket.recvln()
				if not reqstr:
					return
				req = json.loads(b64decode(reqstr))
				print "REQ: {}".format(req)
				resp = {}
				if not req["do"] or req["from"]:
					resp["status"] = "ERR"
					resp["body"] = "Malformed request"
				elif req["do"] == "send":
					if not req["to"]:
						resp["status"] = "ERR"
						resp["body"] = "No recipient"
					else:
						op = sendmsg(req["from"], req["to"], req["msg"], req["timestamp"])
						if not op:
							resp["status"] = "ERR"
							resp["body"] = "Failed to send messages"
						else:
							resp["done"] = "send"
							resp["status"] = "OK"
							resp["body"] = "Messages sent"
				elif req["do"] = "unread_count":
					op, count = unread_count(req["from"])
					if not op:
						resp["status"] = "ERR"
						resp["body"] = "Could not get count"
					else:
						resp["done"] = "unread_count"
						resp["status"] = "OK"
						resp["body"] = "Messages counted"
						resp["count"] = count
				elif req["do"] = "unread_retrieve":
					op, msgs = unread_retrieve(req["from"])
					if not op:
						resp["status"] = "ERR"
						resp["body"] = "Could not get messages"
					else:
						resp["done"] = "unread_retrieve"
						resp["status"] = "OK"
						resp["body"] = "Messages retreived"
						resp["msgs"] = msgs
				elif req["do"] = "mkgroup":
					if not req["name"] or not req["members"]:
						resp["status"] = "ERR"
						resp["body"] = "Missing arguments"
					else:
						op = mkgroup(req["name"], req["members"])
						if not op:
							resp["status"] = "ERR"
							resp["body"] = "Could create group"
						else:
							resp["done"] = "mkgroup"
							resp["status"] = "OK"
							resp["body"] = "Group created"
				elif req["do"] == "addgroup":
					if not req["name"] or not req["members"]:
						resp["status"] = "ERR"
						resp["body"] = "Missing arguments"
					else:
						op = addgroup(req["name"], req["members"])
						if not op:
							resp["status"] = "ERR"
							resp["body"] = "Could create group"
						else:
							resp["done"] = "addgroup"
							resp["status"] = "OK"
							resp["body"] = "Users added to group"
				elif req["do"] == "login":
					if not req["password"]:
						resp["status"] = "ERR"
						resp["body"] = "No password"
					else:
						op = login(req["from"], req["password"])
						if not op:
							resp["status"] = "ERR"
							resp["body"] = "Could log you in (user doesn't exist)"
						else:
							resp["done"] = "login"
							resp["status"] = "OK"
							resp["body"] = "Logged in"
				elif req["do"] == "signup":
					if not req["password"]:
						resp["status"] = "ERR"
						resp["body"] = "No password"
					else:
						op = signup(req["from"], req["password"])
						if not op:
							resp["status"] = "ERR"
							resp["body"] = "Could add user"
						else:
							resp["done"] = "signup"
							resp["status"] = "OK"
							resp["body"] = "User created"
				else:
					resp["status"] = "ERR"
					resp["body"] = "Unknown command"
				#send response
				print "RESP: {}".format(resp)
				print "------------------------------------------------------------------------------------------------"
				respstr = b64encode(json.dumps(resp))
				self.clientsocket.sendln(respstr)
			except socket.error:
				return

########################################################################################################################

class ChatServer:
	"""
	Server object for Chat server
	"""
	def __init__(self, host, port):
		"""
		Construst a ChatServer object, using default config options
		"""
		self.host = host
		self.port = port
		self.server_threads = []

	def serve_forever(self):
		"""
		Main server wait loop, serves incoming conncetions
		"""
		self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server_sock.bind((self.host, self.port))
		self.server_sock.listen(10)

		while True:
			print "Server waiting on TCP port {}".format(self.port)
			(clientsocket, address) = self.server_sock.accept()
			print "Accepted connection from: {}".format(address)
			ct = chat.ChatHandler(clientsocket)
			self.server_threads.append(ct)
			ct.start()


if __name__=='__main__':
	signal.signal(signal.SIGINT, int_handler)
	cs = ChatServer()
	options()
	startup()
	print_server_settings()
	cs.serve_forever()
