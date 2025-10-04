import pygame
import cv2
import os
import json
import random
import numpy as np
import threading
from collections import deque

#TO DO
# test: audio file does not exist, video file does not exist
# force video play of the first song
# highlight_config: make sure we display the right things at the right time (error mgmt)
# raspi keys
# raspi rotary





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



def render_navigation(screen, previous_entry, next_entry, font, screen_width):
	arrow_color = (0, 0, 0)
	nav_y = 0  # Top of screen
	arrow_width = 10
	spacing = 10
	nav_offset = arrow_width + spacing

	# Previous entry and left arrow
	prev_text_surface = font.render(previous_entry, True, arrow_color)
	screen.blit(prev_text_surface, (nav_offset + arrow_width, nav_y))
	pygame.draw.polygon(screen, arrow_color, [
		(nav_offset, nav_y + 5),
		(nav_offset, nav_y + 25),
		(nav_offset - arrow_width, nav_y + 15)
	])

	# Next entry and right arrow
	next_text_surface = font.render(next_entry, True, arrow_color)
	next_text_width = next_text_surface.get_width()
	next_text_x = screen_width - nav_offset - arrow_width - next_text_width
	screen.blit(next_text_surface, (next_text_x, nav_y))
	pygame.draw.polygon(screen, arrow_color, [
		(screen_width - nav_offset, nav_y + 5),
		(screen_width - nav_offset + arrow_width, nav_y + 15),
		(screen_width - nav_offset, nav_y + 25)
	])

def displaySongInfo(screen, song, volume_percent, rate_percent, previous_entry="", next_entry="", highlight_config=None):
	screen.fill((255, 255, 255))  # white background

	pygame.font.init()
	def get_font(size, bold=False):
		return pygame.font.SysFont('Arial', int(size * 1.2), bold=bold)

	# Fonts
	title_font = get_font(32 * 1.1, bold=True)  # Song title 10% bigger
	regular_font = get_font(20)
	bold_font = get_font(20, bold=True)

	bottom_regular_font = pygame.font.SysFont('Arial', 20)
	bottom_bold_font = pygame.font.SysFont('Arial', 20, bold=True)

	highlight_config = highlight_config or {}

	def render_text(label, value, key, font_override=None, color_override=None):
		text_str = f"{label}: {value}"
		config = highlight_config.get(key, {})
		color = color_override if color_override else config.get("color", (0, 0, 0))
		font = font_override if font_override else (bold_font if config.get("bold", False) else regular_font)
		return font.render(text_str, True, color)

	screen_width, screen_height = screen.get_size()
	render_navigation(screen, previous_entry, next_entry, regular_font, screen_width)

	# Song title
	song_color = highlight_config.get("songName", {}).get("color", (0, 0, 0))
	song_title_surface = title_font.render(song.song, True, song_color)
	screen.blit(song_title_surface, (10, 30))

	# Video name
	video_name_surface = render_text("video", song.video, "videoName", font_override=regular_font, color_override=(0, 0, 139))
	screen.blit(video_name_surface, (10, 80))

	# Samples
	sample_start_y = 130
	sample_spacing = 50
	for i in range(3):
		sample_value = song.sample[i] if i < len(song.sample) else "empty"
		sample_surface = render_text(f"sample {i+1}", sample_value, f"sample{i+1}")
		screen.blit(sample_surface, (10, sample_start_y + i * sample_spacing))

	# AUDIO
	audio_label = f"{int(volume_percent * 100)}%"
	audio_config = highlight_config.get("audio", {})
	audio_color = audio_config.get("color", (0, 0, 0))
	audio_font = bottom_bold_font if audio_config.get("bold", False) else bottom_regular_font
	audio_surface = audio_font.render(f"AUDIO {audio_label}", True, audio_color)
	screen.blit(audio_surface, (10, screen_height - 30))  # ~10px from bottom

	# VIDEO with rate_percent
	video_config = highlight_config.get("video", {})
	video_color = video_config.get("color", (0, 0, 0))
	video_font = bottom_bold_font if video_config.get("bold", False) else bottom_regular_font
	video_text = f"VIDEO {int(rate_percent * 100)}%"
	video_surface = video_font.render(video_text, True, video_color)
	screen.blit(video_surface, (screen_width - video_surface.get_width() - 10, screen_height - 30))  # ~10px from bottom

	pygame.display.flip()



"""
highlight_config = {
	"songName": {"color": (255, 0, 0), "bold": True},	   # Red and bold
	"videoName": {"color": (0, 0, 139), "bold": False},	 # Dark blue and regular
	"sample1": {"color": (0, 128, 0), "bold": True},		# Green and bold
	"audio": {"color": (128, 0, 128), "bold": True},		# Purple and bold
	"video": {"color": (0, 0, 0), "bold": False}			# Black and regular
}
"""
	
	
########
# MAIN #
########

# Load the JSON data from the file
with open('./playlist.json', 'r', encoding='utf-8') as file:
	data = json.load(file)

# Create a list of Song objects
playList = [Song(item['song'], item['video'], item['sample'], item['startPosition']) for item in data]


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
			displaySongInfo (screen, playList [playListIndex], volume_percent=audioVolume, rate_percent=videoRate, previous_entry=playList [playListPrevious].song, next_entry=playList [playListNext].song, highlight_config=next_event.values)

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
				videoFileName = next_event.values [1]
				previousVideoFileName = next_event.values [2]
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
		# button would switch between audio volume and video rate



# Cleanup
stop_audio()
if cap is not None:
	cap.release()
cv2.destroyAllWindows()
pygame.mixer.music.stop()
pygame.quit()
