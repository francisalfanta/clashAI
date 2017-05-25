import sys
import os
os.environ["path"] = os.path.dirname(sys.executable) + ";" + os.environ["path"]
import glob
import operator
import datetime
import dateutil.relativedelta
import win32gui
import win32ui
import win32con
import win32api
import numpy
import json
import csv
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import scipy.ndimage
import multiprocessing
import nltk
import matplotlib.pyplot as plt
#from nltk.sentiment.vader import SentimentIntensityAnalyzer
#from sklearn.externals import joblib
from time import strftime
from time import sleep
from PIL import Image
#from sklearn import svm
#from sklearn.neural_network import MLPRegressor
#from sklearn.preprocessing import StandardScaler
#from sklearn.metrics import label_ranking_average_precision_score

DATA_FOLDER = "data"
RED = 2
GREEN = 1
BLUE = 0
MAX_COLOR_DIFF = 15 # 0 to 255
PRINT_LEVEL=0
def myprint(msg, level=0):
	if (level >= PRINT_LEVEL):
		sys.stdout.buffer.write((str(msg) + "\n").encode('UTF-8'))
		
# =============================================================================
# WINAPI SEQUENCE RUN	
def moveMouse(x,y):
	win32api.SetCursorPos((x,y))	

def click(x,y):
	win32api.SetCursorPos((x,y))
	sleep(.5)
	win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
	sleep(.5)
	win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)		

def getWindowByTitle(title_text, exact = False):
	def _window_callback(hwnd, all_windows):
		all_windows.append((hwnd, win32gui.GetWindowText(hwnd)))
	windows = []
	win32gui.EnumWindows(_window_callback, windows)
	if exact:
		return [hwnd for hwnd, title in windows if title_text == title]
	else:
		return [hwnd for hwnd, title in windows if title_text in title]
		
gScreen = []
gScreenAlpha = []
gScreenOffsetT = 0
gScreenOffsetL = 0
gScreenWidth = 0
gScreenHeight = 0
def updateScreen(hwnd = None, wait_focus=True):
	a = ScopedTimer("updateScreen")
	global gScreen
	global gScreenAlpha
	global gScreenOffsetT
	global gScreenOffsetL
	global gScreenWidth
	global gScreenHeight
	
	global gScreenNumpy
	global gScreenAlphaNumpy
	
	if not hwnd:
		hwnd=win32gui.GetDesktopWindow()
	l,t,r,b=win32gui.GetWindowRect(hwnd)
	gScreenOffsetT = t
	gScreenOffsetL = l
	h=b-t
	w=r-l
	gScreenWidth = w
	gScreenHeight = h
	hDC = win32gui.GetWindowDC(hwnd)
	myDC=win32ui.CreateDCFromHandle(hDC)
	newDC=myDC.CreateCompatibleDC()

	myBitMap = win32ui.CreateBitmap()
	myBitMap.CreateCompatibleBitmap(myDC, w, h)

	newDC.SelectObject(myBitMap)

	win32gui.SetForegroundWindow(hwnd)
	if wait_focus:
		sleep(.2) #lame way to allow screen to draw before taking shot
	newDC.BitBlt((0,0),(w, h) , myDC, (0,0), win32con.SRCCOPY)
	myBitMap.Paint(newDC)
	asTuple = myBitMap.GetBitmapBits(False)
	
	# transform asTuple into modifiable list
	gScreen = numpy.array(asTuple)
	gScreen = numpy.where(gScreen < 0, gScreen + 2**8, gScreen)
	gScreen = gScreen.reshape(gScreenHeight * gScreenWidth, 4)
	gScreenAlpha = gScreen
	
	myprint("screenWidth : " + str(gScreenWidth) + ", screenHeight : " + str(gScreenHeight) + ", offsetL : " + str(gScreenOffsetL)  + ", offsetT : " + str(gScreenOffsetT))

def gScreenToNumpy():
	global gScreenNumpy
	gScreenNumpy = numpy.array(gScreen)
	gScreenNumpy = gScreenNumpy.reshape(gScreenHeight, gScreenWidth, 3)
	gScreenNumpy = gScreenNumpy / 255.0
		
