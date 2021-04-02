import os
import sys
import traceback

import dreaminsg_integrated_model.network_sim_models.transportation.network as network
import dreaminsg_integrated_model.network_sim_models.transportation.path as path
import dreaminsg_integrated_model.network_sim_models.transportation.utils as utils
   
IS_MISSING = -1

def approxEqual(value, target, tolerance):
   if (abs(target) <= tolerance ): return abs(value) <= tolerance
   return abs(float(value) / target - 1) <= tolerance
   
def check(name, value, target, tolerance):
   if approxEqual(value, target, tolerance):
      return True
   else:
      print("\nWrong %s: your value %s, correct value %s"
               % (name, value, target))
      return False

def readFlowsFile(flowsFileName):
   flows = dict()
   try:
      with open(flowsFileName, "r") as flowsFile:
         fileLines = flowsFile.read().splitlines()
         for line in fileLines:
            if len(line.strip()) == 0 or line[0] == '#':
               continue
            row = line.split()
            flows[row[0]] = float(row[1])
   except IOError:
      print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % flowsFileName)
      traceback.print_exc(file=sys.stdout) 
   return flows         
               
def relativeGap(testFileName):

   print("Running relative gap test: " + str(testFileName) + "...", end='')
 
   try:
      with open(testFileName, "r") as testFile:
         # Read test information
         try:
            fileLines = testFile.read().splitlines()
            pointsPossible = IS_MISSING
            networkFile = IS_MISSING
            tripsFile = IS_MISSING
            flowsFile = IS_MISSING
            answer = IS_MISSING
            for line in fileLines:
               # Ignore comments and blank lines
               if len(line.strip()) == 0 or line[0] == '#':
                  continue
                   
               # Set points possible
               if pointsPossible == IS_MISSING:
                  pointsPossible = int(line)
                  continue
                  
               # Identify network files
               if networkFile == IS_MISSING:
                  networkFile = os.path.normpath(line)
                  continue
               if tripsFile == IS_MISSING:
                  tripsFile = os.path.normpath(line)
                  continue
               if flowsFile == IS_MISSING:
                  flowsFile = os.path.normpath(line)
                  continue
               
               # Read answer
               if answer == IS_MISSING:
                  answer = float(line)
                  continue
                  
                 
         except:
            print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
            traceback.print_exc(file=sys.stdout)
            return 0, 0
            
         # Now run the actual test
         try:
            testNetwork = network.Network(networkFile, tripsFile)
            linkFlows = readFlowsFile(flowsFile)
            for ij in testNetwork.link:
               testNetwork.link[ij].flow = linkFlows[ij]
               testNetwork.link[ij].updateCost()
            studentGap = testNetwork.relativeGap()
            if check("Relative gap ",studentGap,answer,0.01) == False:
               print("...fail")
               return 0, pointsPossible
         except utils.NotYetAttemptedException:
            print("...not yet attempted")
            return 0, pointsPossible
         except:
            print("\nException raised, attempting to continue:")
            traceback.print_exc(file=sys.stdout)                     
            print("\n...fail")
            return 0, pointsPossible
            
         print("...pass")
         return pointsPossible, pointsPossible

         
   except IOError:
      print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
      traceback.print_exc(file=sys.stdout) 
      return 0, 0

def averageExcessCost(testFileName):

   print("Running average excess cost test: " + str(testFileName) + "...", end='')
 
   try:
      with open(testFileName, "r") as testFile:
         # Read test information
         try:
            fileLines = testFile.read().splitlines()
            pointsPossible = IS_MISSING
            networkFile = IS_MISSING
            tripsFile = IS_MISSING
            flowsFile = IS_MISSING
            answer = IS_MISSING
            for line in fileLines:
               # Ignore comments and blank lines
               if len(line.strip()) == 0 or line[0] == '#':
                  continue
                   
               # Set points possible
               if pointsPossible == IS_MISSING:
                  pointsPossible = int(line)
                  continue
                  
               # Identify network files
               if networkFile == IS_MISSING:
                  networkFile = os.path.normpath(line)
                  continue
               if tripsFile == IS_MISSING:
                  tripsFile = os.path.normpath(line)
                  continue
               if flowsFile == IS_MISSING:
                  flowsFile = os.path.normpath(line)
                  continue
               
               # Read answer
               if answer == IS_MISSING:
                  answer = float(line)
                  continue
                  
                 
         except:
            print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
            traceback.print_exc(file=sys.stdout)
            return 0, 0
            
         # Now run the actual test
         try:
            testNetwork = network.Network(networkFile, tripsFile)
            linkFlows = readFlowsFile(flowsFile)
            for ij in testNetwork.link:
               testNetwork.link[ij].flow = linkFlows[ij]
               testNetwork.link[ij].updateCost()
            studentGap = testNetwork.averageExcessCost()
            if check("Relative gap ",studentGap,answer,0.01) == False:
               print("...fail")
               return 0, pointsPossible
         except utils.NotYetAttemptedException:
            print("...not yet attempted")
            return 0, pointsPossible
         except:
            print("\nException raised, attempting to continue:")
            traceback.print_exc(file=sys.stdout)                     
            print("\n...fail")
            return 0, pointsPossible
            
         print("...pass")
         return pointsPossible, pointsPossible

         
   except IOError:
      print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
      traceback.print_exc(file=sys.stdout) 
      return 0, 0


