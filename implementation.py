import jmri
import java
import javax.swing
import java.awt
import apps
from synchronize import make_synchronized

NTRAINS = 3
NSECTIONS = 16
NPARKINGS = 3

FIRST = 0
LAST = NSECTIONS-1

BACKWARDS = -1
STOPPED = 0
SLOW = 1
FAST = 2

RED = 2
YELLOW = 1
GREEN = 0

NOTINSYSTEM = -1
WANTTOCROSS = 0
WANTTOPARK = 1
WANTTOLEAVE = 2
PARKED = 3

CONTROLLER_MAX_IDLE = 2000

#                      0           1         2        3         4         5         6         7          8         9         10       11       12        13         14        15
SECTION_SENSORS = [ "LS1569", "LS1570", "LS1571", "LS1572", "LS1573", "LS1574", "LS1575", "LS1576", "LS1577", "LS1578", "LS1579", "LS1580", "LS1581",  "LS1582", "LS1583", "LS1584" ]
SWITCHES_ADDRESSES = ["LT22", "LT44", "LT66", "LT88"]
TRAIN_THROTTLES = [5, 6, 8, 4]


class ControllerS1(jmri.jmrit.automat.AbstractAutomaton):
	def __init__(self, manager):
		self.manager = manager
		
		
	def init(self):	
		print "ControllerS1 initializing"
		self.mustContinue = True
		self.syncSensor = sensors.provideSensor("ISSYNC") 
		self.trains = GlobalManager.trains
		self.sections = GlobalManager.sections[10:16]
		print "ControllerS1 initialized"


	def getTrainOnSection(self, section):
		for train in self.trains:
			if train.section == section:
				return train
		return -1
	

	def emergencyStop(self):
		self.manager.emergencyStop()
	
	
	def handle(self):
		self.waitSensorActive(self.syncSensor)
		self.waitMsec(CONTROLLER_MAX_IDLE)
		for train in self.trains:
			if train.section.ID == LAST and train.speed == STOPPED:
				self.takeDecision(train)
		return self.mustContinue

		
	
	def update(self,train):
		self.takeDecision(train)
	
	@make_synchronized
	def takeDecision(self,train):
		print "S1 - Take Decision"
		if train.section.ID < 10:
			print "Controller error. Function updateForSubSystem1() should not be called with a train that is not in the system. \nTrain = " + str(train.ID) + ". CurrentSection = " + str(train.section.ID)
			self.emergencyStop()
		
		if train.section.ID == LAST:
			print "S1 - Train on the last section. CanLeave = " + str(SubSystem2.canLeave()) + ". State of section 0 = " + str(GlobalManager.getSectionWithID(0).state)
			if SubSystem2.canLeave():
				train.runSlow()
			else:
				train.stop()	
			return
			
		nextSection = self.manager.getSectionWithID(train.section.ID + 1)

		if nextSection.state == GREEN:
			train.runFast()
		elif nextSection.state == YELLOW:
			train.runSlow()
		elif nextSection.state == RED:
			train.stop()
	
		
