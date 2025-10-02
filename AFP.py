import pygame
import cv2
import os
import json
import random
import numpy as np
#from display_song_info import displaySongInfo

#TO DO
# variables raspiTarget et pcTarget pour le controle des touches
# sur raspi, peut-on interrompre avec un clavier?
# si problème audio, on ne joue pas audio; idem si pb video
# si video ou audio n'existe pas, on ne joue pass
# UI à redéfinir


# Global variables
audio_thread = None
videoPath = "./video/"
audioPath = "./audio/"
raspiTarget = True
pcTarget = True


# object representing a tuple: name of the song, name of the video/picture, name of samples 
class Song:
	def __init__(self, song="", video="", sample=["","",""], startPosition="beginning"):
		self.song = song
		self.video = video
		self.sample = sample
		self.startPosition = startPosition

	def __repr__(self):
		return f"Song(song={self.song}, video={self.video}, sample={self.sample}, startPosition={self.startPosition})"



# functions to play an audio sample 
def play_audio(audio_file):
	pygame.mixer.music.load(audio_file)
	pygame.mixer.music.play()

def stop_audio():
	pygame.mixer.music.stop()

def start_audio_thread(audio_file):
	global audio_thread
	stop_audio()
	audio_thread = threading.Thread(target=play_audio, args=(audio_file,))
	audio_thread.start()




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
volume = 0.5
muted = False
pygame.mixer.music.set_volume (volume)
# force display of 1st song in playlist and video
playListIndex = 0
keyed = True
keyPressed = ord ('p')

running = True
playing = False
previousVideoFileName = ""

while running:

	# Handle Pygame events
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False

	# check if a key has been pressed; if so, then change display and video 
	if keyed:
		keyed = False

		# quit
		if keyPressed == ord ('q'):
			running = False
			break

		# next or previous
		elif keyPressed == ord ('p') or keyPressed == ord ('n'):
			if keyPressed == ord ('p'):
				# previous in playlist
				playListIndex = max(playListIndex - 1, 0)
			elif keyPressed == ord ('n'):
				# next in playlist
				playListIndex = min(playListIndex + 1, len(playList) - 1)

			playListPrevious = max(playListIndex - 1, 0)
			playListNext = min(playListIndex + 1, len(playList) - 1)
			# display song info
			highlight_config = {
				"songName": {"bold": True, "color": (64,224,208)},  # turquoise and bold
				"audio": {"bold": True, "color": (0, 128, 0)}	# green and bold
			}
			displaySongInfo (screen, playList [playListIndex], volume_percent=volume, previous_entry=playList [playListPrevious].song, next_entry=playList [playListNext].song, highlight_config=highlight_config, muted=muted)


			# if video is same as previous, then don't restart video... we just carry on showing
			videoFileName = videoPath + playList [playListIndex].video
#HERE: make sure video exists
			if videoFileName != previousVideoFileName:
				cap = cv2.VideoCapture(videoFileName)
				previousVideoFileName = videoFileName
				# determine startPos, and set it to video
				if playList [playListIndex].startPosition == "beginning":
					startPos = 0
				else:
					startPos = random.randint (0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
				# set start position
				cap.set(cv2.CAP_PROP_POS_FRAMES, startPos)				
				

		# sample keys are pressed
		elif keyPressed == ord ('1') or keyPressed == ord ('2') or keyPressed == ord ('3'):
			sampleString = "sample" + keyPressed
			try:
				sampleFileName = audioPath + playList [playListIndex].sampleFileName [int (keyPressed - 1)]
			except (ValueError, IndexError):
				sampleFileName = ""

			if playing:
				stop_audio()
				playing = False
				# display song info
				highlight_config = {
					"songName": {"bold": True, "color": (64,224,208)},  # turquoise and bold
					"audio": {"bold": True, "color": (0, 128, 0)}	# green and bold
				}
				displaySongInfo (screen, playList [playListIndex], volume_percent=volume, previous_entry=playList [playListPrevious].song, next_entry=playList [playListNext].song, highlight_config=highlight_config, muted=muted)

			else:
				if sampleFileName != "":
					start_audio_thread (sampleFileName)
					playing = True
					# display song info
					highlight_config = {
						"songName": {"bold": True, "color": (64,224,208)},  # turquoise and bold
						"audio": {"bold": True, "color": (0, 128, 0)},	# green and bold
						sampleString: {"bold": False, "color": (0, 0, 255)}	# blue
					}
					displaySongInfo (screen, playList [playListIndex], volume_percent=volume, previous_entry=playList [playListPrevious].song, next_entry=playList [playListNext].song, highlight_config=highlight_config, muted=muted)



	# main loop for video
	while cap.isOpened():
		ret, frame = cap.read()

		# If the video ends, restart it
		if not ret:
			cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
			continue
		
		cv2.imshow("Video", frame)

		# Check key presses for 25ms
		# if key press, then break and the rest will be managed in the main loop
		keyPressed = cv2.waitKey(25)
		if keyPressed != -1:
			keyPressed &= 0xFF
			keyed = True
			break

		# check if volume is changed
		# check mute button
		#muted = True



# Cleanup
stop_audio()
cap.release()
cv2.destroyAllWindows()
pygame.mixer.music.stop()
pygame.quit()
