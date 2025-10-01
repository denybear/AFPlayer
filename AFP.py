import pygame
import cv2
import os
import json
import random

# TO DO
# highlight des choses qui jouent
# logo HP pour le volume


# Global variables
audio_thread = None
videoPath = "./video/"
audioPath = "./audio/"

# object representing a tuple: name of the song, name of the video/picture, name of samples 
class Song:
    def __init__(self, song="", video="", sample=["","",""], startPosition="beginning"):
        self.song = song
        self.video = video
        self.sample = sample
        self.startPosition = startPosition

    def __repr__(self):
        return f"Song(song={self.song}, video={self.video}, sample={self.sample}, startPosition={self.startPosition})"



# function to display the current song in playList
def displaySongInfo (screen, song, volume_percent, previous_entry="", next_entry=""):
	screen.fill((255, 255, 255))  # white background

	# Initialisation des polices
	pygame.font.init()
	title_font = pygame.font.SysFont('Arial', 28, bold=True)
	regular_font = pygame.font.SysFont('Arial', 20)

	# Préparation des textes
	title_text = title_font.render(song.songName, True, (0, 0, 0))
	volume_text = title_font.render(f"volume {volume_percent*100.0}%", True, (0, 0, 0))
	previous_text = regular_font.render(f"previous in playlist: {previous_entry}", True, (0, 0, 0))
	try:
		sample1_text = regular_font.render(f"sample 1: {song.sample [0]}", True, (0, 0, 0))
	except ValueError:
		sample1_text = regular_font.render(f"sample 1: empty", True, (0, 0, 0))
	try:
		sample2_text = regular_font.render(f"sample 2: {song.sample [1]}", True, (0, 0, 0))
	except ValueError:
		sample2_text = regular_font.render(f"sample 2: empty", True, (0, 0, 0))
	try:
		sample3_text = regular_font.render(f"sample 3: {song.sample [2]}", True, (0, 0, 0))
	except ValueError:
		sample3_text = regular_font.render(f"sample 3: empty", True, (0, 0, 0))
	next_text = regular_font.render(f"next in playlist: {next_entry}", True, (0, 0, 0))

	# Affichage des textes
	screen.blit(title_text, (10, 10))
	screen.blit(volume_text, (320 - volume_text.get_width() - 10, 10))
	screen.blit(previous_text, (10, 50))
	screen.blit(sample1_text, (10, 80))
	screen.blit(sample2_text, (10, 110))
	screen.blit(sample3_text, (10, 140))
	screen.blit(next_text, (10, 170))

	pygame.display.flip()


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



########
# MAIN #
########

# Load the JSON data from the file
with open('./playlist.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Create a list of Song objects
playList = [Song(item['song'], item['video'], item['sample'], item['startPosition']) for item in data]

# Print the playlist to verify
for song in playList:
    print(song)


# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Get display information
display_info = pygame.display.Info()
screen_width, screen_height = display_info.current_w, display_info.current_h

# Create a Pygame window on the primary screen
#pygame_screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
screen = pygame.display.set_mode((320, 480))
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
cv2.moveWindow('Video', 100, 50)



# Main loop
volume = 0.5
pygame.mixer.sound.set_volume (volume)
# force display of 1st song in playlist and video
playListIndex = 0
keyed = True
keyPressed == ord ('p')

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

		# next or previous
		elif keyPressed == ord ('p') or keyPressed == ord ('n'):
			if keyPressed == ord ('p'):
				# previous in playlist
				playListIndex = playListIndex - 1 if playListIndex > 0 else playListIndex = 0
			else keyPressed == ord ('n'):
				# next in playlist
				playListIndex = playListIndex + 1 if playListIndex < len (playList) - 1 else playListIndex = len (playList) - 1
			
			playListPrevious = playListIndex - 1 if playListIndex > 0 else playListPrevious = 0
			playListNext = playListIndex + 1 if playListIndex < len (playList) - 1 else playListNext = len (playList) - 1
			displaySongInfo (screen, playList [playListIndex], volume_percent=volume, previous_entry=playList [playListPrevious].song, next_entry=playList [playListNext].song)


			# if video is same as previous, then don't restart video... we just carry on showing
			videoFileName = videoPath + playList [playListIndex].video
			if videoFileName not previousVideoFileName:
				cap = cv2.VideoCapture(videoFileName)
				previousVideoFileName = videoFileName
				# determine startPos, and set it to video
				if playList [playListIndex].startPosition == "beginning":
					startPos = 0
				else:
					startPos = randint (0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
				# set start position
				cap.set(cv2.CAP_PROP_POS_FRAMES, startPos)				
				

		# sample keys are pressed
		elif keyPressed == ord ('1') or keyPressed == ord ('2') or keyPressed == ord ('3'):
			try:
				sampleFileName = audioPath + playList [playListIndex].sampleFileName [int (keyPressed - 1)]
			except ValueError:
				sampleFileName = ""

			if playing:
				stop_audio()
				playing = False
			else:
				if sampleFileName not "":
					start_audio_thread (sampleFileName)
					playing = True

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
		if keyPressed = (cv2.waitKey(25) & 0xFF):
			keyed = True
			break

		# check if volume is changed
		# check mute button



# Cleanup
stop_audio()
cap.release()
cv2.destroyAllWindows()
pygame.mixer.music.stop()
pygame.quit()
sys.exit()