class ControllerS2(jmri.jmrit.automat.AbstractAutomaton):
	trainLeaving = -1
	def __init__(self, manager, userView):
		self.manager = manager
		self.userView = userView
		
	def init(self):	
		print "ControllerS2 initializing"
		self.mustContinue = True
		self.lockBy = -1
		self.addTrain = False
		self.parkTrain = False
		self.trainIsLeaving = False
		
		self.syncSensor = sensors.provideSensor("ISSYNC") 
		
		self.switches = GlobalManager.switches
		self.trains = GlobalManager.trains
		self.sections = GlobalManager.sections[0:10]
		self.parkedIn = [self.trains[0], self.trains[1], self.trains[2]]
		self.trainsQueue = []
		
		print "ControllerS2 initialized"
	
	def emergencyStop(self):
		self.manager.emergencyStop()


	def getTrainOnSection(self, section):
		for train in self.trains:
			if train.section == section:
				return train
		return -1		
	
	def canLeaveParkingSpot(self, train):
		parkingSpot = self.getParkingOfTrain(train)

		if parkingSpot != -1:
			if parkingSpot == NPARKINGS-1:
				return True

			for spot in range(parkingSpot+1 , NPARKINGS):
				if self.parkedIn[spot] != -1:
					return False
		else:
			return False
		return True
		
	def getParkingOfTrain(self, train):
		for index, trainParked in enumerate(self.parkedIn):
			if trainParked == train:
				return index
		return -1
		
	def getFreeParkingSpot(self):	
		for index, trainParked in enumerate(self.parkedIn):
			if trainParked == -1:
				return index
		return -1
	
	def numberOfTrainParked(self):
		counter = 0
		for train in self.parkedIn:
			if train != -1:
				counter +=1
		return counter
		
	def parkTrainF(self):
		if self.numberOfTrainParked() >= NTRAINS:
			return False
			
		if self.numberOfTrainParked() >= NPARKINGS:
			return False
		
		if self.numberOfTrainParked() < NPARKINGS:
			self.parkTrain = True
			self.userView.deactivateButtons()
			return True
			
		return False  # Should never get here
		

	def addTrainF(self):
		if self.numberOfTrainParked() > 0:
			self.addTrain = True
			self.userView.deactivateButtons()
			return True
		elif self.numberOfTrainParked() <= 0:
			return False
			
		return False  # Should never get here

	def resetAddTrain(self):
		self.addTrain = False
		self.userView.activateButtons()
		
	def resetParkTrain(self):
		self.parkTrain = False
		self.userView.activateButtons()
		
	
	def handle(self):
		self.waitSensorActive(self.syncSensor)
		self.waitMsec(CONTROLLER_MAX_IDLE)
		for train in self.trains:
			if self.canPark(train):
				self.wantToPark(train)			
			elif self.canCross(train):
				self.wantToCross(train)			
			elif self.canLeave(train):
				self.wantToLeave(train)
		return self.mustContinue
	
	def canPark(self, train):
		return train.action == WANTTOPARK and train.speed == STOPPED and not(train.section.ID == 0 and self.getSectionWithID(1).state == RED)
	
	def canCross(self, train):
		return train.action == WANTTOCROSS and train.speed == STOPPED and not(train.section.ID < 4 and self.getSectionWithID(train.section.ID+1).state == RED) and not(train.section.ID == 2 and self.trainIsLeaving)
	
	def canLeave(self, train):
		return (train.action == WANTTOLEAVE and train.speed == STOPPED and not(self.getSectionWithID(2).state == RED or self.getSectionWithID(3).state == RED)) or \
				 (train.action == PARKED and self.addTrain == True and self.canLeave(train) == True and self.lockBy == -1)
	
	def conditionsFullfilledToCross(train):
		return train.action == WANTTOCROSS and (train.section.ID != 0 or self.parkTrain == False or self.getFreeParkingSpot() == -1 or self.lockBy != -1)
	
	def conditionsFullfilledToLeave(train):
		return train.action == WANTTOLEAVE and self.lockBy == train.ID
		
	def conditionsFullfilledToPark(train):
		return (train.action == WANTTOPARK and self.lockBy == train.ID) or (train.action == WANTTOCROSS and train.section.ID == 0 and self.parkTrain == True and self.getFreeParkingSpot() != -1 and self.lockBy == -1)
	
	def update(self, train):
	
		#print "\n \n TakeDecisionForSubSystem2 ----------------------------------------------- "
		#print "Train " + str(train.ID) + ". Action = " + str(train.action) + ". CurrentSection = " + str(train.section.ID)
		#print "LockBy = " + str(self.lockBy) + ". FreeParkingSpot() = " + str(self.getFreeParkingSpot())
		if train.section.ID > 9 or train.section.ID < 0:
			self.emergencyStop()
			print "Controller error. Function updateForSubSystem2() should not be called with a train that is not in the system"
			return
			
		if self.conditionsFullfilledToCross(train):
			self.wantToCross(train)
		elif self.conditionsFullfilledToLeave(train):
			self.wantToLeave(train)
		elif conditionsFullfilledToPark(train):
			self.wantToPark(train)
		return
	
	@make_synchronized
	def wantToPark(self, train):
		#print "Wanttopark. Train = " + str(train.ID) + ". WillParkTo = "+ str(train.willParkTo) + ". freeParkingSpot = " + str(self.getFreeParkingSpot())
		# Special cases
		if train.section.ID == 0 and train.willParkTo == -1 and self.getFreeParkingSpot() != -1:
			train.action = WANTTOPARK
			train.willParkTo = self.getFreeParkingSpot()
			self.lockBy = train.ID
			self.wantToPark(train)
			
		elif train.section.ID == 0 and train.willParkTo == -1 and self.getFreeParkingSpot() == -1:
			train.action = WANTTOCROSS
			self.wantToCross(train)
			
		# Conditions to run slowly
		elif train.section.ID == 0 and self.getSectionWithID(1).state == GREEN and train.willParkTo != -1:
			self.getSwitchWithID(0).close()
			train.runSlow()
		elif train.section.ID == 1:
			self.getSwitchWithID(1).close()
			train.runSlow()
		elif train.section.ID == 7 and train.willParkTo == 0:
			self.getSwitchWithID(2).close()
			train.runSlow()
		elif train.section.ID == 6 and train.speed != BACKWARDS:
			train.runSlow()
		elif train.section.ID == 8 and train.willParkTo == 0:
			train.runSlow()
			
		# Conditions to stop
		elif train.section.ID == 0 and self.getSectionWithID(1).state == RED and train.willParkTo != -1:
			train.stop()
		elif (train.section.ID == 9 and train.willParkTo == 0) or (train.section.ID == 5 and train.willParkTo == 1) or (train.section.ID == 7 and train.willParkTo == 2):
			self.parkedIn[train.willParkTo] = train 
			self.lockBy = -1
			self.resetParkTrain()
			train.action = PARKED
			train.willParkTo = -1
			train.stop()
			
		# Conditions to run backwards
		elif train.section.ID == 6 and train.speed == BACKWARDS:
			train.runBackwards()
		elif train.section.ID == 7 and train.willParkTo == 1:
			self.getSwitchWithID(1).open()
			train.runBackwards()
		
		return
	
	@make_synchronized
	def wantToLeave(self, train):
		# Conditions to stop
		if train.section.ID == 3 and self.getSectionWithID(4) == RED:
			train.action = WANTTOCROSS
			train.stop()
			self.lockBy = -1
			self.trainIsLeaving = False
			self.resetAddTrain()
			
		elif train.section.ID == 3 and self.getSectionWithID(4).state == GREEN:
			train.action = WANTTOCROSS
			train.runSlow()
			self.lockBy = -1
			self.trainIsLeaving = False
			self.resetAddTrain()
			
		elif train.section.ID == 8 and train.speed != BACKWARDS and (self.getSectionWithID(2).state == RED or self.getSectionWithID(3).state == RED):
			train.stop()
		
		# Conditions to run
		elif train.section.ID == 5:
			train.action = WANTTOLEAVE
			train.runSlow()
			self.getSwitchWithID(1).open()
			self.lockBy = train.ID
			self.parkedIn[1] = -1
			
		elif train.section.ID == 7 and train.action == WANTTOLEAVE:
			self.getSwitchWithID(2).open()
			train.runSlow()
			
		elif train.section.ID == 7 and train.action == PARKED:
			train.action = WANTTOLEAVE
			train.runSlow()
			self.getSwitchWithID(2).open()
			self.lockBy = train.ID
			self.parkedIn[2] = -1
			
			
		elif train.section.ID == 8 and train.speed != BACKWARDS and self.getSectionWithID(2).state == GREEN and self.getSectionWithID(3).state == GREEN:
			train.runSlow()
			self.getSwitchWithID(3).open()
			self.trainIsLeaving = True
			
		elif train.section.ID == 6:
			train.runSlow()
			
		
		# Conditions to run backwards
		elif train.section.ID == 8 and train.speed == BACKWARDS:
			train.runBackwards()
			
		elif train.section.ID == 9:
			train.action = WANTTOLEAVE
			train.runBackwards()
			self.getSwitchWithID(2).close()
			self.lockBy = train.ID
			self.parkedIn[0] = -1
			
		return
	
	@make_synchronized
	def wantToCross(self, train):
		# Conditions to stop
		if train.section.ID == 0 and self.getSectionWithID(1).state == RED:
			train.stop()
			
		elif train.section.ID == 1 and self.getSectionWithID(2).state == RED:
			train.stop()
			
		elif train.section.ID == 2 and (self.getSectionWithID(3).state == RED or self.trainIsLeaving):
			train.stop()
			
		elif train.section.ID == 3 and self.getSectionWithID(4).state == RED:
			train.stop()
			
		elif train.section.ID == 4 and not SubSystem1.canLeave():
			print "S2 - Train on the last section. CanLeave = " + str(SubSystem1.canLeave()) + ". State of section 10 = " + str(GlobalManager.getSectionWithID(10).state)
			train.stop()
			
		# Conditions to run
		elif train.section.ID == 2 and self.getSectionWithID(3).state == GREEN and not self.trainIsLeaving:
			self.getSwitchWithID(3).open()
			train.runSlow()
			
		elif train.section.ID == 0 and self.getSectionWithID(1).state == GREEN:
			self.getSwitchWithID(0).open()
			train.runSlow()
			
		elif train.section.ID == 3 and self.getSectionWithID(4).state == GREEN:
			train.runSlow()
			
		elif train.section.ID == 4 and SubSystem1.canLeave():
			print "S2 - Train on the last section. CanLeave = " + str(SubSystem1.canLeave()) + ". State of section 10 = " + str(GlobalManager.getSectionWithID(10).state)
			ControllerS2.trainLeaving = train
			self.trainsQueue.append(train)
			print "S2 - trainsQueue = " + str(len(self.trainsQueue))
			train.runSlow()
			
		elif train.section.ID == 1 and self.getSectionWithID(2).state == GREEN:
			train.runSlow()
		
		return	
	
	def getPreviousSectionID(self, sectionID):
		if sectionID == 0:
			return 15 
		elif sectionID == 1:
			return 0
		elif sectionID == 2:
			return 1
		elif sectionID == 3:
			for train in self.trains:
				if train.section.ID == 8 and train.speed == SLOW and train.action == WANTTOLEAVE and self.trainIsLeaving:
					return 8
			return 2
		elif sectionID == 4:
			return 3
		elif sectionID == 5:
			return 6
		elif sectionID == 6:
			for train in self.trains:
				if train.section.ID == 1 and train.speed == SLOW and train.action == WANTTOPARK and self.parkTrain:
					return 1
				elif train.section.ID == 7 and train.speed == BACKWARDS and train.action == WANTTOPARK and self.parkTrain:
					return 7
				elif train.section.ID == 5 and train.speed == SLOW and train.action == WANTTOLEAVE and self.addTrain:
					return 5
					
		elif sectionID == 7:
			for train in self.trains:
				if train.section.ID == 6 and train.speed == SLOW:
					return 6
				elif train.section.ID == 8 and train.speed == BACKWARDS:
					return 8
			
		elif sectionID == 8:
			for train in self.trains:
				if train.section.ID == 7 and train.speed == SLOW and train.action != WANTTOCROSS and (self.addTrain or self.parkTrain):
					return 7
				elif train.section.ID == 9 and train.speed == BACKWARDS and train.action == WANTTOLEAVE and self.addTrain:
					return 9
		elif sectionID == 9:
			return 8
		elif sectionID == 10:
			return 4
			
		return -1	
	
				
	
	

	