def takeScreenshot(hwnd = None):
	global gScreenshotCount
	if not hwnd:
		hwnd=win32gui.GetDesktopWindow()
	l,t,r,b=win32gui.GetWindowRect(hwnd)
	gScreenOffsetT = t
	gScreenOffsetL = l
	h=b-t
	w=r-l
	gScreenWidth = w
	gScreenHeight = h
	hDC = win32gui.GetWindowDC(hwnd)
	myDC=win32ui.CreateDCFromHandle(hDC)
	newDC=myDC.CreateCompatibleDC()

	myBitMap = win32ui.CreateBitmap()
	myBitMap.CreateCompatibleBitmap(myDC, w, h)

	newDC.SelectObject(myBitMap)

	win32gui.SetForegroundWindow(hwnd)
	sleep(.2) #lame way to allow screen to draw before taking shot
	newDC.BitBlt((0,0),(w, h) , myDC, (0,0), win32con.SRCCOPY)
	myBitMap.Paint(newDC)	
	
	pathbmp = os.path.join(DATA_FOLDER, "screenshots")
	if not os.path.isdir(pathbmp):
		os.makedirs(pathbmp)
	
	timestr = strftime("%Y%m%d-%H%M%S")
	pathbmp = os.path.join(pathbmp, "ss-" + timestr + ".png")
	
	#couldn't find another easy way to convert to png
	myBitMap.SaveBitmapFile(newDC,pathbmp)
	
# =============================================================================
# UTIL METHOD
class ScopedTimer:
	def __init__(self, name):
		self.starttime = datetime.datetime.now()
		self.name = name
		
	def __del__(self):
		delta = datetime.datetime.now() - self.starttime
		myprint(str(self.name) + " : " + str(delta),3)

def toXYCoord(pixIndex, w):
	y = int(pixIndex / w)
	floaty = pixIndex / w
	fraction = floaty - y
	timew = fraction * w
	x = int((((pixIndex / w) - y) * w) + 0.5)
	return [x, y]

def parseUint(val):
	if val < 0:
		return val + 2**8
	else:
		return val
	
def asPILFormat(asTuple, hasAlpha):
	if hasAlpha:
		returnList = [
			tuple(
				[
					parseUint(asTuple[(x*4)+2]), 
					parseUint(asTuple[(x*4)+1]), 
					parseUint(asTuple[(x*4)]), 
					255
				]
			) for x in range(int(len(asTuple) / 4))]
	else:
		returnList = [
			tuple(
				[
					parseUint(asTuple[(x*4)+2]), 
					parseUint(asTuple[(x*4)+1]), 
					parseUint(asTuple[(x*4)])
				]
			) for x in range(int(len(asTuple) / 4))]
	return returnList
	
def toPixIndex(coord, w):
	if coord[0] >= w or coord[0] < 0 or coord[1] < 0:
		return -1
	return (coord[1] * w) + coord[0]
	
# =============================================================================
# CLUSTERING ALGO

def collectSurroundingData(pixIndex, collection, binaryList, board_size, matchAllColor = False):
	indexes = set()
	indexes.add(pixIndex)
	clusterinfo = {}
	newCluster = set()
	while len(indexes) > 0:
		index = indexes.pop()
		if not isIndexInList(index, collection):
			newCluster.add(index)
			coord = toXYCoord(index, board_size[0])
			coordu = [coord[0], coord[1] - 1]
			coordd = [coord[0], coord[1] + 1]
			coordr = [coord[0] + 1, coord[1]]
			coordl = [coord[0] - 1, coord[1]]
			indexu = toPixIndex(coordu, board_size[0])
			indexd = toPixIndex(coordd, board_size[0])
			indexr = toPixIndex(coordr, board_size[0])
			indexl = toPixIndex(coordl, board_size[0])
			if isIndexElement(indexu, binaryList) and not indexu in newCluster and (matchAllColor == False or isMatchAllColors(binaryList, index, indexu)):
				indexes.add(indexu)
			if isIndexElement(indexd, binaryList) and not indexd in newCluster and (matchAllColor == False or isMatchAllColors(binaryList, index, indexd)):
				indexes.add(indexd)
			if isIndexElement(indexr, binaryList) and not indexr in newCluster and (matchAllColor == False or isMatchAllColors(binaryList, index, indexr)):
				indexes.add(indexr)
			if isIndexElement(indexl, binaryList) and not indexl in newCluster and (matchAllColor == False or isMatchAllColors(binaryList, index, indexl)):
				indexes.add(indexl)

	minClusterSize = 5
	if len(newCluster) > minClusterSize:
		minX = -1
		minY = -1
		for index in newCluster:
			coord = toXYCoord(index, board_size[0])
			if minX < 0 or minX > coord[0]:
				minX = coord[0]
				minY = coord[1]
		perim = calculatePerimeter(newCluster, [minX, minY], board_size, False)
		clustercoord = clusterIndexToClusterCoord(newCluster, board_size)
		clusterinfo["clusterIndexes"] = newCluster
		clusterinfo["clusterPerimeter"] = perim
		clusterinfo["clusterCoord"] = clustercoord
		collection.append(clusterinfo)

