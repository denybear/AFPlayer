# Define targets
raspiTarget = False
pcTarget = True


import sys
import time
sys.path.append('./')
import pygame
import cv2
import os
import json
import random
import threading
from collections import deque
from operator import attrgetter
if raspiTarget:
	import RPi.GPIO as GPIO
from control_screen import displaySongInfo
from control_screen import configureScreenAreas
from detect_HW import detectAudioHW
from detect_HW import detectVideoHW


#TO DO
# test: audio file does not exist, video file does not exist
# highlight_config: make sure we display the right things at the right time (error mgmt)
# raspi keys and raspi rotary to be tested
# invert video for the rotary changes (audio or video) to indicate what is changing
# sample X : display, play, etc


# Global variables
audio_thread = None
cap = None
videoPath = "./video/"
audioPath = "./audio/"
running = True
playing = False
dragging = None
rotaryChangesVolume = True
audioVolume = 0.5
videoRate = 1.0
playListIndex = 0
colorNoError = [0, 128, 0]
colorError = [255, 0, 0]
colorWarning = [255, 165, 0]
keyGPIO = [18, 19, 20, 21, 22]
keyGPIOName = [["previous"], ["next"], ["sample","1"], ["sample","2"], ["sample","3"]]
rotaryGPIO = [17, 18, 27]
rotaryGPIOName = ["CLK", "DT", "SW"]
#rotaryLastState = GPIO.input(rotary_gpio("CLK"))
rotaryLastState = False		# dummy value to start with


# functions for raspi key capture and rotary capture
def init_gpio():

	# Set GPIO mode (BCM or BOARD)
	GPIO.setmode(GPIO.BCM)  # Use GPIO numbering (BCM)
	# GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering
	#GPIO.setup(23, GPIO.OUT)  # Pin 23 as output

	# Set up keys GPIOs
	# Pull-up mode : when idle, GPIO is considered at +3V. Switch can be connected to GND, and when closed, GPIO will fall down to GND
	for pin in keyGPIO:
		GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)		# Pin as input with pull-up resistor

	# Set up rotary GPIOs
	for pin in rotaryGPIO:
		GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)		# Pin as input with pull-up resistor
		"""
		# if the above does not work, use the below
		pinName = rotaryGPIOName [rotaryGPIO.index (pin)]
		if pinName == "SW":
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)		# Pin as input with pull-up resistor
		else:
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)	# Pin as input with pull-down resistor
		"""

def rotary_gpio(name):
	for pin in rotaryGPIOName:
		if pin == name:
			return rotaryGPIO [rotaryGPIOName.index (pin)]




# class for handling events in the main loop
class Event:
	def __init__(self, label, values):
		if not isinstance(values, (list, dict)):
			raise ValueError("Values must be a list or dictionary.")
		self.label = label
		self.values = values

class EventQueue:
	def __init__(self):
		self.queue = deque()

	def record_event(self, label, values):
		"""Create an Event and add it to the queue."""
		event = Event(label, values)
		self.queue.append(event)

	def get_next_event(self):
		"""Retrieve and remove the next Event from the queue."""
		if self.queue:
			return self.queue.popleft()
		return None

	def peek_next_event(self):
		"""Retrieve the next Event without removing it."""
		if self.queue:
			return self.queue[0]
		return None

	def is_empty(self):
		"""Check if the queue is empty."""
		return len(self.queue) == 0

	def size(self):
		"""Return the number of events in the queue."""
		return len(self.queue)


# object representing a tuple: name of the song, name of the video/picture, name of samples 
class Song:
	def __init__(self, song="", video="", sample=["","","","","","","","",""], startPosition="beginning"):
		self.song = song
		self.video = video
		self.sample = sample
		self.startPosition = startPosition

	def __repr__(self):
		return f"Song(song={self.song}, video={self.video}, sample={self.sample}, startPosition={self.startPosition})"


# function for the audio thread
def play_audio(audio_file):
	try:
		pygame.mixer.music.load(audio_file)
	except pygame.error:
		# file does not exist
		return False
	pygame.mixer.music.set_endevent(pygame.USEREVENT)	# pygame event is triggered after playing is complete
	pygame.mixer.music.play()
	return True