class SectionS1(jmri.jmrit.automat.AbstractAutomaton):
		
	def __init__(self, identification, controller, sensorName,  state, section):
		self.controller = controller
		self.ID = identification
		self.sensor = sensors.provideSensor(sensorName)
		self.state = state
		self.previousSection = section
        

	def handle(self):
		self.waitSensorActive(self.controller.syncSensor)
		value = "FREE"
		
		if self.state == RED:
			self.waitSensorInactive(self.sensor)
			
			self.waitMsec(50)
			trainToUpdate = self.becomesFree()
			
			if trainToUpdate != -1:
				self.controller.update(trainToUpdate)
				
		elif self.state != RED:
			self.waitSensorActive(self.sensor)
			
			
			self.waitSensorInactive(self.previousSection.sensor)
			value = "OCCUPIED"
			trainToUpdate = self.becomesOccupiedBy()
			if trainToUpdate != -1:
				self.controller.update(trainToUpdate)
			else: 
				self.controller.emergencyStop()
			
		print "\t Section " + str(self.ID) + " became " + str(value)
		return True

	@make_synchronized
 	def becomesOccupiedBy(self):
		self.state = RED
		
		if self.ID > 10:
			currentTrain = self.controller.getTrainOnSection(self.previousSection)
		else:
			currentTrain = ControllerS2.trainLeaving
			
		if currentTrain != -1:
			currentTrain.section = self
			print "S1 - Train " + str(currentTrain.ID) + " has reached Section " + str(self.ID)

		return currentTrain;
	
		
	@make_synchronized
	def becomesFree(self):
		if self.ID != LAST:
			self.state = YELLOW
		else:
			self.state  = GREEN
		
		if self.ID > 10:
			if self.previousSection.state == YELLOW:
				self.previousSection.state = GREEN
		
		return self.getTrainWaitingForSection()
		
		

	
	def getTrainWaitingForSection(self):
		if self.ID > 10:
			return self.controller.getTrainOnSection(self.previousSection)
		return -1

	