def isMatchAllColors(binaryList, curIndex, newIndex):
	return binaryList[curIndex][RED] == binaryList[newIndex][RED] and binaryList[curIndex][GREEN] == binaryList[newIndex][GREEN] and binaryList[curIndex][BLUE] == binaryList[newIndex][BLUE]
		
def isIndexElement(index, binaryList):
	if index < 0 or index >= len(binaryList) or numpy.sum(binaryList[index]) <= 5:
		return False
	return True
			
def isIndexInList(index, listOfList):
	for sublist in listOfList:
		if index in sublist["clusterIndexes"]:
			return True
			
	return False
	
def collectClusters(data):
	a = ScopedTimer("collectClusters")
	myprint("Collect color clusters")
	data["frame_data"]["clusters"] = []
	start = [0,0]
	end = data["frame_data"]["arena_diff_size"]
	board_size = data["frame_data"]["arena_diff_size"]
	for y in range(start[1], end[1]):
		for x in range(start[0], end[0]):
			index = toPixIndex([x,y], board_size[0])
			if numpy.sum(data["frame_data"]["arena_diff"][index]) > 5 and not isIndexInList(index, data["frame_data"]["clusters"]):
				collectSurroundingData(index, data["frame_data"]["clusters"], data["frame_data"]["arena_diff"], board_size)
				
	myprint(str(data["frame_data"]["clusters"]),2)

def clusterIndexToClusterCoord(cluster, board_size):
	clustercoord = set()
	for index in cluster:
		clustercoord.add(tuple(toXYCoord(index, board_size[0])))
		
	return clustercoord
	
def calculatePerimeter(cluster, startCoord, board_size, verbose):
	perimeter = set()
	perimeter.add(tuple(startCoord))
	current = startCoord
	dirs = numpy.array([[0,-1], [-1,-1], [-1,0], [-1,1], [0,1], [1,1], [1,0], [1,-1]])
	backtrace = numpy.array([5, 6, 0, 0, 2, 2, 4, 4])
	clustercoord = clusterIndexToClusterCoord(cluster, board_size)
	i = 0
	start = 0
	# have to move in from an empty direction or the algorithm fails
	for x in range(len(dirs)):
		move = (start + x) % len(dirs)
		inspect = current + dirs[move]
		inspecttuple = tuple(inspect)
		if not inspecttuple in clustercoord:
			start = x
			break

	# this algo has a weakness where it will stop early.
	# the easy solution is to loop twice.
	while not numpy.array_equal(current, startCoord) or i < 10:
		if numpy.array_equal(current, startCoord):
			i += 1
		for x in range(len(dirs)):
			move = (start + x) % len(dirs)
			inspect = current + dirs[move]
			inspecttuple = tuple(inspect)
			if inspecttuple in clustercoord:
				if inspecttuple not in perimeter:
					perimeter.add(inspecttuple)
				current = inspect
				start = backtrace[move] # backtrace (http://www.imageprocessingplace.com/downloads_V3/root_downloads/tutorials/contour_tracing_Abeer_George_Ghuneim/moore.html)
				break
	return perimeter
	
