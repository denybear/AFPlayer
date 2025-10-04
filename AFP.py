import pygame
import cv2
import os
import json
import random
import numpy as np
import threading
from collections import deque

#TO DO
# UI à redéfinir
#
# test: audio file does not exist, video file does not exist
# force video play of the first song
# display name of the animation
# remove muted


# Global variables
audio_thread = None
cap = None
videoPath = "./video/"
audioPath = "./audio/"
raspiTarget = True
pcTarget = True
running = True
playing = False
audioVolume = 0.5
videoRate = 1.0
muted = False
playListIndex = 0


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
	def __init__(self, song="", video="", sample=["","",""], startPosition="beginning"):
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


# User-interface : main screen
def displaySongInfo(screen, song, volume_percent, previous_entry="", next_entry="", highlight_config=None, muted=False):
	screen.fill((255, 255, 255))  # white background

	# Initialise fonts with 15% larger size
	pygame.font.init()
	title_font = pygame.font.SysFont('Arial', int(32 * 1.15), bold=True)
	regular_font = pygame.font.SysFont('Arial', int(20 * 1.15))
	bold_font = pygame.font.SysFont('Arial', int(20 * 1.15), bold=True)

	if highlight_config is None:
		highlight_config = {}

	def render_text(label, value, key):
		text_str = f"{label}: {value}"
		color = highlight_config.get(key, {}).get("color", (0, 0, 0))
		font = bold_font if highlight_config.get(key, {}).get("bold", False) else regular_font
		return font.render(text_str, True, color)

	# Top line: previous and next song entries
	arrow_color = (0, 0, 0)
	pygame.draw.polygon(screen, arrow_color, [(20, 10), (20, 30), (10, 20)])  # left arrow
	prev_text = regular_font.render(previous_entry, True, arrow_color)
	screen.blit(prev_text, (30, 10))

	next_text_surface = regular_font.render(next_entry, True, arrow_color)
	next_text_width = next_text_surface.get_width()
	pygame.draw.polygon(screen, arrow_color, [(460, 10), (470, 20), (460, 30)])  # right arrow
	screen.blit(next_text_surface, (480 - next_text_width - 30, 10))

	# Song title
	song_color = highlight_config.get("songName", {}).get("color", (0, 0, 0))
	song_title = title_font.render(song.song, True, song_color)
	screen.blit(song_title, (10, 50))

	# Samples
	for i in range(3):
		try:
			sample_text = render_text(f"sample {i+1}", song.sample[i], f"sample{i+1}")
		except (ValueError, IndexError):
			sample_text = render_text(f"sample {i+1}", "empty", f"sample{i+1}")
		screen.blit(sample_text, (10, 100 + i * 30))

	# Last line: AUDIO and VIDEO
	audio_label = "muted" if muted else f"{int(volume_percent * 100)}%"
	audio_color = highlight_config.get("audio", {}).get("color", (0, 0, 0))
	audio_font = bold_font if highlight_config.get("audio", {}).get("bold", False) else regular_font
	audio_text = audio_font.render(f"AUDIO {audio_label}", True, audio_color)
	screen.blit(audio_text, (10, 280))

	video_color = highlight_config.get("video", {}).get("color", (0, 0, 0))
	video_font = bold_font if highlight_config.get("video", {}).get("bold", False) else regular_font
	video_text = video_font.render("VIDEO", True, video_color)
	screen.blit(video_text, (480 - video_text.get_width() - 10, 280))

	pygame.display.flip()



########
# MAIN #
########

# Load the JSON data from the file
with open('./playlist.json', 'r', encoding='utf-8') as file:
	data = json.load(file)

# Create a list of Song objects
playList = [Song(item['song'], item['video'], item['sample'], item['startPosition']) for item in data]

# Print the playlist to verify
#for song in playList:
#	print(song)


# Initialize Pygame
pygame.init()
pygame.mixer.init()
pygame.mixer.music.set_volume (audioVolume)

# Get display information
display_info = pygame.display.Info()
screen_width, screen_height = display_info.current_w, display_info.current_h

# Create a Pygame window on the primary screen
#pygame_screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
screen = pygame.display.set_mode((480, 320))
pygame.display.set_caption("Song Info Display")

# Create a blank image for OpenCV
opencv_image = np.zeros((600, 800, 3), dtype=np.uint8)
# Move OpenCV window to the secondary screen
#cv2.namedWindow("OpenCV Window", cv2.WINDOW_NORMAL)
#cv2.resizeWindow("OpenCV Window", 800, 600)
#cv2.moveWindow("OpenCV Window", screen_width + 100, 100)  # Adjust position for secondary screen
# Create a named window; the flags control window behavior
# cv2.WINDOW_NORMAL allows resizing, cv2.WINDOW_AUTOSIZE fixes it to image size
cv2.namedWindow('Video', cv2.WINDOW_NORMAL)
# Resize the window to a specific size (width, height)
cv2.resizeWindow('Video', 800, 600)
# Move the window to a specific location on the screen (x, y)
cv2.moveWindow('Video', 800, 0)



# Main loop
eq = EventQueue()		# event queue to manage the events happening in the main loop
# force display of 1st song in playlist and video by faking a press on "previous" key; this will force the display in its turn
eq.record_event("key", ["previous"])