class SectionS2(jmri.jmrit.automat.AbstractAutomaton):
	def init(self):
		return
		
	def __init__(self, identification, controller, sensorName,  state):
		self.controller = controller
		self.ID = identification
		self.sensor = sensors.provideSensor(sensorName)
		self.state = state
        
	def handle(self):
		#print "\n \n SECTION HANDLE - " + str(self.ID)
		self.waitSensorActive(self.controller.syncSensor)
		value = "FREE"
		
		if self.state == RED:
			#print "waitForSensorInactive"
			self.waitSensorInactive(self.sensor)
			self.becomesFree()
					
		elif self.state != RED:
			#print "waitForSensorActive"
			self.waitSensorActive(self.sensor)
				
			previousSectionID = self.controller.getPreviousSectionID(self.ID)
			self.waitSensorInactive(GlobalManager.getSectionWithID(previousSectionID).sensor)
			value = "OCCUPIED"
			trainToUpdate = self.becomesOccupiedBy(previousSectionID)
			if trainToUpdate != -1:
				self.controller.update(trainToUpdate)
			else :
				self.controller.emergencyStop()
			
		print "\t Section " + str(self.ID) + " became " + str(value)
		return True

	@make_synchronized
	def becomesOccupiedBy(self, previousSectionID):
		self.state = RED

		if previousSectionID == 15:
			if len(self.controller.trainsQueue) > 0:
				currentTrain = self.controller.trainsQueue.pop(0)
			else:
				print "SectionS2 - Fatal error. TrainsQueue is empty."
				self.controller.emergencyStop()
		else:
			previousSection = self.controller.getSectionWithID(previousSectionID)
			currentTrain = self.controller.getTrainOnSection(previousSection)
			
		if currentTrain != -1:
			currentTrain.section = self
			print "S2 - Train " + str(currentTrain.ID) + " has reached Section " + str(self.ID)
			
		return currentTrain			
       
    @make_synchronized
    def becomesFree(self):
		self.state = green;
		#if (id == 4){
		#	int[-1, nTrains-1] train = getTrainOnSection(id);
		#	if (train != -1) {
		#		trainSection[train] = -1;
		#	}	
		#	enqueue(train);
		#}
	




