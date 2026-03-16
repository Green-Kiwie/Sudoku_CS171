import SudokuBoard
import Variable
import Domain
import Trail
import Constraint
import ConstraintNetwork
import time
import random
import sys
from collections import deque

class BTSolver:

    # ==================================================================
    # Constructors
    # ==================================================================

    def __init__ ( self, gb, trail, val_sh, var_sh, cc ):
        self.network = ConstraintNetwork.ConstraintNetwork(gb)
        self.hassolution = False
        self.gameboard = gb
        self.trail = trail

        self.varHeuristics = var_sh
        self.valHeuristics = val_sh
        self.cChecks = cc

    # ==================================================================
    # Consistency Checks
    # ==================================================================

    # Basic consistency check, no propagation done
    def assignmentsCheck ( self ):
        for c in self.network.getConstraints():
            if not c.isConsistent():
                return False
        return True

    """
        Part 1 TODO: Implement the Forward Checking Heuristic

        This function will do both Constraint Propagation and check
        the consistency of the network

        (1) If a variable is assigned then eliminate that value from
            the square's neighbors.

        Note: remember to trail.push variables before you assign them
        Return: a tuple of a dictionary and a bool. The dictionary contains all MODIFIED variables, mapped to their MODIFIED domain.
                The bool is true if assignment is consistent, false otherwise.
    """
    def forwardChecking ( self ):
        modified = dict()

        def checkOneVariable(variable):
            if variable.isAssigned():
                value = variable.getAssignment()
                return checkNeighbours(value, variable)
            else:
                return True
                
        def checkNeighbours(value, variable):
            for neighbor in self.network.getNeighborsOfVariable(variable):
                if updateNeighborDomain(neighbor, value) == False:
                    return False
            return True

        def updateNeighborDomain(neighbor, value):
            if neighbor.isAssigned():
                return neighbor.getAssignment() != value
            if neighbor.getDomain().contains(value):
                self.trail.push(neighbor)
                neighbor.removeValueFromDomain(value)
                modified[neighbor] = neighbor.getDomain()
                if neighbor.getDomain().size() == 0:
                    return False
            return True

        firstTimeCheck = self.trail.size() == 0
        if firstTimeCheck:
            for variable in self.network.getVariables():
                if checkOneVariable(variable) == False:
                    return (modified, False)
        else:
            lastEditedVariable = self.trail.trailStack[-1][0]
            if checkOneVariable(lastEditedVariable) == False:
                    return (modified, False)

        return (modified, True)

    # =================================================================
	# Arc Consistency
	# =================================================================
    def arcConsistency( self ):
        assignedVars = []
        for c in self.network.constraints:
            for v in c.vars:
                if v.isAssigned():
                    assignedVars.append(v)
        while len(assignedVars) != 0:
            av = assignedVars.pop(0)
            for neighbor in self.network.getNeighborsOfVariable(av):
                if neighbor.isChangeable and not neighbor.isAssigned() and neighbor.getDomain().contains(av.getAssignment()):
                    neighbor.removeValueFromDomain(av.getAssignment())
                    if neighbor.domain.size() == 1:
                        neighbor.assignValue(neighbor.domain.values[0])
                        assignedVars.append(neighbor)

    
    """
        Part 2 TODO: Implement both of Norvig's Heuristics

        This function will do both Constraint Propagation and check
        the consistency of the network

        (1) If a variable is assigned then eliminate that value from
            the square's neighbors.

        (2) If a constraint has only one possible place for a value
            then put the value there.

        Note: remember to trail.push variables before you assign them
        Return: a pair of a dictionary and a bool. The dictionary contains all variables 
		        that were ASSIGNED during the whole NorvigCheck propagation, and mapped to the values that they were assigned.
                The bool is true if assignment is consistent, false otherwise.
    """
    def norvigCheck ( self ):

        self._init_caches() # Ensure caches are ready
        newly_assigned = dict()
        trail_push = self.trail.push

        if self.trail.size() == 0:
            queue = [v for v in self.network.getVariables() if v.isAssigned()]
        else:
            last_var = self.trail.trailStack[-1][0]
            queue = [last_var] if last_var.isAssigned() else []

        def propagate_from(var):
            value = var.getAssignment()
            for neighbor in self._var_neighbors[var]:
                if neighbor.isAssigned():
                    if neighbor.getAssignment() == value:
                        return False
                    continue

                neighbor_domain = neighbor.domain
                if neighbor_domain.contains(value):
                    trail_push(neighbor)
                    neighbor.removeValueFromDomain(value)
                    if neighbor.domain.size() == 0:
                        return False
            return True

        # Rule 1: If a variable is assigned then eliminate that value from the square's neighbors.
        changed_var = set()
        while queue:
            var = queue.pop()
            if not propagate_from(var):
                return (newly_assigned, False)
            changed_var.add(var)

        # Repeat Rule 2 + Rule 1 until no more assignments can be made.
        # changed = True
        queue = deque()
        queued_set = set()
        for v in changed_var:
            for con in self._var_constraints[v]:
                if con not in queued_set:
                    queue.append(con)
                    queued_set.add(con)
        
        while queue:
            # changed = False

            # Scan each constraint (row, col, box)
            # constraintsToCheck = []
            # for v in changed_var:
            #     constraintsToCheck.extend(self.network.getConstraintsContainingVariable(v))
            

            c = queue.popleft()
            queued_set.remove(c)
            # for c in constraintsToCheck:
            assigned_vals = set()
            val_count = {}   # value -> number of unassigned vars that can take it
            val_to_var = {}  # value -> the unique unassigned var that can take it (if count == 1)

            # Examine variables in this constraint
            for var in c.vars:
                if var.isAssigned():
                    val = var.getAssignment()
                    # If the same value appears twice in this constraint -> inconsistent
                    if val in assigned_vals:
                        return (newly_assigned, False)
                    assigned_vals.add(val)
                else:
                    # Only look at domain values that are not already used in the unit
                    for val in var.domain.values:
                        if val in assigned_vals:
                            continue
                        if val in val_count:
                            val_count[val] += 1
                        else:
                            val_count[val] = 1
                            val_to_var[val] = var

            # Now, for any value that appears in exactly one unassigned variable's domain, assign it there
            # changed_var = set()
            for val, cnt in val_count.items():
                if cnt == 1 and val not in assigned_vals:
                    v = val_to_var[val]
                    if not v.isAssigned():
                        for con in self._var_constraints[v]:
                            if con not in queued_set:
                                queued_set.add(con)
                                queue.append(con)
                        trail_push(v)
                        v.assignValue(val)
                        newly_assigned[v] = val

                        # This new assignment must propagate to neighbors via Rule (1)
                        if not propagate_from(v):
                            return (newly_assigned, False)

                        # Check for singleton neighbors (domain size 1) created by propagation
                        for neighbor in self._var_neighbors[v]:
                            if not neighbor.isAssigned() and neighbor.domain.size() == 1:
                                singleton_val = neighbor.domain.values[0]
                                trail_push(neighbor)
                                for con in self._var_constraints[neighbor]:
                                    if con not in queued_set:
                                        queued_set.add(con)
                                        queue.append(con)
                                neighbor.assignValue(singleton_val)
                                newly_assigned[neighbor] = singleton_val
                                if not propagate_from(neighbor):
                                    return (newly_assigned, False)

                        # Re-scan constraints if assignment made
                        # changed = True

        return (newly_assigned, True)

        # newly_assigned = dict()

        # if self.trail.size() == 0:
        #     queue = [v for v in self.network.getVariables() if v.isAssigned()]
        # else:
        #     last_var = self.trail.trailStack[-1][0]
        #     queue = [last_var] if last_var.isAssigned() else []

        # def propagate_from(var):
        #     value = var.getAssignment()
        #     for neighbor in self.network.getNeighborsOfVariable(var):
        #         if neighbor.isAssigned():
        #             if neighbor.getAssignment() == value:
        #                 return False
        #             continue

        #         neighbor_domain = neighbor.getDomain()
        #         if neighbor_domain.contains(value):
        #             self.trail.push(neighbor)
        #             neighbor.removeValueFromDomain(value)
        #             if neighbor.domain.size() == 0:
        #                 return False
        #     return True

        # # Rule 1: If a variable is assigned then eliminate that value from the square's neighbors.
        # while queue:
        #     var = queue.pop()
        #     if not propagate_from(var):
        #         return (newly_assigned, False)

        # # Repeat Rule 2 + Rule 1 until no more assignments can be made.
        # changed = True
        # while changed:
        #     changed = False

        #     # Scan each constraint (row, col, box)
        #     for c in self.network.getConstraints():
        #         assigned_vals = set()
        #         val_count = {}   # value -> number of unassigned vars that can take it
        #         val_to_var = {}  # value -> the unique unassigned var that can take it (if count == 1)

        #         # Examine variables in this constraint
        #         for var in c.vars:
        #             if var.isAssigned():
        #                 val = var.getAssignment()
        #                 # If the same value appears twice in this constraint -> inconsistent
        #                 if val in assigned_vals:
        #                     return (newly_assigned, False)
        #                 assigned_vals.add(val)
        #             else:
        #                 # Only look at domain values that are not already used in the unit
        #                 for val in var.getDomain().values:
        #                     if val in assigned_vals:
        #                         continue
        #                     cnt = val_count.get(val, 0) + 1
        #                     val_count[val] = cnt
        #                     if cnt == 1:
        #                         val_to_var[val] = var

        #         # Now, for any value that appears in exactly one unassigned variable's domain, assign it there
        #         for val, cnt in val_count.items():
        #             if cnt == 1 and val not in assigned_vals:
        #                 v = val_to_var[val]
        #                 if not v.isAssigned():
        #                     self.trail.push(v)
        #                     v.assignValue(val)
        #                     newly_assigned[v] = val

        #                     # This new assignment must propagate to neighbors via Rule (1)
        #                     if not propagate_from(v):
        #                         return (newly_assigned, False)

        #                     # Check for singleton neighbors (domain size 1) created by propagation
        #                     for neighbor in self.network.getNeighborsOfVariable(v):
        #                         if not neighbor.isAssigned() and neighbor.domain.size() == 1:
        #                             singleton_val = neighbor.domain.values[0]
        #                             self.trail.push(neighbor)
        #                             neighbor.assignValue(singleton_val)
        #                             newly_assigned[neighbor] = singleton_val
        #                             if not propagate_from(neighbor):
        #                                 return (newly_assigned, False)

        #                     # Re-scan constraints if assignment made
        #                     changed = True

        # return (newly_assigned, True)

    def _init_caches ( self ):
        if not hasattr(self, '_var_neighbors'):
            self._var_neighbors = {
                v: self.network.getNeighborsOfVariable(v)
                for v in self.network.getVariables()
            }
            self._var_constraints = {
                v: self.network.getConstraintsContainingVariable(v)
                for v in self.network.getVariables()
            }

    """
         Optional TODO: Implement your own advanced Constraint Propagation

         Completing the three tourn heuristic will automatically enter
         your program into a tournament.
     """
    def getTournCC ( self ):
        return self.norvigCheck()

    # ==================================================================
    # Variable Selectors
    # ==================================================================

    # Basic variable selector, returns first unassigned variable
    def getfirstUnassignedVariable ( self ):
        for v in self.network.variables:
            if not v.isAssigned():
                return v

        # Everything is assigned
        return None

    """
        Part 1 TODO: Implement the Minimum Remaining Value Heuristic

        Return: The unassigned variable with the smallest domain
    """
    def getMRV ( self ):
        lowest_var = None
        for variable in self.network.getVariables():
            if variable.isAssigned():
                continue
            elif lowest_var == None or variable.domain.size() < lowest_var.domain.size():
                lowest_var = variable
        return lowest_var

    """
        Part 2 TODO: Implement the Minimum Remaining Value Heuristic
                       with Degree Heuristic as a Tie Breaker

        Return: The unassigned variable with the smallest domain and affecting the  most unassigned neighbors.
                If there are multiple variables that have the same smallest domain with the same number of unassigned neighbors, add them to the list of Variables.
                If there is only one variable, return the list of size 1 containing that variable.
    """
    def MRVwithTieBreaker ( self ):
        lowest_vars = []
        lowest_size, lowest_neighbors = 0, 0

        def count_neighbors(variable):
            count = 0
            for neighbor in self.network.getNeighborsOfVariable(variable):
                if not neighbor.isAssigned():
                    count += 1
            return count

        for variable in self.network.getVariables():

            if variable.isAssigned():
                continue

            neighbor_count = count_neighbors(variable)
            
            if not lowest_vars or (variable.domain.size() < lowest_size or (variable.domain.size() == lowest_size and neighbor_count > lowest_neighbors)):
                lowest_vars = [variable]
                lowest_size = variable.domain.size()
                lowest_neighbors = neighbor_count
            elif variable.domain.size() == lowest_size and neighbor_count == lowest_neighbors:
                lowest_vars.append(variable)

        if not lowest_vars:
            return [None]
            
        return lowest_vars

    """
         Optional TODO: Implement your own advanced Variable Heuristic

         Completing the three tourn heuristic will automatically enter
         your program into a tournament.
     """
    def getTournVar ( self ):
        self._init_caches()
        best_var = None
        best_domain = float('inf')
        best_degree = -1
        for v in self.network.getVariables():
            if v.isAssigned():
                continue
            dom = v.domain.size()

            if dom < best_domain:
                best_var = v
                best_domain = dom
                deg = 0
                for n in self._var_neighbors[v]:
                    if not n.isAssigned():
                        deg += 1
                best_degree = deg
            elif dom == best_domain:
                deg = 0
                for n in self._var_neighbors[v]:
                    if not n.isAssigned():
                        deg += 1
                if deg > best_degree:
                    best_var = v
                    best_degree = deg
        
        if best_var is None:
            return self.getfirstUnassignedVariable()

        return best_var

    # ==================================================================
    # Value Selectors
    # ==================================================================

    # Default Value Ordering
    def getValuesInOrder ( self, v ):
        values = v.domain.values
        return sorted( values )

    """
        Part 1 TODO: Implement the Least Constraining Value Heuristic

        The Least constraining value is the one that will knock the least
        values out of it's neighbors domain.

        Return: A list of v's domain sorted by the LCV heuristic
                The LCV is first and the MCV is last
    """
    def getValuesLCVOrder ( self, v ):
        values = []
        for val in v.domain.values:
            affect_count = 0
            for neighbour in self.network.getNeighborsOfVariable(v):
                if neighbour.domain.contains(val):
                    affect_count += 1
            
            values.append((affect_count, val))
        
        sorted_vals = sorted(values)
        output = []
        for val in sorted_vals:
            output.append(val[1])
        return  output

    """
         Optional TODO: Implement your own advanced Value Heuristic

         Completing the three tourn heuristic will automatically enter
         your program into a tournament.
     """
    def getTournVal ( self, v ):
        self._init_caches()
        scores = []
        for val in v.domain.values:
            affect_count = 0
            for n in self._var_neighbors[v]:
                if not n.isAssigned() and n.domain.contains(val):
                    affect_count += 1
            scores.append((affect_count, val))
            
        scores.sort(key=lambda x: x[0])
        return [val for _, val in scores]

    # ==================================================================
    # Engine Functions
    # ==================================================================

    def solve ( self, time_left=600):
        if time_left <= 60:
            return -1

        start_time = time.time()
        if self.hassolution:
            return 0

        # Variable Selection
        v = self.selectNextVariable()

        # check if the assigment is complete
        if ( v == None ):
            # Success
            self.hassolution = True
            return 0

        # Attempt to assign a value
        for i in self.getNextValues( v ):

            # Store place in trail and push variable's state on trail
            self.trail.placeTrailMarker()
            self.trail.push( v )

            # Assign the value
            v.assignValue( i )

            # Propagate constraints, check consistency, recur
            if self.checkConsistency():
                elapsed_time = time.time() - start_time 
                new_start_time = time_left - elapsed_time
                if self.solve(time_left=new_start_time) == -1:
                    return -1
                
            # If this assignment succeeded, return
            if self.hassolution:
                return 0

            # Otherwise backtrack
            self.trail.undo()
        
        return 0

    def checkConsistency ( self ):
        if self.cChecks == "forwardChecking":
            return self.forwardChecking()[1]

        if self.cChecks == "norvigCheck":
            return self.norvigCheck()[1]

        if self.cChecks == "tournCC":
            return self.getTournCC()[1]

        else:
            return self.assignmentsCheck()

    def selectNextVariable ( self ):
        if self.varHeuristics == "MinimumRemainingValue":
            return self.getMRV()

        if self.varHeuristics == "MRVwithTieBreaker":
            return self.MRVwithTieBreaker()[0]

        if self.varHeuristics == "tournVar":
            return self.getTournVar()

        else:
            return self.getfirstUnassignedVariable()

    def getNextValues ( self, v ):
        if self.valHeuristics == "LeastConstrainingValue":
            return self.getValuesLCVOrder( v )

        if self.valHeuristics == "tournVal":
            return self.getTournVal( v )

        else:
            return self.getValuesInOrder( v )

    def getSolution ( self ):
        return self.network.toSudokuBoard(self.gameboard.p, self.gameboard.q)