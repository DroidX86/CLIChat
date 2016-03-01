if __name__=='__main__':
	with open('times', 'r') as tmf:
		lines = tmf.read().splitlines()
		first = float(lines[0])
		current = float(lines[1])
	with open('pstats', 'r') as psf:
		delays = [float(line) for line in psf]
		count = len(delays)
		totaldelay = sum(delays)
	with open('peaks', 'r') as pkf:
		peakusers = max([int(line) for line in pkf])
	print "[Server Statistics]"
	print "Served {} requests in {} secs".format(count, current - first)
	print "{} requests served per second".format(count/(current - first))
	print "Total delay in serving requests: {}, Average: {} microseconds".format(totaldelay*10**6, totaldelay*10**6/count)
	print "Peak user count: {}".format(peakusers-1)
