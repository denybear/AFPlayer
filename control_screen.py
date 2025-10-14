import pygame


# Global variable to store screen area ratios
screen_area_ratios = {
	"top": 0.1,
	"info": 0.2,
	"sample": 0.5,
	"slider": 0.2
}


default_config = {
	"previous": {"font_size": 0.06, "bold": True, "italic": False, "inverse": False, "color": (0, 0, 0), "font_name": "verdana", "spacing": 1.0},
	"next": {"font_size": 0.06, "bold": True, "italic": False, "inverse": False, "color": (0, 0, 0), "font_name": "verdana", "spacing": 1.0},
	"song": {"font_size": 0.08, "bold": True, "italic": False, "inverse": False, "color": (0, 128, 255), "font_name": "verdana", "spacing": 1.0},
	"video": {"font_size": 0.05, "bold": False, "italic": True, "inverse": False, "color": (128, 0, 128), "font_name": "verdana", "spacing": 1.0},
	"sample": {"font_size": 0.05, "bold": False, "italic": False, "inverse": False, "color": (0, 100, 0), "font_name": "couriernew", "spacing": 1.5},
	"video_rate": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": (0, 100, 0), "font_name": "arial", "spacing": 1.0},
	"audio_volume": {"font_size": 0.04, "bold": True, "italic": False, "inverse": False, "color": (0, 100, 0), "font_name": "arial", "spacing": 1.0}
}


def configureScreenAreas(top_ratio, info_ratio, sample_ratio, slider_ratio):
	"""
	Configure the height ratios for each screen section.
	Ratios must sum to 1.0.
	"""
	global screen_area_ratios
	total = top_ratio + info_ratio + sample_ratio + slider_ratio
	if abs(total - 1.0) > 0.01:
		raise ValueError("Total of all ratios must be approximately 1.0")
	screen_area_ratios = {
		"top": top_ratio,
		"info": info_ratio,
		"sample": sample_ratio,
		"slider": slider_ratio
	}


