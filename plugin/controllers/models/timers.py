##############################################################################
#                        2011 E2OpenPlugins                                  #
#                                                                            #
#  This file is open source software; you can redistribute it and/or modify  #
#     it under the terms of the GNU General Public License version 2 as      #
#               published by the Free Software Foundation.                   #
#                                                                            #
##############################################################################

from enigma import eEPGCache, eServiceReference
from Components.UsageConfig import preferredTimerPath, preferredInstantRecordPath
from RecordTimer import RecordTimerEntry, RecordTimer, parseEvent, AFTEREVENT
from ServiceReference import ServiceReference
from Components.config import config
from time import time

def getTimers(session):
	rt = session.nav.RecordTimer
	timers = []
	for timer in rt.timer_list + rt.processed_timers:
		descriptionextended = "N/A"
		filename = None
		nextactivation = None
		if timer.eit and timer.service_ref:
			event = eEPGCache.getInstance().lookupEvent(['EX', (str(timer.service_ref) , 2, timer.eit)])
			if event and event[0][0]:
				descriptionextended = event[0][0]
				
		try:
			filename = timer.Filename
		except Exception, e:
			pass
			
		try:
			nextactivation = timer.next_activation
		except Exception, e:
			pass
			
		timers.append({
			"serviceref": timer.service_ref,
			"servicename": timer.service_ref.getServiceName(),
			"eit": timer.eit,
			"name": timer.name,
			"description": timer.description,
			"descriptionextended": descriptionextended,
			"disabled": timer.disabled,
			"begin": timer.begin,
			"end": timer.end,
			"duration": timer.end - timer.begin,
			"startprepare": timer.start_prepare,
			"justplay": timer.justplay,
			"afterevent": timer.afterEvent,
			"dirname": timer.dirname,
			"tags": " ".join(timer.tags),
			"logentries": timer.log_entries,
			"backoff": timer.backoff,
			"firsttryprepare": timer.first_try_prepare,
			"state": timer.state,
			"repeated": timer.repeated,
			"dontsave": timer.dontSave,
			"cancelled": timer.cancelled,
			"filename": filename,
			"nextactivation": nextactivation
		})
		
	return {
		"result": True,
		"timers": timers
	}

def addTimer(session, serviceref, begin, end, name, description, disabled, justplay, afterevent, dirname, tags, repeated, logentries=None, eit=0):
	rt = session.nav.RecordTimer
	
	if not dirname:
		dirname = preferredTimerPath()
	
	try:
		timer = RecordTimerEntry(
			ServiceReference(serviceref),
			begin,
			end,
			name,
			description,
			eit,
			disabled,
			justplay,
			afterevent,
			dirname=dirname,
			tags=tags)

		if repeated:
			timer.repeated = 1
		else:
			timer.repeated = 0

		if logentries:
			timer.log_entries = logentries
			
		conflicts = rt.record(timer)
		if conflicts:
			errors = []
			for conflict in conflicts:
				errors.append(conflict.name)

			return {
				"result": False,
				"message": "Conflicting Timer(s) detected! %s" % " / ".join(errors)
			}
	except Exception, e:
		print e
		return {
			"result": False,
			"message": "Could not add timer '%s'!" % name
		}
		
	if config.plugins.Webinterface.autowritetimer.value:
		session.nav.RecordTimer.saveTimer()
	return {
		"result": True,
		"message": "Timer '%s' added" % name
	}

def addTimerByEventId(session, eventid, serviceref, justplay, dirname, tags):
	event = eEPGCache.getInstance().lookupEventId(eServiceReference(serviceref), eventid)
	if event is None:
		return {
			"result": False,
			"message": "EventId not found"
		}
	
	(begin, end, name, description, eit) = parseEvent(event)
	return addTimer(
		session,
		serviceref,
		begin,
		end,
		name,
		description,
		False,
		justplay,
		AFTEREVENT.AUTO,
		dirname,
		tags,
		False,
		None,
		eit
	)
	
def editTimer(session, serviceref, begin, end, name, description, disabled, justplay, afterevent, dirname, tags, repeated, channelOld, beginOld, endOld):
	rt = session.nav.RecordTimer
	for timer in rt.timer_list + rt.processed_timers:
		if str(timer.service_ref) == channelOld and int(timer.begin) == beginOld and int(timer.end) == endOld:
			rt.removeEntry(timer)
			res = addTimer(
				session,
				serviceref,
				begin,
				end,
				name,
				description,
				disabled,
				justplay,
				afterevent,
				dirname,
				tags,
				repeated,
				timer.log_entries
			)
			if not res["result"]:
				rt.record(timer)
				
			if config.plugins.Webinterface.autowritetimer.value:
				session.nav.RecordTimer.saveTimer()
				
			return res
			
	return {
		"result": False,
		"message": "Could not find timer '%s' with given start and end time!" % name
	}

def removeTimer(session, serviceref, begin, end):
	rt = session.nav.RecordTimer
	for timer in rt.timer_list + rt.processed_timers:
		if str(timer.service_ref) == serviceref and int(timer.begin) == begin and int(timer.end) == end:
			rt.removeEntry(timer)
			if config.plugins.Webinterface.autowritetimer.value:
				session.nav.RecordTimer.saveTimer()
			return {
				"result": True,
				"message": "The timer '%s' has been deleted successfully" % timer.name
			}
			
	return {
		"result": False,
		"message": "No matching Timer found"
	}
	
def cleanupTimer(session):
	session.nav.RecordTimer.cleanup()
	if config.plugins.Webinterface.autowritetimer.value:
		session.nav.RecordTimer.saveTimer()
	return {
		"result": True,
		"message": "List of Timers has been cleaned"
	}

def writeTimerList(session):
	session.nav.RecordTimer.saveTimer()
	return {
		"result": True,
		"message": "TimerList has been saved"
	}
	
def recordNow(session, infinite):
	rt = session.nav.RecordTimer
	serviceref = session.nav.getCurrentlyPlayingServiceReference().toString()

	try:
		event = session.nav.getCurrentService().info().getEvent(0)
	except Exception:
		event = None
		
	if not event and not infinite:
		return {
			"result": False,
			"message": "No event found! Not recording!"
		}
		
	if event:
		(begin, end, name, description, eit) = parseEvent(event)
		begin = time()
		msg = "Instant record for current Event started"
	else:
		name = "instant record"
		description = ""
		eit = 0
		
	if infinite:
		begin = time()
		end = begin + 3600 * 10
		msg = "Infinite Instant recording started"
		
	timer = RecordTimerEntry(
		ServiceReference(serviceref),
		begin,
		end,
		name,
		description, 
		eit,
		False,
		False,
		0,
		dirname=preferredInstantRecordPath()
	)
	timer.dontSave = True
	
	if rt.record(timer):
		return {
			"result": False,
			"message": "Timer conflict detected! Not recording!"
		}
		
	return {
		"result": True,
		"message": msg
	}
	