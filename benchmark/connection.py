import socket, warnings
from requests import ConnectionError

class CustomSocket:
	"""
	Wrapper around raw TCP socket to deliminate messages using newline.
	Using Delegated methods.
	"""
	def __init__(self, sock):
		self._sock = sock

	@staticmethod
	def newCustomSocket(family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0):
		"""
		Factory method for creating a CustomSocket object, to avoid confusing with socket constructor
		"""
		newsock = socket.socket(family, type, proto)
		return CustomSocket(newsock)

	def accept(self):
		(nsock, addr) = self._sock.accept()
		lsock = CustomSocket(nsock)	#Wrap it now for compatibility
		return (lsock, addr)

	def bind(self, address):
		self._sock.bind(address)

	def close(self):
		self._sock.close()

	def connect(self, address):
		self._sock.connect(address)

	def fileno(self):
		return self._sock.fileno()

	def getpeername(self):
		return self._sock.getpeername()

	def getsockopt(self, *args):
		return self._sock.getsockopt(*args)

	def listen(self, backlog):
		self._sock.listen(backlog)

	def makefile(self, *args):
		return self._sock.makefile(*args)

	def recv(self, bufsize, flags = 0):
		warnings.warn("Should not be used in a CustomSocket, use recvln() instead")
		return self._sock.recv(bufsize, flags)

	def recvfrom(self, bufsize, flags = 0):
		return self._sock.recvfrom(bufsize, flags)

	def send(self, *args):
		warnings.warn("Should not be used in a CustomSocket, use sendln() instead")
		return self._sock.send(*args)

	def sendto(self, string, address):
		self._sock.sendto(string, address)

	def recvln(self):
		"""
		Receive one line (seperated by \n) from other endpoint
		"""
		buffer = ''
		while '\n' not in buffer:
			recieved = self._sock.recv(2048)
			if len(recieved) == 0:
				print "Connection from {} closed".format(self._sock.getpeername())
				return None
			buffer += recieved
		return buffer[:buffer.find('\n')]

	def sendln(self, msg):
		"""
		Send one line (seperated by \n) to other endpoint
		"""
		msg += '\n'
		sent = self._sock.send(msg)
		if sent == 0:
			print "Connection from {} closed".format(self._sock.getpeername())
			raise ConnectionError("Other endpoint closed connection")
		return sent

	def setblocking(self, flag):
		self._sock.setblocking(flag)

	def settimeout(self, value):
		self._sock.settimeout(value)

	def gettimeout(self):
		return self._sock.gettimeout()

	def setsockopt(self, *args):
		self._sock.setsockopt(*args)