def stop_audio():
	pygame.mixer.music.stop()

def start_audio_thread(audio_file):
	global audio_thread
	stop_audio()

	if not os.path.isfile(audio_file):
		# file does not exist
		return False

	audio_thread = threading.Thread(target=play_audio, args=(audio_file,))
	audio_thread.start()
	return True

	
	
########
# MAIN #
########
# init raspi hardware
if raspiTarget:
	init_gpio ()

# Load the JSON data from the file
with open('./playlist.json', 'r', encoding='utf-8') as file:
	data = json.load(file)

# Create a list of Song objects
playList = [Song(item['song'], item['video'], item['sample'], item['startPosition']) for item in data]

# Manage audio HW: select the right audio device for outputing sound
isAudioHW, audioColor, primaryAudio = detectAudioHW ("Headphones 1 (Realtek HD Audio 2nd output with SST)")
# Manage video HW: primary and secondary monitors
isVideoHW, videoColor, primaryVideo, secondaryVideo = detectVideoHW ()

# Initialize Pygame
pygame.init()
pygame.mixer.init(devicename=primaryAudio['name'])
pygame.mixer.music.set_volume (audioVolume)

# Create windows
# primary monitor will always get the control panel
screen = pygame.display.set_mode((primaryVideo.width, primaryVideo.height))
pygame.display.set_caption("Song Info Display")
# Configure screen layout
configureScreenAreas(0.1, 0.2, 0.5, 0.2)

# secondary monitor will get the video
# Create a named window; the flags control window behavior
# In this case, we don't want any title bar or border
if isVideoHW:
	cv2.namedWindow('Video', cv2.WND_PROP_FULLSCREEN)
	cv2.setWindowProperty('Video', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
	# Resize the window to a specific size (width, height) : this is useless as we have WINDOW_FULLSCREEN as a window property
	#cv2.resizeWindow('Video', secondaryVideo.width, secondaryVideo.height)
	# Move the window to the secondary monitor (secondaryVideo.x, secondaryVideo.y)
	cv2.moveWindow('Video', secondaryVideo.x, secondaryVideo.y)


# Main loop
eq = EventQueue()		# event queue to manage the events happening in the main loop
# force display of 1st song in playlist and video
eq.record_event("key", ["first song"])
		

while running:

	# Handle Pygame events
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False

		elif event.type == pygame.USEREVENT:
			# audio playing is complete, let's record an event to stop playing and update the display
			eq.record_event("audio", ["stop"])		

		elif event.type == pygame.KEYDOWN:
			# key press
			keyPressed = pygame.key.name(event.key)
			if keyPressed == 'q':
				eq.record_event("key", ["quit"])
			if keyPressed == 'p':
				eq.record_event("key", ["previous"])
			if keyPressed == 'n':
				eq.record_event("key", ["next"])
			if keyPressed in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):		# nomore than 9 samples per song, we don't have enough keys on raspi!
				eq.record_event("key", ["sample", keyPressed])