while running:

	# Handle Pygame events
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False

	# Handle main loop events
	next_event = eq.get_next_event()
	if next_event:		# make sure there is an event to process

		# display events
		if next_event.label == "display":
			displaySongInfo (screen, playList [playListIndex], volume_percent=audioVolume, previous_entry=playList [playListPrevious].song, next_entry=playList [playListNext].song, highlight_config=next_event.values, muted=muted)

		# key events
		if next_event.label == "key":

			# quit
			if next_event.values [0] == "quit":
				running = False
				break

			# previous
			if next_event.values [0] == "previous":
				# get video file name that is currently playing
				try:
					previousVideoFileName = videoPath + playList [playListIndex].video
				except (ValueError, IndexError):
					previousVideoFileName = ""
				# previous in playlist
				playListIndex = max(playListIndex - 1, 0)
				playListPrevious = max(playListIndex - 1, 0)
				playListNext = min(playListIndex + 1, len(playList) - 1)
				# record new event to update the display
				eq.record_event("display", {
					"songName": {"bold": True, "color": (64,224,208)},	# turquoise and bold
					"audio": {"bold": True, "color": (0, 128, 0)},		# green and bold
					"video": {"bold": True, "color": (0, 128, 0)}		# green and bold
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
					"songName": {"bold": True, "color": (64,224,208)},	# turquoise and bold
					"audio": {"bold": True, "color": (0, 128, 0)},		# green and bold
					"video": {"bold": True, "color": (0, 128, 0)}		# green and bold
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
					sampleString = "sample" + str (int (next_event.values [1]) - 1)
					eq.record_event("audio", ["play", sampleString, sampleFileName])

		# audio events
		if next_event.label == "audio":

			# stop
			if next_event.values [0] == "stop":
				stop_audio()
				playing = False
				# record new event to update the display
				eq.record_event("display", {
					"songName": {"bold": True, "color": (64,224,208)},	# turquoise and bold
					"audio": {"bold": True, "color": (0, 128, 0)}		# green and bold
				})

			# play
			if next_event.values [0] == "play":
				# attempt to open audio file and play it
				sampleString = next_event.values [1]
				sampleFileName = next_event.values [2]
				playing = start_audio_thread (sampleFileName)
				# record new event to update the display, based on the result of playing (sample exists or not)
				if playing:
					eq.record_event("display", {
						"songName": {"bold": True, "color": (64,224,208)},	# turquoise and bold
						"audio": {"bold": True, "color": (0, 128, 0)},		# green and bold
						sampleString: {"bold": False, "color": (0, 0, 255)}	# blue
					})
				else:
					eq.record_event("display", {
						"songName": {"bold": True, "color": (64,224,208)},	# turquoise and bold
						"audio": {"bold": True, "color": (255, 165, 0)}		# orange (ie. warning) and bold
					})

		# video events
		if next_event.label == "video":

			# play
			if next_event.values [0] == "play":
#				print (next_event.values [0], next_event.values [1], next_event.values [2], next_event.values [3])
				videoFileName = next_event.values [1]
				previousVideoFileName = next_event.values [2]
				print (videoFileName, previousVideoFileName)
				# if video is same as previous, then don't restart video... we just carry on showing
				if videoFileName != previousVideoFileName:
					cap = cv2.VideoCapture(videoFileName)						# cap.isOpened() returns False if file does not exist
					# in case file does not exists, cap.isOpened () will return False
					if not cap.isOpened():
						# file does not exist, update song info
						eq.record_event("display", {
							"songName": {"bold": True, "color": (64,224,208)},	# turquoise and bold
							"audio": {"bold": True, "color": (255, 165, 0)},	# orange (ie. warning) and bold
							"video": {"bold": True, "color": (255, 165, 0)}		# orange (ie. warning) and bold
						})
					else:
						# determine startPos, and set it to video
						if next_event.values [3] == "beginning":
							startPos = 0
						else:
							startPos = random.randint (0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
						# set start position
						cap.set(cv2.CAP_PROP_POS_FRAMES, startPos)				



	# Perform non-event based functions, ie. video display and key capture

	# display video (if exists)
	if cap is not None and cap.isOpened():
		ret, frame = cap.read()

		# If the video ends, restart it
		if not ret:
			cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
			continue
		# display video frame
		cv2.imshow("Video", frame)

	# check if raspi keypress
	if raspiTarget:
		pass

	# check if a key has been pressed; if so, then change display and video 
	# Check key presses for 25ms
	# if key press, then break and the rest will be managed in the main loop
	keyPressed = cv2.waitKey(25)
	if keyPressed != -1:
		keyPressed &= 0xFF
		if keyPressed == ord ('q'):
			eq.record_event("key", ["quit"])
		if keyPressed == ord ('p'):
			eq.record_event("key", ["previous"])
		if keyPressed == ord ('n'):
			eq.record_event("key", ["next"])
		if keyPressed == ord ('1'):
			eq.record_event("key", ["sample", "1"])
		if keyPressed == ord ('2'):
			eq.record_event("key", ["sample", "2"])
		if keyPressed == ord ('3'):
			eq.record_event("key", ["sample", "3"])

	# check if raspi rotary
	if raspiTarget:
		pass
		# check if volume is changed
		# check mute button
		#muted = True



# Cleanup
stop_audio()
cap.release()
cv2.destroyAllWindows()
pygame.mixer.music.stop()
pygame.quit()
