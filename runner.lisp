(load "BCP_KERNEL.lisp")

(defun parse-naive-json (str)
  (let* ((s1 (substitute #\( #\[ str))
         (s2 (substitute #\) #\] s1))
         (s3 (substitute #\Space #\, s2))
         (s4 (substitute #\Space #\: s3))
         (s5 (remove #\{ s4))
         (s6 (remove #\} s5))
         (s7 (remove #\" s6)))
    (read-from-string (concatenate 'string "(" s7 ")"))))

(defun shuffle-array (arr)
  (let ((n (length arr)))
    (loop for i from (1- n) downto 1 do
      (let* ((j (random (1+ i)))
             (temp (aref arr i)))
        (setf (aref arr i) (aref arr j))
        (setf (aref arr j) temp)))
    arr))

(defvar *global-formula* nil)
(defvar *global-watches* nil)
(defvar *stabilized-state* nil)

(defun main ()
  (loop
    (let ((input (read-line nil nil)))
      (unless input (return))
      (let* ((parsed (parse-naive-json input))
             (msg-type (getf parsed 'type)))
        (cond
          ((eq msg-type 'init)
           (let* ((context-list (getf parsed 'context))
                  (formula-list (getf parsed 'formula))
                  (m (length formula-list)))
             (setf *global-formula* (make-array m :element-type 'clause))
             (setf *max-var* 0)
             (loop for i from 0 below m do
               (let* ((clause-list (nth i formula-list))
                      (len (length clause-list))
                      (clause (make-array len :element-type 'literal :initial-contents clause-list)))
                 (dolist (lit clause-list)
                   (setf *max-var* (max *max-var* (abs lit))))
                 (setf (aref *global-formula* i) clause)))
             ;; shuffle formula database exactly once per execution to eliminate memory-layout priority bias
             (shuffle-array *global-formula*)
             ;; setup watches globally
             (setf *global-watches* (setup-watches *global-formula*))
             ;; build state
             (let ((s0 (make-solver-state))
                   (conflict nil))
               ;; 1. Hydrate s0 with context literals
               (dolist (lit context-list)
                 (let ((val (aref (ss-assignment s0) (abs lit))))
                   (when (and (> val 0) (not (= val (if (> lit 0) 1 2))))
                     (setf conflict t)))
                 (push lit (ss-trail s0))
                 (setf (aref (ss-assignment s0) (abs lit)) (if (> lit 0) 1 2)))
               (when conflict
                 (setf (ss-status s0) :unsat))
               
               ;; 2. Run a pre-flight BCP to stabilize the context
               (let ((stab (pre-flight-bcp s0 *global-formula* *global-watches*)))
                 (cond 
                   ;; Case A: Context is inherently contradictory / falsifies a clause
                   ((eq (ss-status stab) :unsat)
                    (setf *stabilized-state* nil)
                    (format t "{\"status\": \"init_conflict\", \"decisions\": 0, \"props\": 0, \"cardinality_gap\": 0}~%")
                    (finish-output))
                   ;; Case B: Context was safe, or stabilized after pulling in forced unit literals
                   (t
                    ;; CRITICAL RESET: Wipe out any metric counts accumulated during context stabilization
                    ;; so they don't pollute the downstream macro permutation tracking.
                    (setf (ss-props stab) 0)
                    (setf (ss-decisions stab) 0)
                    (setf *stabilized-state* stab)
                    (format t "{\"status\": \"initialized\"}~%")
                    (finish-output)))))))
          ((eq msg-type 'seq)
           (if (null *stabilized-state*)
               (progn
                 (format t "{\"status\": \"error\", \"message\": \"Not initialized or init_conflict\"}~%")
                 (finish-output))
               (let* ((seq-list (getf parsed 'sequence))
                      (local-f (deep-copy-formula *global-formula*))
                      (local-w (deep-copy-watches *global-watches*))
                      (result-state (execute-macro-sequence-watched *stabilized-state* local-f local-w seq-list)))
                 (setf result-state (backtrack-to-ancestor result-state *stabilized-state*))
                 (format t "{\"status\": \"~A\", \"decisions\": ~D, \"props\": ~D, \"cardinality_gap\": ~D}~%"
                         (string-downcase (symbol-name (ss-status result-state)))
                         (ss-decisions result-state)
                         (ss-props result-state)
                         (ss-cardinality-gap result-state))
                 (finish-output)))))))))

(main)
