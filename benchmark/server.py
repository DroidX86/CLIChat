#Define the server connectivity, create threads, use protocol to serve.
import sys, socket, time, os, threading, multiprocessing, base64, signal
from connection import CustomSocket
import simplejson as json

mailbox = 'mbox/'
glock = None
slock = None

server_start = 0
server_stop = 0
count = 0
totaldelay = 0.0
peakusers = 0

def make_locks(proc_flag):
	global glock, slock
	if not proc_flag:
		glock = threading.Lock()
		slock = threading.Lock()
	else:
		man = multiprocessing.Manager()
		glock = man.Lock()
		slock = man.Lock()

def make_file_if_not_exist(user):
	global glock, mailbox
	#print "{} waiting for glock at make".format(threading.current_thread())
	glock.acquire()
	#print "{} acquired glock at make".format(threading.current_thread())
	try:
		if not os.path.isfile(mailbox + user):
			open(mailbox + user, 'w').close()
	finally:
		glock.release()
	#print "{} released glock at make".format(threading.current_thread())

def broadcast(message, user, dest):
	global glock, mailbox
	#print "{} waiting for glock at broadcast".format(threading.current_thread())
	glock.acquire()
	#print "{} acquired glock at broadcast".format(threading.current_thread())
	i = 0
	try:
		for u in os.listdir(mailbox):
			if u == user:
				continue
			if dest and u not in dest:
				continue
			i += 1
			with open(mailbox + u, 'a') as uf:
				uf.write(message + "\n")
	finally:
		glock.release()
	#print "{} released glock at broadcast".format(threading.current_thread())
	return "OK", "Sent message to {} users in the mailbox".format(i)

def retrieve(user):
	global glock, mailbox
	#print "{} waiting for glock at get".format(threading.current_thread())
	glock.acquire()
	#print "{} acquired glock at get".format(threading.current_thread())
	try:
		with open(mailbox + user, 'r') as uf:
			msgs = uf.read()
		open(mailbox + user, 'w').close()
		return "OK", msgs
	finally:
		glock.release()
	#print "{} released glock at get".format(threading.current_thread())

def do_chat(req, user):
	command = json.loads(req)
	resp = {}
	if command["name"] == 'read':
		resp["status"], resp["body"] = retrieve(user=user)
	elif command["name"] == 'send':
		resp["status"], resp["body"] = broadcast(command["body"], user=user, dest=command["dest"])
	else:
		resp["status"], resp["body"] = "Unknown command", ""

	return base64.b64encode(json.dumps(resp))

def tstat_handler(sig, frame):
	global server_start, server_stop, totaldelay, count
	server_stop = time.time()
	print "[Server Statistics]"
	print "Served {} requests in {} secs".format(count, server_stop - server_start)
	print "{} requests served per second".format(count/(server_stop - server_start))
	print "Total delay in serving requests: {}, Average: {} microseconds".format(totaldelay*10**6, totaldelay*10**6/count)
	print "Peak user count: {}".format(peakusers-1)
	sys.exit(0)

def pstat_handler(sig, frame):
	global slock
	#print "{} waiting for slock at ctrl-c".format(threading.current_thread())
	slock.acquire()
	#print "{} acquired slock at ctrl-c".format(threading.current_thread())
	with open('times', 'a') as f:
		f.write("{}\n".format(time.time()))
	slock.release()
	#print "{} released slock at ctrl-c".format(threading.current_thread())


class ChatHandler(threading.Thread):
	def __init__(self, clientsocket):
		super(ChatHandler, self).__init__()
		self.clientsocket = clientsocket
		self.user = None

	def run(self):
		global count, totaldelay, slock, server_start, server_stop

		self.user = self.clientsocket.recvln()
		print "[Thread-{}] Connected to user {} at {}".format(threading.current_thread().ident, self.user, self.clientsocket.getpeername())
		make_file_if_not_exist(self.user)
		while True:
			try:
				req = self.clientsocket.recvln()
				if not req:
					return
				print "[Thread-{}] REQ: \"{}\" @ {}".format(threading.current_thread().ident, req, time.time())

				start = time.time()
				resp = do_chat(req, user=self.user)
				end = time.time()

				#print "{} waiting for slock at run".format(threading.current_thread())
				slock.acquire()
				#print "{} acquired slock at run".format(threading.current_thread())
				count += 1
				totaldelay += (end - start)
				slock.release()
				#print "{} released slock at run".format(threading.current_thread())

				print "[Thread-{}] RESP: \"{}\" @ {}".format(threading.current_thread().ident, resp, time.time())
				self.clientsocket.sendln(resp)
				print "------------------------------------------------------------------------"
			except socket.error:
				return

