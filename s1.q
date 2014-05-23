//This file was generated from (Academic) UPPAAL 4.0.13 (rev. 4577), September 2010

/*

*/
E<> trainSpeed[0] == fast

/*

*/
E<> trainSpeed[0] == slow

/*

*/
E<> trainSpeed[0] == stopped

/*

*/
(!Controller.Init && trainSection[0] == first )--> trainSection[0] == last

/*

*/
trainSection[0] == last --> trainSection[0] == -1 

/*

*/
sectionState[0] != green --> sectionState[0] == green

/*

*/
A[] forall(i:Train_t) (trainSection[i] != -1  && trainSpeed[i] == stopped && trainSection[i] < last) imply (sectionState[trainSection[i]+1] == red || timeBeforeRestart[i] < 1)

/*

*/
A[] forall(i: Train_t) (trainSpeed[i] == fast && trainSection[i] < last) imply (sectionState[trainSection[i]+1] == green || (sectionState[trainSection[i]+1] == yellow && trainClock[i] < 1))

/*

*/
A[] forall(i:Train_t) forall(j:Train_t) (!Controller.Init &&  trainSection[i] != -1  && trainSection[j] != -1  && trainSection[i] == trainSection[j]) imply i == j

/*

*/
A[] forall(i:Train_t) trainSection[i] > -1 imply timeToCross[i] < 7*MAX_TIME_PER_SECTION

/*

*/
A[] not deadlock