#********HERE********** keys for volume and for video


		"""
		##########################################
		# THIS PART HAS NEVER BEEN TESTED		#
		# IT IS INTENDED FOR TOUCHSCREEN SUPPORT #
		##########################################
		
		elif event.type == pygame.MOUSEBUTTONDOWN:
			if slider_info["video_slider_rect"].collidepoint(event.pos):
				dragging = "video"
			elif slider_info["audio_slider_rect"].collidepoint(event.pos):
				dragging = "audio"
			elif slider_info["arrow_left_rect"].collidepoint(event.pos):
				print("Previous song clicked")
			elif slider_info["arrow_right_rect"].collidepoint(event.pos):
				print("Next song clicked")
			else:
				for rect, label in slider_info["sample_rects"]:
					if rect.collidepoint(event.pos):
						print(f"Sample clicked: {label}")

		elif event.type == pygame.MOUSEBUTTONUP:
			dragging = None

		elif event.type == pygame.MOUSEMOTION and dragging:
			mx = event.pos[0]
			if dragging == "video":
				videoRate = max(0.0, min(1.0, (mx - slider_info["video_slider_rect"].x) / slider_info["video_slider_rect"].width))
			elif dragging == "audio":
				audioVolume = max(0.0, min(1.0, (mx - slider_info["audio_slider_rect"].x) / slider_info["audio_slider_rect"].width))
			#slider_info = displaySongInfo(screen, song, volume_percent, rate_percent, "Previous Song", "Next Song", highlight_config)

		"""


	# Handle main loop events
	next_event = eq.get_next_event()
	if next_event:		# make sure there is an event to process

		# display events
		if next_event.label == "display":
			slider_info = displaySongInfo (screen, playList [playListIndex], volume_percent=audioVolume, rate_percent=videoRate, previous_entry=playList [playListPrevious].song, next_entry=playList [playListNext].song, highlight_config=next_event.values)

		# key events
		if next_event.label == "key":

			# quit
			if next_event.values [0] == "quit":
				running = False
				break

			# previous
			if next_event.values [0] == "previous" or next_event.values [0] == "first song":
				# get video file name that is currently playing
				try:
					previousVideoFileName = videoPath + playList [playListIndex].video
				except (ValueError, IndexError):
					previousVideoFileName = ""
				# in case of 1st song, force display of video by specifying no previous video
				if next_event.values [0] == "first song":
					previousVideoFileName = ""
				# previous in playlist
				playListIndex = max(playListIndex - 1, 0)
				playListPrevious = max(playListIndex - 1, 0)
				playListNext = min(playListIndex + 1, len(playList) - 1)
				# record new event to update the display
				eq.record_event("display", {
					"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
					"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
				})
				
				# record event to play video
				try:
					videoFileName = videoPath + playList [playListIndex].video
				except (ValueError, IndexError):
					videoFileName = ""
				try:
					startPos = playList [playListIndex].startPosition
				except (ValueError, IndexError):
					startPos = "beginning"
				eq.record_event("video", ["play", videoFileName, previousVideoFileName, startPos])

			# next
			if next_event.values [0] == "next":
				# get video file name that is currently playing
				try:
					previousVideoFileName = videoPath + playList [playListIndex].video
				except (ValueError, IndexError):
					previousVideoFileName = ""
				# next in playlist
				playListIndex = min(playListIndex + 1, len(playList) - 1)
				playListPrevious = max(playListIndex - 1, 0)
				playListNext = min(playListIndex + 1, len(playList) - 1)
				# record new event to update the display
				eq.record_event("display", {
					"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
					"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
				})
				# record event to play video
				try:
					videoFileName = videoPath + playList [playListIndex].video
				except (ValueError, IndexError):
					videoFileName = ""
				try:
					startPos = playList [playListIndex].startPosition
				except (ValueError, IndexError):
					startPos = "beginning"
				eq.record_event("video", ["play", videoFileName, previousVideoFileName, startPos])

			# sample keys
			if next_event.values [0] == "sample":
				# get actual sample filename from playlist; check whether empty
				try:
					sampleFileName = audioPath + playList [playListIndex].sample [int (next_event.values [1]) - 1]
				except (ValueError, IndexError):
					sampleFileName = ""

				# check if playing or not; if playing, we should stop the audio first (update of the display will be done in stop event processing)
				if playing:
					eq.record_event("audio", ["stop"])
				# if not playing, then we should initiate playing
				else:
					sampleString = "sample" + next_event.values [1]
					eq.record_event("audio", ["play", sampleString, sampleFileName])

		# audio events
		if next_event.label == "audio":

			# stop
			if next_event.values [0] == "stop":
				if isAudioHW: stop_audio()
				playing = False
				audioColor = colorNoError
				# record new event to update the display
				eq.record_event("display", {
					"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
					"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
				})

			# play
			if next_event.values [0] == "play":
				# attempt to open audio file and play it
				sampleString = next_event.values [1]
				sampleFileName = next_event.values [2]
				playing = start_audio_thread (sampleFileName) if isAudioHW else False
				# record new event to update the display, based on the result of playing (sample exists or not)
				if playing:
					audioColor = colorNoError