class Train():
	def __init__(self, identification, throttle, section, speed, action, slow, fast):
		
		self.ID = identification
		self.loco = throttle
		self.section = section
		
		self.speed = speed
		self.action = action
		self.willParkTo = -1
        
		self.slow = slow
		self.fast = fast
		
        
		if(self.loco == None):
				print "Error initializing throttle."
		return

        
	def runFast(self):
		self.speed = FAST
		throttle = GlobalManager.throttles[self.ID]
		throttle.setIsForward(True)
		throttle.setSpeedSetting(self.fast)
		print "Train "+ str(self.ID)+" - runFast sent"
		return
	
	def runSlow(self):
		self.speed = SLOW
		throttle = GlobalManager.throttles[self.ID]
		throttle.setIsForward(True)
		throttle.setSpeedSetting(self.slow)
		print "Train "+ str(self.ID)+" - runSlow sent"
		return
		
	def stop(self):
		self.speed = STOPPED
		throttle = GlobalManager.throttles[self.ID]
		throttle.setIsForward(True)
		throttle.setSpeedSetting(0.0)
		print "Train "+ str(self.ID)+" - stop sent"
		return
		
	def runBackwards(self):
		self.speed = BACKWARDS
		throttle = GlobalManager.throttles[self.ID]
		throttle.setIsForward(False)
		throttle.setSpeedSetting(self.slow)
		print "Train "+ str(self.ID)+" - runSlow sent"
		return