# =============================================================================
# GAME LOGIC
def get_current_screen_name(data):
	homescreen_coord = data["button_correct_coords"]["homescreen"]
	homescreen_color = data["screen_colors"]["homescreen"]
	battlescreen_coord = data["button_correct_coords"]["battlescreen"]
	battlescreen_color = data["screen_colors"]["battlescreen"]
	victoryscreen_coord = data["button_correct_coords"]["victoryscreen"]
	victoryscreen_color = data["screen_colors"]["victoryscreen"]
	
	homescreen_index = toPixIndex(homescreen_coord, gScreenWidth)
	battlescreen_index = toPixIndex(battlescreen_coord, gScreenWidth)
	victoryscreen_index = toPixIndex(victoryscreen_coord, gScreenWidth)
	
	screen_home_val = gScreen[homescreen_index]
	screen_battle_val = gScreen[battlescreen_index]
	screen_victory_val = gScreen[victoryscreen_index]
	
	myprint("color at home ({x},{y}) : {home}, at battle ({x2},{y2}) : {battle}, at victory ({x3},{y3}) : {victory}".format(
		x=homescreen_coord[0], y=homescreen_coord[1], home=screen_home_val, x2=battlescreen_coord[0], y2=battlescreen_coord[1],
		battle=screen_battle_val, x3=victoryscreen_coord[0], y3=victoryscreen_coord[1], victory=screen_victory_val
	), 2)
	
	diffhome = screen_home_val[RED] - homescreen_color[RED] + screen_home_val[BLUE] - homescreen_color[BLUE] + screen_home_val[GREEN] - homescreen_color[GREEN]
	diffbattle = screen_battle_val[RED] - battlescreen_color[RED] + screen_battle_val[BLUE] - battlescreen_color[BLUE] + screen_battle_val[GREEN] - battlescreen_color[GREEN]
	diffvictory = screen_victory_val[RED] - victoryscreen_color[RED] + screen_victory_val[BLUE] - victoryscreen_color[BLUE] + screen_victory_val[GREEN] - victoryscreen_color[GREEN]
	
	if abs(diffhome) < MAX_COLOR_DIFF:
		data["frame_data"]["current_screen"] = "homescreen"
		return "homescreen"
	elif abs(diffbattle) < MAX_COLOR_DIFF:
		data["frame_data"]["current_screen"] = "battlescreen"
		return "battlescreen"
	elif abs(diffvictory) < MAX_COLOR_DIFF:
		data["frame_data"]["current_screen"] = "victoryscreen"
		return "victoryscreen"
	else:
		myprint("Error: Could not identify current screen !", 5)
		return None
	

def searchCoordInScreen(pixelToFind, x, y, w, h, gwidth, gheight, hasAlpha):
	a = ScopedTimer("searchCoordInScreen")
	#startindex = toPixIndex((x, y), gScreenWidth)
	#endindex = toPixIndex((x + w, y + h), gScreenWidth)
	if gwidth == -1 or (gwidth+x) > gScreenWidth:
		gwidth = gScreenWidth-x
	if gheight == -1 or (gheight+y) > gScreenHeight:
		gheight = gScreenHeight-y
	for refy in range(y, y + gheight):
		for refx in range(x, x + gwidth):
			pixIndex = toPixIndex((refx, refy), gScreenWidth)
			pix = gScreen[pixIndex]
			diff = pix[0] - pixelToFind[0][0] + pix[1] - pixelToFind[0][1] + pix[2] - pixelToFind[0][2]
			if diff <= MAX_COLOR_DIFF:
				match = True
				row = 0
				while(match and row < 1):
					coordscreen = toXYCoord(pixIndex, gScreenWidth)
					coordscreen[0] += row
					screenIndex = toPixIndex(coordscreen, gScreenWidth)
					if screenIndex > len(gScreen):
						match = False
						break;
					
					coordimg = (row, 0)
					imgIndex = toPixIndex(coordimg, w)
					
					screenline = []
					if hasAlpha:
						screenline = gScreenAlpha[screenIndex:screenIndex+w]
					else:
						screenline = gScreen[screenIndex:screenIndex+w]
					subimgline = pixelToFind[imgIndex:imgIndex+w]
					screenline = screenline.tolist()
					
					for i in range(len(screenline)):
						diff = subimgline[i][0] - screenline[i][0] + subimgline[i][1] - screenline[i][1] + subimgline[i][2] - screenline[i][2]
						if abs(diff) > MAX_COLOR_DIFF:
							match = False
							break

					row += 1
				if match == True:
					coord = toXYCoord(pixIndex, gScreenWidth)
					coord[0] += int(w / 2) + gScreenOffsetL
					coord[1] += int(h / 2) + gScreenOffsetT
					return coord
				
	return None