#*********HERE********* samplestring !!!
					eq.record_event("display", {
						sampleString: {"font_size": 0.05, "bold": False, "italic": False, "inverse": False, "color": (0, 100, 0), "font_name": "couriernew", "spacing": 1.5},
						"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
						"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}


					})
				else:
					audioColor = colorWarning
					eq.record_event("display", {
						"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
						"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
					})

		# video events
		if next_event.label == "video":

			# play
			if next_event.values [0] == "play":
				videoFileName = next_event.values [1]
				previousVideoFileName = next_event.values [2]
				# make sure video HW is on
				if isVideoHW:
					# if video is same as previous, then don't restart video... we just carry on showing
					if videoFileName != previousVideoFileName:
						cap = cv2.VideoCapture(videoFileName)						# cap.isOpened() returns False if file does not exist
						# in case file does not exists, cap.isOpened () will return False
						if not cap.isOpened():
							# file does not exist, update display
							videoColor = colorWarning
							eq.record_event("display", {
								"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
								"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
							})
						else:
							# file exists, update display
							videoColor = colorNoError
							eq.record_event("display", {
								"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
								"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
							})
							# determine startPos, and set it to video
							if next_event.values [3] == "beginning":
								startPos = 0
							else:
								startPos = random.randint (0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
							# set start position
							cap.set(cv2.CAP_PROP_POS_FRAMES, startPos)				



	# Perform non-event based functions, ie. video display and key capture

	# display video (if exists)
	if isVideoHW and (cap is not None and cap.isOpened()):
		ret, frame = cap.read()

		# If the video ends, restart it
		if not ret:
			cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
			continue
		# display video frame
		cv2.imshow("Video", frame)
		# Wait for a key press for 1 millisecond; but don't capture it. waitKey() is mandatory so the image is displayed in opencv2
		cv2.waitKey(1)
		# Wait for some milliseconds, based on video rate : 25ms at full rate, 12.5ms at 50%
		time.sleep (0.025 * videoRate)


	"""
	###################################################
	# THIS PART HAS NEVER BEEN TESTED				 #
	# IT IS INTENDED FOR RASPI KEY AND ROTARY SUPPORT #
	###################################################

	# check if raspi keypress or rotary
	if raspiTarget:
		# RASPI KEYS
		# Read the state of each GPIO to determine which are on and off, ie. which key is pressed or not
		for pin in keyGPIO:
			# LOW means key is pressed, HIGH means key is not pressed; we change this so True=pressed, False=not pressed
			if not GPIO.input(pin):
				# key is pressed, add key event
				eq.record_event("key", keyGPIOName [keyGPIO.index (pin)])

		# RASPI ROTARY
		# check if audio volume or video rate is changed
		# button would switch between audio volume and video rate
		counter = audioVolume if rotaryChangesVolume else videoRate
		rotaryCurrentState = GPIO.input(rotary_gpio("CLK"))

		if rotaryCurrentState != rotaryLastState:			# Detect rotation
			# new counter value
			if GPIO.input(rotary_gpio("DT")) != rotaryCurrentState:
				counter += 0.01  # Clockwise
			else:
				counter -= 0.01  # Counter-clockwise
			# record display event to show change in the display
			eq.record_event("display", {
				"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
				"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
			})
		rotaryLastState = rotaryCurrentState

		# cap and map new counter value to audioVolume or videoRate
		if rotaryChangesVolume:
			counter = max (0, counter)
			counter = min (counter, 1.0)
			audioVolume = counter
		else:
			counter = max (0.3, counter)	# lowest video rate would be 30%
			counter = min (counter, 1.0)
			videoRate = counter

		# Detect button press
		#if GPIO.input(SW) == GPIO.LOW:
		if not GPIO.input(rotary_gpio("SW")):
			rotaryChangesVolume = not rotaryChangesVolume
			#print("Button Pressed!")
			#sleep(0.3)  # Debounce delay

			# record display event to show change in the display
			eq.record_event("display", {
				"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": videoColor, "font_name": "arial", "spacing": 1.0},
				"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": audioColor, "font_name": "arial", "spacing": 1.0}
			})

	"""

# Cleanup
if raspiTarget:
	GPIO.cleanup()		# Clean up GPIO on exit

if isAudioHW: stop_audio()
if isVideoHW and cap is not None:
	cap.release()
cv2.destroyAllWindows()
pygame.mixer.music.stop()
pygame.quit()
