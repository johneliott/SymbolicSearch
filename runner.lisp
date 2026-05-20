(load "bpc.lisp")

(defun parse-naive-json (str)
  (let* ((s1 (substitute #\( #\[ str))
         (s2 (substitute #\) #\] s1))
         (s3 (substitute #\Space #\, s2))
         (s4 (substitute #\Space #\: s3))
         (s5 (remove #\{ s4))
         (s6 (remove #\} s5))
         (s7 (remove #\" s6)))
    (read-from-string (concatenate 'string "(" s7 ")"))))

(defun main ()
  (loop
    (let ((input (read-line nil nil)))
      (unless input (return))
      (let* ((parsed (parse-naive-json input))
             (context-list (getf parsed 'context))
             (formula-list (getf parsed 'formula))
             (seq-list (getf parsed 'sequence))
             (m (length formula-list))
             (formula (make-array m :element-type 'clause)))
        ;; build formula array
        (loop for i from 0 below m do
          (let* ((clause-list (nth i formula-list))
                 (len (length clause-list))
                 (clause (make-array len :element-type 'literal :initial-contents clause-list)))
            (setf (aref formula i) clause)))
        ;; build state
        (let ((s0 (make-solver-state)))
          ;; 1. Hydrate s0 with context literals
          (let ((conflict nil))
            (dolist (lit context-list)
              (let ((existing (assoc (abs lit) (ss-assignment s0))))
                (when (and existing (not (eq (cdr existing) (> lit 0))))
                  (setf conflict t)))
              (push lit (ss-trail s0))
              (push (cons (abs lit) (> lit 0)) (ss-assignment s0)))
            (when conflict
              (setf (ss-status s0) :unsat)))
          
          ;; 2. Run a pre-flight BCP to stabilize the context
          (let ((stabilized-state (propagate s0 formula)))
            (cond 
              ;; Case A: Context is inherently contradictory / falsifies a clause
              ((eq (ss-status stabilized-state) :unsat)
               (format t "{\"status\": \"init_conflict\", \"decisions\": 0, \"props\": 0, \"cardinality_gap\": 0}~%")
               (finish-output))
              
              ;; Case B: Context was safe, or stabilized after pulling in forced unit literals
              (t
               ;; CRITICAL RESET: Wipe out any metric counts accumulated during context stabilization
               ;; so they don't pollute the downstream macro permutation tracking.
               (setf (ss-props stabilized-state) 0)
               (setf (ss-decisions stabilized-state) 0)
               
               ;; 3. Execute macro sequence on the now-stabilized state
               (let ((result-state (execute-macro-sequence stabilized-state formula seq-list)))
                 ;; Update the cardinality gap relative to the root ancestor stabilized-state
                 (setf result-state (backtrack-to-ancestor result-state stabilized-state))
                 ;; print json
                 (format t "{\"status\": \"~A\", \"decisions\": ~D, \"props\": ~D, \"cardinality_gap\": ~D}~%"
                         (string-downcase (symbol-name (ss-status result-state)))
                         (ss-decisions result-state)
                         (ss-props result-state)
                         (ss-cardinality-gap result-state))
                 (finish-output))))))))))

(main)
