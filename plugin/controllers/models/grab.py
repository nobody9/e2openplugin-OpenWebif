##############################################################################
#                        2011 E2OpenPlugins                                  #
#                                                                            #
#  This file is open source software; you can redistribute it and/or modify  #
#     it under the terms of the GNU General Public License version 2 as      #
#               published by the Free Software Foundation.                   #
#                                                                            #
##############################################################################
from enigma import eConsoleAppContainer
from twisted.web import static, resource, http
from os.path import getsize as os_getsize
from os import system as os_system

GRAB_PATH = '/usr/bin/grab'

class grabScreenshot(resource.Resource):

	def __init__(self, path = ""):
		resource.Resource.__init__(self)

		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.grabFinished)
		
	def render(self, request):
		self.request = request
		graboptions = ""
		
		if "format" in request.args.keys():
			self.fileformat = request.args["format"][0]
		else:
			self.fileformat = "jpg"
			
		if self.fileformat == "jpg":
			graboptions += " -j 100"
		elif self.fileformat == "png":
			graboptions += " -p"
				
		if "r" in request.args.keys():
			size = request.args["r"][0]
			graboptions += " -r %s" % size

		if "mode" in request.args.keys():
			mode = request.args["mode"][0]
			if mode == "osd":
				graboptions += " -o"
			elif mode == "video":
				graboptions += " -v"
				
		self.filepath = "/tmp/screenshot." + self.fileformat
		grabcommand = GRAB_PATH + graboptions + " " + self.filepath
		
		#self.container.execute(grabcommand)
		
		os_system(grabcommand)
		self.grabFinished()

	def grabFinished(self, data=""):
		try:
			self.request.setHeader('Content-Disposition', 'inline; filename=screenshot.%s;' % self.fileformat)
			self.request.setHeader('Content-Type','image/%s' % self.fileformat)
			self.request.setHeader('Content-Length', '%i' % os_getsize(self.filepath))
			
			file = open(self.filepath)
			self.request.write(file.read())
			file.close()
			self.request.finish()
		except Exception, error:
			self.request.setResponseCode(http.OK)
			self.request.write("Error creating screenshot:\n %s" % error)
			self.request.finish()				
				