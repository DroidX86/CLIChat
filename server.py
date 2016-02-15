#Define the server connectivity, create threads, use protocol to serve.
import socket, time
from connection import CustomSocket

class ChatServer:
	"""
	Server object for Chat server
	"""
	def __init__(self):
		"""
		Construst a ChatServer object, using default config options
		"""
		self.host = ""
		self.port = 36699
		self.server_sock = CustomSocket.newCustomSocket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_threads = None
		self.userdb = "userdb"
		self.mdir = "mailbox"

	def options(self):
		"""
		Parse command line arguments
		"""
		import argparse
		parser = argparse.ArgumentParser(description="Chat server")
		parser.add_argument("-p", "--port", help="Use given port instead of default (36699)", type=int)
		parser.add_argument("-m", "--mailbox", help="Set the server to use this folder as mailbox (default: mailbox)")
		parser.add_argument("-u", "--userdb", help="Set the server to use this file as user database (default: userdb)")

		args = parser.parse_args()

		if args.port is not None and args.port > 1024 and args.port < 65363:
			self.port = args.port

	def print_server_settings(self):
		pass

	def setup(self):
		#depending on mode -f, use normal dicts or dicts from multiprocessing.Manager and Locks.
		pass

	def first_time_setup(self):
		pass

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
			#Start thread or process here


if __name__=='__main__':
