import sys
from client import ChatClient
from multiprocessing import Process

def do_chat(user, server, input_file):
	cc = ChatClient()
	cc.user = user
	cc.server_hostname = server
	cc.connect_socket()
	cc.chat_from_file(input_file, delay=0.05)

if __name__=='__main__':
	users = ['c3po','chewbacca','hansolo','leia','luke','obiwan','r2d2','vader','yoda', 'bobafett']
	if len(sys.argv) < 3:
		print "Not enough arguments"
		sys.exit(1)
	server = sys.argv[1]
	input_file = sys.argv[2]
	procs = []
	for user in users:
		p = Process(target=do_chat, args=(user, server, input_file))
		procs.append(p)
		p.start()
	for p in procs:
		p.join()