def convert_RGB_to_BGR(img):
	returnList = [[x[2], x[1], x[0], x[3]] for x in img]
	return returnList
	
def board_coord_to_mousepos(data, a, b):
	square_dim_x = data["drop_area"]["width"] / (data["grid_size"][0]-1)
	square_dim_y = data["drop_area"]["height"] / (data["grid_size"][1]-1)
	pos_x = data["drop_area_abs"]["left"] + (a * square_dim_x)
	pos_y = data["drop_area_abs"]["top"] + (b * square_dim_y)
	
	myprint("square_dim_x : {dimx}, square_dim_y : {dimy}, a {va}, b {vb}, abs left {aleft}, abs top {atop}, finalx {fx}, finaly {fy}".format(
		dimx=square_dim_x, dimy=square_dim_y, va=a, vb=b, aleft=data["drop_area_abs"]["left"], atop=data["drop_area_abs"]["top"], fx=pos_x, fy=pos_y))
	return int(pos_x), int(pos_y)
	
def search_image(path, x=0, y=0, w=-1, h=-1):
	im = Image.open(path)
	width, height = im.size
	btnpixeldata = list(im.getdata())
	hasAlpha = im.mode == "RGBA"
	btnpixeldata = convert_RGB_to_BGR(btnpixeldata)
	myprint("search_image " + path)
	coord = searchCoordInScreen(btnpixeldata, x, y, width, height, w, h, hasAlpha)
	if coord is not None:
		coord[0] -= int(width/2)
		coord[1] -= int(height/2)
	return coord
	
def calculate_offset_from_appname_ref(data):
	coord = search_image(data["ref_img"]["settingbtn"])
	myprint("coord : " + str(coord),3)
	data["appname_key"] = "settingbtn"
	data["world_ref"] = coord
	
def calculate_absolute_button_pos(data):
	data["button_abs_coords"] = {}
	data["drop_area_abs"] = {}
	appname_abs_offset_x = data["world_ref"][0] - data["button_coords"]["settingbtn"][0]
	appname_abs_offset_y = data["world_ref"][1] - data["button_coords"]["settingbtn"][1]
	for button_name in data["button_coords"]:
		world_pos_x = data["button_coords"][button_name][0] + appname_abs_offset_x
		world_pos_y = data["button_coords"][button_name][1] + appname_abs_offset_y
		data["button_abs_coords"][button_name] = (int(world_pos_x), int(world_pos_y))
		
	world_pos_x = data["drop_area"]["left"] + appname_abs_offset_x
	world_pos_y = data["drop_area"]["top"] + appname_abs_offset_y
	data["drop_area_abs"]["left"] = int(world_pos_x)
	data["drop_area_abs"]["top"] = int(world_pos_y)
	
def calculate_corrected_button_pos(data):
	data["button_correct_coords"] = {}
	for button_name in data["button_abs_coords"]:
		corrected_coord = (data["button_abs_coords"][button_name][0] - gScreenOffsetL, data["button_abs_coords"][button_name][1] - gScreenOffsetT)
		data["button_correct_coords"][button_name] = corrected_coord
		
def calculate_current_energy(data):
	data["frame_data"]["current_energy"] = 0
	energy_color = data["screen_colors"]["energybar"]
	energy_color_high = data["screen_colors"]["energybar_high"]
	for i in range(12):
		coord_name = "energy" + str(i)
		if coord_name not in data["button_correct_coords"]:
			break
		coord = data["button_correct_coords"][coord_name]
		coord_index = toPixIndex(coord, gScreenWidth)
		coord_val = gScreen[coord_index]
		if coord_val[RED] <= 128:
			break
	
	data["frame_data"]["current_energy"] = i-1
	
