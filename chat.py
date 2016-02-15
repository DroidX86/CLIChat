"""
Define basic server side chat functions
All threads wil run these
Chat thread class definitions
"""
import threading, os, sys, time, datetime

locks = {}
glock = None

def make_locks(folder):
	#make dict of filre locks for files in folder


class ChatHandler(threading.Thread):
	def __init__(self):