def convexCombination(testFileName):

   print("Running convex combination test: " + str(testFileName) + "...", end='')
 
   try:
      with open(testFileName, "r") as testFile:
         # Read test information
         try:
            fileLines = testFile.read().splitlines()
            pointsPossible = IS_MISSING
            networkFile = IS_MISSING
            tripsFile = IS_MISSING
            baseFlowsFile = IS_MISSING
            targetFlowsFile = IS_MISSING
            stepSize = IS_MISSING
            answerFlowsFile = IS_MISSING
            for line in fileLines:
               # Ignore comments and blank lines
               if len(line.strip()) == 0 or line[0] == '#':
                  continue
                   
               # Set points possible
               if pointsPossible == IS_MISSING:
                  pointsPossible = int(line)
                  continue
                  
               # Identify network files
               if networkFile == IS_MISSING:
                  networkFile = os.path.normpath(line)
                  continue
               if tripsFile == IS_MISSING:
                  tripsFile = os.path.normpath(line)
                  continue
               if baseFlowsFile == IS_MISSING:
                  baseFlowsFile = os.path.normpath(line)
                  continue
               if targetFlowsFile == IS_MISSING:
                  targetFlowsFile = os.path.normpath(line)
                  continue
               if stepSize == IS_MISSING:
                  stepSize = float(line)
                  continue
                  
               
               # Read answer
               if answerFlowsFile == IS_MISSING:
                  answerFlowsFile = os.path.normpath(line)
                  continue
                  
                 
         except:
            print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
            traceback.print_exc(file=sys.stdout)
            return 0, 0
            
         # Now run the actual test
         try:
            testNetwork = network.Network(networkFile, tripsFile)
            linkFlows = readFlowsFile(baseFlowsFile)
            targetFlows = readFlowsFile(targetFlowsFile)
            answerFlows = readFlowsFile(answerFlowsFile)
            for ij in testNetwork.link:
               testNetwork.link[ij].flow = linkFlows[ij]
            testNetwork.shiftFlows(targetFlows, stepSize)
            for ij in testNetwork.link:            
               if check("Link %s flow" % ij,testNetwork.link[ij].flow,answerFlows[ij],0.01) == False:
                  print("...fail")
                  return 0, pointsPossible
         except utils.NotYetAttemptedException:
            print("...not yet attempted")
            return 0, pointsPossible
         except:
            print("\nException raised, attempting to continue:")
            traceback.print_exc(file=sys.stdout)                     
            print("\n...fail")
            return 0, pointsPossible
            
         print("...pass")
         return pointsPossible, pointsPossible

         
   except IOError:
      print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
      traceback.print_exc(file=sys.stdout) 
      return 0, 0

def frankWolfe(testFileName):

   print("Running Frank-Wolfe step size test: " + str(testFileName) + "...", end='')
 
   try:
      with open(testFileName, "r") as testFile:
         # Read test information
         try:
            fileLines = testFile.read().splitlines()
            pointsPossible = IS_MISSING
            networkFile = IS_MISSING
            tripsFile = IS_MISSING
            baseFlowsFile = IS_MISSING
            targetFlowsFile = IS_MISSING
            stepSizeAnswer = IS_MISSING

            for line in fileLines:
               # Ignore comments and blank lines
               if len(line.strip()) == 0 or line[0] == '#':
                  continue
                   
               # Set points possible
               if pointsPossible == IS_MISSING:
                  pointsPossible = int(line)
                  continue
                  
               # Identify network files
               if networkFile == IS_MISSING:
                  networkFile = os.path.normpath(line)
                  continue
               if tripsFile == IS_MISSING:
                  tripsFile = os.path.normpath(line)
                  continue
               if baseFlowsFile == IS_MISSING:
                  baseFlowsFile = os.path.normpath(line)
                  continue
               if targetFlowsFile == IS_MISSING:
                  targetFlowsFile = os.path.normpath(line)
                  continue
               # Read answer
               if stepSizeAnswer == IS_MISSING:
                  stepSizeAnswer = float(line)
                  continue
                 
                 
         except:
            print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
            traceback.print_exc(file=sys.stdout)
            return 0, 0
            
         # Now run the actual test
         try:
            testNetwork = network.Network(networkFile, tripsFile)
            linkFlows = readFlowsFile(baseFlowsFile)
            targetFlows = readFlowsFile(targetFlowsFile)
            for ij in testNetwork.link:
               testNetwork.link[ij].flow = linkFlows[ij]
            stepSize = testNetwork.FrankWolfeStepSize(targetFlows,1e-10)
            if check("Step size",stepSize,stepSizeAnswer,0.01) == False:
                  print("...fail")
                  return 0, pointsPossible
         except utils.NotYetAttemptedException:
            print("...not yet attempted")
            return 0, pointsPossible
         except:
            print("\nException raised, attempting to continue:")
            traceback.print_exc(file=sys.stdout)                     
            print("\n...fail")
            return 0, pointsPossible
            
         print("...pass")
         return pointsPossible, pointsPossible

         
   except IOError:
      print("\nError running test %s, attempting to continue with remaining tests.  Exception details: " % testFileName)
      traceback.print_exc(file=sys.stdout) 
      return 0, 0