class Switch():
	def __init__(self, ID, switch):
		self.ID = ID
		self.switch = switch
		
	def open(self):
		self.switch.setState(THROWN)	
		return
	
	def close(self):
		self.switch.setState(CLOSED)
		return

class UserView():
	def __init__(self, manager):
		self.manager = manager
				
		self.stopButton = javax.swing.JButton("/!\   Stop System   /!\ ")
		self.stopButton.setEnabled(True)       
		self.stopButton.setToolTipText("Stops the run - there is a delay as the loco slows")
		self.stopButton.actionPerformed = self.stopButtonClicked

		self.addTrainButton = javax.swing.JButton("Add Train")
		self.addTrainButton.setEnabled(True)       
		self.addTrainButton.setToolTipText("Add a train in the system")
		self.addTrainButton.actionPerformed = self.addTrain 

		self.parkTrainButton = javax.swing.JButton("Park Train")
		self.parkTrainButton.setEnabled(True)       
		self.parkTrainButton.setToolTipText("Park a train")
		self.parkTrainButton.actionPerformed = self.parkTrain



		self.totalGUI = javax.swing.JPanel()
		self.totalGUI.setSize(400,400)
		self.totalGUI.setLayout(None)
		
		self.stopPanel =  javax.swing.JPanel()
		self.stopPanel.setLayout(java.awt.GridLayout(1, 1))
		self.stopPanel.setLocation(100, 10)
		self.stopPanel.setSize(200,100)
		self.stopPanel.add(self.stopButton)
		self.totalGUI.add(self.stopPanel)

		self.commandPanel = javax.swing.JPanel()
		self.commandPanel.setLayout(java.awt.GridLayout(1, 2))
		self.commandPanel.setLocation(50, 150)
		self.commandPanel.setSize(300, 50)
		self.commandPanel.add(self.addTrainButton)
		self.commandPanel.add(self.parkTrainButton)
		self.totalGUI.add(self.commandPanel)
        		
		self.frame = javax.swing.JFrame("Controls Commands Center")
		self.frame.setPreferredSize(java.awt.Dimension(400, 280));
		self.frame.contentPane.add(self.totalGUI)
		self.frame.pack()
		self.frame.show()
		self.frame.setVisible(True)
	
	def stopButtonClicked(self,event):
		print "\n --------------------------------- \nSystem is stopping"
		self.manager.emergencyStop()	
		self.frame.dispose()
		print "System stopped\n --------------------------------- \n"
		
	def deactivateButtons(self):
		self.parkTrainButton.setEnabled(False)
		self.addTrainButton.setEnabled(False)
	
	def activateButtons(self):
		self.parkTrainButton.setEnabled(True)
		self.addTrainButton.setEnabled(True)
		
	def addTrain(self, event):
		if self.manager.controllerS2.addTrainF() :
			print "addTrain - REQUEST OK"
		else: 
			print "addTrain - REQUEST NOT OK"
		return
		
	def parkTrain(self, event):
		if self.manager.controllerS2.parkTrainF():
			print "parkTrain - REQUEST OK"
		else: 
			print "parkTrain - REQUEST NOT OK"
		return
		