def calculate_current_cards_in_hand(data):
	a = ScopedTimer("calculate_current_cards_in_hand")
	data["frame_data"]["hand"] = {
		"card0" : "",
		"card1" : "",
		"card2" : "",
		"card3" : ""
	}
	myprint("corrected_button_coord = " + str(data["button_abs_coords"]))
	
	startsearch = data["button_correct_coords"]["deckstarcorner"]
	width = data["button_correct_coords"]["card3"][0] + 100
	height = data["button_correct_coords"]["card3"][1] + 100
	
	for card in data["ref_img"]["cards"]:
		coord = search_image(data["ref_img"]["cards"][card], startsearch[0], startsearch[1], width, height)
		if coord is not None:
			if coord[0] <= data["button_abs_coords"]["card0"][0]:
				data["frame_data"]["hand"]["card0"] = card
			elif coord[0] <= data["button_abs_coords"]["card1"][0]:
				data["frame_data"]["hand"]["card1"] = card
			elif coord[0] <= data["button_abs_coords"]["card2"][0]:
				data["frame_data"]["hand"]["card2"] = card
			elif coord[0] <= data["button_abs_coords"]["card3"][0]:
				data["frame_data"]["hand"]["card3"] = card
			else:
				myprint("ERROR : Invalid coord, card found at : " + str(coord) + " for card " + card, 3)
				
def calculate_arena_diff(data):
	cur_arena = data["current_arena"]
	
	im = Image.open(data["ref_img"][cur_arena])
	width, height = im.size
	btnpixeldata = list(im.getdata())
	hasAlpha = im.mode == "RGBA"
	btnpixeldata = convert_RGB_to_BGR(btnpixeldata)
	arena_offset_x = data["button_correct_coords"]["arena_top_left"][0]
	arena_offset_y = data["button_correct_coords"]["arena_top_left"][1]
	
	# extract the arena picture from gScreen
	myprint("screen width " + str(gScreenWidth) + " height " + str(gScreenHeight) + " len(gscreen) " + str(len(gScreen)))
	arena_pic = gScreen.reshape(gScreenHeight, gScreenWidth, 4)
	
	arena_pic = arena_pic[arena_offset_y:arena_offset_y + height, arena_offset_x:arena_offset_x + width]
	myprint("width " + str(width) + " height " + str(height) + " arena_offset_x " + str(arena_offset_x) + " arena_offset_y " + str(arena_offset_y))
	arena_pic = arena_pic.reshape(width * height, 4)
	
	#t = arena_pic / 255
	#t = t.reshape(height, width, 4)
	#plt.imshow(t)
	#<matplotlib.image.AxesImage object at 0x04123CD0>
	#plt.show()
	
	# MAX_COLOR_DIFF * 10 to try to get rid of clouds. I think the contrast between bg and units should be big enought
	sub_img = [(p[0], p[1], p[2]) if abs(numpy.subtract(pref, p).sum()) > (MAX_COLOR_DIFF*10) else (0,0,0) for p, pref in zip(arena_pic,btnpixeldata)]
	data["frame_data"]["arena_diff"] = sub_img
	data["frame_data"]["arena_diff_size"] = (width, height)
	
	a = numpy.array(sub_img)
	a = a / 255
	a = a.reshape(height, width, 3)
	plt.imshow(a)
	#<matplotlib.image.AxesImage object at 0x04123CD0>
	plt.show()
	
def play_dumb_strat(data):
	# finding cards in hand is expensive. Only do it when necessary (first update and after playing a card)
	if data["frame_data"]["needHandUpdate"] == True:
		calculate_current_cards_in_hand(data)
		
	calculate_arena_diff(data)
	collectClusters(data)
	calculate_current_energy(data)
	
	
		