def ChatFunction(clientsocket):
	global slock, count, totaldelay, server_start, server_stop, peakusers
	user = clientsocket.recvln()
	print "[Process-{}] Connected to user {} at {}".format(multiprocessing.current_process().pid, user, clientsocket.getpeername())
	make_file_if_not_exist(user)
	while True:
		try:
			req = clientsocket.recvln()
			if not req:
				return
			print "[Process-{}] REQ: \"{}\" @ {}".format(multiprocessing.current_process().pid, req, time.time())
			start = time.time()
			resp = do_chat(req, user=user)
			end = time.time()

			slock.acquire()
			with open('pstats', 'a') as f:
				f.write(str(end - start) + '\n')
			slock.release()

			print "[Process-{}] RESP: \"{}\" @ {}".format(multiprocessing.current_process().pid, resp, time.time())
			clientsocket.sendln(resp)
			print "------------------------------------------------------------------------"
		except socket.error:
			clientsocket.close()
			return

class ChatServer:
	"""
	Server object for TCP or UDP server.
	"""
	def __init__(self):
		"""
		Construst a ChatServer object, using default config options
		"""
		self.host = ""
		self.port = 36699
		self.server_sock = CustomSocket.newCustomSocket(socket.AF_INET, socket.SOCK_STREAM)
		self.proc_flag = False
		self.server_threads = []
		self.server_procs = []

	def options(self):
		"""
		Parse command line arguments
		"""
		import argparse
		parser = argparse.ArgumentParser(description="Chat server")
		parser.add_argument("-p", "--port", help="Use given port instead of default (36699)", type=int)
		parser.add_argument("-f", "--fork", help="Fork processes instead of threads for handling clients", action='store_true')

		args = parser.parse_args()

		if args.port is not None and args.port > 1024 and args.port < 65563:
			self.port = args.port
		if args.fork:
			self.proc_flag = True

	def serve_forever(self):
		"""
		Main server wait loop, serves incoming conncetions
		"""
		global peakusers, server_start
		server_start = time.time()
		if self.proc_flag:
			global slock

		self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server_sock.bind((self.host, self.port))
		self.server_sock.listen(10)

		if self.proc_flag:
			with open('times', 'w') as f:
				f.write("{}\n".format(time.time()))
			open('peaks', 'w').close()
			open('pstats', 'w').close()

		while True:
			if not self.proc_flag:
				curusers = threading.active_count()
				if curusers > peakusers:
					peakusers = curusers
			else:
				curusers = len(multiprocessing.active_children())
				slock.acquire()
				with open('peaks', 'a') as f:
					f.write(str(curusers) + "\n")
				slock.release()
			print "Server waiting on TCP port {}".format(self.port)
			(clientsocket, address) = self.server_sock.accept()
			print "Accepted connection from: {}".format(address)
			if not self.proc_flag:
				ct = ChatHandler(clientsocket)
				self.server_threads.append(ct)
				ct.start()
			else:
				cp = multiprocessing.Process(target=ChatFunction, args=(clientsocket,))
				self.server_procs.append(cp)
				cp.start()
				clientsocket.close()

		if not self.proc_flag:
			for t in self.server_threads:
				t.join()
		else:
			for p in self.server_procs:
				p.join()

if __name__=='__main__':
	cs = ChatServer()
	cs.options()
	make_locks(cs.proc_flag)
	if not cs.proc_flag:
		signal.signal(signal.SIGINT, tstat_handler)
	else:
		signal.signal(signal.SIGINT, pstat_handler)
	cs.serve_forever()
