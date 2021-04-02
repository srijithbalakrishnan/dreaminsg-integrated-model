NO_PATH_EXISTS = "N/A"
INFINITY = 99999
FRANK_WOLFE_STEPSIZE_PRECISION = 1e-5

class NotYetAttemptedException(Exception):
   """
   This exception is used as a placeholder for code you should fill in.
   """
   pass   
   
class BadFileFormatException(Exception):
   """
   This exception is raised if a network or demand file is in the wrong format or
   expresses an invalid network.
   """
   pass   

def readMetadata(lines):
   """
   Read metadata tags and values from a TNTP file, returning a dictionary whose
   keys are the tags (strings between the <> characters) and corresponding values.
   The last metadata line (reading <END OF METADATA>) is stored with a value giving
   the line number this tag was found in.  You can use this to proceed with reading
   the rest of the file after the metadata.
   """
   metadata = dict()
   lineNumber = 0
   for line in lines:
      lineNumber += 1
      line.strip()
      commentPos = line.find("~")
      if commentPos >= 0: # strip comments
         line = line[:commentPos]
      if len(line) == 0:
         continue

      startTagPos = line.find("<")
      endTagPos = line.find(">")
      if startTagPos < 0 or endTagPos < 0 or startTagPos >= endTagPos:
         print("Error reading this metadata line, ignoring: '%s'" % line)
      metadataTag = line[startTagPos+1 : endTagPos]
      metadataValue = line[endTagPos+1:]
      if metadataTag == 'END OF METADATA':
         metadata['END OF METADATA'] = lineNumber
         return metadata
      metadata[metadataTag] = metadataValue.strip()
      
   print("Warning: END OF METADATA not found in file")
   return metadata

         
def path2linkTuple(pathString):
   """
   Converts a path expressed as a sequence of nodes, e.g. [1,2,3,4] into a tuple
   of link IDs for use with the Path object (see path.py), in this case
   ((1,2),(2,3),(3,4))
   """
   
   # Remove braces
   pathString = pathString[1:-1]
   # Parse into node list
   nodeList = pathString.split(",")
   # Now create tuple
   linkList = list()
   prevNode = nodeList[0]
   for i in nodeList[1:]:
      curNode = i
      linkID = '(' + prevNode + ',' + curNode + ')'
      linkList.append(linkID)
      prevNode = i
   return tuple(linkList)
         