def run_all(actions, data):
	if data["use_paint"] == True:
		handle = getWindowByTitle("Paint", False)
	else:
		handle = getWindowByTitle("BlueStacks", False)
		
	if handle is None or handle[0] is None:
		myprint("Could not find window !", 5)
	
	if "takeScreenshot" in actions:
		while True:
			updateScreen(handle[0])
			takeScreenshot(handle[0])
			sleep(10)
	
	if "update_screen" in actions:
		updateScreen(handle[0])
	
	if "init" in actions:
		data["frame_data"] = {}
		calculate_offset_from_appname_ref(data)
		calculate_absolute_button_pos(data)
		calculate_corrected_button_pos(data)
		a = (data["world_ref"][0] - gScreenOffsetL, data["world_ref"][1] - gScreenOffsetT)
		
		myprint("found world ref at : " + str(a) + " with : " + data["appname_key"],2)
		myprint("corrected setting coord : " + str(data["button_correct_coords"]["settingbtn"]))
		myprint("corrected start coord : " + str(data["button_correct_coords"]["battle"]))
		myprint("corrected arena top left coord : " + str(data["button_correct_coords"]["arena_top_left"]))
		
		
	if "wait_after_init" in actions:
		sleep(8)
		
	if "test_screen_diff" in actions:
		while True:
			updateScreen(handle[0])
			calculate_arena_diff(data)
			collectClusters(data)
			sleep(10)
		
	if "find_screen" in actions:
		cur_screen = get_current_screen_name(data)
		myprint("current screen name = " + cur_screen,2)
		
		if "start_battle" in actions:
			if cur_screen == "homescreen":
				click(*data["button_abs_coords"]["battle"])
				sleep(3)
				updateScreen(handle[0])
				cur_screen = get_current_screen_name(data)
				myprint("battle should be starting, current screen : " + str(cur_screen))
				
	if "test_play_area" in actions:
		sleep(5)
		for x in range(data["grid_size"][0]):
			for y in range(data["grid_size"][1]):
				board_x, board_y = board_coord_to_mousepos(data, x, y)
				#moveMouse(data["drop_area_abs"]["left"], data["drop_area_abs"]["top"])
				#moveMouse(data["button_abs_coords"]["card2"][0], data["button_abs_coords"]["card2"][1])
				moveMouse(board_x, board_y)
				sleep(0.2)
			sleep(2)
				
	if "test_battle_button" in actions:
		moveMouse(*data["button_abs_coords"]["settingbtn"])
		sleep(4)
		moveMouse(*data["button_abs_coords"]["battle"])
		sleep(4)
		moveMouse(*data["button_abs_coords"]["shop_side"])
				
	if "test_energy" in actions:
		while True:
			updateScreen(handle[0])
			#cur_screen = get_current_screen_name(data)
			calculate_current_energy(data)
			myprint("current energy : " + str(data["frame_data"]["current_energy"]))
			sleep(4)
			
	if "test_cards" in actions:
		while True:
			updateScreen(handle[0])
			calculate_current_cards_in_hand(data)
			myprint("current hand : " + str(data["frame_data"]["hand"]),3)
			sleep(5)
	
	if "play" in actions:
		max_game = 4
		num_game = 0
		wait_card = 0
		cur_time = datetime.datetime.now()
		prev_time = cur_time
		while num_game < max_game:
			updateScreen(handle[0])
			cur_screen = get_current_screen_name(data)
			calculate_current_energy(data)
			if cur_screen == "homescreen":
				click(*data["button_abs_coords"]["battle"])
				data["frame_data"]["needHandUpdate"] = True
				sleep(3)
			elif cur_screen == "victoryscreen":
				num_game += 1
				click(*data["button_abs_coords"]["finish"])
				sleep(3)
			elif cur_screen == "battlescreen":
				play_dumb_strat(data)
				#deltat = (cur_time - prev_time).total_seconds()
				#myprint("deltat = {dt}, wait_card = {wt}".format(dt=deltat, wt=wait_card))
				#wait_card -= deltat
				#if wait_card <= 0:
				#	click(*data["button_abs_coords"]["card0"])
				#	sleep(0.1)
				#	# front of my right tower
				#	default_x = 15
				#	default_y = 6
				#	default_x, default_y = board_coord_to_mousepos(data, default_x, default_y)
				#	click(default_x, default_y)
				#	wait_card = 5.0
					
			prev_time = cur_time
			cur_time = datetime.datetime.now()
				
		
