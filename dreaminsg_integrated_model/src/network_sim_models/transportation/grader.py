from collections import OrderedDict
import os
import sys


import tests
   
def runTests(testFunction, testDirectory):
   score = 0
   possible = 0
   testFileName = os.path.normpath(testDirectory + "tests.txt")
   
   try:
      testList = open(testFileName).read().splitlines()
   except Exception as e:
      print("Error running tests from path %s, attempting to continue with remaining tests.  Exception details: " % testDirectory)
      print(e)
      return 0, 0
      
   for test in testList:
      # Ignore comments and blank lines
      if len(test.strip()) == 0 or test[0] == '#':
         continue
            
      thisScore, thisPossible = testFunction(testDirectory + test)
      score += thisScore
      possible += thisPossible      
   
   return score, possible
   
def displayScores(scores):
   longestQuestion = len(max(scores.keys(), key=len))
   totalScore = 0
   totalPossible = 0
   print("")
   print("SCORES: ")
   for question in scores.keys():
      totalScore += scores[question][0]
      totalPossible += scores[question][1]
      print("%s %d/%d" % (question.ljust(longestQuestion), scores[question][0], scores[question][1]))
   print("----------")
   print("%s %d/%d" % ("TOTAL: ".ljust(longestQuestion), totalScore, totalPossible))
   print("")
   print("This is an unofficial score, please submit code on Canvas for final scoring.")
   print("")
   
if __name__ == '__main__':
   
   scores = OrderedDict()
 
   # Run relative gap tests
   scores['Relative gap'] = runTests(tests.relativeGap, "tests/relativegap/")

   # Run average excess cost tests
   scores['Average excess cost'] = runTests(tests.averageExcessCost, "tests/aec/")

   # Run convex combination tests
   scores['Convex combination test'] = runTests(tests.convexCombination, "tests/convexcombo/")

   # Run FW stepsize tests
   scores['Frank-Wolfe step size test'] = runTests(tests.frankWolfe, "tests/fwstepsize/")
   
   displayScores(scores)
   sys.exit()
   
   
