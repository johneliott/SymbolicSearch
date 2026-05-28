(require 'asdf)

; this program builds a Boolean Constraint Propagation (BCP) execution kernel to take in a macro M of length k, generates permutations of M so there are k! permutations, and runs unit propagation on each permutation, and applies stopping-time truncation on first conflict and tracks backtrack count, decision count, and stopping index for each permutation. The goal with this kernel is to eventually compare these metrics across the various permutations for Boolean SAT formulas and analyze the causal effect of ordering in propagation (permutation sensitivity across macro orderings).


; All updates must use (push (cons var val) assignment).
; DO NOT ATTEMPT TO SETF CDR ETC... NEED TO JUST DO PUSH!!!


; DATA STRUCTURES AND REPRESENTATION DEFINITIONS 

; A literal is a signed integer:
; +n => variable n is TRUE
; n => variable n is FALSE
(deftype literal () 'fixnum)


;;; A clause is a simple vector of literals
(deftype clause  () '(simple-array literal (*)))

;;; A formula is a simple vector of clauses
(deftype formula () '(simple-array clause (*)))



(defstruct (solver-state (:conc-name ss-))
  ; Chronological list of assigned literals
  ; The trail keeps track of what assignments were made in order (not by index) 
  ; What WE tried to do 
  ; (3 1 -2) --> x3 = True, x1 = True, x2 = False
  (trail          '()  :type list)

  ; Append-only shadow stack history log of (var . bool)
  ; Need to keep track of how variables were assigned/all assignments over time for full history to make sure we can do path analysis/determine causality/trace reconstruction
  ; What the SYSTEM did in response
  ; ((3 . t) (1 . t) (2 . nil))
  (assignment     '()  :type list)
  ; SAT --> no conflict so far/UNSAT --> conflict reached/UNDEF --> undefined/lacks info to determine if SAT/UNSAT
  (status         :SAT :type (member :SAT :UNSAT :UNDEF))

  ;; --- Structural Workload Metrics ---
  ; Count of macro-level manual injections (D_c)
  ; Number of manual assignments done
  (decisions      0    :type fixnum)
  ; Continuous variable propagation counter (P_c)
  ; Number of forced assignments from BCP/what propagation/work the system did automatically
  (props      0    :type fixnum)
  ; One-dimensional projection of support-size gap (B_c)
  ; Backtracking cost
  (cardinality-gap 0   :type fixnum)
)





; THREE-VALUED EVALUATION ENGINE 
; options are true, false, or unknown

; 1. eval-literal (lit assignment)
; Input: literal and an assignment alist history log

; LOOK UP THE ABSOLUTE VARIABLE (abs lit) USING ASSOC.
; LIFO SHADOWING GUARANTEES THAT ASSOC INHERENTLY RETRIEVES THE MOST RECENT BINDING
; if no binding is found, return :unknown
; if a binding exists (var . bool), a positive literal is :true if bool is T (otherwise, :false)

(defun eval-literal (lit assignment)
  ; creates a local variable named "binding" and lets it equal the pair in the assignment list whose key matches the variable ID = which is the absolute value of lit, THIS PULLS THE MOST RECENT BINDING SINCE ITS LIFO!!!
  (let ((binding (assoc (abs lit) assignment)))
    ; if no binding was found, then binding = nil, so the function should return :unknown
    (if (null binding)
      :unknown
      ; now if a binding does exist, (there's a value for (var . bool)) 
      (if (> lit 0)
        ; lit is positive --> return true/false based on its value
        (if (cdr binding) :true :false)
        ; lit is negative --> return NOT/negated value, so true actually returns false, and false actually returns true
        (if (cdr binding) :false :true)
      )
    )
  )
)


; 2. evaluate-clause (clause assignment)
; Input: a clause vector and an assignment list log

; EVALUATE EACH LITERAL IN THE CLAUSE SEQUENTIALLY VIA A DETERMINISTIC LEFT-TO-RIGHT SCAN
; the SAT short-circuit rule says:
; the FIRST ENCOUNTERED :true LITERAL MUST TERMINATE CLAUSE EVALUATION IMMEDIATE, RETURNING :sat
; this ^^ overrides any subsequent presence of unknown/false literals
; otherwise --> track the number of :unknown literals encountered
; --------> IF EXACTLY 1 UNKNOWN LITERAL IS FOUND, RETAIN ITS IDENTITY!!!
; if there are 0 :unknown literals (all literals evaluate to false), return :unsat
; if there is exactly 1 :unknown literal, return (:unit . lit)
; if there are 2 or more :unknown literals, return :undef 
; (THIS IS BECAUSE THE SPECIFIC IDENTITIES OR INTERNAL ORDER OF MULTIPLE UNKNOWN LITERALS MUST BE IGNORED!!!)

(defun evaluate-clause (clause assignment)
  ; creating local variables unknown-count to track unknowns (initialized to 0) and unit-lit to nil (checking for unit literal)
  (let ((unknown-count 0) 
        (unit-lit nil))
    ; iteratively go through every literal in the clause from left to right
    (loop for lit across clause do
      ; call the eval-literal function with the current literal and assignment and store the result (the truth value) in res
      (let ((res (eval-literal lit assignment)))
        ; do stuff based on the value of res
        (cond
          ; if the literal's res is true
          ((eq res :true)
            ; return :sat and get out ASAP (this is the SAT short-circuit rule)
            ; (return :sat))
            (return-from evaluate-clause :sat))

          ; if the result is unknown
          ((eq res :unknown)
            ; increment the unknown-count by 1
            (incf unknown-count)
            ; update unit-lit to hold the literal, and if only one is found, you want to retain (and return) the identity of that literal
            (setf unit-lit lit)
          )
        )
      )
    )
    ; do stuff based on the value of unknown-count
    (cond
      ; if there's zero unknown literals and we got to this point, that means no :true short-circuit happened, so all the literals are known and can't break out, then the clause is unsatisfiable
      ((= unknown-count 0) :unsat)
      ; if there's only 1 unknown literal, return the identity of that literal as a unit clause
      ((= unknown-count 1) (cons :unit unit-lit))
      ; if there's 2 or more unknown literals, the clause is still undetermined, so can back out with undefined
      (t :undef)
    )
  )
)

; PROPAGATION ENGINE

; propagate (state formula)
; Input: a solver-state and a formula vector
; need to initialize a new state as a SHALLOW COPY of the input state via (copy-structure state)
; loop as long as a boolean flag changed is T. Reset changed to NIL at the start of every loop iteration
; iterate sequentially through every clause in the formula vector from index 0 to m-1
; --> compute res via (evaluate-clause clause (ss-assignment new-state))
; --> if res is :unsat, IMMEDIATELY UPDATE (ss-status new-state) to :unsat and return new-state without further looping
; if res matches (:unit . lit):
; --> increment (ss-props new-state)
; --> push lit to (ss-trail new-state)
; --> Push (cons (abs lit) (> lit 0)) to the front of (ss-assignment new-state)
; --> set changed to T
; --> BREAK OUT OF THE CLAUSE LOOP IMMEDIATELY TO RESTART SCANNING FROM CLAUSE INDEX 0

; IF: a complete pass over all clauses finishes with changed remaining NIL, return new-state completely unchanged (leaving the current status exactly as it was inherited, preventing any structural outcome erasures)


(defun propagate (state formula)
  ; new-state is a SHALLOW COPY of the input state
  (let ((new-state (copy-structure state)))
    ; keep looping until BCP reaches a fixed point where no changes are made
    (loop 
      ; loop as long as a boolean flag changed is T, and reset changed to nil at the start of the loop
      (let ((changed nil))
        ; iterate sequentially through every clause in the formula vector from index 0 to m-1
        (loop for i from 0 below (length formula) do
          ; pull the index i clause from the formula
          (let* ((clause (aref formula i))
                ; evaluate the clause with the new-state's assigned variables and store the rsult as res
                (res (evaluate-clause clause (ss-assignment new-state))
                )
              )
            ; do stuff based on the result of the evaluated current clause
            (cond
              ; if the clause is unsatisfied, a conflict has been reached
              ((eq res :unsat)
                ; set the current/new state as unsatisfied
                (setf (ss-status new-state) :unsat)
                ; return the current/new state and get out without any further looping
                (return-from propagate new-state)
              )
              ; if the result matches a unit clause 
              ((and (consp res) (eq (car res) :unit))
                ; bind forced-lit to the literal that's true
                (let ((forced-lit (cdr res)))
                  ; need to increment the solver state's propagation counter by 1
                  (incf (ss-props new-state))
                  ; add the newly forced literal to the trail (to keep track of the new variable's assignment in chronological order)
                  (push forced-lit (ss-trail new-state))
                  ; push the new variable ID and boolean value pair to the assignment list (tracking what the system did in response)
                  (push (cons (abs forced-lit) (> forced-lit 0))
                        (ss-assignment new-state)
                  )
                  ; set the changed tracking flag to true since we changed a variable's assignment
                  (setf changed t)
                  ; get out of the inner clause loop to begin scanning the clause from index 0
                  (return)
                )
              )
            )
          )
        )
        ; if a complete pass over all clauses finishes wit changed staying as NIL, return new-state unchanged (avoids any structural outcome erasures)
        (unless changed
          (return new-state)
        )
      )
    )
  )
)


; MACRO TRAJECTORY & METRIC INTERFACES

; inject-literal (state formula lit &key is-decision)
; allocates a fresh structural clone using (copy-structure state)
; --> if is-decision is true, increments ss-decisions
; --> appends lit to ss-trail, pushes its truth value to the front of ss-assignment via (push (cons (abs lit) (> lit 0)) ... ) and returns the closed state by passing it directly to propagate
; EVERY MANUAL INJECTION TRIGGERS A FULL CLOSURE OPERATION!!!

(defun inject-literal (state formula lit &key is-decision)
  ; new-state is a SHALLOW COPY of the input state
  (let ((new-state (copy-structure state)))
    ; if is-decision is passed in and its true (means its a macro decision):
    (when is-decision
      ; increments the ss-decisions (tracking the total number of MANUAL decisions/assignments made)
      (incf (ss-decisions new-state))
    )
    ; add the literal to the trail (to keep track of the new variable's assignment in chronological order)
    (push lit (ss-trail new-state))
    ; push the new variable ID and boolean value pair to the assignment list (tracking what the system did in response)
    (push (cons (abs lit) (> lit 0)) 
          (ss-assignment new-state)
    )
    ; returns the closed state by passing it directly to propagate -- EVERY MANUAL INJECTION TRIGGERS A FULL CLOSURE OPERATION!!!
    (propagate new-state formula)
  )
)


; execute-macro-sequence (state formula seq)
; process the list of literals in the injection sequence (sigma) sequentially
; before processing each entry, inspect the accumulator state
; --> if (ss-status state) matches :unsat, STOP PROCESSING IMMEDIATELY AND RETURN THE STATE
; this hard truncation defines the path-dependent stopping time T
; otherwise, recursively call inject-literal, setting is-decision to T


(defun execute-macro-sequence (state formula seq)
  ; current just points to the input state; this is the accumulator state; points to a new state after each injection
  (let ((current state))
    ; iteratively loop through seq one item at a time; did this instead of recursively to avoid a possible stack overflow problem; lit holds the current literal; if the loop finishes normally with no early exits/return, it'll return current as is. 
    (dolist (lit seq current)
      ; inspecting the accumulator state to make sure it's all fine, if the accumulator is :unsat before processing a literal, that means its a conflict, and need to stop processing IMMEDIATELY and return the current state
      (when (eq (ss-status current) :unsat)
        ; return the current conflict state
        (return current)
      )
      ; otherwise, still no problems, so pass the current state to inject-literal and the current literal and is-decision true flag, and whatever state it returns will overwrite current
      (setf current
        ; running inject-literal makes it so we don't need to create a SHALLOW COPY of the input state each time in this function
        (inject-literal current formula lit :is-decision t)
      )
    )
  )
)



; backtrack-to-ancestor (current ancestor)
; evaluates the support cardinality gap (B_c) between an experimental trajectory and its common baseline ancestor 
; this is a ONE-DIMENSIONAL REDUCTION OF STATE DIFFERENCE ONTO THE SUPPORT-SIZE AXIS!!!
; --> it does NOT measure structural assignment divergence, trajectory distance, or logical disagreement
; computation is ss-cardinality-gap = ||{vars(current)}| - |{vars(ancestor)}||

; to implement: need to extract the variable keys using (mapcar #'car ...), then filter historical duplicate entries via remove-duplicates, compute the absolute difference between the lengths of the two resulting unique lists, write that scalar directly into (ss-cardinality-gap current) and return the modified current record



(defun backtrack-to-ancestor (current ancestor)
  ; extract the variable keys from both the current and ancestor states, and remove the duplicate entries of each
  (let* ((current-vars
            (remove-duplicates (mapcar #'car (ss-assignment current)))
          )
          (ancestor-vars 
            (remove-duplicates (mapcar #'car (ss-assignment ancestor)))
          )
          ; compute the absolute difference between the current and ancestor states' assignment lists' lengths with duplicates removed and save it in gap
          (gap (abs (- (length current-vars) (length ancestor-vars)))
          )
        )
      ; write the resulting scalar into the current state's structure under the cardinality gap and return the modified current state
      (setf (ss-cardinality-gap current) gap) 
      current
  )
)