def displaySongInfo(screen, song, volume_percent, rate_percent, previous_entry="", next_entry="", highlight_config=None):
	pygame.font.init()
	screen_width, screen_height = screen.get_size()
	screen.fill((255, 255, 255))  # White background

	# merge provided config (highlight_config) with default_config
	merged_config = default_config.copy()
	if highlight_config:
		for key in highlight_config:
			if key in merged_config:
				merged_config[key].update(highlight_config[key])
			else:
				merged_config[key] = highlight_config[key]

	def get_style(key):
		cfg = merged_config.get(key, {})
		font_size = int(cfg.get("font_size", 0.05) * screen_height)
		bold = cfg.get("bold", False)
		italic = cfg.get("italic", False)
		inverse = cfg.get("inverse", False)
		color = cfg.get("color", (0, 0, 0))
		font_name = cfg.get("font_name", None)
		spacing = cfg.get("spacing", 1.0)
		font = pygame.font.SysFont(font_name, font_size, bold=bold, italic=italic)
		return font, font_size, color, inverse, spacing

	def get_style_from_cfg(cfg):
		font_size = int(cfg.get("font_size", 0.05) * screen_height)
		bold = cfg.get("bold", False)
		italic = cfg.get("italic", False)
		inverse = cfg.get("inverse", False)
		color = cfg.get("color", (0, 0, 0))
		font_name = cfg.get("font_name", None)
		spacing = cfg.get("spacing", 1.0)
		font = pygame.font.SysFont(font_name, font_size, bold=bold, italic=italic)
		return font, font_size, color, inverse, spacing

	# Calculate area positions
	top_height = int(screen_area_ratios["top"] * screen_height)
	info_height = int(screen_area_ratios["info"] * screen_height)
	sample_height = int(screen_area_ratios["sample"] * screen_height)
	slider_height_total = int(screen_area_ratios["slider"] * screen_height)

	info_top = top_height
	sample_top = info_top + info_height
	slider_top = sample_top + sample_height
	video_slider_y = slider_top
	audio_slider_y = slider_top + slider_height_total // 2

	# Top area: arrows and previous/next song
	arrow_height = int(0.6 * top_height)
	arrow_width = int(arrow_height * 0.6)
	spacing_arrow = 20

	left_arrow_rect = pygame.Rect(0, 0, arrow_width, top_height)
	right_arrow_rect = pygame.Rect(screen_width - arrow_width, 0, arrow_width, top_height)

	pygame.draw.polygon(screen, (0, 0, 0), [(left_arrow_rect.left, top_height // 2),
											(left_arrow_rect.right, top_height // 2 - arrow_height // 2),
											(left_arrow_rect.right, top_height // 2 + arrow_height // 2)])
	pygame.draw.polygon(screen, (0, 0, 0), [(right_arrow_rect.right, top_height // 2),
											(right_arrow_rect.left, top_height // 2 - arrow_height // 2),
											(right_arrow_rect.left, top_height // 2 + arrow_height // 2)])

	font_prev, _, color_prev, inverse_prev, _ = get_style("previous")
	prev_surface = font_prev.render(previous_entry, True, (255, 255, 255) if inverse_prev else color_prev)
	prev_x = left_arrow_rect.right + spacing_arrow
	prev_y = (top_height - prev_surface.get_height()) // 2
	if inverse_prev:
		pygame.draw.rect(screen, color_prev, prev_surface.get_rect(topleft=(prev_x, prev_y)))
	screen.blit(prev_surface, (prev_x, prev_y))

	font_next, _, color_next, inverse_next, _ = get_style("next")
	next_surface = font_next.render(next_entry, True, (255, 255, 255) if inverse_next else color_next)
	next_x = right_arrow_rect.left - spacing_arrow - next_surface.get_width()
	next_y = (top_height - next_surface.get_height()) // 2
	if inverse_next:
		pygame.draw.rect(screen, color_next, next_surface.get_rect(topleft=(next_x, next_y)))
	screen.blit(next_surface, (next_x, next_y))

	# Song and video titles
	font_song, _, color_song, inverse_song, spacing_song = get_style("song")
	song_surface = font_song.render(song.song, True, (255, 255, 255) if inverse_song else color_song)
	song_x = (screen_width - song_surface.get_width()) // 2
	song_y = info_top
	if inverse_song:
		pygame.draw.rect(screen, color_song, song_surface.get_rect(topleft=(song_x, song_y)))
	screen.blit(song_surface, (song_x, song_y))

	font_video, _, color_video, inverse_video, spacing_video = get_style("video")
	video_surface = font_video.render(song.video, True, (255, 255, 255) if inverse_video else color_video)
	video_x = (screen_width - video_surface.get_width()) // 2
	video_y = song_y + int(font_song.get_height() * spacing_video)
	if inverse_video:
		pygame.draw.rect(screen, color_video, video_surface.get_rect(topleft=(video_x, video_y)))
	screen.blit(video_surface, (video_x, video_y))

	# Sample list and individual samples
	sample_rects = []
	sample_y = sample_top
	for i, sample_text in enumerate(song.sample):
		sample_key = f"sample{i+1}"
		# Start with the merged "sample" config
		sample_cfg = merged_config["sample"].copy()
		# If highlight_config has a specific config for this sample, merge it
		if highlight_config and sample_key in highlight_config:
			sample_cfg.update(highlight_config[sample_key])
		# Get style for this sample
		font_sample, sample_size, color_sample, inverse_sample, spacing_sample = get_style_from_cfg(sample_cfg)
		label = f"Sample {i+1}: {sample_text}"
		sample_x = int(0.02 * screen_width)
		sample_surface = font_sample.render(label, True, (255, 255, 255) if inverse_sample else color_sample)
		if inverse_sample:
			pygame.draw.rect(screen, color_sample, sample_surface.get_rect(topleft=(sample_x, sample_y)))
		screen.blit(sample_surface, (sample_x, sample_y))
		sample_rects.append((pygame.Rect(sample_x, sample_y, sample_surface.get_width(), sample_surface.get_height()), label))
		sample_y += int(sample_size * spacing_sample)

	# Sliders
	font_rate, _, color_rate, inverse_rate, _ = get_style("video_rate")
	font_volume, _, color_volume, inverse_volume, _ = get_style("audio_volume")

	slider_width = int(0.6 * screen_width)
	slider_x = int(0.35 * screen_width)
	slider_bar_height = 4

	# Video rate slider
	video_slider_rect = pygame.Rect(slider_x, video_slider_y + 20, slider_width, slider_bar_height + 20)
	rate_pos = slider_x + int(rate_percent * slider_width)
	pygame.draw.rect(screen, color_rate, (slider_x, video_slider_y + 20, slider_width, slider_bar_height))
	pygame.draw.circle(screen, color_rate, (rate_pos, video_slider_y + 20 + slider_bar_height // 2), 10)
	rate_label_text = f"VIDEO RATE: {int(rate_percent * 100)}%"
	rate_label = font_rate.render(rate_label_text, True, (255, 255, 255) if inverse_rate else color_rate)
	screen.blit(rate_label, (int(0.02 * screen_width), video_slider_y))

	# Audio volume slider
	audio_slider_rect = pygame.Rect(slider_x, audio_slider_y + 20, slider_width, slider_bar_height + 20)
	volume_pos = slider_x + int(volume_percent * slider_width)
	pygame.draw.rect(screen, color_volume, (slider_x, audio_slider_y + 20, slider_width, slider_bar_height))
	pygame.draw.circle(screen, color_volume, (volume_pos, audio_slider_y + 20 + slider_bar_height // 2), 10)
	volume_label_text = f"AUDIO VOLUME: {int(volume_percent * 100)}%"
	volume_label = font_volume.render(volume_label_text, True, (255, 255, 255) if inverse_volume else color_volume)
	screen.blit(volume_label, (int(0.02 * screen_width), audio_slider_y))

	pygame.display.flip()

	return {
		"video_slider_rect": video_slider_rect,
		"audio_slider_rect": audio_slider_rect,
		"video_knob_x": rate_pos,
		"audio_knob_x": volume_pos,
		"sample_rects": sample_rects,
		"arrow_left_rect": left_arrow_rect,
		"arrow_right_rect": right_arrow_rect
	}