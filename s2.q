//This file was generated from (Academic) UPPAAL 4.0.13 (rev. 4577), September 2010

/*

*/
E<> trainAction[0] == parked

/*

*/
E<> trainAction[0] == wantToLeave

/*

*/
E<> trainAction[0] == wantToPark

/*

*/
E<> trainAction[0] == wantToCross

/*

*/
A[] exists(j:Train_t) trainAction[j] == parked imply exists(i:int[0,2]) parkedIn[i] != -1

/*

*/
A[]  addTrain == true imply (exists(j:int[0,2]) parkedIn[j] != -1 ||  exists(i:Train_t)  trainAction[i] == wantToLeave)

/*

*/
A[] exists(i:Train_t) trainAction[i] == wantToPark imply lockBy == i

/*

*/
A[] exists(i:Train_t) trainAction[i] == wantToLeave imply lockBy == i

/*

*/
A[] parkTrain == true imply  exists(i:int[0,2]) parkedIn[i] == -1

/*

*/
A[] parkTrain + addTrain <= 1

/*

*/
A[] (parkedIn[1] != -1 imply parkedIn[0] != -1) and (parkedIn[2] != -1 imply (parkedIn[1] != -1 && parkedIn[0] != -1))

/*

*/
A[] (parkedIn[0] != -1 && !Controller.Init) imply (sectionState[9] == red || trainAction[parkedIn[0]] == wantToLeave)

/*

*/
A[] sectionState[5] + sectionState[6] + sectionState[7] + sectionState[8]  +sectionState[9] <= numberOfTrainParked() + 1

/*

*/
trainAction[0] == wantToLeave --> trainAction[0] == wantToCross

/*

*/
trainAction[0] == wantToPark --> (trainSection[0] == 5 || trainSection[0] == 7 || trainSection[0] == 9)

/*

*/
(trainSection[0] == 1 && trainAction[0] == wantToCross) --> trainSection[0] == -1

/*

*/
(addTrain == true && trainAction[0] == parked && canLeaveParkingSpot(0) &&  lockBy == -1) --> trainAction[0] == wantToLeave

/*

*/
 exists(i:Train_t)  ((addTrain == true && trainAction[i] == parked  && i == parkedIn[2]) --> trainAction[i] == wantToLeave)

/*

*/
A[] queueLength <= nTrains

/*

*/
A[] forall(i:Train_t) forall(j:Train_t) (!Controller.Init && trainSection[i] != -1 && trainSection[i] == trainSection[j]) imply i == j

/*

*/
A[]  (sectionState[0] + sectionState[1] + sectionState[2] + sectionState[3] + sectionState[4] + sectionState[5] + sectionState[6] + sectionState[7] + sectionState[8] + sectionState[9]) <= nTrains

/*

*/
A[] not deadlock