if __name__ == '__main__':
	
	#handle = getWindowByTitle("Paint", False)
	#updateScreen(handle[0])
	
	#a = gScreen
	#a = a / 255
	#a = a.reshape(gScreenHeight, gScreenWidth, 4)
	#b = a[:,0:200,:]
	
	#plt.imshow(b)
	#plt.show()
	
	#sys.exit()
	
	run_all([
			#"takeScreenshot",
			"update_screen",
			"init",
			"wait_after_init",
			"test_screen_diff",
			#"test_cards",
			#"find_screen",
			#"test_play_area",
			#"test_battle_button",
			#"test_energy",
			#"start_battle",
			#"play",
			"none" # put this here so I don't have to add , when I change list size.
		],
		{
			"use_paint" : True,
			"current_arena": "arena_0", #could detect it eventually, for now should be ok
			"ref_img" : {
				"appname" : os.path.join(DATA_FOLDER, "ref", "appname.png"),
				"settingbtn" : os.path.join(DATA_FOLDER, "ref", "settingbtn_noside.png"),
				#"settingbtn_noside" : os.path.join(DATA_FOLDER, "ref", "settingbtn_noside.png"),
				"shop_side" : os.path.join(DATA_FOLDER, "ref", "shop_noside.png"),
				#"shop_noside" : os.path.join(DATA_FOLDER, "ref", "shop_noside.png"),
				"arena_0" : os.path.join(DATA_FOLDER, "ref", "training_arena.png"), #training arena
				"cards" : {
					"skelarmy" : os.path.join(DATA_FOLDER, "ref", "cardskelarmy.png"),
					"archer" : os.path.join(DATA_FOLDER, "ref", "cardarcher.png"),
					"balloon" : os.path.join(DATA_FOLDER, "ref", "cardballoon.png"),
					"fireball" : os.path.join(DATA_FOLDER, "ref", "cardfireball.png"),
					"giant" : os.path.join(DATA_FOLDER, "ref", "cardgiant.png"),
					"goblinspear" : os.path.join(DATA_FOLDER, "ref", "cardgoblinspear.png"),
					"minion" : os.path.join(DATA_FOLDER, "ref", "cardminion.png"),
					"valkyrie" : os.path.join(DATA_FOLDER, "ref", "cardvalkyrie.png"),
					"goblin" : os.path.join(DATA_FOLDER, "ref", "cardgoblin.png")
				}
			},
			"button_coords" : {
				"battle" : (650,477), #(677,477),
				"finish" : (650,645),
				"card0" : (572,650),
				"card1" : (648,650),
				"card2" : (721,650),
				"card3" : (796,650),
				#"appname" : (245,3),
				"settingbtn" : (802,81),
				#"settingbtn_noside" : (772,81),
				#"shop_side" : (442,668),
				#"shop_noside" : (442,668),
				"homescreen" : (652,453), #(683,453),
				"battlescreen" : (683,598), #(711,598),
				"victoryscreen" : (616,631), #(673,631),
				"energy0" : (557,706),
				"energy1" : (581,706),
				"energy2" : (599,706),
				"energy3" : (626,706),
				"energy4" : (653,706),
				"energy5" : (681,706),
				"energy6" : (707,706),
				"energy7" : (735,706),
				"energy8" : (763,706),
				"energy9" : (790,706),
				"energy10" : (825,706),
				"stacksidebar" : (29,61),
				"deckstarcorner" : (569,607),
				"arena_top_left" : (452,31)
			},
			"screen_colors" : {
				"homescreen" : [83,208,255], # color of the pixel at button_coords/homescreen (BGR)
				"battlescreen" : [101,135,166],
				"victoryscreen" : [255,187,105],
				"energybar" : [244,136,240],
				"energybar_high" : [255,191,255],
				"stacksidebar" : [68,59,60]
			},
			"game_area" : {
				"top":31,
				"left":452,
				"width":391,
				"height":696
			},
			"drop_area" : {
				"top":349,
				"left":492,
				"width":314,
				"height":209
			},
			"grid_size" : (18,15)
		})
	
	myprint("done", 5)