class SubSystem2():
	@staticmethod
	def canLeave():
		if GlobalManager.getSectionWithID(0).state != RED:
			return True
		return False
		
		

			
class SubSystem1():
	@staticmethod
	def canLeave():
		if GlobalManager.getSectionWithID(10).state != RED:
			return True
		return False
			
		
	
class GlobalManager(jmri.jmrit.automat.AbstractAutomaton):
	throttles = []
	trains = []
	sections = []
	switches = []
	
	def init(self):
		self.userView = UserView(self)
		print "Global Manager - userView initialized"
		
		self.controllerS1 = ControllerS1(self)
		self.controllerS2 = ControllerS2(self, self.userView)
		print "Global Manager - controllers initialized"
		
		GlobalManager.throttles.append(self.getThrottle(TRAIN_THROTTLES[0], False))
		GlobalManager.throttles.append(self.getThrottle(TRAIN_THROTTLES[1], False))
		GlobalManager.throttles.append(self.getThrottle(TRAIN_THROTTLES[2], False))
		GlobalManager.throttles.append(self.getThrottle(TRAIN_THROTTLES[3], False))
		print "Global Manager - throttles initialized"
		
	
		# Sections for second controller
		GlobalManager.sections.append(SectionS2(0, self.controllerS2, SECTION_SENSORS[0], GREEN))
		GlobalManager.sections.append(SectionS2(1, self.controllerS2, SECTION_SENSORS[1], GREEN))
		GlobalManager.sections.append(SectionS2(2, self.controllerS2, SECTION_SENSORS[2], RED))
		GlobalManager.sections.append(SectionS2(3, self.controllerS2, SECTION_SENSORS[3], GREEN))
		GlobalManager.sections.append(SectionS2(4, self.controllerS2, SECTION_SENSORS[4], GREEN))
		GlobalManager.sections.append(SectionS2(5, self.controllerS2, SECTION_SENSORS[5], RED))
		GlobalManager.sections.append(SectionS2(6, self.controllerS2, SECTION_SENSORS[6], GREEN))
		GlobalManager.sections.append(SectionS2(7, self.controllerS2, SECTION_SENSORS[7], RED))
		GlobalManager.sections.append(SectionS2(8, self.controllerS2, SECTION_SENSORS[8], GREEN))
		GlobalManager.sections.append(SectionS2(9, self.controllerS2, SECTION_SENSORS[9], RED))
		# Sections for first controller
		GlobalManager.sections.append(SectionS1(10, self.controllerS1, SECTION_SENSORS[10], GREEN, GlobalManager.sections[4]))
		GlobalManager.sections.append(SectionS1(11, self.controllerS1, SECTION_SENSORS[11], GREEN, GlobalManager.sections[10]))
		GlobalManager.sections.append(SectionS1(12, self.controllerS1, SECTION_SENSORS[12], GREEN, GlobalManager.sections[11]))
		GlobalManager.sections.append(SectionS1(13, self.controllerS1, SECTION_SENSORS[13], GREEN, GlobalManager.sections[12]))
		GlobalManager.sections.append(SectionS1(14, self.controllerS1, SECTION_SENSORS[14], GREEN, GlobalManager.sections[13]))
		GlobalManager.sections.append(SectionS1(15, self.controllerS1, SECTION_SENSORS[15], GREEN, GlobalManager.sections[14]))
		
		
		GlobalManager.trains.append(Train(0, GlobalManager.throttles[0], GlobalManager.sections[9], STOPPED, PARKED, 0.25, 0.99))
		GlobalManager.trains.append(Train(1, GlobalManager.throttles[1], GlobalManager.sections[5], STOPPED, PARKED, 0.20, 0.99))
		GlobalManager.trains.append(Train(2, GlobalManager.throttles[2], GlobalManager.sections[7], STOPPED, PARKED, 0.10, 0.40))
		GlobalManager.trains.append(Train(3, GlobalManager.throttles[3], GlobalManager.sections[2], STOPPED, WANTTOCROSS, 0.21, 0.99))
		print "GlobalManager - trains initialized"
		
		GlobalManager.switches.append(Switch(0,turnouts.provideTurnout(SWITCHES_ADDRESSES[0])))
		GlobalManager.switches.append(Switch(1,turnouts.provideTurnout(SWITCHES_ADDRESSES[1])))
		GlobalManager.switches.append(Switch(2,turnouts.provideTurnout(SWITCHES_ADDRESSES[2])))
		GlobalManager.switches.append(Switch(3,turnouts.provideTurnout(SWITCHES_ADDRESSES[3])))
		print "GlobalManager - switches initialized"
	
		
		
		self.syncSensor = sensors.provideSensor("ISSYNC") # To synchronise the start of all the automaton (actually, for the section to start once all is initialized)
		self.syncSensor.setState(INACTIVE)
		self.waitMsec(100) # To be sure that the sensor is inactive when the controllers start
		
		
		self.controllerS1.start()
		self.controllerS2.start()
		
		self.waitMsec(200)
		
		for section in GlobalManager.sections:
			section.start()
		print "GlobalManager - sections started"
		
		
		self.waitMsec(3000)
		print "------------------------------------ SYNC OK ------------------------------------"
		self.syncSensor.setState(ACTIVE)
		
	def emergencyStop(self):
		print "EMERGENCY STOP - SOMETHING WENT WRONG !"
		
		for train in GlobalManager.trains:
			train.stop()
			
		for section in GlobalManager.sections:
			section.stop()
			
		self.controllerS1.stop()
		self.controllerS2.stop()
		self.printInfo()
		self.stop()
		return
		
	@staticmethod
	def printInfo():
	
		print "\n"
		for index,section in enumerate(GlobalManager.sections):
			value = "green"
			if section.state == RED:
				value = "red"
			elif section.state == YELLOW:
				value = "yellow"
			print "Section " + str(index) + " : " + str(value) 
		print "\n"
		
		for index,train in enumerate(GlobalManager.trains):
			if train.section != -1:
				print "Train " + str(index) + " : " + str(train.speed) + ". CurrentSection = " + str(train.section.ID) 
		print "\n"
		
	@staticmethod
	def getSectionWithID(ID):
		for section in GlobalManager.sections:
			if section.ID == ID:
				return section
		return -1
	
	
if __name__ == "__main__":
	manager = GlobalManager()
	manager.start()
